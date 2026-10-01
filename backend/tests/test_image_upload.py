import io
from tests.helpers import create_test_image_bytes
from app.services.project_service import project_service


def test_upload_valid_image(client):
    # 1. Create project
    proj_resp = client.post("/api/projects", json={"name": "Seaside Condo"})
    project_id = proj_resp.json()["data"]["id"]

    # 2. Upload valid image
    img_bytes = create_test_image_bytes(width=1920, height=1080, img_format="JPEG")
    files = [("files", ("living-room.jpg", img_bytes, "image/jpeg"))]

    upload_resp = client.post(f"/api/projects/{project_id}/images", files=files)
    assert upload_resp.status_code == 201
    json_data = upload_resp.json()
    assert json_data["success"] is True
    data = json_data["data"]
    assert data["total_accepted"] == 1
    assert data["total_rejected"] == 0
    assert len(data["uploaded"]) == 1

    img_meta = data["uploaded"][0]
    assert img_meta["original_filename"] == "living-room.jpg"
    assert img_meta["width"] == 1920
    assert img_meta["height"] == 1080
    assert img_meta["format"] == "JPEG"
    assert img_meta["aspect_ratio"] == 1.7778
    assert img_meta["status"] == "validated"
    assert "sha256" in img_meta

    # Verify physical file existence in backend storage
    project_dir = project_service.storage.get_project_dir(project_id)
    upload_file_path = project_service.storage.get_project_uploads_dir(project_id) / img_meta["filename"]
    thumb_file_path = project_service.storage.get_project_processed_dir(project_id) / f"thumb_{img_meta['id']}.jpg"

    assert upload_file_path.exists()
    assert thumb_file_path.exists()

    # Verify project status updated
    get_proj = client.get(f"/api/projects/{project_id}")
    assert get_proj.json()["data"]["status"] == "validated"
    assert get_proj.json()["data"]["image_count"] == 1


def test_upload_multiple_valid_images(client):
    proj_resp = client.post("/api/projects", json={"name": "Multi-Room Villa"})
    project_id = proj_resp.json()["data"]["id"]

    img1 = create_test_image_bytes(width=1024, height=768, img_format="JPEG", color=(255, 0, 0))
    img2 = create_test_image_bytes(width=1280, height=720, img_format="PNG", color=(0, 255, 0))
    img3 = create_test_image_bytes(width=800, height=800, img_format="WEBP", color=(0, 0, 255))

    files = [
        ("files", ("room1.jpg", img1, "image/jpeg")),
        ("files", ("room2.png", img2, "image/png")),
        ("files", ("room3.webp", img3, "image/webp")),
    ]

    upload_resp = client.post(f"/api/projects/{project_id}/images", files=files)
    assert upload_resp.status_code == 201
    data = upload_resp.json()["data"]
    assert data["total_received"] == 3
    assert data["total_accepted"] == 3
    assert data["total_rejected"] == 0


def test_upload_invalid_format_rejected(client):
    proj_resp = client.post("/api/projects", json={"name": "Format Test"})
    project_id = proj_resp.json()["data"]["id"]

    text_bytes = b"This is just a text file, not an image."
    files = [("files", ("document.txt", text_bytes, "text/plain"))]

    upload_resp = client.post(f"/api/projects/{project_id}/images", files=files)
    assert upload_resp.status_code in [400, 415]
    json_data = upload_resp.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] in ["INVALID_IMAGE_FORMAT", "IMAGE_CORRUPTED"]


def test_upload_oversized_file_rejected(client):
    proj_resp = client.post("/api/projects", json={"name": "Size Test"})
    project_id = proj_resp.json()["data"]["id"]

    # 21 MB dummy bytes
    large_bytes = b"0" * (21 * 1024 * 1024)
    files = [("files", ("huge.jpg", large_bytes, "image/jpeg"))]

    upload_resp = client.post(f"/api/projects/{project_id}/images", files=files)
    assert upload_resp.status_code == 413
    json_data = upload_resp.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "IMAGE_TOO_LARGE"


