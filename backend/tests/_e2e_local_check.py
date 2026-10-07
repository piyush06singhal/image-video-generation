"""End-to-end verification of the CinéEstate pipeline, against whichever provider is configured.

Drives the real HTTP API: project -> upload -> scene metadata -> plan -> generate
-> assemble, then probes the produced walkthrough.mp4 and reports which render engine
actually produced each clip.

Run it against any engine, e.g.:

    VIDEO_PROVIDER=kenburns     ./venv/bin/python tests/_e2e_local_check.py   # free, offline
    VIDEO_PROVIDER=json2video \
      PUBLIC_BASE_URL=https://<tunnel> ./venv/bin/python tests/_e2e_local_check.py

Underscore-prefixed so pytest does not collect it (it needs a live server).
"""
import sys
import time
from pathlib import Path

import cv2
import httpx

BASE = "http://127.0.0.1:8000/api"
TEST_IMAGES = {
    "exterior.jpg": "exterior",
    "living_room.jpg": "living_room",
    "kitchen.jpg": "kitchen",
    "bedroom.jpg": "bedroom",
}


def unwrap(resp):
    body = resp.json()
    if not body.get("success"):
        raise RuntimeError(f"API error {resp.status_code}: {body.get('error')}")
    return body["data"]


def main():
    c = httpx.Client(timeout=180.0)

    health = unwrap(c.get(f"{BASE}/health"))
    print(f"[1] health: {health}")

    proj = unwrap(c.post(f"{BASE}/projects", json={"name": "E2E Local Walkthrough"}))
    pid = proj["id"]
    print(f"[2] project: {pid}")

    files = []
    for name in TEST_IMAGES:
        p = Path("test_images") / name
        files.append(("files", (name, p.read_bytes(), "image/jpeg")))
    up = unwrap(c.post(f"{BASE}/projects/{pid}/images", files=files))
    print(f"[3] uploaded: {up['total_accepted']} accepted, {up['total_rejected']} rejected")

    for img in up["uploaded"]:
        stype = TEST_IMAGES.get(img["original_filename"])
        if stype:
            unwrap(
                c.patch(
                    f"{BASE}/projects/{pid}/images/{img['id']}/scene",
                    json={"scene_type": stype},
                )
            )
    print("[4] scene metadata assigned")

    plan = unwrap(c.post(f"{BASE}/projects/{pid}/plan/rebuild"))
    print(f"[5] plan v{plan['plan_version']} with {len(plan['scenes'])} scenes:")
    for s in plan["scenes"]:
        print(f"      {s['order']}. {s['label']:<20} motion={s['camera']['motion_type']} {s['camera']['duration_seconds']}s")

    config = unwrap(c.get(f"{BASE}/projects/{pid}/generation"))
    configured = config.get("active_provider") or "unknown"
    unwrap(c.post(f"{BASE}/projects/{pid}/generate", json={"force_regenerate": False}))
    print(f"[6] generation launched (engine: {configured})")

    deadline = time.time() + 600  # real cloud renders take ~20-30s per clip
    overview = None
    while time.time() < deadline:
        overview = unwrap(c.get(f"{BASE}/projects/{pid}/generation"))
        if overview["status"] in ("completed", "partially_completed", "failed", "paused"):
            break
        time.sleep(2)

    print(
        f"[7] generation status={overview['status']} "
        f"completed={overview['completed_scenes']}/{overview['total_scenes']} "
        f"failed={overview['failed_scenes']}"
    )
    for s in overview["scenes"]:
        clip = s.get("clip")
        info = f"{clip['width']}x{clip['height']} {clip['duration_seconds']}s" if clip else s.get("last_error")
        print(f"      {s['label']:<20} {s['status']:<10} {info}")
    providers = sorted({s["clip"]["provider"] for s in overview["scenes"] if s.get("clip")})
    print(f"      rendered by: {', '.join(providers) or 'none'}")
    fallbacks = [p for p in providers if p != configured]
    if fallbacks:
        print(f"      NOTE: {overview['completed_scenes']} clip(s) fell back to {', '.join(fallbacks)}")
    if overview["completed_scenes"] == 0:
        print("FATAL: no clips generated")
        return 1

    job = unwrap(c.post(f"{BASE}/projects/{pid}/assemble", json={}))
    print(f"[8] assembly status={job['status']} message={job.get('stage_message')}")
    meta = job.get("result")
    if not meta:
        print("FATAL: assembly produced no metadata")
        return 1

    print(
        f"[9] final video: {meta['width']}x{meta['height']} @ {meta['fps']}fps, "
        f"{meta['duration_seconds']}s, {meta['scene_count']} scenes, "
        f"{meta['file_size_bytes']} bytes"
    )

    final_path = Path("storage/projects") / pid / "final" / "walkthrough.mp4"
    assert final_path.exists(), f"final video missing at {final_path}"
    cap = cv2.VideoCapture(str(final_path))
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ok, _ = cap.read()
    cap.release()
    assert ok, "final video could not be decoded"
    print(f"[10] decoded walkthrough.mp4: {frames} frames -> {final_path}")
    print(f"\nPASS: project_id={pid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
