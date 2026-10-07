from pathlib import Path

import cv2
import numpy as np
import pytest

from app.core.config import settings
from app.core.errors import AppException
from app.services.video_generation.base import ImageToVideoProvider, ProviderResult
from app.services.video_generation.fallback_provider import FallbackProvider
from app.services.video_generation.factory import build_video_provider
from app.services.video_generation.gemini_veo_provider import GeminiVeoProvider
from app.services.video_generation.kenburns_provider import KenBurnsProvider
from app.services.video_generation.video_validator import VideoValidator


def _make_source_image(path: Path, width: int = 1280, height: int = 720) -> Path:
    """A high-contrast pattern so camera motion produces visible frame differences."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for x in range(0, width, 40):
        img[:, x : x + 20] = (255, 255, 255)
    for y in range(0, height, 40):
        img[y : y + 20, :] = np.maximum(img[y : y + 20, :], 80)
    cv2.imwrite(str(path), img)
    return path


@pytest.mark.asyncio
async def test_kenburns_provider_generates_valid_motion_clip(tmp_path):
    source = _make_source_image(tmp_path / "room.jpg")
    provider = KenBurnsProvider(width=640, height=360, fps=24.0)
    output = tmp_path / "clip.mp4"

    result = await provider.generate_clip(
        source_image_path=source,
        prompt="cinematic walkthrough",
        negative_prompt=None,
        duration_seconds=2.0,
        camera_motion="slow_forward",
        output_path=output,
    )

    assert output.exists()
    assert result.provider_name == "local_kenburns"

    valid, meta, quality, err = VideoValidator.validate_and_extract_metadata(output)
    assert valid, err
    assert meta["width"] == 640
    assert meta["height"] == 360
    assert meta["duration_seconds"] >= 1.8

    # Camera motion must actually move pixels between the first and last frame.
    cap = cv2.VideoCapture(str(output))
    ok_first, first = cap.read()
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_count - 1))
    ok_last, last = cap.read()
    cap.release()
    assert ok_first and ok_last
    diff = float(np.abs(first.astype(np.int16) - last.astype(np.int16)).mean())
    assert diff > 1.0, f"Expected visible camera motion, frame difference was {diff}"


@pytest.mark.asyncio
async def test_kenburns_is_deterministic(tmp_path):
    source = _make_source_image(tmp_path / "room.jpg")
    provider = KenBurnsProvider(width=320, height=180, fps=24.0)

    out_a = tmp_path / "a.mp4"
    out_b = tmp_path / "b.mp4"
    await provider.generate_clip(source, "p", None, 1.0, "pan_right", out_a)
    await provider.generate_clip(source, "p", None, 1.0, "pan_right", out_b)

    cap_a = cv2.VideoCapture(str(out_a))
    cap_b = cv2.VideoCapture(str(out_b))
    _, fa = cap_a.read()
    _, fb = cap_b.read()
    cap_a.release()
    cap_b.release()
    assert np.array_equal(fa, fb), "Local provider should be deterministic for a given plan"


def test_factory_selects_configured_provider(monkeypatch):
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "kenburns")
    assert isinstance(build_video_provider(), KenBurnsProvider)

    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "gemini_veo")
    assert isinstance(build_video_provider(), GeminiVeoProvider)

    # Pin the auto-selection inputs so this stays deterministic regardless of the
    # developer's local .env / shell environment.
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "auto")
    monkeypatch.setattr(settings, "VIDEO_FALLBACK_TO_LOCAL", True)
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", None)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key")
    provider = build_video_provider()
    assert isinstance(provider, FallbackProvider)
    assert isinstance(provider.primary, GeminiVeoProvider)
    assert isinstance(provider.fallback, KenBurnsProvider)


class _FailingProvider(ImageToVideoProvider):
    def __init__(self, code: str):
        self.code = code
        self.calls = 0

    def get_provider_name(self) -> str:
        return "fake_remote"

    def get_model_name(self) -> str:
        return "fake-model"

    async def generate_clip(
        self, source_image_path, prompt, negative_prompt, duration_seconds, camera_motion, output_path, options=None
    ):
        self.calls += 1
        raise AppException(code=self.code, message="simulated provider failure", status_code=429)


@pytest.mark.asyncio
async def test_fallback_provider_degrades_on_quota(tmp_path):
    source = _make_source_image(tmp_path / "room.jpg", width=640, height=360)
    primary = _FailingProvider("PROVIDER_RATE_LIMIT")
    fallback = KenBurnsProvider(width=320, height=180, fps=24.0)
    provider = FallbackProvider(primary, fallback)
    output = tmp_path / "clip.mp4"

    result = await provider.generate_clip(source, "p", None, 1.0, "slow_forward", output)

    assert primary.calls == 1
    assert output.exists()
    assert result.provider_name == "local_kenburns"


@pytest.mark.asyncio
async def test_fallback_provider_propagates_non_capacity_errors(tmp_path):
    source = _make_source_image(tmp_path / "room.jpg", width=640, height=360)
    primary = _FailingProvider("SOURCE_IMAGE_ERROR")
    fallback = KenBurnsProvider(width=320, height=180, fps=24.0)
    provider = FallbackProvider(primary, fallback)

    with pytest.raises(AppException) as exc:
        await provider.generate_clip(source, "p", None, 1.0, "slow_forward", tmp_path / "clip.mp4")
    assert exc.value.code == "SOURCE_IMAGE_ERROR"
