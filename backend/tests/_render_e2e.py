"""Throwaway harness: drives a full render through the public HTTP API.

Run it against a live backend to produce a real artifact from the real pipeline
rather than from the internal service objects, so the verification covers the
API surface the studio actually uses.

    PYTHONPATH=. ./venv/bin/python tests/_render_e2e.py <project_id> [preset]
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("CINE_BASE", "http://127.0.0.1:8000")
KEY = os.environ.get("API_ACCESS_KEY", "")


def call(method: str, path: str, payload=None, timeout: int = 300):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json", "X-API-Key": KEY},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def wait_for_generation(project_id: str, timeout: float = 900.0):
    start = time.time()
    while time.time() - start < timeout:
        _, body = call("GET", f"/api/projects/{project_id}/generation")
        data = body.get("data") or {}
        done, total = data.get("completed_scenes", 0), data.get("total_scenes", 0)
        pending = data.get("pending_scenes", 0) + data.get("generating_scenes", 0)
        print(f"  generation: {done}/{total} done, {pending} pending", flush=True)
        if total and pending == 0:
            return data
        time.sleep(5)
    raise TimeoutError("generation did not finish")


def main():
    project_id = sys.argv[1]
    preset = sys.argv[2] if len(sys.argv) > 2 else "cinematic_luxury"
    print(f"▶ {project_id} @ preset={preset}")

    # 1. Apply the preset that carries the new production features.
    status, body = call(
        "PATCH", f"/api/projects/{project_id}/render-options",
        {"preset": preset, "options": {}},
    )
    print(f"  PATCH render-options -> {status}")
    opts = (body.get("data") or {})
    for field in (
        "depth_parallax", "motion_blur", "cinematic_bloom", "letterbox",
        "room_counter", "music_style", "resolution", "fps",
    ):
        print(f"    {field}: {opts.get(field)!r}")

    # 2. Regenerate the clips so the new renderer runs (skip when only the
    #    assembly-side options changed, since clips are unaffected by those).
    if os.environ.get("SKIP_GENERATE") == "1":
        print("  (skipping clip generation)")
    else:
        status, body = call(
            "POST", f"/api/projects/{project_id}/generate", {"force_regenerate": True}
        )
        print(f"  POST generate -> {status}")
        if status >= 400:
            print(json.dumps(body)[:600])
        wait_for_generation(project_id)

    # 3. Assemble.
    status, body = call("POST", f"/api/projects/{project_id}/assemble", {"force_reassemble": True})
    print(f"  POST assemble -> {status}")
    if status >= 400:
        print(json.dumps(body)[:900])
        return 1

    start = time.time()
    while time.time() - start < 900:
        _, res = call("GET", f"/api/projects/{project_id}/assembly")
        job = res.get("data") or {}
        stage = job.get("stage_message") or job.get("status")
        print(f"  assembly: {job.get('status')} {job.get('progress_percentage')}% — {stage}", flush=True)
        if job.get("status") in ("completed", "failed"):
            if job.get("status") == "failed":
                print("  FAILED:", job.get("error"))
                return 1
            break
        time.sleep(4)

    _, res = call("GET", f"/api/projects/{project_id}/final-video")
    meta = res.get("data") or {}
    print(
        "✔ final: {w}x{h} @{fps}fps {dur}s {size:.1f}MB audio={audio} hash={hash}".format(
            w=meta.get("width"), h=meta.get("height"), fps=meta.get("fps"),
            dur=meta.get("duration_seconds"),
            size=(meta.get("file_size_bytes") or 0) / 1e6,
            audio=meta.get("audio_codec"), hash=meta.get("render_options_hash"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
