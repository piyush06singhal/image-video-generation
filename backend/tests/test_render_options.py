"""Tests for the cinematic render options that make the walkthrough configurable.

Before this existed, duration, resolution, motion, transitions, grading and music
were hardcoded in the pipeline and the studio had no way to change any of them.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.project import ProjectCreate
from app.schemas.render_options import (
    PRESET_DEFINITIONS,
    AspectRatio,
    ColorGrade,
    MusicStyle,
    RenderOptions,
    TransitionStyle,
    build_render_options,
    default_render_options,
    target_dimensions,
)
from app.services.project_service import project_service
from app.services.render_options_service import render_options_service


client = TestClient(app)


def _seed_single_scene_plan(project_id: str) -> None:
    """The generation overview needs a plan; the planner is not under test here."""
    from app.schemas.plan import CameraInstruction, CameraMotionType, GenerationPlan, PlannedScene

    plan = GenerationPlan(
        plan_id="plan_options_test",
        project_id=project_id,
        scenes=[
            PlannedScene(
                order=1,
                scene_id="scene_only",
                image_id="img_1",
                scene_type="living_room",
                label="Living Room",
                reason="only scene",
                camera=CameraInstruction(motion_type=CameraMotionType.SLOW_FORWARD, prompt="push in"),
            )
        ],
    )
    project_service.storage.save_plan_json(project_id, plan.model_dump())


# ── pure option logic ────────────────────────────────────────────────────

def test_default_is_the_cinematic_luxury_house_style():
    options = default_render_options()
    assert options.preset == "cinematic_luxury"
    assert options.color_grade == ColorGrade.WARM_LUXURY
    assert options.music_enabled is True
    assert options.room_labels_enabled is True
    assert options.transition_style == TransitionStyle.CROSSFADE
    # Not the old hardcoded 24fps/1080p-with-no-grading output.
    assert options.fps == 30
    assert options.film_grain is True


@pytest.mark.parametrize(
    "aspect,resolution,expected",
    [
        (AspectRatio.LANDSCAPE, "1080p", (1920, 1080)),
        (AspectRatio.LANDSCAPE, "720p", (1280, 720)),
        (AspectRatio.VERTICAL, "1080p", (1080, 1920)),
        (AspectRatio.VERTICAL, "720p", (720, 1280)),
        (AspectRatio.SQUARE, "1080p", (1080, 1080)),
    ],
)
def test_target_dimensions_keep_the_tier_meaningful_in_every_aspect(aspect, resolution, expected):
    assert target_dimensions(aspect, resolution) == expected
    # The RenderOptions accessor must return even numbers for H.264.
    assert all(dim % 2 == 0 for dim in build_render_options("cinematic_luxury", {"aspect_ratio": aspect.value, "resolution": resolution}).dimensions())


def test_invalid_resolution_is_rejected():
    with pytest.raises(Exception):
        RenderOptions(resolution="8k")


def test_provider_hints_serialise_every_field_a_provider_needs():
    options = build_render_options("energetic_reel")
    hints = options.provider_hints(scene_index=2)
    assert hints == {
        "motion_intensity": "bold",
        "camera_variety": True,
        "depth_parallax": True,
        "motion_blur": True,
        "scene_index": 2,
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "duration_seconds": 3.0,
        "aspect_ratio": "9:16",
        "resolution": "1080p",
    }


def test_generation_signature_only_tracks_clip_affecting_fields():
    base = default_render_options()

    # Grading and music only change the final cut, not the pixels of a clip.
    look_only = base.model_copy(update={"color_grade": ColorGrade.NOIR, "music_enabled": False})
    assert look_only.generation_signature() == base.generation_signature()
    assert look_only.assembly_signature() != base.assembly_signature()

    # Duration / frame size / motion do change the clips.
    for field, value in [
        ("scene_duration_seconds", 8.0),
        ("fps", 24),
        ("resolution", "720p"),
        ("aspect_ratio", AspectRatio.VERTICAL),
        ("camera_variety", False),
    ]:
        changed = base.model_copy(update={field: value})
        assert changed.generation_signature() != base.generation_signature(), field


def test_every_preset_is_constructible_and_distinct():
    assert len(PRESET_DEFINITIONS) >= 4
    signatures = set()
    for name in PRESET_DEFINITIONS:
        options = build_render_options(name)
        assert options.preset == name
        signatures.add(options.assembly_signature())
    # A preset that renders identically to another would be a pointless menu entry.
    assert len(signatures) == len(PRESET_DEFINITIONS)


def test_unknown_preset_is_rejected():
    with pytest.raises(ValueError):
        build_render_options("does_not_exist")


def test_the_flagship_preset_shows_the_whole_property():
    """The house style must not ship the two things that read as 'diluted'.

    Scope bars remove 11% of the picture the client is paying to see, and long
    title cards spend a fifth of a short tour on graphics instead of rooms. Both are
    still available — they are just not what a listing gets by default.
    """
    flagship = build_render_options("cinematic_luxury")

    assert flagship.letterbox is False
    assert flagship.intro_duration_seconds + flagship.outro_duration_seconds <= 4.5
    assert flagship.cinematic_bloom is True, "the grade should still be finished"
    assert flagship.depth_parallax is True


def test_the_sound_design_is_on_by_default_without_being_a_switch():
    """Whooshes and a closing button are part of the mix, not an option to forget."""
    from app.services.video_assembler.music_engine import music_engine

    accents = music_engine.plan_accents(20.0, [2.2, 7.0, 11.5, 16.0], opening_riser=True, final_impact=True)
    assert len(accents) == 6  # four cuts + riser + button
    assert all(0.0 <= a.at <= 20.0 for a in accents)


# ── service persistence and merge semantics ──────────────────────────────

def test_options_default_before_anything_is_saved():
    proj = project_service.create_project(ProjectCreate(name="Options Default"))
    options = render_options_service.get(proj.id)
    assert options.preset == "cinematic_luxury"
    assert render_options_service.storage.load_render_options(proj.id) is None


def test_partial_update_merges_onto_existing_values():
    proj = project_service.create_project(ProjectCreate(name="Options Merge"))
    render_options_service.update(proj.id, preset="modern_minimal")

    updated = render_options_service.update(proj.id, overrides={"scene_duration_seconds": 9.0})

    assert updated.scene_duration_seconds == 9.0
    # Untouched fields keep the preset's values rather than resetting.
    assert updated.preset == "modern_minimal"
    assert updated.color_grade == ColorGrade.COOL_MODERN
    assert updated.music_style == MusicStyle.MINIMAL_PIANO


def test_preset_selection_replaces_the_whole_option_set():
    proj = project_service.create_project(ProjectCreate(name="Options Preset"))
    render_options_service.update(proj.id, overrides={"fps": 60, "film_grain": True})

    switched = render_options_service.update(proj.id, preset="documentary_tour")

    # A preset is an explicit "make it look like this" action.
    assert switched.preset == "documentary_tour"
    assert switched.fps == 24
    assert switched.film_grain is False


def test_options_survive_a_reload_and_corrupt_files_fall_back():
    proj = project_service.create_project(ProjectCreate(name="Options Reload"))
    render_options_service.update(proj.id, preset="energetic_reel")
    assert render_options_service.get(proj.id).preset == "energetic_reel"

    # A hand-edited/corrupt file must not break a render.
    render_options_service.storage.get_render_options_path(proj.id).write_text("{not json")
    fallback = render_options_service.get(proj.id)
    assert fallback.preset == "cinematic_luxury"


# ── API surface ──────────────────────────────────────────────────────────

def test_api_lists_presets_with_a_recommendation():
    resp = client.get("/api/projects/render-options/presets")
    assert resp.status_code == 200
    presets = resp.json()["data"]
    assert {p["id"] for p in presets} >= {"cinematic_luxury", "energetic_reel", "quick_draft"}
    assert [p["id"] for p in presets if p["recommended"]] == ["cinematic_luxury"]
    assert all(p["label"] and p["description"] for p in presets)


def test_api_get_and_patch_render_options():
    proj = project_service.create_project(ProjectCreate(name="Options API"))

    initial = client.get(f"/api/projects/{proj.id}/render-options")
    assert initial.status_code == 200
    assert initial.json()["data"]["preset"] == "cinematic_luxury"

    patched = client.patch(
        f"/api/projects/{proj.id}/render-options",
        json={"preset": "energetic_reel", "options": {"music_volume": 0.4}},
    )
    assert patched.status_code == 200
    data = patched.json()["data"]
    assert data["preset"] == "energetic_reel"
    assert data["aspect_ratio"] == "9:16"
    assert data["music_volume"] == 0.4

    # And it is persisted, not just echoed.
    assert client.get(f"/api/projects/{proj.id}/render-options").json()["data"]["preset"] == "energetic_reel"


def test_api_rejects_an_unknown_preset():
    proj = project_service.create_project(ProjectCreate(name="Options Bad Preset"))
    resp = client.patch(f"/api/projects/{proj.id}/render-options", json={"preset": "nope"})
    assert resp.status_code >= 400
    assert resp.json()["success"] is False


def test_api_render_options_for_unknown_project_is_404():
    assert client.get("/api/projects/project_does_not_exist/render-options").status_code == 404


def test_generation_overview_reports_the_active_render_options_and_staleness():
    """The overview must expose the active style so the studio can render its controls."""
    proj = project_service.create_project(ProjectCreate(name="Options Overview"))
    _seed_single_scene_plan(proj.id)

    overview = client.get(f"/api/projects/{proj.id}/generation")
    assert overview.status_code == 200
    data = overview.json()["data"]
    assert data["render_options"]["preset"] == "cinematic_luxury"
    # No clips yet, so nothing can be stale.
    assert data["clips_outdated"] is False


def test_rendered_clips_are_reported_stale_after_the_options_change():
    """Changing an option that reshapes the clips must invalidate them."""
    from app.services.video_generation import video_generation_service

    proj = project_service.create_project(ProjectCreate(name="Stale Clips"))
    _seed_single_scene_plan(proj.id)

    render_options_service.storage.save_generation_json(
        proj.id,
        {
            "jobs": [],
            "clips": [
                {
                    "scene_id": "scene_only",
                    "image_id": "img_1",
                    "clip_filename": "clip_only.mp4",
                    "clip_path": "projects/x/clips/clip_only.mp4",
                    "clip_url": "/api/projects/x/clips/scene_only/file",
                    "duration_seconds": 4.0,
                    "width": 1920,
                    "height": 1080,
                    "file_size_bytes": 10,
                    "provider": "local_kenburns",
                    "model": "cinematic-affine-2.5d",
                    "camera_motion": "slow_forward",
                    "prompt": "p",
                    "render_signature": "signature-of-the-old-settings",
                }
            ],
        },
    )

    stale = video_generation_service.get_or_create_overview(proj.id)
    assert stale.clips_outdated is True

    # Re-saving the current fingerprint makes them current again.
    saved = render_options_service.storage.load_generation_json(proj.id)
    saved["clips"][0]["render_signature"] = render_options_service.get(proj.id).generation_signature()
    render_options_service.storage.save_generation_json(proj.id, saved)

    assert video_generation_service.get_or_create_overview(proj.id).clips_outdated is False
