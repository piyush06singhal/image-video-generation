import httpx
from PIL import Image
import io
import os
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000/api"

def create_image(width, height, color, fmt="JPEG"):
    buf = io.BytesIO()
    mode = "RGB" if fmt == "JPEG" else "RGBA"
    img = Image.new(mode, (width, height), color)
    img.save(buf, format=fmt)
    return buf.getvalue()

def run_e2e():
    client = httpx.Client(timeout=10.0)
    print("--- 1. Testing Health Endpoint ---")
    h_resp = client.get(f"{BASE_URL}/health")
    assert h_resp.status_code == 200, f"Health check failed: {h_resp.text}"
    print("Health response:", h_resp.json())

    print("\n--- 2. Testing Project Creation ---")
    p_resp = client.post(f"{BASE_URL}/projects", json={"name": "Modern 3BHK Apartment"})
    assert p_resp.status_code == 201, f"Project creation failed: {p_resp.text}"
    p_data = p_resp.json()["data"]
    project_id = p_data["id"]
    print(f"Created project: {project_id} - '{p_data['name']}'")

    print("\n--- 3. Testing Real Image Uploads ---")
    img1 = create_image(1920, 1080, (200, 100, 50), "JPEG")
    img2 = create_image(1280, 720, (50, 150, 200), "PNG")
    img3 = create_image(1000, 1000, (100, 200, 100), "WEBP")

    files = [
        ("files", ("living_room.jpg", img1, "image/jpeg")),
        ("files", ("master_bedroom.png", img2, "image/png")),
        ("files", ("kitchen.webp", img3, "image/webp")),
    ]

    u_resp = client.post(f"{BASE_URL}/projects/{project_id}/images", files=files)
    assert u_resp.status_code == 201, f"Image upload failed: {u_resp.text}"
    u_data = u_resp.json()["data"]
    print(f"Uploaded {u_data['total_accepted']} images successfully.")
    for img in u_data["uploaded"]:
        print(f"  - {img['original_filename']}: {img['width']}x{img['height']} ({img['format']}), Aspect: {img['aspect_ratio']}, Hash: {img['sha256'][:12]}...")

    print("\n--- 4. Verifying Physical Storage on Disk ---")
    storage_path = Path("backend/storage/projects") / project_id
    uploads_dir = storage_path / "uploads"
    processed_dir = storage_path / "processed"
    project_json = storage_path / "project.json"

    assert project_json.exists(), "project.json missing!"
    assert uploads_dir.exists(), "uploads/ missing!"
    assert processed_dir.exists(), "processed/ missing!"
    
    upload_files = list(uploads_dir.iterdir())
    processed_files = list(processed_dir.iterdir())
    print(f"Physical original files in uploads/: {[f.name for f in upload_files]}")
    print(f"Physical thumbnails in processed/: {[f.name for f in processed_files]}")
    assert len(upload_files) == 3, f"Expected 3 original files, found {len(upload_files)}"
    assert len(processed_files) == 3, f"Expected 3 thumbnail files, found {len(processed_files)}"

    print("\n--- 5. Testing Exact Duplicate Detection ---")
    dup_files = [("files", ("living_room_duplicate.jpg", img1, "image/jpeg"))]
    dup_resp = client.post(f"{BASE_URL}/projects/{project_id}/images", files=dup_files)
    assert dup_resp.status_code == 400, f"Duplicate was not rejected: {dup_resp.text}"
    dup_json = dup_resp.json()
    assert dup_json["error"]["code"] == "DUPLICATE_IMAGE"
    print("Duplicate correctly rejected with message:", dup_json["error"]["message"])

    print("\n--- 6. Testing Image Deletion ---")
    img_to_delete = u_data["uploaded"][0]["id"]
    del_resp = client.delete(f"{BASE_URL}/projects/{project_id}/images/{img_to_delete}")
    assert del_resp.status_code == 200, f"Delete failed: {del_resp.text}"
    print(f"Deleted image {img_to_delete} successfully.")

    # Re-check physical storage
    upload_files_after = list(uploads_dir.iterdir())
    assert len(upload_files_after) == 2, f"Expected 2 original files after deletion, found {len(upload_files_after)}"
    print(f"Remaining original files: {[f.name for f in upload_files_after]}")

    print("\n--- 7. Verifying Updated Project State ---")
    p_get = client.get(f"{BASE_URL}/projects/{project_id}")
    assert p_get.status_code == 200
    p_get_data = p_get.json()["data"]
    print(f"Project status: {p_get_data['status']}, image count: {p_get_data['image_count']}")
    assert p_get_data["image_count"] == 2

    print("\n==========================================")
    print("ALL END-TO-END VALIDATION CHECKS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    run_e2e()
