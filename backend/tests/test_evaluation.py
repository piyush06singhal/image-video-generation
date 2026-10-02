import io
import pytest
from PIL import Image

from app.schemas.project import ProjectCreate
from app.services.project_service import project_service


def create_mock_image_bytes(width: int = 1280, height: int = 720, format_name: str = "JPEG") -> bytes:
    img = Image.new("RGB", (width, height), color=(180, 140, 90))
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


def test_panoramic_image_detection_and_classification(client):
    """
    Tests automated detection of 2:1 equirectangular panoramic images vs standard perspective images.
    """
    project = project_service.create_project(ProjectCreate(name="Panorama Test Villa"))
    pid = project.id

    # 1. Upload a normal 16:9 perspective image
    normal_bytes = create_mock_image_bytes(width=1920, height=1080)
    # 2. Upload a genuine 2:1 equirectangular panorama
    pano_bytes = create_mock_image_bytes(width=2048, height=1024)

    res = client.post(
        f"/api/projects/{pid}/images",
        files=[
            ("files", ("living_room.jpg", normal_bytes, "image/jpeg")),
            ("files", ("360_foyer.jpg", pano_bytes, "image/jpeg")),
        ],
    )
    assert res.status_code == 201
    images = res.json()["data"]["uploaded"]
    assert len(images) == 2

    normal_img = next(img for img in images if img["original_filename"] == "living_room.jpg")
    pano_img = next(img for img in images if img["original_filename"] == "360_foyer.jpg")

    # Verify normal image is NOT falsely flagged as panorama
    assert normal_img["is_panoramic"] is False
    assert normal_img["is_panoramic_detected"] is False
    assert normal_img["panoramic_type"] == "wide"

    # Verify 2:1 image is accurately detected as equirectangular panorama
    assert pano_img["is_panoramic"] is True
    assert pano_img["is_panoramic_detected"] is True
    assert pano_img["panoramic_type"] == "equirectangular"

    # 3. Test manual toggle of panorama classification via API
    patch_res = client.patch(
        f"/api/projects/{pid}/images/{normal_img['id']}/panorama",
        json={"is_panoramic": True, "panoramic_type": "equirectangular"},
    )
    assert patch_res.status_code == 200
    updated_normal = patch_res.json()["data"]
    assert updated_normal["is_panoramic"] is True
    assert updated_normal["panoramic_type"] == "equirectangular"


def test_evaluation_validation_and_scoring(client):
    """
    Tests evaluation submission, 1-5 validation bounds, and mathematical average computation.
    """
    project = project_service.create_project(ProjectCreate(name="Evaluation Property"))
    pid = project.id

    # 1. Invalid evaluation score (> 5) should fail validation
    invalid_res = client.post(
        f"/api/projects/{pid}/evaluations",
        json={
            "visual_quality": 6,  # Out of bounds
            "property_consistency": 4,
            "scene_ordering": 5,
            "motion_quality": 4,
            "temporal_stability": 3,
            "walkthrough_usefulness": 5,
            "comments": "Too high score",
        },
    )
    assert invalid_res.status_code == 422

    # 2. Valid evaluation submission 1
    eval1_res = client.post(
        f"/api/projects/{pid}/evaluations",
        json={
            "visual_quality": 4,
            "property_consistency": 4,
            "scene_ordering": 5,
            "motion_quality": 4,
            "temporal_stability": 4,
            "walkthrough_usefulness": 5,
            "comments": "Great camera paths and smooth transitions.",
            "reviewer_name": "Lead Architect",
        },
    )
    assert eval1_res.status_code == 201
    eval1 = eval1_res.json()["data"]
    assert eval1["visual_quality"] == 4
    assert eval1["reviewer_name"] == "Lead Architect"

    # 3. Valid evaluation submission 2
    eval2_res = client.post(
        f"/api/projects/{pid}/evaluations",
        json={
            "visual_quality": 5,
            "property_consistency": 5,
            "scene_ordering": 4,
            "motion_quality": 5,
            "temporal_stability": 4,
            "walkthrough_usefulness": 4,
            "comments": "Impressive spatial continuity.",
            "reviewer_name": "Senior Broker",
        },
    )
    assert eval2_res.status_code == 201

    # 4. Fetch summary and verify real arithmetic averages
    summary_res = client.get(f"/api/projects/{pid}/evaluations")
    assert summary_res.status_code == 200
    summary = summary_res.json()["data"]

    assert summary["total_evaluations"] == 2
    assert summary["average_visual_quality"] == 4.5  # (4 + 5) / 2
    assert summary["average_property_consistency"] == 4.5
    assert summary["average_scene_ordering"] == 4.5
    assert summary["average_motion_quality"] == 4.5
    assert summary["average_temporal_stability"] == 4.0
    assert summary["average_walkthrough_usefulness"] == 4.5
    assert summary["overall_average"] == 4.42


