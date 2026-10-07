from pathlib import Path

import httpx
import pytest

from app.core.config import settings
from app.core.errors import AppException
from app.services.video_generation.fallback_provider import DEFAULT_FALLBACK_CODES, FallbackProvider
from app.services.video_generation.factory import build_video_provider
from app.services.video_generation.json2video_provider import (
    _DEFAULT_EFFECTS,
    _MOTION_EFFECTS,
    JSON2VideoProvider,
)
from app.services.video_generation.kenburns_provider import KenBurnsProvider

PROJECT_ID = "JkGxEoPRF9EgRb32"
CLIP_BYTES = b"\x00\x00\x00\x18ftypmp42fake-rendered-clip"


def _make_source(tmp_path: Path) -> Path:
    """Mirrors the real upload layout: projects/<pid>/uploads/img_<hex>_<orig>.

    A genuinely decodable JPEG so the local fallback provider can also render it.
    """
    import cv2
    import numpy as np

    upload_dir = tmp_path / "storage" / "projects" / "project_test123" / "uploads"
    upload_dir.mkdir(parents=True)
    path = upload_dir / "img_aee57278c93c_exterior.jpg"
    image = np.zeros((360, 640, 3), dtype=np.uint8)
    image[:, :320] = (200, 180, 160)
    image[:, 320:] = (90, 110, 130)
    cv2.imwrite(str(path), image)
    return path


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0)


def _provider(client: httpx.AsyncClient, **kwargs) -> JSON2VideoProvider:
    return JSON2VideoProvider(
        api_key="test-key",
        public_base_url="https://tunnel.example.com",
        client=client,
        **kwargs,
    )


def _happy_handler(statuses):
    """Serves submit -> poll sequence -> clip download."""
    state = {"polls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.headers["x-api-key"] == "test-key"
            return httpx.Response(200, json={"success": True, "project": PROJECT_ID})

        if "assets.example.com" in str(request.url):
            return httpx.Response(200, content=CLIP_BYTES)

        # status poll
        idx = min(state["polls"], len(statuses) - 1)
        payload = statuses[idx]
        state["polls"] += 1
        return httpx.Response(200, json={"success": True, "movie": payload})

    return handler


def test_resolves_public_image_url_from_stored_upload(tmp_path):
    provider = _provider(_client(lambda r: httpx.Response(200, json={})))
    url = provider._resolve_public_image_url(_make_source(tmp_path))
    assert url == (
        "https://tunnel.example.com/api/projects/project_test123/images/img_aee57278c93c/file"
    )


@pytest.mark.asyncio
async def test_generates_clip_via_json2video(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "JSON2VIDEO_POLL_INTERVAL_SECONDS", 0.01)
    source = _make_source(tmp_path)
    output = tmp_path / "clip.mp4"
    handler = _happy_handler(
        [
            {"status": "pending"},
            {"status": "running"},
            {"status": "done", "url": "https://assets.example.com/renders/clip.mp4", "duration": 4.5, "rendering_time": 30},
        ]
    )

    provider = _provider(_client(handler))
    result = await provider.generate_clip(
        source_image_path=source,
        prompt="cinematic walkthrough",
        negative_prompt=None,
        duration_seconds=4.5,
        camera_motion="pan_right",
        output_path=output,
    )

    assert output.read_bytes() == CLIP_BYTES
    assert result.provider_name == "json2video"
    assert result.provider_job_id == PROJECT_ID
    assert result.duration_seconds == 4.5
    assert result.raw_metadata["camera_motion"] == "pan_right"
    assert result.raw_metadata["synthetic_pixels"] is False


def test_movie_json_uses_real_photo_and_motion_effects(tmp_path):
    provider = _provider(_client(lambda r: httpx.Response(200, json={})))
    url = provider._resolve_public_image_url(_make_source(tmp_path))
    movie = provider._build_movie_json(url, 4.0, "pan_left")

    element = movie["scenes"][0]["elements"][0]
    assert element["type"] == "image"
    assert element["src"] == url  # the real photograph, not synthesized pixels
    assert element["duration"] == 4.0
    assert element["pan"] == "left"
    assert movie["resolution"] == "full-hd"


def test_zoom_is_always_an_integer():
    """Regression: the live API rejects a float zoom asynchronously (only on the status
    poll) with \"Property 'zoom' is not an integer\", despite the docs saying 'number'."""
    for motion, effects in {**_MOTION_EFFECTS, "_default": _DEFAULT_EFFECTS}.items():
        if "zoom" in effects:
            assert isinstance(effects["zoom"], int) and not isinstance(effects["zoom"], bool), (
                f"motion '{motion}' must send an integer zoom, got {effects['zoom']!r}"
            )


@pytest.mark.asyncio
async def test_malformed_payload_is_not_masked_by_fallback(tmp_path, monkeypatch):
    """A schema rejection means this provider built a bad request. It must surface as a
    structural error rather than silently degrading to the local renderer."""
    monkeypatch.setattr(settings, "JSON2VIDEO_POLL_INTERVAL_SECONDS", 0.01)
    handler = _happy_handler(
        [{"status": "error", "message": "Property 'zoom' is not an integer in movie/scenes[0]/elements[0]"}]
    )
    provider = _provider(_client(handler))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "pan_left", tmp_path / "c.mp4")
    assert exc.value.code == "PROVIDER_REQUEST_REJECTED"
    assert exc.value.code not in DEFAULT_FALLBACK_CODES