def test_upload_undersized_image_rejected(client):
    proj_resp = client.post("/api/projects", json={"name": "Dimension Test"})
    project_id = proj_resp.json()["data"]["id"]

    small_bytes = create_test_image_bytes(width=200, height=200)
    files = [("files", ("tiny.jpg", small_bytes, "image/jpeg"))]

    upload_resp = client.post(f"/api/projects/{project_id}/images", files=files)
    assert upload_resp.status_code == 400
    json_data = upload_resp.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "IMAGE_TOO_SMALL"


def test_duplicate_image_detection(client):
    proj_resp = client.post("/api/projects", json={"name": "Duplicate Test"})
    project_id = proj_resp.json()["data"]["id"]

    img_bytes = create_test_image_bytes(width=1024, height=768, img_format="JPEG", color=(120, 130, 140))

    # First upload -> Success
    files1 = [("files", ("kitchen.jpg", img_bytes, "image/jpeg"))]
    resp1 = client.post(f"/api/projects/{project_id}/images", files=files1)
    assert resp1.status_code == 201

    # Second upload with identical bytes (even if filename differs) -> Rejected
    files2 = [("files", ("kitchen_copy.jpg", img_bytes, "image/jpeg"))]
    resp2 = client.post(f"/api/projects/{project_id}/images", files=files2)
    assert resp2.status_code == 400
    json_data = resp2.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "DUPLICATE_IMAGE"
    assert "already been uploaded" in json_data["error"]["message"].lower()


def test_delete_image_success(client):
    proj_resp = client.post("/api/projects", json={"name": "Delete Test"})
    project_id = proj_resp.json()["data"]["id"]

    img_bytes = create_test_image_bytes(width=800, height=600)
    files = [("files", ("bathroom.jpg", img_bytes, "image/jpeg"))]
    upload_resp = client.post(f"/api/projects/{project_id}/images", files=files)
    image_id = upload_resp.json()["data"]["uploaded"][0]["id"]
    stored_filename = upload_resp.json()["data"]["uploaded"][0]["filename"]

    # Check file exists on disk
    upload_path = project_service.storage.get_project_uploads_dir(project_id) / stored_filename
    assert upload_path.exists()

    # Delete image
    del_resp = client.delete(f"/api/projects/{project_id}/images/{image_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Check file is removed from disk
    assert not upload_path.exists()

    # Check project image count is 0
    get_proj = client.get(f"/api/projects/{project_id}")
    assert get_proj.json()["data"]["image_count"] == 0


def test_delete_nonexistent_image_returns_404(client):
    proj_resp = client.post("/api/projects", json={"name": "Delete 404 Test"})
    project_id = proj_resp.json()["data"]["id"]

    del_resp = client.delete(f"/api/projects/{project_id}/images/img_non_existent")
    assert del_resp.status_code == 404
    assert del_resp.json()["error"]["code"] == "IMAGE_NOT_FOUND"


def test_serve_original_and_thumbnail_files(client):
    proj_resp = client.post("/api/projects", json={"name": "Serve Files Test"})
    project_id = proj_resp.json()["data"]["id"]

    img_bytes = create_test_image_bytes(width=1000, height=800)
    files = [("files", ("hallway.jpg", img_bytes, "image/jpeg"))]
    upload_resp = client.post(f"/api/projects/{project_id}/images", files=files)
    image_id = upload_resp.json()["data"]["uploaded"][0]["id"]

    # Request original file
    orig_resp = client.get(f"/api/projects/{project_id}/images/{image_id}/file")
    assert orig_resp.status_code == 200
    assert len(orig_resp.content) == len(img_bytes)

    # Request thumbnail file
    thumb_resp = client.get(f"/api/projects/{project_id}/images/{image_id}/thumbnail")
    assert thumb_resp.status_code == 200
    assert len(thumb_resp.content) > 0
