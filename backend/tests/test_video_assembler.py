import os
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.plan import CameraInstruction, CameraMotionType, GenerationPlan, PlannedScene, TransitionInstruction, TransitionType
from app.schemas.project import ProjectCreate
from app.services.project_service import project_service
from app.services.storage_service import storage_service
from app.services.video_assembler import ffmpeg_engine, video_assembler_service
from app.services.video_assembler.service import AssemblyValidationError


client = TestClient(app)


def _create_synthetic_mp4(output_path: Path, width: int = 640, height: int = 360, duration_secs: float = 1.0, color=(100, 150, 200)) -> Path:
    """Helper to generate tiny synthetic test video clip."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fps = 24.0
    total_frames = max(1, int(duration_secs * fps))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    for _ in range(total_frames):
        frame = np.full((height, width, 3), color, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return output_path


def test_ffmpeg_probe_and_normalize(tmp_path):
    """Verifies that probing and normalization extract accurate metrics and normalize specs."""
    raw_clip = tmp_path / "raw.mp4"
    _create_synthetic_mp4(raw_clip, width=640, height=360, duration_secs=1.0)

    meta = ffmpeg_engine.probe_video(raw_clip)
    assert meta["width"] == 640
    assert meta["height"] == 360
    assert meta["duration_seconds"] >= 0.9

    norm_clip = tmp_path / "norm.mp4"
    ffmpeg_engine.normalize_clip(raw_clip, norm_clip, target_width=1280, target_height=720, target_fps=24.0)

    norm_meta = ffmpeg_engine.probe_video(norm_clip)
    assert norm_meta["width"] == 1280
    assert norm_meta["height"] == 720
    assert norm_meta["fps"] == 24.0


def test_create_title_intro_clip(tmp_path):
    """Verifies title intro card creation."""
    intro_path = tmp_path / "intro.mp4"
    ffmpeg_engine.create_title_intro_clip(
        title="Modern Luxury Villa",
        output_path=intro_path,
        duration=1.0,
        width=1280,
        height=720,
        fps=24.0,
    )
    assert intro_path.exists()
    meta = ffmpeg_engine.probe_video(intro_path)
    assert meta["duration_seconds"] >= 0.9
    assert meta["width"] == 1280
    assert meta["height"] == 720


def test_assembly_missing_clip_raises_error(tmp_path):
    """Verifies that missing clips immediately block assembly with descriptive message."""
    proj = project_service.create_project(ProjectCreate(name="Missing Clip Test"))
    pid = proj.id

    plan = GenerationPlan(
        plan_id="plan_test_missing",
        project_id=pid,
        scenes=[
            PlannedScene(
                order=1,
                scene_id="scene_kitchen",
                image_id="img_1",
                scene_type="kitchen",
                label="Gourmet Kitchen",
                reason="test",
                camera=CameraInstruction(motion_type=CameraMotionType.SLOW_FORWARD, prompt="push in"),
            )
        ],
    )
    project_service.storage.save_plan_json(pid, plan.model_dump())

    with pytest.raises(AssemblyValidationError) as exc_info:
        video_assembler_service.validate_required_clips(pid, plan)

    assert "Gourmet Kitchen clip is unavailable" in str(exc_info.value.message)


def test_assembly_straight_cut_end_to_end(tmp_path):
    """Verifies complete assembly pipeline preserving exact scene order."""
    proj = project_service.create_project(ProjectCreate(name="End to End Walkthrough"))
    pid = proj.id

    # Create 3 synthetic clips
    s1_clip = project_service.storage.get_clip_path(pid, "scene_ext")
    s2_clip = project_service.storage.get_clip_path(pid, "scene_liv")
    s3_clip = project_service.storage.get_clip_path(pid, "scene_bed")

    _create_synthetic_mp4(s1_clip, color=(50, 100, 150))
    _create_synthetic_mp4(s2_clip, color=(150, 100, 50))
    _create_synthetic_mp4(s3_clip, color=(50, 150, 100))

    plan = GenerationPlan(
        plan_id="plan_e2e",
        project_id=pid,
        scenes=[
            PlannedScene(
                order=1,
                scene_id="scene_ext",
                image_id="img_ext",
                scene_type="exterior",
                label="Modern Exterior",
                reason="entry",
                camera=CameraInstruction(motion_type=CameraMotionType.EXTERIOR_FORWARD, prompt="push in"),
                transition_to_next=TransitionInstruction(type=TransitionType.STRAIGHT_CUT),
            ),
            PlannedScene(
                order=2,
                scene_id="scene_liv",
                image_id="img_liv",
                scene_type="living_room",
                label="Living Room",
                reason="living",
                camera=CameraInstruction(motion_type=CameraMotionType.PAN_LEFT, prompt="pan left"),
                transition_to_next=TransitionInstruction(type=TransitionType.STRAIGHT_CUT),
            ),
            PlannedScene(
                order=3,
                scene_id="scene_bed",
                image_id="img_bed",
                scene_type="bedroom",
                label="Master Bedroom",
                reason="private",
                camera=CameraInstruction(motion_type=CameraMotionType.SLOW_FORWARD, prompt="forward"),
            ),
        ],
    )
    project_service.storage.save_plan_json(pid, plan.model_dump())

    job = video_assembler_service.assemble_walkthrough(pid)
    assert job.status.value == "completed"
    assert job.result is not None
    assert job.result.scene_count == 3
    assert job.result.scenes_in_order[0].label == "Modern Exterior"
    assert job.result.scenes_in_order[1].label == "Living Room"
    assert job.result.scenes_in_order[2].label == "Master Bedroom"

    # Verify physical final video exists
    final_file = project_service.storage.get_final_video_path(pid)
    assert final_file.exists()
    assert final_file.stat().st_size > 0

    # Verify project status
    updated_proj = project_service.storage.load_project_json(pid)
    assert updated_proj["status"] == "completed"


def test_assembly_outdated_detection():
    """Verifies that modifying the plan marks existing final walkthrough as outdated."""
    proj = project_service.create_project(ProjectCreate(name="Outdated Test"))
    pid = proj.id

    s1_clip = project_service.storage.get_clip_path(pid, "scene_1")
    s2_clip = project_service.storage.get_clip_path(pid, "scene_2")
    _create_synthetic_mp4(s1_clip)
    _create_synthetic_mp4(s2_clip)

    plan = GenerationPlan(
        plan_id="plan_v1",
        project_id=pid,
        plan_version=1,
        scenes=[
            PlannedScene(
                order=1,
                scene_id="scene_1",
                image_id="img_1",
                scene_type="living_room",
                label="Living Room",
                reason="1",
                camera=CameraInstruction(motion_type=CameraMotionType.SLOW_FORWARD, prompt="fwd"),
            ),
            PlannedScene(
                order=2,
                scene_id="scene_2",
                image_id="img_2",
                scene_type="bedroom",
                label="Bedroom",
                reason="2",
                camera=CameraInstruction(motion_type=CameraMotionType.SLOW_FORWARD, prompt="fwd"),
            ),
        ],
    )
    project_service.storage.save_plan_json(pid, plan.model_dump())

    # Assemble
    video_assembler_service.assemble_walkthrough(pid)

    meta_v1 = video_assembler_service.get_final_metadata(pid)
    assert meta_v1 is not None
    assert meta_v1.is_outdated is False

    # Now modify plan (reorder scenes)
    plan.scenes[0].order = 2
    plan.scenes[1].order = 1
    plan.plan_version = 2
    project_service.storage.save_plan_json(pid, plan.model_dump())

    meta_v2 = video_assembler_service.get_final_metadata(pid)
    assert meta_v2 is not None
    assert meta_v2.is_outdated is True


def test_api_assembly_endpoints():
    """Tests the FastAPI assembly endpoints."""
    proj = project_service.create_project(ProjectCreate(name="API Assembly Test"))
    pid = proj.id

    s1_clip = project_service.storage.get_clip_path(pid, "scene_api_1")
    _create_synthetic_mp4(s1_clip)

    plan = GenerationPlan(
        plan_id="plan_api",
        project_id=pid,
        scenes=[
            PlannedScene(
                order=1,
                scene_id="scene_api_1",
                image_id="img_api_1",
                scene_type="entrance",
                label="Foyer",
                reason="entry",
                camera=CameraInstruction(motion_type=CameraMotionType.SLOW_FORWARD, prompt="in"),
            )
        ],
    )
    project_service.storage.save_plan_json(pid, plan.model_dump())

    # 1. Trigger assembly POST
    res = client.post(f"/api/projects/{pid}/assemble")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["status"] == "completed"

    # 2. Get assembly status GET
    res_status = client.get(f"/api/projects/{pid}/assembly")
    assert res_status.status_code == 200
    assert res_status.json()["data"]["status"] == "completed"

    # 3. Get final-video metadata
    res_meta = client.get(f"/api/projects/{pid}/final-video")
    assert res_meta.status_code == 200
    assert res_meta.json()["data"]["scene_count"] == 1

    # 4. Stream final video
    res_file = client.get(f"/api/projects/{pid}/final-video/file")
    assert res_file.status_code == 200
    assert res_file.headers["content-type"] == "video/mp4"

    # 5. Download final video
    res_dl = client.get(f"/api/projects/{pid}/final-video/download")
    assert res_dl.status_code == 200
    assert "attachment" in res_dl.headers.get("content-disposition", "")