@pytest.mark.asyncio
async def test_submit_retries_transient_5xx_then_succeeds(tmp_path, monkeypatch):
    """The docs say a 5xx means no movie was created — so retry instead of degrading."""
    monkeypatch.setattr(settings, "JSON2VIDEO_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(settings, "JSON2VIDEO_BACKOFF_SECONDS", 0.01)
    calls = {"n": 0}
    polled = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(500, json={"message": "Error starting subprocess"})
            return httpx.Response(200, json={"success": True, "project": PROJECT_ID})
        if "assets.example.com" in str(request.url):
            return httpx.Response(200, content=CLIP_BYTES)
        polled["n"] += 1
        return httpx.Response(200, json={"success": True, "movie": {"status": "done", "url": "https://assets.example.com/renders/c.mp4", "duration": 4.0}})

    provider = _provider(_client(handler))
    out = tmp_path / "c.mp4"
    result = await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "pan_left", out)

    assert calls["n"] == 2, "should have retried the 500 once"
    assert result.provider_job_id == PROJECT_ID
    assert out.read_bytes() == CLIP_BYTES


@pytest.mark.asyncio
async def test_submit_gives_up_after_max_retries(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "JSON2VIDEO_BACKOFF_SECONDS", 0.01)
    monkeypatch.setattr(settings, "JSON2VIDEO_MAX_RETRIES", 2)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, json={"message": "Error storing movie JSON"})

    provider = _provider(_client(handler))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "pan_left", tmp_path / "c.mp4")
    assert calls["n"] == 2, "should stop after JSON2VIDEO_MAX_RETRIES attempts"
    assert exc.value.code == "UNKNOWN_GENERATION_ERROR"


@pytest.mark.asyncio
async def test_polling_survives_transient_5xx(tmp_path, monkeypatch):
    """A blip while polling must not abandon a render that is still in flight server-side."""
    monkeypatch.setattr(settings, "JSON2VIDEO_POLL_INTERVAL_SECONDS", 0.01)
    polls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"success": True, "project": PROJECT_ID})
        if "assets.example.com" in str(request.url):
            return httpx.Response(200, content=CLIP_BYTES)
        polls["n"] += 1
        if polls["n"] == 1:
            return httpx.Response(503, json={"message": "temporarily unavailable"})
        return httpx.Response(200, json={"success": True, "movie": {"status": "done", "url": "https://assets.example.com/renders/c.mp4", "duration": 4.0}})

    provider = _provider(_client(handler))
    out = tmp_path / "c.mp4"
    result = await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "pan_left", out)
    assert polls["n"] == 2
    assert out.read_bytes() == CLIP_BYTES


