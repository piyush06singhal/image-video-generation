import json
from pathlib import Path

import cv2
import httpx
import numpy as np
import pytest

from app.core.config import settings
from app.core.errors import AppException
from app.services.video_generation.fallback_provider import DEFAULT_FALLBACK_CODES, FallbackProvider
from app.services.video_generation.factory import build_video_provider
from app.services.video_generation.kenburns_provider import KenBurnsProvider
from app.services.video_generation.magic_hour_provider import MagicHourProvider, _snap_duration

# A fake host: every request is served by the MockTransport handler, so a live
# Magic Hour call is impossible even if the developer's .env holds a real key.
API_URL = "https://api.test.magichour.local/v1"
JOB_ID = "clx1234567890"
UPLOADED_PATH = "api-assets/id/img_aee57278c93c.jpg"
CLIP_BYTES = b"\x00\x00\x00\x18ftypmp42fake-generated-clip"


def _make_source(tmp_path: Path) -> Path:
    """Mirrors the real upload layout: projects/<pid>/uploads/img_<hex>_<orig>.

    A genuinely decodable JPEG so the local fallback provider can also render it.
    """
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


def _provider(client: httpx.AsyncClient, **kwargs) -> MagicHourProvider:
    kwargs.setdefault("resolution", "720p")
    return MagicHourProvider(api_key="test-key", api_url=API_URL, client=client, **kwargs)


def _handler(statuses, *, created=None, uploads=None, upload_status=200, job_status=200, job_body=None):
    """Serves upload-URL request -> signed PUT -> job create -> poll -> download."""
    state = {"polls": 0}
    created = created if created is not None else []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)

        if url.endswith("/files/upload-urls"):
            assert request.headers["authorization"] == "Bearer test-key"
            if upload_status != 200:
                return httpx.Response(upload_status, json={"code": "unauthorized", "message": "bad key"})
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "upload_url": "https://upload.example.com/signed/photo.jpg?X-Amz=1",
                            "expires_at": "2026-10-01T00:00:00.000Z",
                            "file_path": UPLOADED_PATH,
                        }
                    ]
                },
            )

        if request.method == "PUT":
            # Documented: the pre-signed URL is PUT *without* the bearer token.
            assert request.headers.get("authorization") is None
            if uploads is not None:
                uploads.append(request.content)
            return httpx.Response(200, content=b"")

        if url.endswith("/image-to-video"):
            created.append(json.loads(request.content))
            if job_status != 200:
                return httpx.Response(job_status, json=job_body or {})
            return httpx.Response(200, json={"id": JOB_ID, "credits_charged": 450})

        if url.startswith("https://cdn.example.com/"):
            return httpx.Response(200, content=CLIP_BYTES)

        idx = min(state["polls"], len(statuses) - 1)
        state["polls"] += 1
        return httpx.Response(200, json=statuses[idx])

    return handler


COMPLETED = {
    "status": "complete",
    "model": "kling-3.0",
    "duration": 4.0,
    "fps": 24,
    "credits_charged": 450,
    "downloads": [{"url": "https://cdn.example.com/out.mp4", "expires_at": "2026-10-08T00:00:00Z"}],
}


# ── duration snapping ────────────────────────────────────────────────────────
def test_snaps_duration_to_values_the_model_accepts():
    """``end_seconds`` is an integer from a per-model set, so 4.5 must not be sent raw."""
    # 4.5 -> 4 for the project's house style (ties go to the shorter clip).
    assert _snap_duration(None, 4.5) == 4
    assert _snap_duration("kling-3.0", 4.5) == 4
    # kling-2.6 only accepts 5 and 10.
    assert _snap_duration("kling-2.6", 4.0) == 5
    # veo3.1 only accepts 4/6/8/16/...
    assert _snap_duration("veo3.1", 5.0) == 4
    # Exactly between 6 and 8 the shorter clip wins, so a walkthrough never
    # silently gains seconds the user did not ask for.
    assert _snap_duration("veo3.1", 7.0) == 6
    assert _snap_duration("veo3.1", 7.1) == 8
    # Every value produced in this project's range is a legal integer.
    for model in (None, "kling-3.0", "ltx-2.5", "veo3.1", "wan-2.2"):
        for requested in (0.5, 1.0, 3.0, 4.5, 6.0, 12.0, 60.0):
            assert isinstance(_snap_duration(model, requested), int)


