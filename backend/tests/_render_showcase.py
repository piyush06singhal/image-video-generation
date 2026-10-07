"""Throwaway harness: drive a full cinematic render through the public HTTP API.

Underscore-prefixed so pytest ignores it. Usage:

    ./venv/bin/python tests/_render_showcase.py <project_id> <preset> '<json overrides>'
"""

import json
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"


def load_key() -> str:
    env = Path(__file__).resolve().parent.parent / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("API_ACCESS_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    project_id, preset = sys.argv[1], sys.argv[2]
    overrides = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

    client = httpx.Client(base_url=BASE, headers={"X-API-Key": load_key()}, timeout=600.0)

    patched = client.patch(
        f"/api/projects/{project_id}/render-options",
        json={"preset": preset, "options": overrides},
    )
    patched.raise_for_status()
    options = patched.json()["data"]
    print(f"options -> preset={options['preset']} {options['aspect_ratio']} {options['resolution']} "
          f"{options['fps']}fps dur={options['scene_duration_seconds']}s grade={options['color_grade']} "
          f"transition={options['transition_style']} music={options['music_enabled']}"
          f"/{options['music_style']} labels={options['room_labels_enabled']} "
          f"intro={options['intro_title_enabled']} outro={options['outro_enabled']} "
          f"motion={options['motion_intensity']} variety={options['camera_variety']}")

    started = client.post(
        f"/api/projects/{project_id}/generate", json={"force_regenerate": True}
    )
    started.raise_for_status()
    print(f"generation queued: {started.json()['data']['total_scenes']} scenes")

    deadline = time.time() + 600
    while time.time() < deadline:
        overview = client.get(f"/api/projects/{project_id}/generation").json()["data"]
        done, total = overview["completed_scenes"], overview["total_scenes"]
        print(f"  clips {done}/{total} status={overview['status']} engine={overview['active_provider']}")
        if done == total and total > 0:
            break
        if overview["status"] in ("failed", "partially_completed") and overview["generating_scenes"] == 0:
            print("generation stalled:", json.dumps(overview, indent=2)[:1500])
            return 1
        time.sleep(4)
    else:
        print("timed out waiting for clips")
        return 1

    clips_outdated = overview.get("clips_outdated")
    print(f"clips_outdated={clips_outdated}")

    t0 = time.time()
    assembled = client.post(
        f"/api/projects/{project_id}/assemble", json={"force_reassemble": True}
    )
    assembled.raise_for_status()
    job = assembled.json()["data"]
    result = job["result"]
    print(
        f"assembled in {time.time() - t0:.1f}s: {result['width']}x{result['height']} "
        f"{result['fps']}fps {result['duration_seconds']}s scenes={result['scene_count']} "
        f"audio={result['audio_codec']} render_hash={result['render_options_hash']}"
    )
    print("video_url:", result["video_url"])

    after = client.get(f"/api/projects/{project_id}/final-video").json()["data"]
    print(f"is_outdated_after_assemble={after['is_outdated']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