@pytest.mark.asyncio
async def test_missing_api_key_is_not_configured(tmp_path):
    provider = JSON2VideoProvider(api_key="", public_base_url="https://x", client=_client(lambda r: httpx.Response(200, json={})))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "pan_left", tmp_path / "c.mp4")
    assert exc.value.code == "PROVIDER_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_missing_public_base_url_is_not_configured(tmp_path):
    provider = JSON2VideoProvider(api_key="test-key", public_base_url="", client=_client(lambda r: httpx.Response(200, json={})))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "pan_left", tmp_path / "c.mp4")
    assert exc.value.code == "PROVIDER_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_submit_quota_exhaustion_maps_to_rate_limit(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "You exceeded the quota of movies in your plan."})

    provider = _provider(_client(handler))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "pan_left", tmp_path / "c.mp4")
    assert exc.value.code == "PROVIDER_RATE_LIMIT"


@pytest.mark.asyncio
async def test_render_error_maps_to_generation_error(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "JSON2VIDEO_POLL_INTERVAL_SECONDS", 0.01)
    handler = _happy_handler([{"status": "error", "message": "media could not be downloaded"}])
    provider = _provider(_client(handler))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "pan_left", tmp_path / "c.mp4")
    assert exc.value.code == "UNKNOWN_GENERATION_ERROR"
    assert "media could not be downloaded" in exc.value.message


@pytest.mark.asyncio
async def test_render_timeout_when_poll_budget_exceeded(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "JSON2VIDEO_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(settings, "JSON2VIDEO_TIMEOUT_SECONDS", 0.05)
    provider = _provider(_client(_happy_handler([{"status": "running"}])))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "pan_left", tmp_path / "c.mp4")
    assert exc.value.code == "PROVIDER_TIMEOUT"


def test_factory_selects_json2video_with_local_fallback(monkeypatch):
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "json2video")
    monkeypatch.setattr(settings, "VIDEO_FALLBACK_TO_LOCAL", True)
    provider = build_video_provider()
    assert isinstance(provider, FallbackProvider)
    assert isinstance(provider.primary, JSON2VideoProvider)
    assert isinstance(provider.fallback, KenBurnsProvider)


def test_auto_prefers_json2video_only_when_fully_configured(monkeypatch):
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "auto")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", None)
    monkeypatch.setattr(settings, "VIDEO_API_KEY", None)

    # Key present but no public base URL -> cannot fetch photos -> not usable.
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", "test-key")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", None)
    assert isinstance(build_video_provider(), KenBurnsProvider)

    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://tunnel.example.com")
    assert isinstance(build_video_provider().primary, JSON2VideoProvider)

    # Nothing configured at all -> straight to the local renderer.
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", None)
    assert isinstance(build_video_provider(), KenBurnsProvider)


@pytest.mark.asyncio
async def test_unconfigured_json2video_degrades_to_local_render(tmp_path, monkeypatch):
    """The core free-tier guarantee: a mis/quota-limited remote never dead-ends a job."""
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "json2video")
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", None)  # simulate unconfigured/quota-less
    source = _make_source(tmp_path)
    output = tmp_path / "clip.mp4"

    provider = build_video_provider()
    assert isinstance(provider, FallbackProvider)

    result = await provider.generate_clip(
        source_image_path=source,
        prompt="p",
        negative_prompt=None,
        duration_seconds=1.0,
        camera_motion="slow_forward",
        output_path=output,
    )

    # The clip was rendered locally even though the selected remote was unusable.
    assert result.provider_name == "local_kenburns"
    assert output.exists() and output.stat().st_size > 0

    import cv2

    cap = cv2.VideoCapture(str(output))
    ok, _ = cap.read()
    cap.release()
    assert ok, "degraded clip should be a decodable video"