# ── happy path ───────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_creates_job_from_uploaded_photo_and_downloads_clip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(settings, "MAGIC_HOUR_AUDIO", False)
    created: list = []
    provider = _provider(_client(_handler([{"status": "queued"}, {"status": "rendering"}, COMPLETED], created=created)))
    output = tmp_path / "clip.mp4"

    result = await provider.generate_clip(
        source_image_path=_make_source(tmp_path),
        prompt="Smooth cinematic walkthrough of this Living Room.",
        negative_prompt=None,
        duration_seconds=4.5,
        camera_motion="slow_forward",
        output_path=output,
    )

    assert output.read_bytes() == CLIP_BYTES
    assert result.provider_name == "magic_hour"
    assert result.provider_job_id == JOB_ID
    assert result.duration_seconds == 4.0
    assert result.model_name == "kling-3.0"
    assert result.raw_metadata["synthetic_pixels"] is True
    assert result.raw_metadata["credits_charged"] == 450

    payload = created[0]
    # The photo was handed over by upload, so no PUBLIC_BASE_URL / tunnel is needed.
    assert payload["assets"]["image_file_path"] == UPLOADED_PATH
    assert "http" not in payload["assets"]["image_file_path"]
    assert result.raw_metadata["asset_handoff"] == "upload"
    assert payload["end_seconds"] == 4 and isinstance(payload["end_seconds"], int)
    assert payload["resolution"] == "720p"
    # The assembler owns the soundtrack, so model audio stays off unless asked for.
    assert payload["audio"] is False
    # The model is only pinned when explicitly configured (plan-aware default).
    assert "model" not in payload
    assert payload["style"]["prompt"].startswith("Smooth cinematic walkthrough of this Living Room.")


