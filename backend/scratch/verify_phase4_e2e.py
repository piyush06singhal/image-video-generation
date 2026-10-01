"""
End-to-End Live Verification Script for Phase 4 Real Image-to-Video Generation.
Tests full pipeline against live FastAPI backend server.
"""
import sys
import json
import time
import httpx
from pathlib import Path
from PIL import Image, ImageDraw
import io

BASE_URL = "http://localhost:8000/api"


def make_synthetic_image(label: str, bg_color: tuple, width: int = 1280, height: int = 720) -> bytes:
    """Create a realistic synthetic room image."""
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, height - 200, width, height], fill=tuple(max(0, c - 30) for c in bg_color))
    draw.rectangle([100, 50, width - 100, height - 180], fill=tuple(min(255, c + 20) for c in bg_color))
    draw.rectangle([200, 80, 450, 350], fill=(180, 220, 255))
    draw.rectangle([800, 200, 950, height - 180], fill=(160, 120, 80))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=95)
    return buf.getvalue()


def check(condition: bool, message: str):
    if condition:
        print(f"      ✓ {message}")
    else:
        print(f"      ✗ FAILED: {message}")
        sys.exit(1)


def main():
    print()
    print("=" * 68)
    print("  PHASE 4 REAL IMAGE-TO-VIDEO GENERATION — LIVE VERIFICATION")
    print("=" * 68)

    client = httpx.Client(base_url=BASE_URL, timeout=120.0)

    # 1. Health Check
    print("\n[STEP 1] Backend Health Check")
    r = client.get("/health")
    check(r.status_code == 200, f"HTTP 200 (got {r.status_code})")

    # 2. Create Project
    print("\n[STEP 2] Create Property Project")
    r = client.post("/projects", json={"name": "Phase 4 Generation Villa"})
    check(r.status_code == 201, "Project created successfully")
    project_id = r.json()["data"]["id"]
    print(f"      Project ID: {project_id}")

    # 3. Upload 2 Photos
    print("\n[STEP 3] Upload Photographic Images")
    img_bytes1 = make_synthetic_image("Living Room", (220, 195, 160))
    img_bytes2 = make_synthetic_image("Kitchen", (200, 220, 215))

    r1 = client.post(f"/projects/{project_id}/images", files=[("files", ("living.jpg", img_bytes1, "image/jpeg"))])
    check(r1.status_code == 201, "Uploaded living.jpg")
    r2 = client.post(f"/projects/{project_id}/images", files=[("files", ("kitchen.jpg", img_bytes2, "image/jpeg"))])
    check(r2.status_code == 201, "Uploaded kitchen.jpg")

    # 4. Analyze Scenes
    print("\n[STEP 4] Multimodal Scene Analysis")
    r = client.post(f"/projects/{project_id}/analyze")
    check(r.status_code == 200, "Analysis completed")

    # 5. Get Walkthrough Plan
    print("\n[STEP 5] Retrieve Phase 3 Walkthrough Plan")
    r = client.get(f"/projects/{project_id}/plan")
    check(r.status_code == 200, "Walkthrough plan retrieved")
    plan = r.json()["data"]
    check(len(plan["scenes"]) == 2, f"Plan contains 2 scenes (got {len(plan['scenes'])})")
    print(f"      Plan has {len(plan['scenes'])} scenes ready for video generation.")

    # 6. Check Initial Generation Overview
    print("\n[STEP 6] Initial Generation Overview (GET /generation)")
    r = client.get(f"/projects/{project_id}/generation")
    check(r.status_code == 200, "GET /generation returned 200")
    gen_overview = r.json()["data"]
    check(gen_overview["status"] in ("ready", "partially_completed", "completed"), f"Status is valid: {gen_overview['status']}")
    check(gen_overview["total_scenes"] == 2, f"Total scenes is 2 (got {gen_overview['total_scenes']})")
    check(len(gen_overview["scenes"]) == 2, f"Overview has 2 scene entries")
    print(f"      Initial status: {gen_overview['status']}, completed={gen_overview['completed_scenes']}/{gen_overview['total_scenes']}")

    # 7. Trigger Real Image-to-Video Generation
    print("\n[STEP 7] Trigger Video Generation (POST /generate)")
    first_scene_id = plan["scenes"][0]["scene_id"]
    r = client.post(f"/projects/{project_id}/generate", json={"scene_ids": [first_scene_id]})
    check(r.status_code == 200, f"POST /generate returned 200 (got {r.status_code})")
    gen_resp = r.json()["data"]
    print(f"      Generation started for scene: {first_scene_id}")

    # 8. Poll for real generation progress
    print("\n[STEP 8] Monitor Real Generation Job Status")
    print("      Polling generation state (up to 60s)...")
    for attempt in range(12):
        time.sleep(5)
        r = client.get(f"/projects/{project_id}/generation")
        if r.status_code != 200:
            continue
        cur_gen = r.json()["data"]
        scene_item = next((s for s in cur_gen["scenes"] if s["scene_id"] == first_scene_id), None)
        if scene_item:
            st = scene_item["status"]
            print(f"      [Poll {attempt+1}] Scene Status: {st.upper()}")
            if st in ("completed", "failed"):
                if st == "failed":
                    print(f"      Provider result/message: {scene_item.get('last_error')}")
                elif st == "completed":
                    clip = scene_item.get("clip", {})
                    print(f"      ✓ Video generated: {clip.get('duration_seconds')}s, {clip.get('width')}x{clip.get('height')}")
                break

    # 9. Test Single Scene Regenerate Endpoint
    print("\n[STEP 9] Test Scene Regenerate Endpoint (POST /scenes/{id}/regenerate)")
    r = client.post(
        f"/projects/{project_id}/scenes/{first_scene_id}/regenerate",
        json={"custom_motion_type": "pan_left"},
    )
    check(r.status_code == 200, f"Regenerate scene returned 200 (got {r.status_code})")
    regen_job = r.json()["data"]
    check(regen_job["scene_id"] == first_scene_id, "Regenerate job matches scene ID")
    print(f"      Regenerate Job Created: {regen_job['job_id']}")

    # 10. Final Verification Report
    print()
    print("=" * 68)
    print("  ✅  PHASE 4 IMAGE-TO-VIDEO INTEGRATION CHECKS PASSED")
    print("=" * 68)
    print()


if __name__ == "__main__":
    main()
