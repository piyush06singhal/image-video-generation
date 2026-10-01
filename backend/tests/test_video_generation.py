import asyncio
from pathlib import Path
import tempfile
import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.errors import AppException
from app.main import app
from app.schemas.generation import (
    GenerateRequest,
    GenerationJobStatus,
    ProjectGenerationStatus,
    QualityAssessment,
    RegenerateSceneRequest,
    SceneGenerationStatus,
    VideoClipMetadata,
)
from app.schemas.plan import (
    CameraInstruction,
    CameraMotionType,
    GenerationPlan,
    PlannedScene,
    PlanSource,
)
from app.services.storage_service import storage_service
from app.services.video_generation.base import ImageToVideoProvider, ProviderResult
from app.services.video_generation.gemini_veo_provider import GeminiVeoProvider
from app.services.video_generation.service import VideoGenerationService
from app.services.video_generation.video_validator import VideoValidator


class MockVideoProvider(ImageToVideoProvider):
    """Mock provider for unit test assertions that produces a real, valid tiny MP4."""

    def __init__(self, should_fail: bool = False, fail_code: str = "PROVIDER_RATE_LIMIT"):
        self.should_fail = should_fail
        self.fail_code = fail_code
        self.call_count = 0

    def get_provider_name(self) -> str:
        return "mock_video_provider"

    def get_model_name(self) -> str:
        return "mock-veo-model"

    async def generate_clip(
        self,
        source_image_path: Path,
        prompt: str,
        negative_prompt: str,
        duration_seconds: float,
        camera_motion: str,
        output_path: Path,
    ) -> ProviderResult:
        self.call_count += 1
        if self.should_fail:
            raise AppException(code=self.fail_code, message="Simulated provider error", status_code=429)

        # Write a real, tiny valid MP4 video using OpenCV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        width, height = 640, 360
        fps = 24.0
        num_frames = int(fps * max(duration_seconds, 1.0))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        for i in range(num_frames):
            frame = np.full((height, width, 3), (i * 2) % 255, dtype=np.uint8)
            out.write(frame)
        out.release()

        return ProviderResult(
            provider_job_id="mock_op_123",
            output_video_path=output_path,
            provider_name=self.get_provider_name(),
            model_name=self.get_model_name(),
            duration_seconds=duration_seconds,
            raw_metadata={"mock": True},
        )


@pytest.fixture
def test_project_with_plan(isolated_storage):
    """Sets up a project in isolated storage with uploaded image and Phase 3 plan."""
    service_storage = isolated_storage
    project_id = "test_video_proj_001"
    uploads_dir, processed_dir = service_storage.create_project_storage(project_id)

    # Save a fake uploaded source image
    img_filename = "img_001_living.jpg"
    img_path = uploads_dir / img_filename
    cv2.imwrite(str(img_path), np.full((720, 1280, 3), 200, dtype=np.uint8))

    project_data = {
        "id": project_id,
        "name": "Luxury Test Villa",
        "status": "planned",
        "images": [
            {
                "id": "img_001",
                "filename": img_filename,
                "original_filename": "living.jpg",
                "file_size": 50000,
                "width": 1280,
                "height": 720,
                "aspect_ratio": "16:9",
                "format": "JPEG",
                "scene_type": "living_room",
                "scene_description": "Bright modern living room with large glass windows",
                "visible_features": ["sofa", "coffee table", "windows"],
                "lighting": "natural_daylight",
                "view_type": "wide",
                "camera_view": "eye_level",
                "confidence": 0.95,
                "user_confirmed": True,
            }
        ],
        "image_count": 1,
    }
    service_storage.save_project_json(project_id, project_data)

    # Save Phase 3 plan
    plan = GenerationPlan(
        plan_id="plan_test_001_v1",
        project_id=project_id,
        plan_version=1,
        source=PlanSource.AI,
        scenes=[
            PlannedScene(
                order=1,
                scene_id="scene_img_001",
                image_id="img_001",
                scene_type="living_room",
                label="Living Room",
                reason="Primary living space",
                camera=CameraInstruction(
                    motion_type=CameraMotionType.SLOW_FORWARD,
                    prompt="Smooth forward push through living room",
                    constraints=["do not alter geometry", "no new furniture"],
                    duration_seconds=4.0,
                ),
                thumbnail_url="/api/projects/test_video_proj_001/images/img_001/thumbnail",
                original_filename="living.jpg",
                user_confirmed=True,
            )
        ],
    )
    service_storage.save_plan_json(project_id, plan.model_dump())

    yield project_id, plan


