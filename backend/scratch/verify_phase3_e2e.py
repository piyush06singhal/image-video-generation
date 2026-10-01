"""
End-to-End Live Verification Script for Phase 3 Walkthrough Planner.
Tests with synthetic fixture images against the live FastAPI server.
"""
import sys
import json
import httpx
from pathlib import Path
from PIL import Image, ImageDraw
import io

BASE_URL = "http://localhost:8000/api"
TEST_IMG_DIR = Path("tests/fixtures/real_images")


def make_synthetic_image(label: str, bg_color: tuple, width: int = 1280, height: int = 720) -> bytes:
    """Create a realistic-looking synthetic room image."""
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    # Floor
    draw.rectangle([0, height - 200, width, height], fill=tuple(max(0, c - 30) for c in bg_color))
    # Back wall with lighter shade
    draw.rectangle([100, 50, width - 100, height - 180], fill=tuple(min(255, c + 20) for c in bg_color))
    # Window
    draw.rectangle([200, 80, 450, 350], fill=(180, 220, 255))
    draw.rectangle([215, 95, 435, 335], fill=(200, 235, 255))
    # Door
    draw.rectangle([800, 200, 950, height - 180], fill=(160, 120, 80))
    draw.rectangle([810, 210, 940, height - 190], fill=(140, 100, 70))
    # Simple label
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
    print("=" * 65)
    print("  PHASE 3 WALKTHROUGH PLANNER — LIVE END-TO-END VERIFICATION")
    print("=" * 65)

    client = httpx.Client(base_url=BASE_URL, timeout=60.0)

    # ──────────────────────────────────────────────────────────────
    # 1. Health Check
    # ──────────────────────────────────────────────────────────────
    print("\n[STEP 1] Backend Health Check")
    r = client.get("/health")
    check(r.status_code == 200, f"HTTP 200 (got {r.status_code})")
    print(f"      {r.json()}")

    # ──────────────────────────────────────────────────────────────
    # 2. Create Project
    # ──────────────────────────────────────────────────────────────
    print("\n[STEP 2] Create Project")
    r = client.post("/projects", json={
        "name": "Phase 3 E2E Villa",
        "description": "Automated Phase 3 walkthrough planner verification"
    })
    check(r.status_code == 201, f"Project creation returned 201 (got {r.status_code})")
    project_id = r.json()["data"]["id"]
    print(f"      Project ID: {project_id}")

    # ──────────────────────────────────────────────────────────────
    # 3. Upload 4 Fixture Images (different room types)
    # ──────────────────────────────────────────────────────────────
    print("\n[STEP 3] Upload Fixture Images")
    rooms = [
        ("exterior.jpg", (120, 180, 230)),
        ("living_room.jpg", (220, 195, 160)),
        ("kitchen.jpg", (200, 220, 215)),
        ("bedroom.jpg", (190, 170, 200)),
    ]

    uploaded_images = []
    for fname, color in rooms:
        img_bytes = make_synthetic_image(fname.replace('_', ' ').replace('.jpg', ''), color)
        # Backend expects field name "files" (plural)
        files = [("files", (fname, img_bytes, "image/jpeg"))]
        r = client.post(f"/projects/{project_id}/images", files=files)
        check(r.status_code == 201, f"Upload {fname} returned 201 (got {r.status_code}): {r.text[:200]}")
        resp_data = r.json()["data"]
        # Response may be a dict with "uploaded" list or a single image
        if "uploaded" in resp_data:
            img_data = resp_data["uploaded"][0]
        else:
            img_data = resp_data
        uploaded_images.append(img_data)
        print(f"      → {fname}: ID={img_data['id'][:12]}...")

    print(f"      {len(uploaded_images)} images uploaded.")

    # ──────────────────────────────────────────────────────────────
    # 4. Scene Analysis (uses Gemini Vision)
    # ──────────────────────────────────────────────────────────────
    print("\n[STEP 4] Scene Analysis (Gemini Vision API)")
    print("      Running analysis — this may take 10–30 seconds...")
    r = client.post(f"/projects/{project_id}/analyze", timeout=120.0)
    check(r.status_code == 200, f"Analyze returned 200 (got {r.status_code})")
    project_after = r.json()["data"]
    images_meta = project_after.get("images", [])
    analyzed_count = sum(1 for img in images_meta if img.get("scene_type") and img.get("scene_type") != "unknown")
    print(f"      Analyzed images count: {len(images_meta)}")
    for img in images_meta:
        conf = img.get("confidence") or 0.0
        print(f"      → {img.get('original_filename', '?')}: type={img.get('scene_type')}, conf={conf:.2f}")

    # ──────────────────────────────────────────────────────────────
    # 5. GET Plan (auto-generates baseline if none exists)
    # ──────────────────────────────────────────────────────────────
    print("\n[STEP 5] Get / Auto-Generate Walkthrough Plan")
    r = client.get(f"/projects/{project_id}/plan")
    check(r.status_code == 200, f"GET /plan returned 200 (got {r.status_code})")
    plan = r.json()["data"]

    print(f"      Plan ID: {plan.get('plan_id', 'N/A')}")
    print(f"      Plan Version: {plan['plan_version']}, Source: {plan['source']}")
    print(f"      Total Scenes in Plan: {len(plan['scenes'])}")

    # KEY ASSERTION: No hallucinated rooms
    planned_img_ids = {s["image_id"] for s in plan["scenes"]}
    uploaded_img_ids = {img["id"] for img in uploaded_images}
    check(
        planned_img_ids == uploaded_img_ids,
        "Zero hallucinated rooms: planned images match uploaded images exactly"
    )
    check(len(plan["scenes"]) == 4, f"Exactly 4 scenes (got {len(plan['scenes'])})")
    check(plan["plan_version"] == 1, f"Plan Version is 1 (got {plan['plan_version']})")
    check(plan["source"] == "ai", f"Source is 'ai' (got {plan['source']})")

    print()
    print("      ── Ordered Scene Plan ─────────────────────────────────")
    for s in sorted(plan["scenes"], key=lambda x: x["order"]):
        print(f"      [{s['order']:02d}] {s['label']} ({s['scene_type']})")
        cam = s.get("camera", {})
        print(f"           Motion: {cam.get('motion_type', 'N/A')}")
        print(f"           Prompt: {str(cam.get('prompt',''))[:70]}...")
        print(f"           Constraints: {len(cam.get('constraints', []))} safety rules")
        if s.get("transition_to_next"):
            t = s["transition_to_next"]
            print(f"           → Transition to next: {t['type']}")
    print("      ────────────────────────────────────────────────────────")

    # ──────────────────────────────────────────────────────────────
    # 6. User Manual Reorder (PUT /plan)
    # ──────────────────────────────────────────────────────────────
    print("\n[STEP 6] User Manual Reorder (PUT /plan)")
    scenes_reversed = sorted(plan["scenes"], key=lambda x: x["order"], reverse=True)
    updated_scenes = []
    for new_order, scene in enumerate(scenes_reversed, start=1):
        updated_scenes.append({
            "scene_id": scene["scene_id"],
            "order": new_order,
            "label": f"User-{scene['label']}",
            "motion_type": scene.get("camera", {}).get("motion_type"),
            "camera_prompt": scene.get("camera", {}).get("prompt"),
            "user_confirmed": True,
        })

    r = client.put(f"/projects/{project_id}/plan", json={"scenes": updated_scenes, "removed_scene_ids": []})
    check(r.status_code == 200, f"PUT /plan returned 200 (got {r.status_code})")
    updated_plan = r.json()["data"]
    check(updated_plan["plan_version"] == 2, f"Plan Version incremented to 2 (got {updated_plan['plan_version']})")
    check(updated_plan["source"] == "user", f"Source is 'user' (got {updated_plan['source']})")
    check(
        updated_plan["scenes"][0]["label"].startswith("User-"),
        "Custom label preserved"
    )
    print(f"      Plan now at version {updated_plan['plan_version']} with source '{updated_plan['source']}'.")

    # ──────────────────────────────────────────────────────────────
    # 7. Persistence Check (GET plan again)
    # ──────────────────────────────────────────────────────────────
    print("\n[STEP 7] Persistence Check (GET /plan after save)")
    r = client.get(f"/projects/{project_id}/plan")
    check(r.status_code == 200, "GET /plan returned 200")
    persisted_plan = r.json()["data"]
    check(persisted_plan["plan_version"] == 2, f"Persisted plan version is 2 (got {persisted_plan['plan_version']})")
    check(persisted_plan["source"] == "user", f"Persisted source is 'user' (got {persisted_plan['source']})")
    check(
        persisted_plan["scenes"][0]["label"].startswith("User-"),
        "Custom label persisted through GET"
    )
    print("      Plan correctly persisted across GET requests.")

    # ──────────────────────────────────────────────────────────────
    # 8. Rebuild AI Plan (POST /plan/rebuild)
    # ──────────────────────────────────────────────────────────────
    print("\n[STEP 8] Rebuild AI Plan (POST /plan/rebuild)")
    r = client.post(f"/projects/{project_id}/plan/rebuild")
    check(r.status_code == 200, f"POST /plan/rebuild returned 200 (got {r.status_code})")
    rebuilt_plan = r.json()["data"]
    check(rebuilt_plan["plan_version"] == 3, f"Plan version incremented to 3 (got {rebuilt_plan['plan_version']})")
    check(rebuilt_plan["source"] == "ai", f"Source reset to 'ai' (got {rebuilt_plan['source']})")

    # Confirm still no hallucinated rooms after rebuild
    rebuilt_img_ids = {s["image_id"] for s in rebuilt_plan["scenes"]}
    check(
        rebuilt_img_ids == uploaded_img_ids,
        "No hallucinated rooms after rebuild"
    )
    print(f"      Rebuilt plan: plan_version={rebuilt_plan['plan_version']}, source='{rebuilt_plan['source']}'")

    # ──────────────────────────────────────────────────────────────
    # 9. Validate Rejection of Invalid Plan (duplicates / unknown scenes)
    # ──────────────────────────────────────────────────────────────
    print("\n[STEP 9] Validation — Reject Duplicate Scene IDs")
    first_scene = rebuilt_plan["scenes"][0]
    bad_scenes = [
        {
            "scene_id": first_scene["scene_id"],
            "order": 1,
            "label": "Duplicate Scene",
        },
        {
            "scene_id": first_scene["scene_id"],  # DUPLICATE
            "order": 2,
            "label": "Duplicate Scene Again",
        },
    ]
    r = client.put(f"/projects/{project_id}/plan", json={"scenes": bad_scenes})
    check(r.status_code == 422 or r.status_code == 400, f"Duplicate scenes rejected with 4xx (got {r.status_code})")
    print(f"      Correctly rejected: {r.json().get('error', {}).get('message', r.text[:100])}")

    # ──────────────────────────────────────────────────────────────
    # 10. 3-Room Subset Test: No Extra Rooms Added
    # ──────────────────────────────────────────────────────────────
    print("\n[STEP 10] 3-Room Project: No Hallucinated Rooms Test")
    r2 = client.post("/projects", json={"name": "Tiny 3-Room E2E Test"})
    check(r2.status_code == 201, "Created 3-room test project")
    pid2 = r2.json()["data"]["id"]

    three_rooms = [
        ("kitchen2.jpg", (200, 220, 215)),
        ("living2.jpg", (220, 195, 160)),
        ("bedroom2.jpg", (190, 170, 200)),
    ]
    uploaded2 = []
    for fname, color in three_rooms:
        img_bytes = make_synthetic_image(fname, color)
        files = [("files", (fname, img_bytes, "image/jpeg"))]
        r3 = client.post(f"/projects/{pid2}/images", files=files)
        check(r3.status_code == 201, f"Upload {fname} (got {r3.status_code}): {r3.text[:100]}")
        resp3 = r3.json()["data"]
        img3 = resp3["uploaded"][0] if "uploaded" in resp3 else resp3
        uploaded2.append(img3)

    print("      Running analysis on 3-room project...")
    r4 = client.post(f"/projects/{pid2}/analyze", timeout=120.0)
    check(r4.status_code == 200, "Analysis OK")

    r5 = client.get(f"/projects/{pid2}/plan")
    check(r5.status_code == 200, "GET plan OK")
    plan2 = r5.json()["data"]
    check(len(plan2["scenes"]) == 3, f"Exactly 3 scenes in plan (got {len(plan2['scenes'])})")
    ids2 = {s["image_id"] for s in plan2["scenes"]}
    uploaded_ids2 = {img["id"] for img in uploaded2}
    check(ids2 == uploaded_ids2, "3-room plan contains exactly the 3 uploaded images")
    print(f"      3-room plan scenes: {[s['scene_type'] for s in plan2['scenes']]}")

    # ──────────────────────────────────────────────────────────────
    # FINAL REPORT
    # ──────────────────────────────────────────────────────────────
    print()
    print("=" * 65)
    print("  ✅  ALL PHASE 3 END-TO-END CHECKS PASSED")
    print("=" * 65)
    print()
    print("Sample GenerationPlan (Phase 4 Input Contract):")
    print("-" * 65)
    print(json.dumps({
        "project_id": project_id,
        "plan_version": rebuilt_plan["plan_version"],
        "source": rebuilt_plan["source"],
        "scenes": rebuilt_plan["scenes"][:2]  # show first 2 for brevity
    }, indent=2))
    print("  ... (remaining scenes omitted for brevity)")


if __name__ == "__main__":
    main()