def test_scene_review_flags(client):
    """
    Tests submitting and updating reviewer flags for individual scenes.
    """
    project = project_service.create_project(ProjectCreate(name="Scene Review Property"))
    pid = project.id

    # 1. Submit review flag for scene_01
    rev1 = client.post(
        f"/api/projects/{pid}/scene-reviews",
        json={
            "scene_id": "scene_01",
            "status": "acceptable",
            "flags": [],
            "notes": "Sharp entrance lighting and clear doorway path.",
        },
    )
    assert rev1.status_code == 200
    data1 = rev1.json()["data"]
    assert data1["scene_id"] == "scene_01"
    assert data1["status"] == "acceptable"

    # 2. Submit review flag for scene_02 with flags
    rev2 = client.post(
        f"/api/projects/{pid}/scene-reviews",
        json={
            "scene_id": "scene_02",
            "status": "needs_review",
            "flags": ["lighting_drift", "unnatural_motion"],
            "notes": "Slight shadow flickering near dining chandelier.",
        },
    )
    assert rev2.status_code == 200
    data2 = rev2.json()["data"]
    assert data2["status"] == "needs_review"
    assert "lighting_drift" in data2["flags"]

    # 3. Retrieve all reviews
    list_res = client.get(f"/api/projects/{pid}/scene-reviews")
    assert list_res.status_code == 200
    reviews = list_res.json()["data"]
    assert len(reviews) == 2


def test_technical_report_generation(client):
    """
    Tests generation of structured JSON technical report and formatted plain-text report.
    """
    project = project_service.create_project(ProjectCreate(name="Report Architecture Penthouse"))
    pid = project.id

    # Upload images
    img_bytes = create_mock_image_bytes(width=1920, height=1080)
    client.post(
        f"/api/projects/{pid}/images",
        files=[("files", ("penthouse_living.jpg", img_bytes, "image/jpeg"))],
    )

    # Submit an evaluation
    client.post(
        f"/api/projects/{pid}/evaluations",
        json={
            "visual_quality": 5,
            "property_consistency": 5,
            "scene_ordering": 5,
            "motion_quality": 5,
            "temporal_stability": 4,
            "walkthrough_usefulness": 5,
            "comments": "Exceptional panoramic perspective.",
        },
    )

    # 1. JSON Report
    report_res = client.get(f"/api/projects/{pid}/report")
    assert report_res.status_code == 200
    rep = report_res.json()["data"]
    assert rep["property_name"] == "Report Architecture Penthouse"
    assert rep["source_images_count"] == 1
    assert rep["evaluation_summary"]["total_evaluations"] == 1

    # 2. Plain Text Report
    text_res = client.get(f"/api/projects/{pid}/report/text")
    assert text_res.status_code == 200
    text_content = text_res.text
    assert "WALKTHROUGH GENERATION & EVALUATION REPORT" in text_content
    assert "Report Architecture Penthouse" in text_content
    assert "Visual Quality" in text_content


def test_safe_project_cleanup(client):
    """
    Tests safe project deletion with mandatory confirmation flag.
    """
    project = project_service.create_project(ProjectCreate(name="Temporary Cleanable Villa"))
    pid = project.id

    # 1. Deletion without confirm=true must fail
    res_no_confirm = client.delete(f"/api/projects/{pid}")
    assert res_no_confirm.status_code == 400

    # 2. Deletion with confirm=true must succeed
    res_confirm = client.delete(f"/api/projects/{pid}?confirm=true")
    assert res_confirm.status_code == 200
    assert res_confirm.json()["data"]["deleted"] is True

    # 3. Subsequent fetch must return 404
    get_res = client.get(f"/api/projects/{pid}")
    assert get_res.status_code == 404