def test_video_validator_valid_and_corrupt(tmp_path):
    validator = VideoValidator()

    # 1. Non-existent file
    valid, _, quality, err = validator.validate_and_extract_metadata(tmp_path / "ghost.mp4")
    assert not valid
    assert quality == QualityAssessment.FAILED

    # 2. Corrupt/empty file
    corrupt_file = tmp_path / "corrupt.mp4"
    corrupt_file.write_bytes(b"garbage content")
    valid, _, quality, err = validator.validate_and_extract_metadata(corrupt_file)
    assert not valid
    assert quality == QualityAssessment.FAILED

    # 3. Valid video file
    valid_file = tmp_path / "valid.mp4"
    width, height, fps = 640, 360, 24.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(valid_file), fourcc, fps, (width, height))
    for i in range(48):
        frame = np.full((height, width, 3), 150, dtype=np.uint8)
        out.write(frame)
    out.release()

    valid, meta, quality, err = validator.validate_and_extract_metadata(valid_file)
    assert valid
    assert meta["width"] == 640
    assert meta["height"] == 360
    assert meta["duration_seconds"] >= 1.9
    assert quality == QualityAssessment.ACCEPTABLE


@pytest.mark.asyncio
async def test_video_generation_service_end_to_end(test_project_with_plan, isolated_storage):
    project_id, plan = test_project_with_plan
    mock_provider = MockVideoProvider()
    service = VideoGenerationService(provider=mock_provider)
    service.storage = isolated_storage


    # 1. Initial Overview
    overview = service.get_or_create_overview(project_id)
    assert overview.total_scenes == 1
    assert overview.completed_scenes == 0
    assert overview.status == ProjectGenerationStatus.READY
    assert overview.scenes[0].status == SceneGenerationStatus.PENDING

    # 2. Launch Generation
    updated_overview = await service.generate_clips(project_id)
    assert updated_overview.total_scenes == 1
    # Allow background execution to complete
    await asyncio.sleep(0.5)

    # 3. Check completed state
    final_overview = service.get_or_create_overview(project_id)
    assert final_overview.completed_scenes == 1
    assert final_overview.status == ProjectGenerationStatus.COMPLETED
    assert final_overview.scenes[0].status == SceneGenerationStatus.COMPLETED
    assert final_overview.scenes[0].clip is not None
    assert final_overview.scenes[0].clip.width == 640

    # 4. Clip reuse (do not re-run if already completed)
    calls_before = mock_provider.call_count
    await service.generate_clips(project_id, GenerateRequest(force_regenerate=False))
    await asyncio.sleep(0.1)
    assert mock_provider.call_count == calls_before

    # 5. Force regenerate single scene
    await service.regenerate_scene(
        project_id,
        "scene_img_001",
        RegenerateSceneRequest(custom_motion_type=CameraMotionType.PAN_LEFT),
    )
    await asyncio.sleep(0.5)
    regen_overview = service.get_or_create_overview(project_id)
    assert regen_overview.scenes[0].clip.camera_motion == CameraMotionType.PAN_LEFT


@pytest.mark.asyncio
async def test_video_generation_failure_and_retry(test_project_with_plan, isolated_storage):
    project_id, plan = test_project_with_plan
    mock_provider = MockVideoProvider(should_fail=True)
    service = VideoGenerationService(provider=mock_provider)
    service.storage = isolated_storage

    # 1. Trigger generation expecting failure
    await service.generate_clips(project_id)
    await asyncio.sleep(0.5)

    overview = service.get_or_create_overview(project_id)
    assert overview.failed_scenes == 1
    assert overview.status == ProjectGenerationStatus.PARTIALLY_COMPLETED or overview.status == ProjectGenerationStatus.FAILED
    assert overview.scenes[0].status == SceneGenerationStatus.FAILED
    assert overview.scenes[0].last_error is not None

    job_id = overview.scenes[0].job_id
    assert job_id is not None

    # 2. Fix provider and Retry
    mock_provider.should_fail = False
    retried_job = await service.retry_job(project_id, job_id)
    assert retried_job.retry_count == 1
    await asyncio.sleep(0.5)

    post_retry_overview = service.get_or_create_overview(project_id)
    assert post_retry_overview.completed_scenes == 1
    assert post_retry_overview.scenes[0].status == SceneGenerationStatus.COMPLETED


def test_api_video_generation_routes(test_project_with_plan):
    project_id, _ = test_project_with_plan
    client = TestClient(app)

    # 1. GET generation overview
    r = client.get(f"/api/projects/{project_id}/generation")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["project_id"] == project_id
    assert data["total_scenes"] == 1
