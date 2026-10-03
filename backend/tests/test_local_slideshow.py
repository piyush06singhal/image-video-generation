import cv2
import numpy as np
import pytest

from app.services import local_slideshow_service as slideshow_module
from app.services.local_slideshow_service import LocalSlideshowService
from app.schemas.plan import CameraInstruction, CameraMotionType, GenerationPlan, PlannedScene, PlanSource


@pytest.fixture
def slideshow_project(isolated_storage):
    project_id = "test_slideshow_proj"
    uploads_dir, _ = isolated_storage.create_project_storage(project_id)
    image_name = "living.jpg"
    cv2.imwrite(
        str(uploads_dir / image_name),
        np.full((600, 800, 3), 180, dtype=np.uint8),
    )
    isolated_storage.save_project_json(
        project_id,
        {
            "id": project_id,
            "name": "Slideshow Test",
            "status": "planned",
            "images": [{"id": "img_001", "filename": image_name}],
            "image_count": 1,
        },
    )
    plan = GenerationPlan(
        plan_id="plan_slideshow_v1",
        project_id=project_id,
        plan_version=1,
        source=PlanSource.USER,
        scenes=[
            PlannedScene(
                order=1,
                scene_id="scene_img_001",
                image_id="img_001",
                scene_type="living_room",
                label="Living Room",
                reason="Primary room",
                camera=CameraInstruction(
                    motion_type=CameraMotionType.SLOW_FORWARD,
                    prompt="Slow forward movement",
                    duration_seconds=1.0,
                ),
                original_filename=image_name,
            )
        ],
    )
    isolated_storage.save_plan_json(project_id, plan.model_dump())
    return project_id, plan


def test_local_slideshow_creates_valid_final_video(slideshow_project, isolated_storage):
    project_id, plan = slideshow_project
    original_storage = slideshow_module.storage_service
    slideshow_module.storage_service = isolated_storage
    try:
        metadata = LocalSlideshowService().create(project_id, seconds_per_scene=1.0)
    finally:
        slideshow_module.storage_service = original_storage

    output_path = isolated_storage.get_final_video_path(project_id)
    assert output_path.exists()
    assert metadata.project_id == project_id
    assert metadata.width == 1280
    assert metadata.height == 720
    assert metadata.scene_count == len(plan.scenes)
    assert metadata.file_size_bytes == output_path.stat().st_size

    capture = cv2.VideoCapture(str(output_path))
    try:
        assert capture.isOpened()
        assert int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) == 1280
        assert int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) == 720
        assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) > 0
    finally:
        capture.release()


def test_local_slideshow_rejects_missing_source_image(slideshow_project, isolated_storage):
    project_id, _ = slideshow_project
    project = isolated_storage.load_project_json(project_id)
    project["images"][0]["filename"] = "missing.jpg"
    isolated_storage.save_project_json(project_id, project)

    original_storage = slideshow_module.storage_service
    slideshow_module.storage_service = isolated_storage
    try:
        with pytest.raises(Exception, match="unavailable"):
            LocalSlideshowService().create(project_id)
    finally:
        slideshow_module.storage_service = original_storage
