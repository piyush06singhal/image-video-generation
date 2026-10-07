"""End-to-end assembly tests for the option-driven cinematic pipeline.

These assert on the *artifact*, not just the returned metadata: frame size,
presence of an audio stream, burned-in labels, and the stale-detection that stops
a previously rendered cut from silently surviving a settings change.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.schemas.assembly import AssemblyConfig, AssemblyRequest
from app.schemas.plan import (
    CameraInstruction,
    CameraMotionType,
    GenerationPlan,
    PlannedScene,
    TransitionInstruction,
    TransitionType,
)
from app.schemas.project import ProjectCreate
from app.schemas.render_options import (
    AspectRatio,
    ColorGrade,
    MusicStyle,
    RenderOptions,
    TransitionStyle,
    build_render_options,
)
from app.services.project_service import project_service
from app.services.render_options_service import render_options_service
from app.services.video_assembler import ffmpeg_engine, video_assembler_service


def _write_clip(path: Path, width: int = 320, height: int = 180, seconds: float = 1.2, tint=(40, 60, 90)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fps = 24.0
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for i in range(max(2, int(seconds * fps))):
        frame = np.zeros((height, width, 3), np.uint8)
        frame[:] = tint
        frame[height // 3 : height // 2, 10 + i * 2 : width // 2 + i * 2] = (210, 190, 130)
        writer.write(frame)
    writer.release()
    return path


def _scene(order: int, scene_id: str, label: str, motion: CameraMotionType) -> PlannedScene:
    return PlannedScene(
        order=order,
        scene_id=scene_id,
        image_id=f"img_{scene_id}",
        scene_type="living_room" if order == 1 else "bedroom",
        label=label,
        reason=f"position {order}",
        camera=CameraInstruction(motion_type=motion, prompt="push in"),
        transition_to_next=TransitionInstruction(type=TransitionType.STRAIGHT_CUT),
    )


def _project_with_clips(name: str = "Cinematic Assembly") -> str:
    proj = project_service.create_project(ProjectCreate(name=name))
    pid = proj.id

    _write_clip(project_service.storage.get_clip_path(pid, "scene_liv"), tint=(50, 100, 150))
    _write_clip(project_service.storage.get_clip_path(pid, "scene_bed"), tint=(150, 100, 50))

    # Real source photos so the branded cards have a backdrop to blur.
    uploads = project_service.storage.get_project_uploads_dir(pid)
    uploads.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(uploads / "img_scene_liv_living.jpg"), np.full((240, 320, 3), 120, np.uint8))

    plan = GenerationPlan(
        plan_id="plan_cinematic",
        project_id=pid,
        scenes=[
            _scene(1, "scene_liv", "Living Room", CameraMotionType.PAN_LEFT),
            _scene(2, "scene_bed", "Primary Bedroom", CameraMotionType.SLOW_FORWARD),
        ],
    )
    project_service.storage.save_plan_json(pid, plan.model_dump())
    return pid


def test_vertical_1080p_reel_with_music_and_labels(tmp_path):
    """The headline scenario: a portrait reel, graded, scored and labelled."""
    pid = _project_with_clips()
    render_options_service.save(
        pid,
        build_render_options(
            "energetic_reel",
            {
                "aspect_ratio": AspectRatio.VERTICAL.value,
                "resolution": "720p",
                "scene_duration_seconds": 3.0,
            },
        ),
    )

    job = video_assembler_service.assemble_walkthrough(
        pid, AssemblyRequest(force_reassemble=True)
    )

    assert job.status.value == "completed"
    meta = job.result
    assert meta is not None

    # Options were honoured on the artifact, not just the metadata.
    assert (meta.width, meta.height) == (720, 1280)
    assert meta.fps == pytest.approx(30.0, abs=1.0)
    assert meta.video_codec == "h264"

    final_path = project_service.storage.get_final_video_path(pid)
    probe = ffmpeg_engine.probe_video(final_path)
    assert (probe["width"], probe["height"]) == (720, 1280)

    # Music is actually in the container, and the metadata says so truthfully.
    audio_codec = ffmpeg_engine.probe_audio_codec(final_path)
    assert audio_codec is not None
    assert meta.audio_codec == audio_codec
    assert meta.audio_enabled is True

    # Intro card + 2 scenes + outro card all made it into the timeline.
    clips_total = 2 * 3.0
    assert meta.duration_seconds > clips_total

    assert meta.scene_count == 2
    assert meta.render_options is not None
    assert meta.render_options.aspect_ratio == AspectRatio.VERTICAL
    assert meta.render_options_hash == meta.render_options.assembly_signature()


def test_quick_draft_is_silent_and_unbranded():
    """The fast preview preset must not pay for music, cards or labels."""
    pid = _project_with_clips("Quick Draft")
    render_options_service.save(pid, build_render_options("quick_draft"))

    job = video_assembler_service.assemble_walkthrough(pid, AssemblyRequest(force_reassemble=True))
    meta = job.result
    assert meta is not None

    assert (meta.width, meta.height) == (1280, 720)
    assert meta.fps == pytest.approx(24.0, abs=1.0)
    assert meta.audio_codec is None
    assert meta.audio_enabled is False
    assert ffmpeg_engine.probe_audio_codec(project_service.storage.get_final_video_path(pid)) is None

    # No intro/outro cards, so the cut is just the two clips (minus no transitions).
    assert meta.duration_seconds == pytest.approx(2 * 1.2, abs=0.5)


def test_room_labels_change_the_rendered_pixels():
    labeled_pid = _project_with_clips("Labels On")
    render_options_service.save(
        labeled_pid,
        build_render_options("cinematic_luxury", {"room_labels_enabled": True, "intro_title_enabled": False,
                                                   "outro_enabled": False, "music_enabled": False}),
    )
    plain_pid = _project_with_clips("Labels Off")
    render_options_service.save(
        plain_pid,
        build_render_options("cinematic_luxury", {"room_labels_enabled": False, "intro_title_enabled": False,
                                                   "outro_enabled": False, "music_enabled": False}),
    )

    video_assembler_service.assemble_walkthrough(labeled_pid, AssemblyRequest(force_reassemble=True))
    video_assembler_service.assemble_walkthrough(plain_pid, AssemblyRequest(force_reassemble=True))

    def mid_frame(pid: str) -> np.ndarray:
        cap = cv2.VideoCapture(str(project_service.storage.get_final_video_path(pid)))
        cap.set(cv2.CAP_PROP_POS_MSEC, 900)
        ok, frame = cap.read()
        cap.release()
        assert ok
        return frame.astype(np.int16)

    # Frame sizes match, so any large difference is the burned-in label.
    assert np.abs(mid_frame(labeled_pid) - mid_frame(plain_pid)).max() > 40


def test_changing_options_marks_the_existing_walkthrough_outdated():
    """A rendered cut must not silently survive a settings change."""
    pid = _project_with_clips("Outdated By Options")
    render_options_service.save(pid, build_render_options("cinematic_luxury"))

    video_assembler_service.assemble_walkthrough(pid, AssemblyRequest(force_reassemble=True))
    assert video_assembler_service.get_final_metadata(pid).is_outdated is False

    # A look-only change still invalidates the cut (nothing needs regenerating,
    # but the final video must be rebuilt).
    render_options_service.update(pid, overrides={"color_grade": ColorGrade.NOIR.value})
    assert video_assembler_service.get_final_metadata(pid).is_outdated is True

    video_assembler_service.assemble_walkthrough(pid, AssemblyRequest(force_reassemble=True))
    assert video_assembler_service.get_final_metadata(pid).is_outdated is False

    # And a frame-size change invalidates it too.
    render_options_service.update(pid, overrides={"transition_style": TransitionStyle.FADE_TO_BLACK.value})
    assert video_assembler_service.get_final_metadata(pid).is_outdated is True


def test_reassembly_is_skipped_when_nothing_changed():
    pid = _project_with_clips("Idempotent Reassembly")
    render_options_service.save(pid, build_render_options("documentary_tour"))

    first = video_assembler_service.assemble_walkthrough(pid, AssemblyRequest(force_reassemble=True))
    assert first.status.value == "completed"

    second = video_assembler_service.assemble_walkthrough(pid)
    assert second.status.value == "completed"
    assert "already assembled" in second.stage_message
    # Same job result, i.e. no re-encode happened.
    assert second.result.duration_seconds == first.result.duration_seconds


def test_legacy_assembly_config_overrides_project_options():
    """Old clients that post only a config must still be able to turn music off."""
    pid = _project_with_clips("Legacy Config")
    render_options_service.save(pid, build_render_options("cinematic_luxury"))

    job = video_assembler_service.assemble_walkthrough(
        pid,
        AssemblyRequest(config=AssemblyConfig(audio_enabled=False, intro_title_enabled=False, output_fps=24.0),
                        force_reassemble=True),
    )

    meta = job.result
    assert meta is not None
    assert meta.audio_enabled is False
    assert meta.fps == pytest.approx(24.0, abs=1.0)
    # Music style stays on in the stored options: the override is per-call only.
    assert render_options_service.get(pid).music_style == MusicStyle.AMBIENT


def test_inline_render_options_on_the_assemble_request_are_persisted():
    pid = _project_with_clips("Inline Options")
    payload = RenderOptions(
        preset="modern_minimal",
        aspect_ratio=AspectRatio.SQUARE,
        resolution="720p",
        music_enabled=False,
        intro_title_enabled=False,
        outro_enabled=False,
    )

    job = video_assembler_service.assemble_walkthrough(
        pid, AssemblyRequest(render_options=payload, force_reassemble=True)
    )

    assert (job.result.width, job.result.height) == (720, 720)
    saved = render_options_service.get(pid)
    assert saved.preset == "modern_minimal"
    assert saved.aspect_ratio == AspectRatio.SQUARE


def test_api_can_assemble_with_options_end_to_end():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    pid = _project_with_clips("API Options Assembly")

    resp = client.patch(
        f"/api/projects/{pid}/render-options",
        json={
            "preset": "modern_minimal",
            "options": {"aspect_ratio": "9:16", "resolution": "720p", "music_enabled": False},
        },
    )
    assert resp.status_code == 200

    assembled = client.post(f"/api/projects/{pid}/assemble", json={"force_reassemble": True})
    assert assembled.status_code == 200
    data = assembled.json()["data"]["result"]
    assert (data["width"], data["height"]) == (720, 1280)
    assert data["render_options"]["preset"] == "modern_minimal"
    assert data["audio_enabled"] is False

    # The final MP4 streams and carries the promised frame size.
    streamed = client.get(f"/api/projects/{pid}/final-video/file")
    assert streamed.status_code == 200
    assert streamed.headers["content-type"] == "video/mp4"