@pytest.mark.asyncio
async def test_prompt_carries_camera_move_and_fidelity_clause(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    created: list = []
    provider = _provider(_client(_handler([COMPLETED], created=created)))
    await provider.generate_clip(
        _make_source(tmp_path), "walkthrough", None, 4.0, "pan_left", tmp_path / "c.mp4"
    )

    prompt = created[0]["style"]["prompt"]
    assert "Pan the camera smoothly to the left." in prompt
    # The generative risk is the model redecorating the property; say so plainly.
    assert "do not add, remove or move any object" in prompt

    # An unknown motion still gets a usable instruction.
    assert "slow, smooth, steady cinematic camera move" in provider._build_style_prompt("x", "not_a_move")


@pytest.mark.asyncio
async def test_model_and_audio_are_pinned_when_configured(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(settings, "MAGIC_HOUR_AUDIO", True)
    created: list = []
    provider = _provider(_client(_handler([COMPLETED], created=created)), model="veo3.1")
    result = await provider.generate_clip(
        _make_source(tmp_path), "p", None, 7.0, "gentle_orbit", tmp_path / "c.mp4"
    )

    assert created[0]["model"] == "veo3.1"
    assert created[0]["audio"] is True
    assert created[0]["end_seconds"] == 6  # snapped to veo3.1's legal set
    # The API's reported model wins over the requested one in the result.
    assert result.model_name == "kling-3.0"


# ── plan / resolution recovery ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_plan_rejection_downgrades_resolution_instead_of_failing(tmp_path, monkeypatch):
    """A free-tier key must not dead-end the walkthrough by asking for 1080p."""
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    created: list = []
    state = {"jobs": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/files/upload-urls"):
            return httpx.Response(200, json={"items": [{"upload_url": "https://upload.example.com/s", "file_path": UPLOADED_PATH}]})
        if request.method == "PUT":
            return httpx.Response(200, content=b"")
        if url.endswith("/image-to-video"):
            created.append(json.loads(request.content))
            state["jobs"] += 1
            if state["jobs"] == 1:
                return httpx.Response(
                    422,
                    json={"code": "unprocessable_entity", "message": "resolution 1080p requires a paid plan"},
                )
            return httpx.Response(200, json={"id": JOB_ID, "credits_charged": 200})
        if url.startswith("https://cdn.example.com/"):
            return httpx.Response(200, content=CLIP_BYTES)
        return httpx.Response(200, json=COMPLETED)

    provider = _provider(_client(handler), resolution="1080p")
    result = await provider.generate_clip(
        _make_source(tmp_path), "p", None, 4.0, "slow_forward", tmp_path / "c.mp4"
    )

    assert state["jobs"] == 2, "should retry once without the pinned resolution"
    assert created[0]["resolution"] == "1080p"
    assert "resolution" not in created[1]
    assert result.raw_metadata["requested_resolution"] == "1080p"
    assert result.raw_metadata["resolution"] == "plan-default"
    assert (tmp_path / "c.mp4").read_bytes() == CLIP_BYTES


# ── transport resilience ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_submit_retries_transient_5xx_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(settings, "MAGIC_HOUR_BACKOFF_SECONDS", 0.01)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/files/upload-urls"):
            return httpx.Response(200, json={"items": [{"upload_url": "https://upload.example.com/s", "file_path": UPLOADED_PATH}]})
        if request.method == "PUT":
            return httpx.Response(200, content=b"")
        if url.endswith("/image-to-video"):
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(503, json={"code": "internal_server_error", "message": "try later"})
            return httpx.Response(200, json={"id": JOB_ID, "credits_charged": 100})
        if url.startswith("https://cdn.example.com/"):
            return httpx.Response(200, content=CLIP_BYTES)
        return httpx.Response(200, json=COMPLETED)

    out = tmp_path / "c.mp4"
    result = await _provider(_client(handler)).generate_clip(
        _make_source(tmp_path), "p", None, 4.0, "slow_forward", out
    )
    assert calls["n"] == 2, "should have retried the 503 once"
    assert result.provider_job_id == JOB_ID
    assert out.read_bytes() == CLIP_BYTES


@pytest.mark.asyncio
async def test_submit_gives_up_after_max_retries(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_BACKOFF_SECONDS", 0.01)
    monkeypatch.setattr(settings, "MAGIC_HOUR_MAX_RETRIES", 2)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/files/upload-urls"):
            return httpx.Response(200, json={"items": [{"upload_url": "https://upload.example.com/s", "file_path": UPLOADED_PATH}]})
        if request.method == "PUT":
            return httpx.Response(200, content=b"")
        calls["n"] += 1
        return httpx.Response(500, json={"code": "internal_server_error", "message": "down"})

    with pytest.raises(AppException) as exc:
        await _provider(_client(handler)).generate_clip(
            _make_source(tmp_path), "p", None, 4.0, "slow_forward", tmp_path / "c.mp4"
        )
    assert calls["n"] == 2, "should stop after MAGIC_HOUR_MAX_RETRIES attempts"
    assert exc.value.code == "UNKNOWN_GENERATION_ERROR"


@pytest.mark.asyncio
async def test_polling_survives_transient_5xx(tmp_path, monkeypatch):
    """A blip while polling must not abandon a render still in flight server-side."""
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    polls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/files/upload-urls"):
            return httpx.Response(200, json={"items": [{"upload_url": "https://upload.example.com/s", "file_path": UPLOADED_PATH}]})
        if request.method == "PUT":
            return httpx.Response(200, content=b"")
        if url.endswith("/image-to-video"):
            return httpx.Response(200, json={"id": JOB_ID, "credits_charged": 100})
        if url.startswith("https://cdn.example.com/"):
            return httpx.Response(200, content=CLIP_BYTES)
        polls["n"] += 1
        if polls["n"] == 1:
            return httpx.Response(503, json={"message": "temporarily unavailable"})
        return httpx.Response(200, json=COMPLETED)

    out = tmp_path / "c.mp4"
    result = await _provider(_client(handler)).generate_clip(
        _make_source(tmp_path), "p", None, 4.0, "slow_forward", out
    )
    assert polls["n"] == 2
    assert out.read_bytes() == CLIP_BYTES


# ── error taxonomy ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_render_error_status_raises_generation_error(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    provider = _provider(_client(_handler([{"status": "error", "message": "model failed to render"}])))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "slow_forward", tmp_path / "c.mp4")
    assert exc.value.code == "UNKNOWN_GENERATION_ERROR"
    assert "model failed to render" in exc.value.message


@pytest.mark.asyncio
async def test_canceled_render_degrades(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    provider = _provider(_client(_handler([{"status": "canceled"}])))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "slow_forward", tmp_path / "c.mp4")
    assert exc.value.code in DEFAULT_FALLBACK_CODES


@pytest.mark.asyncio
async def test_render_timeout_when_poll_budget_exceeded(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(settings, "MAGIC_HOUR_TIMEOUT_SECONDS", 0.05)
    provider = _provider(_client(_handler([{"status": "rendering"}])))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "slow_forward", tmp_path / "c.mp4")
    assert exc.value.code == "PROVIDER_TIMEOUT"


@pytest.mark.asyncio
async def test_complete_without_download_url_is_a_download_error(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    provider = _provider(_client(_handler([{"status": "complete", "downloads": []}])))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "slow_forward", tmp_path / "c.mp4")
    assert exc.value.code == "RESULT_DOWNLOAD_ERROR"


@pytest.mark.asyncio
async def test_insufficient_credits_maps_to_rate_limit(tmp_path):
    """Out of credits is a capacity problem: the walkthrough degrades locally."""
    provider = _provider(
        _client(_handler([], job_status=402, job_body={"code": "insufficient_credits", "message": "no credits"}))
    )
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "slow_forward", tmp_path / "c.mp4")
    assert exc.value.code == "PROVIDER_RATE_LIMIT"
    assert exc.value.code in DEFAULT_FALLBACK_CODES


@pytest.mark.asyncio
async def test_auth_failure_maps_to_auth_error_and_degrades(tmp_path):
    provider = _provider(_client(_handler([], upload_status=401)))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "slow_forward", tmp_path / "c.mp4")
    assert exc.value.code == "PROVIDER_AUTH_ERROR"
    assert exc.value.code in DEFAULT_FALLBACK_CODES


@pytest.mark.asyncio
async def test_malformed_payload_is_not_masked_by_fallback(tmp_path):
    """A schema rejection means this provider built a bad request; surface it."""
    provider = _provider(
        _client(_handler([], job_status=422, job_body={"code": "invalid_request", "message": "assets is required"}))
    )
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "slow_forward", tmp_path / "c.mp4")
    assert exc.value.code == "PROVIDER_REQUEST_REJECTED"
    assert exc.value.code not in DEFAULT_FALLBACK_CODES


@pytest.mark.asyncio
async def test_missing_api_key_is_not_configured(tmp_path):
    provider = MagicHourProvider(api_key="", api_url=API_URL, client=_client(lambda r: httpx.Response(200, json={})))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(_make_source(tmp_path), "p", None, 4.0, "slow_forward", tmp_path / "c.mp4")
    assert exc.value.code == "PROVIDER_NOT_CONFIGURED"
    assert exc.value.code in DEFAULT_FALLBACK_CODES


@pytest.mark.asyncio
async def test_missing_source_image_is_structural(tmp_path):
    provider = _provider(_client(lambda r: httpx.Response(200, json={})))
    with pytest.raises(AppException) as exc:
        await provider.generate_clip(tmp_path / "nope.jpg", "p", None, 4.0, "slow_forward", tmp_path / "c.mp4")
    assert exc.value.code == "SOURCE_IMAGE_ERROR"
    assert exc.value.code not in DEFAULT_FALLBACK_CODES


def test_unknown_configured_resolution_falls_back_to_the_plan_default():
    provider = MagicHourProvider(api_key="k", api_url=API_URL, resolution="9000p")
    assert provider._resolve_resolution() is None
    assert MagicHourProvider(api_key="k", api_url=API_URL, resolution="1440p")._resolve_resolution() == "1080p"


# ── factory / fallback wiring ────────────────────────────────────────────────
def test_factory_selects_magic_hour_with_local_fallback(monkeypatch):
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "magic_hour")
    monkeypatch.setattr(settings, "VIDEO_FALLBACK_TO_LOCAL", True)
    provider = build_video_provider()
    assert isinstance(provider, FallbackProvider)
    assert isinstance(provider.primary, MagicHourProvider)
    assert isinstance(provider.fallback, KenBurnsProvider)


