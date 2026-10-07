"""Tests for the 2.5D depth parallax renderer.

The headline claim of this feature is mechanical, and therefore testable: given a
depth map, the near plane of the frame must move further than the far plane when
the virtual camera translates. These tests inject a synthetic depth map and a pair
of trackable markers, so the behaviour is verified without depending on the depth
model file being present and without depending on any particular photograph.

The control case matters as much as the positive one: with no depth, the same shot
must be a rigid translation, i.e. the two markers must move by the same amount.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.core.config import settings
from app.services.video_generation.depth_estimator import DepthEstimator
from app.services.video_generation.kenburns_provider import KenBurnsProvider


class _FakeDepthEstimator:
    """Stands in for the ONNX model so these tests stay hermetic and fast."""

    def __init__(self, depth: np.ndarray):
        self._depth = depth

    def estimate(self, image_bgr: np.ndarray):
        return self._depth.copy()

    def is_available(self) -> bool:
        return True


# Half-size of the local search window used to re-find a marker. The camera
# travels a long way horizontally (and the near plane further still), while the
# two markers are only separated vertically — so the window is wide in x and tight
# in y, large enough to follow the motion but never wide enough to drift onto the
# other marker.
_TRACK_RADIUS_X = 280
_TRACK_RADIUS_Y = 70


def _scene_with_markers(width: int = 640, height: int = 360):
    """A lightly textured plate with two high-contrast, trackable markers.

    Both markers sit at the same x so that any radial (zoom) component of the warp
    affects them symmetrically, leaving translation as the only variable. They are
    drawn with *inverted* centres so ``matchTemplate`` can never confuse one for the
    other: with two identical bulls-eyes the tracker happily reports the wrong
    marker, which shows up as a nonsense displacement rather than a real failure.
    """
    rng = np.random.default_rng(7)
    image = (58 + rng.integers(0, 38, size=(height, width, 3))).astype(np.uint8)
    markers = [(width // 2, height // 4), (width // 2, 3 * height // 4)]
    for index, (cx, cy) in enumerate(markers):
        outer, inner, core = ((255, 255, 255), (0, 0, 0), (255, 255, 255))
        if index % 2:
            outer, inner, core = inner, outer, inner
        image[cy - 14 : cy + 14, cx - 14 : cx + 14] = outer
        image[cy - 8 : cy + 8, cx - 8 : cx + 8] = inner
        image[cy - 3 : cy + 3, cx - 3 : cx + 3] = core
    return image, markers


def _read_all_frames(path: Path):
    cap = cv2.VideoCapture(str(path))
    assert cap.isOpened()
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    assert frames
    return frames


def _track(
    frame: np.ndarray,
    template: np.ndarray,
    size: int = 36,
    around: tuple | None = None,
):
    """Finds a marker patch in a frame; returns its centre and the match score.

    ``around`` limits the search to a window centred on where the marker started,
    so the tracker follows *this* marker rather than the best-looking patch in the
    whole frame.
    """
    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    if around is not None:
        cx, cy = around
        x0 = max(0, int(cx - size / 2.0) - _TRACK_RADIUS_X)
        y0 = max(0, int(cy - size / 2.0) - _TRACK_RADIUS_Y)
        x1 = min(result.shape[1], int(cx - size / 2.0) + _TRACK_RADIUS_X + 1)
        y1 = min(result.shape[0], int(cy - size / 2.0) + _TRACK_RADIUS_Y + 1)
        window = result[y0:y1, x0:x1]
        _, score, _, location = cv2.minMaxLoc(window)
        location = (location[0] + x0, location[1] + y0)
    else:
        _, score, _, location = cv2.minMaxLoc(result)
    return np.array([location[0] + size / 2.0, location[1] + size / 2.0]), float(score)


def _marker_displacements(frames, markers):
    """Displacement of each marker between the first and last frame."""
    first, last = frames[0], frames[-1]
    size = 36
    displacements = []
    for cx, cy in markers:
        template = first[cy - size // 2 : cy + size // 2, cx - size // 2 : cx + size // 2]
        start, _ = _track(first, template, size, around=(cx, cy))
        end, score = _track(last, template, size, around=(cx, cy))
        assert score > 0.4, f"marker tracking was unreliable (score {score:.2f})"
        displacements.append(end - start)
    return displacements


def test_depth_estimator_without_a_model_is_unavailable(tmp_path):
    estimator = DepthEstimator(model_path=tmp_path / "missing.onnx")

    assert estimator.is_available() is False


@pytest.mark.asyncio
async def test_kenburns_reports_that_depth_was_unavailable(tmp_path):
    """A missing model must degrade to the flat camera, never fail the render."""
    image, _ = _scene_with_markers(width=320, height=180)
    source = tmp_path / "scene.png"
    cv2.imwrite(str(source), image)

    provider = KenBurnsProvider(
        width=320,
        height=180,
        fps=24.0,
        depth_estimator=DepthEstimator(model_path=tmp_path / "missing.onnx"),
    )
    output = tmp_path / "clip.mp4"

    result = await provider.generate_clip(
        source_image_path=source,
        prompt="",
        negative_prompt=None,
        duration_seconds=1.0,
        camera_motion="pan_left",
        output_path=output,
        options={"depth_parallax": True},
    )

    assert output.exists()
    assert result.raw_metadata["depth_parallax"] is False
    assert result.raw_metadata["synthetic_pixels"] is False


@pytest.mark.asyncio
async def test_depth_parallax_moves_the_near_plane_further_than_the_far_plane(
    tmp_path, monkeypatch
):
    image, markers = _scene_with_markers()
    height, width = image.shape[:2]
    source = tmp_path / "scene.png"
    cv2.imwrite(str(source), image)

    # Top half is nearer the camera than the bottom half.
    depth = np.zeros((height, width), dtype=np.float32)
    depth[: height // 2] = 1.0

    # Isolate translation: the depth-proportional magnification is a separate,
    # radial effect that would muddy exactly what this test measures.
    monkeypatch.setattr(settings, "DEPTH_ZOOM_PARALLAX", 0.0)

    provider = KenBurnsProvider(
        width=width,
        height=height,
        fps=24.0,
        depth_estimator=_FakeDepthEstimator(depth),
    )
    output = tmp_path / "parallax.mp4"

    result = await provider.generate_clip(
        source_image_path=source,
        prompt="",
        negative_prompt=None,
        duration_seconds=1.0,
        camera_motion="pan_left",
        output_path=output,
        options={
            "depth_parallax": True,
            "motion_blur": False,
            "camera_variety": False,
            "scene_index": 0,
        },
    )
    assert result.raw_metadata["depth_parallax"] is True

    near_disp, far_disp = _marker_displacements(_read_all_frames(output), markers)

    # The near marker must travel a long way relative to the far one.
    differential = float(np.linalg.norm(near_disp - far_disp))
    assert differential > 15.0, (
        f"depth parallax did not separate the planes (differential {differential:.1f}px, "
        f"near {near_disp}, far {far_disp})"
    )


@pytest.mark.asyncio
async def test_flat_camera_without_depth_moves_both_planes_together(tmp_path):
    """The control for the parallax test: no depth means one rigid translation."""
    image, markers = _scene_with_markers()
    height, width = image.shape[:2]
    source = tmp_path / "scene.png"
    cv2.imwrite(str(source), image)

    provider = KenBurnsProvider(
        width=width,
        height=height,
        fps=24.0,
        depth_estimator=_FakeDepthEstimator(np.ones((height, width), dtype=np.float32)),
    )
    output = tmp_path / "flat.mp4"

    result = await provider.generate_clip(
        source_image_path=source,
        prompt="",
        negative_prompt=None,
        duration_seconds=1.0,
        camera_motion="pan_left",
        output_path=output,
        options={"depth_parallax": False, "camera_variety": False, "scene_index": 0},
    )
    assert result.raw_metadata["depth_parallax"] is False

    near_disp, far_disp = _marker_displacements(_read_all_frames(output), markers)

    differential = float(np.linalg.norm(near_disp - far_disp))
    assert differential < 5.0, (
        f"a flat camera move should be a rigid translation (differential "
        f"{differential:.1f}px, near {near_disp}, far {far_disp})"
    )
    # And it must still actually move.
    assert float(np.linalg.norm(near_disp)) > 2.0