def test_factory_accepts_magic_hour_spellings(monkeypatch):
    for spelling in ("magic_hour", "magichour", "magic-hour", "mh"):
        monkeypatch.setattr(settings, "VIDEO_PROVIDER", spelling)
        assert isinstance(build_video_provider().primary, MagicHourProvider)


def test_auto_prefers_magic_hour_over_veo_but_not_over_plate_rendering(monkeypatch):
    """Fidelity first: a plate-based cloud renderer outranks a generative one."""
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "auto")
    monkeypatch.setattr(settings, "VIDEO_FALLBACK_TO_LOCAL", True)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", None)
    monkeypatch.setattr(settings, "VIDEO_API_KEY", None)
    monkeypatch.setattr(settings, "MAGIC_HOUR_API_KEY", "test-magic-key")
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", None)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", None)

    assert isinstance(build_video_provider().primary, MagicHourProvider)

    # A fully configured JSON2Video still wins, because it never invents furniture.
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", "test-j2v-key")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://tunnel.example.com")
    from app.services.video_generation.json2video_provider import JSON2VideoProvider

    assert isinstance(build_video_provider().primary, JSON2VideoProvider)

    # Nothing configured -> straight to the local renderer.
    monkeypatch.setattr(settings, "JSON2VIDEO_API_KEY", None)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", None)
    monkeypatch.setattr(settings, "MAGIC_HOUR_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    assert isinstance(build_video_provider(), KenBurnsProvider)


@pytest.mark.asyncio
async def test_unconfigured_magic_hour_degrades_to_local_render(tmp_path, monkeypatch):
    """The core guarantee: a credit-less or mis-keyed Magic Hour never dead-ends a job."""
    monkeypatch.setattr(settings, "VIDEO_PROVIDER", "magic_hour")
    monkeypatch.setattr(settings, "MAGIC_HOUR_API_KEY", None)
    monkeypatch.setattr(settings, "VIDEO_FALLBACK_TO_LOCAL", True)
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

    assert result.provider_name == "local_kenburns"
    assert output.exists() and output.stat().st_size > 0

    cap = cv2.VideoCapture(str(output))
    ok, _ = cap.read()
    cap.release()
    assert ok, "degraded clip should be a decodable video"


# ── export-frame cropping ────────────────────────────────────────────────────
def _make_portrait_source(tmp_path: Path, width: int = 600, height: int = 1000) -> Path:
    """A portrait still, as a phone photo of a listing very often is."""
    upload_dir = tmp_path / "storage" / "projects" / "project_test123" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / "img_bbbbbbbbbbbb_living_room.jpg"
    image = np.full((height, width, 3), 20, dtype=np.uint8)
    middle = height // 2
    image[middle - 60 : middle + 60, :] = (240, 240, 240)
    cv2.imwrite(str(path), image)
    return path


@pytest.mark.asyncio
async def test_uploaded_asset_is_cropped_to_the_export_frame(tmp_path, monkeypatch):
    """Magic Hour mirrors the input still's aspect ratio, so a portrait photo must be
    cropped to the export frame *before* upload. Otherwise the model returns a portrait
    clip that the assembler has to cover-crop and upscale, which throws away most of the
    generated pixels (a live probe returned 522x784 and would have needed a 3.7x blowup)."""
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    uploads: list = []
    provider = _provider(_client(_handler([COMPLETED], uploads=uploads)))

    result = await provider.generate_clip(
        _make_portrait_source(tmp_path),
        "p",
        None,
        4.0,
        "slow_forward",
        tmp_path / "c.mp4",
        options={"width": 1920, "height": 1080, "fps": 30},
    )

    assert len(uploads) == 1
    uploaded = cv2.imdecode(np.frombuffer(uploads[0], np.uint8), cv2.IMREAD_COLOR)
    assert uploaded is not None
    height, width = uploaded.shape[:2]
    assert width == 600, "the crop must not resample the still"
    assert abs(width / height - 16 / 9) < 0.01
    # The centre band survives; the dark strips are the ones the assembler would have
    # discarded anyway, so nothing the export would have shown is lost.
    assert uploaded[height // 2].mean() > 200
    assert uploaded[0].mean() < 40
    assert result.raw_metadata["asset_crop"] == f"{width}x{height}"


@pytest.mark.asyncio
async def test_still_already_in_the_export_frame_is_uploaded_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    uploads: list = []
    provider = _provider(_client(_handler([COMPLETED], uploads=uploads)))
    source = _make_source(tmp_path)  # 640x360, already 16:9

    result = await provider.generate_clip(
        source, "p", None, 4.0, "slow_forward", tmp_path / "c.mp4",
        options={"width": 1920, "height": 1080},
    )

    assert uploads == [source.read_bytes()], "a matching frame must not be re-encoded"
    assert result.raw_metadata["asset_crop"] == "none"


@pytest.mark.asyncio
async def test_no_frame_size_option_means_no_crop(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MAGIC_HOUR_POLL_INTERVAL_SECONDS", 0.01)
    uploads: list = []
    provider = _provider(_client(_handler([COMPLETED], uploads=uploads)))
    source = _make_portrait_source(tmp_path)

    result = await provider.generate_clip(source, "p", None, 4.0, "slow_forward", tmp_path / "c.mp4")

    assert uploads == [source.read_bytes()]
    assert result.raw_metadata["asset_crop"] == "none"
