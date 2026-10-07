"""Generative image-to-video provider backed by the Magic Hour API.

Magic Hour's ``POST /v1/image-to-video`` runs a diffusion video model (Kling,
LTX, Veo, Seedance, Wan, ...) over a single still photograph. Unlike the local
Ken Burns renderer or the JSON2Video compositor it therefore **synthesises new
pixels**: the camera genuinely moves and people/foliage/water animate, but the
model can also invent furniture or shift geometry that was never in the
listing. That accuracy trade-off is the one already documented for Gemini Veo,
which is why this provider is opt-in (``VIDEO_PROVIDER=magic_hour``) and sits
behind the plate-based renderers in the ``auto`` preference order.

Two properties make it a much better *fallback* than the other remote options:

* **No public URL required.** Magic Hour exposes a file-upload flow
  (``POST /v1/files/upload-urls`` → ``PUT`` the bytes → reference the returned
  ``file_path``), so this backend does **not** need a tunnel or a deployed host
  the way JSON2Video does. It works from a laptop on ``localhost``.
* **Plan-aware defaults.** ``model`` and ``resolution`` are only sent when
  explicitly configured, and a rejection that cites the plan/tier is retried
  once without a pinned resolution — so a free-tier key is never dead-ended by
  asking for a frame size the account cannot render.

Every failure mode that is really a *capacity* problem (missing key, exhausted
credits, auth rejection, timeout, 5xx) raises a code that
:class:`FallbackProvider` converts into a local Ken Burns clip, so a
walkthrough is always produced. Only a genuinely malformed request surfaces.
"""

import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import tempfile
import time
from typing import Any, AsyncIterator, Dict, Optional, Tuple

import httpx

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.services.video_generation.base import ImageToVideoProvider, ProviderResult

# ── Durations ────────────────────────────────────────────────────────────────
# ``end_seconds`` must be an integer, and every model publishes the exact values
# it accepts (kling-3.0 any integer 3-15, veo3.1 only 4/6/8/16/...). An illegal
# value is rejected asynchronously, so the scene's requested duration is snapped
# to the nearest legal value instead of being sent raw.
#
# The project's own scene duration is ~4.5s, and {4, 6, 8} is legal for every
# documented model except kling-2.6, so it is the safe set to snap against when
# no model is pinned (Magic Hour then picks whichever model the plan allows).
_SAFE_DEFAULT_DURATIONS: Tuple[int, ...] = (4, 6, 8)
_MODEL_DURATIONS: Dict[str, Tuple[int, ...]] = {
    "kling-2.6": (5, 10),
    "kling-3.0": tuple(range(3, 16)),
    "ltx-2.5": tuple(range(1, 61)),
    "gemini-omni-1.1": tuple(range(3, 11)),
    "minimax-h3": tuple(range(1, 31)),
    "seedance-1.5": tuple(range(4, 13)),
    "seedance-2.0": tuple(range(4, 16)),
    "seedance-2.0-mini": tuple(range(4, 16)),
    "seedance-2.5": tuple(range(4, 31)),
    "veo3.1": (4, 6, 8, 16, 24, 32, 40, 48, 56),
    "veo3.1-lite": (4, 6, 8, 16, 24, 32, 40, 48, 56),
    "wan-2.2": (3, 4, 5, 6, 7, 8, 9, 10, 15),
    "wan-3.0": (2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30),
}

# ── Output resolution ────────────────────────────────────────────────────────
# Magic Hour exposes 360p/480p/720p/1080p/4k. This project's quality tiers are
# 720p/1080p/1440p, so 1440p collapses onto Magic Hour's 1080p (there is no
# 1440p tier) and the assembler upscales afterwards either way.
_RESOLUTION_ALIASES: Dict[str, str] = {
    "360p": "360p",
    "480p": "480p",
    "720p": "720p",
    "1080p": "1080p",
    "1440p": "1080p",
    "4k": "4k",
    "2160p": "4k",
}

# A plan/tier/resolution rejection is recoverable: drop the pinned resolution and
# let Magic Hour use the frame size the account is entitled to.
_PLAN_REJECTION_MARKERS = ("resolution", "plan", "tier", "subscription", "upgrade")

# ── Prompt shaping ───────────────────────────────────────────────────────────
# Unlike JSON2Video (explicit pan/zoom keys) Magic Hour is prompt-driven, so the
# planned camera move has to be described in words for the model to perform it.
_MOTION_PROMPTS: Dict[str, str] = {
    "slow_forward": "Push the camera slowly and steadily forward into the room.",
    "exterior_forward": "Drift the camera slowly forward toward the property exterior.",
    "slight_dolly": "Make a slow dolly movement with a gentle push in.",
    "slow_backward": "Pull the camera slowly backwards, revealing more of the room.",
    "pan_left": "Pan the camera smoothly to the left.",
    "pan_right": "Pan the camera smoothly to the right.",
    "gentle_orbit": "Orbit the camera gently around the space, keeping the room centred.",
    "static_subtle_motion": "Keep the camera almost static with only a very subtle drift.",
}
_DEFAULT_MOTION_PROMPT = "Make one slow, smooth, steady cinematic camera move."

# The single biggest real-estate risk with a generative model is it quietly
# redecorating the property. Say so explicitly in every prompt.
_FIDELITY_CLAUSE = (
    "Keep the layout, architecture, furniture, materials and lighting exactly as they "
    "appear in the photograph; do not add, remove or move any object, and do not add "
    "people, logos or text."
)

_SUPPORTED_IMAGE_EXTENSIONS = {
    "png", "jpg", "jpeg", "jfif", "heic", "heif", "webp", "avif", "jp2", "tiff", "tif", "bmp",
}


def _snap_duration(model: Optional[str], duration_seconds: float) -> int:
    """Nearest duration value the selected model actually accepts."""
    allowed = _MODEL_DURATIONS.get((model or "").strip().lower()) or _SAFE_DEFAULT_DURATIONS
    try:
        target = float(duration_seconds)
    except (TypeError, ValueError):
        target = 4.0
    # ``min`` with a tuple key breaks ties towards the shorter clip, which keeps
    # the walkthrough from silently gaining seconds the user did not ask for.
    return min(allowed, key=lambda value: (abs(value - target), value))


def _target_aspect(options: Dict[str, Any]) -> Optional[float]:
    """The project's export aspect ratio, when the caller supplied a frame size."""
    try:
        width = int(options.get("width") or 0)
        height = int(options.get("height") or 0)
    except (TypeError, ValueError):
        return None
    return width / height if width > 0 and height > 0 else None


class MagicHourProvider(ImageToVideoProvider):
    """Generative image-to-video through Magic Hour's single-shot REST API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        resolution: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        # `is None` rather than `or`: an explicitly empty key means "deliberately
        # unset" and must not silently fall back to the environment.
        self.api_key = api_key if api_key is not None else settings.MAGIC_HOUR_API_KEY
        self.api_url = (api_url or settings.MAGIC_HOUR_API_URL).rstrip("/")
        self.model = model if model is not None else (settings.MAGIC_HOUR_MODEL or None)
        self.resolution = (
            resolution if resolution is not None else (settings.MAGIC_HOUR_RESOLUTION or None)
        )
        self.audio = bool(settings.MAGIC_HOUR_AUDIO)
        self.poll_interval = float(settings.MAGIC_HOUR_POLL_INTERVAL_SECONDS)
        self.timeout_seconds = float(settings.MAGIC_HOUR_TIMEOUT_SECONDS)
        self.max_retries = int(settings.MAGIC_HOUR_MAX_RETRIES)
        self.backoff_base = float(settings.MAGIC_HOUR_BACKOFF_SECONDS)
        # Injectable so tests can drive a MockTransport without touching the network.
        self._injected_client = client

    def get_provider_name(self) -> str:
        return "magic_hour"

    def get_model_name(self) -> str:
        return self.model or "magic-hour-auto"

    # ── helpers ──────────────────────────────────────────────────────────
    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._injected_client is not None:
            yield self._injected_client
            return
        async with httpx.AsyncClient(timeout=120.0) as client:
            yield client

    def _resolve_resolution(self) -> Optional[str]:
        """Pins an output frame size, or ``None`` to let Magic Hour choose.

        Nothing is guessed from the project's quality tier: a free-tier key can
        only render small frames, so an unpinned request is the safest default.
        """
        if not self.resolution:
            return None
        normalized = _RESOLUTION_ALIASES.get(self.resolution.strip().lower())
        if not normalized:
            logger.warning(
                f"[magic_hour] Unknown MAGIC_HOUR_RESOLUTION '{self.resolution}'; "
                "letting Magic Hour pick the plan's frame size."
            )
        return normalized

    def _build_style_prompt(self, prompt: str, camera_motion: str) -> str:
        motion = _MOTION_PROMPTS.get((camera_motion or "").strip().lower(), _DEFAULT_MOTION_PROMPT)
        base = (prompt or "").strip().rstrip(".")
        lead = f"{base}. " if base else ""
        return f"{lead}{motion} {_FIDELITY_CLAUSE}"

    def _aspect_cropped_copy(
        self, source_image_path: Path, target_aspect: float
    ) -> Tuple[Optional[Path], str]:
        """Centre-crops the still to the export aspect, returning a temp PNG.

        Magic Hour has no aspect-ratio control: it mirrors the input still's shape.
        A portrait listing photo therefore produced a *portrait* clip, which the
        assembler then cover-cropped and upscaled by ~3.7x. Cropping the still to
        the shape that actually ships keeps every generated pixel and roughly
        halves the final upscale — and the strips discarded here are exactly the
        ones the assembler would have cropped away anyway.
        """
        import cv2

        image = cv2.imread(str(source_image_path))
        if image is None:
            return None, "unreadable"

        height, width = image.shape[:2]
        source_aspect = width / height
        # Already the export shape: hand the original file over untouched, so no
        # pixel is re-encoded.
        if abs(source_aspect - target_aspect) < 0.01:
            return None, "none"

        if source_aspect > target_aspect:
            new_w = max(1, int(round(height * target_aspect)))
            x0 = (width - new_w) // 2
            crop = image[:, x0 : x0 + new_w]
        else:
            new_h = max(1, int(round(width / target_aspect)))
            y0 = (height - new_h) // 2
            crop = image[y0 : y0 + new_h, :]

        # mkstemp (not NamedTemporaryFile) so the path can be reopened and the
        # handle is not held open while cv2 writes to it.
        handle, name = tempfile.mkstemp(prefix="cineestate_mh_", suffix=".png")
        os.close(handle)
        path = Path(name)
        if not cv2.imwrite(str(path), crop):
            path.unlink(missing_ok=True)
            return None, "none"

        label = f"{crop.shape[1]}x{crop.shape[0]}"
        logger.info(
            f"[magic_hour] Cropped {source_image_path.name} {width}x{height} -> "
            f"{label} to match the export frame."
        )
        return path, label

    def _classify_http_error(
        self, status_code: int, body: Dict[str, Any], *, during: str
    ) -> AppException:
        """Maps a Magic Hour error payload onto this app's error taxonomy.

        Capacity-class codes (auth, credits, 5xx) are deliberately in
        :data:`DEFAULT_FALLBACK_CODES` so the walkthrough degrades to the local
        renderer instead of failing.
        """
        code = str(body.get("code") or "").lower()
        detail = str(body.get("message") or "").strip() or f"HTTP {status_code}"

        if code == "unauthorized" or status_code in (401, 403):
            return AppException(
                code="PROVIDER_AUTH_ERROR",
                message=(
                    f"Magic Hour refused the request while {during}: {detail}. "
                    "Check MAGIC_HOUR_API_KEY."
                ),
                status_code=401,
            )
        if code == "insufficient_credits" or status_code in (402, 429):
            return AppException(
                code="PROVIDER_RATE_LIMIT",
                message=f"Magic Hour is out of credits or rate-limiting this account: {detail}",
                status_code=429,
            )
        if status_code >= 500 or code == "internal_server_error":
            return AppException(
                code="UNKNOWN_GENERATION_ERROR",
                message=f"Magic Hour server error while {during}: {detail}",
                status_code=502,
            )
        if code in {"invalid_request", "unprocessable_entity"} or 400 <= status_code < 500:
            # A malformed request means this provider built a bad payload; the
            # local fallback would only hide the defect, so let it surface.
            return AppException(
                code="PROVIDER_REQUEST_REJECTED",
                message=f"Magic Hour rejected the image-to-video request: {detail}",
                status_code=422,
            )
        return AppException(
            code="UNKNOWN_GENERATION_ERROR",
            message=f"Magic Hour request failed while {during}: {detail}",
            status_code=502,
        )

    # ── asset handoff ────────────────────────────────────────────────────
    async def _upload_image(self, client: httpx.AsyncClient, source_image_path: Path) -> str:
        """Uploads the still and returns the ``file_path`` Magic Hour references.

        Using the upload flow (rather than a public URL) is what lets this
        provider run with no tunnel and no ``PUBLIC_BASE_URL``: the photo is
        handed over directly. Magic Hour documents that the signed URL must be
        PUT *without* the bearer token.
        """
        extension = source_image_path.suffix.lstrip(".").lower()
        if extension not in _SUPPORTED_IMAGE_EXTENSIONS:
            extension = "jpg"

        try:
            resp = await client.post(
                f"{self.api_url}/files/upload-urls",
                headers=self._auth_headers(),
                json={"items": [{"type": "image", "extension": extension}]},
            )
        except httpx.HTTPError as exc:
            raise AppException(
                code="UNKNOWN_GENERATION_ERROR",
                message=f"Could not reach Magic Hour to request an upload URL: {exc}",
                status_code=502,
            )

        if resp.status_code >= 400:
            body = resp.json() if resp.content else {}
            raise self._classify_http_error(resp.status_code, body, during="requesting an upload URL")

        items = (resp.json() or {}).get("items") or []
        item = items[0] if items else {}
        upload_url = item.get("upload_url")
        file_path = item.get("file_path")
        if not upload_url or not file_path:
            raise AppException(
                code="UNKNOWN_GENERATION_ERROR",
                message=f"Magic Hour returned no usable upload URL: {resp.text[:300]}",
                status_code=502,
            )

        payload = source_image_path.read_bytes()
        try:
            # No auth header and no explicit Content-Type: the URL is pre-signed,
            # and a header the signature does not cover is rejected.
            put = await client.put(upload_url, content=payload)
        except httpx.HTTPError as exc:
            raise AppException(
                code="UNKNOWN_GENERATION_ERROR",
                message=f"Uploading {source_image_path.name} to Magic Hour failed: {exc}",
                status_code=502,
            )
        if put.status_code >= 400:
            raise AppException(
                code="UNKNOWN_GENERATION_ERROR",
                message=(
                    f"Magic Hour rejected the upload of {source_image_path.name} "
                    f"(HTTP {put.status_code})."
                ),
                status_code=502,
            )

        logger.info(
            f"[magic_hour] Uploaded {source_image_path.name} ({len(payload)} bytes) -> {file_path}"
        )
        return str(file_path)

    # ── provider contract ────────────────────────────────────────────────
    async def generate_clip(
        self,
        source_image_path: Path,
        prompt: str,
        negative_prompt: Optional[str],
        duration_seconds: float,
        camera_motion: str,
        output_path: Path,
        options: Optional[Dict[str, Any]] = None,
    ) -> ProviderResult:
        options = options or {}
        if not self.api_key:
            raise AppException(
                code="PROVIDER_NOT_CONFIGURED",
                message=(
                    "Magic Hour is selected but MAGIC_HOUR_API_KEY is not set. Add a key from "
                    "https://magichour.ai/developer, or set VIDEO_PROVIDER=kenburns for the "
                    "fully local renderer."
                ),
                status_code=503,
            )
        if not source_image_path.exists():
            raise AppException(
                code="SOURCE_IMAGE_ERROR",
                message=f"Source property image file not found at: {source_image_path}",
                status_code=404,
            )

        model = self.model or None
        end_seconds = _snap_duration(model, duration_seconds)
        style_prompt = self._build_style_prompt(prompt, camera_motion)

        # Only pin model/resolution when explicitly configured: an unpinned
        # request gets the model and frame size the account is entitled to, so a
        # free-tier key is not rejected for asking for paid-tier output.
        payload: Dict[str, Any] = {
            "name": f"CineEstate {source_image_path.stem}"[:120],
            "end_seconds": int(end_seconds),
            "audio": self.audio,
            "style": {"prompt": style_prompt},
        }
        if model:
            payload["model"] = model
        resolution = self._resolve_resolution()
        if resolution:
            payload["resolution"] = resolution

        # Magic Hour mirrors the input still's aspect ratio, so crop the photo to
        # the frame that actually ships before handing it over.
        temp_asset: Optional[Path] = None
        asset_source = source_image_path
        crop_label = "none"
        target_aspect = _target_aspect(options)
        if target_aspect:
            temp_asset, crop_label = self._aspect_cropped_copy(source_image_path, target_aspect)
            if temp_asset is not None:
                asset_source = temp_asset

        try:
            async with self._client() as client:
                asset_path = await self._upload_image(client, asset_source)
                payload["assets"] = {"image_file_path": asset_path}

                job_id, credits_charged, used_resolution = await self._submit(client, payload)
                logger.info(
                    f"[magic_hour] Image-to-video queued: id={job_id} "
                    f"({source_image_path.name}, {end_seconds}s, credits≈{credits_charged})"
                )
                project = await self._await_completion(client, job_id)
                download_url = self._first_download_url(project, job_id)
                await self._download(client, download_url, output_path)
        finally:
            if temp_asset is not None:
                temp_asset.unlink(missing_ok=True)

        # The API reports the model it actually ran, which is authoritative when
        # nothing was pinned. It is only known after completion.
        actual_model = str(project.get("model") or payload.get("model") or self.get_model_name())

        return ProviderResult(
            provider_job_id=job_id,
            output_video_path=output_path,
            provider_name=self.get_provider_name(),
            model_name=actual_model,
            duration_seconds=float(project.get("duration") or end_seconds),
            raw_metadata={
                "job_id": job_id,
                "requested_model": model or "magic-hour-auto",
                "effective_model": actual_model,
                "resolution": used_resolution or "plan-default",
                "requested_resolution": resolution or "plan-default",
                "end_seconds": end_seconds,
                "credits_charged": project.get("credits_charged", credits_charged),
                "fps": project.get("fps"),
                "audio": self.audio,
                "camera_motion": camera_motion,
                "style_prompt": style_prompt,
                "asset_handoff": "upload",
                "asset_crop": crop_label,
                # The model re-synthesises the frame; the property is not guaranteed
                # pixel-exact the way it is with the plate-based renderers.
                "synthetic_pixels": True,
                "options_ignored": [
                    key
                    for key in ("width", "height", "fps", "aspect_ratio")
                    if options.get(key) is not None
                ],
            },
        )

    async def _submit(
        self, client: httpx.AsyncClient, payload: Dict[str, Any]
    ) -> Tuple[str, int, Optional[str]]:
        """Creates the job, retrying transient 5xx and plan-level rejections."""
        used_resolution = payload.get("resolution")
        downgraded = False
        last_error = ""
        # Counts only consumed attempts — transport errors and 5xx. The plan/tier
        # downgrade below retries *without* consuming the budget: with the old
        # counting, MAGIC_HOUR_MAX_RETRIES=1 plus a rejected pinned resolution
        # would log the downgrade and then raise without ever retrying.
        attempts_used = 0

        while attempts_used < self.max_retries:
            resp: Optional[httpx.Response] = None
            try:
                resp = await client.post(
                    f"{self.api_url}/image-to-video",
                    headers=self._auth_headers(),
                    json=payload,
                )
            except httpx.HTTPError as exc:
                last_error = str(exc)
            else:
                if resp.status_code < 400:
                    body = resp.json() if resp.content else {}
                    job_id = body.get("id")
                    if not job_id:
                        raise AppException(
                            code="UNKNOWN_GENERATION_ERROR",
                            message=f"Magic Hour returned an unexpected submission response: {body}",
                            status_code=502,
                        )
                    return str(job_id), int(body.get("credits_charged") or 0), used_resolution

                body = resp.json() if resp.content else {}
                detail = str(body.get("message") or resp.text[:300])

                # A rejection that cites the plan/tier is really "this account
                # cannot render that frame size". Drop the pinned resolution and
                # try once more instead of dead-ending the walkthrough.
                if (
                    not downgraded
                    and "resolution" in payload
                    and resp.status_code < 500
                    and any(marker in detail.lower() for marker in _PLAN_REJECTION_MARKERS)
                ):
                    logger.warning(
                        f"[magic_hour] {detail.strip()[:160]} — retrying without a pinned resolution."
                    )
                    payload.pop("resolution", None)
                    downgraded = True
                    used_resolution = None
                    continue

                if resp.status_code < 500:
                    raise self._classify_http_error(resp.status_code, body, during="creating the job")

                last_error = f"HTTP {resp.status_code}"

            attempts_used += 1
            if attempts_used < self.max_retries:
                delay = self.backoff_base * (2 ** (attempts_used - 1))
                logger.warning(
                    f"[magic_hour] submit attempt {attempts_used}/{self.max_retries} failed "
                    f"({last_error or 'transport error'}); retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        raise AppException(
            code="UNKNOWN_GENERATION_ERROR",
            message=(
                f"Magic Hour did not accept the job after {self.max_retries} attempts: "
                f"{last_error or 'no response'}"
            ),
            status_code=502,
        )

    def _first_download_url(self, project: Dict[str, Any], job_id: str) -> str:
        downloads = project.get("downloads") or []
        url = (downloads[0] or {}).get("url") if downloads else None
        if not url:
            raise AppException(
                code="RESULT_DOWNLOAD_ERROR",
                message=f"Magic Hour job {job_id} completed without a download URL.",
                status_code=502,
            )
        return str(url)

    async def _await_completion(self, client: httpx.AsyncClient, job_id: str) -> Dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        consecutive_errors = 0

        while True:
            try:
                resp = await client.get(
                    f"{self.api_url}/video-projects/{job_id}", headers=self._auth_headers()
                )
            except httpx.HTTPError as exc:
                # A dropped connection mid-render must not abandon a job that is
                # still rendering server-side; keep polling until the deadline.
                consecutive_errors += 1
                logger.warning(
                    f"[magic_hour] poll for {job_id} failed ({exc}); attempt {consecutive_errors}"
                )
                if time.monotonic() >= deadline:
                    raise AppException(
                        code="PROVIDER_TIMEOUT",
                        message=(
                            f"Lost contact with Magic Hour while polling job {job_id} and "
                            f"exceeded the {self.timeout_seconds:.0f}s budget."
                        ),
                        status_code=503,
                    )
                await asyncio.sleep(self.poll_interval)
                continue

            if resp.status_code >= 500:
                consecutive_errors += 1
                logger.warning(
                    f"[magic_hour] poll for {job_id} returned {resp.status_code}; "
                    f"attempt {consecutive_errors}"
                )
                if time.monotonic() >= deadline:
                    raise AppException(
                        code="UNKNOWN_GENERATION_ERROR",
                        message=f"Magic Hour polling kept failing ({resp.status_code}) until the timeout.",
                        status_code=502,
                    )
                await asyncio.sleep(self.poll_interval)
                continue

            if resp.status_code >= 400:
                body = resp.json() if resp.content else {}
                raise self._classify_http_error(
                    resp.status_code, body, during=f"polling job {job_id}"
                )

            project = resp.json() or {}
            status = str(project.get("status") or "").lower()

            if status == "complete":
                return project
            if status in ("error", "canceled"):
                detail = str(project.get("message") or project.get("error") or "unknown error")
                raise AppException(
                    code="UNKNOWN_GENERATION_ERROR",
                    message=f"Magic Hour render {job_id} ended as '{status}': {detail}",
                    status_code=502,
                )

            if time.monotonic() >= deadline:
                raise AppException(
                    code="PROVIDER_TIMEOUT",
                    message=(
                        f"Magic Hour render {job_id} did not finish within "
                        f"{self.timeout_seconds:.0f}s (last status: {status or 'unknown'})."
                    ),
                    status_code=504,
                )
            await asyncio.sleep(self.poll_interval)

    async def _download(self, client: httpx.AsyncClient, url: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(output_path, "wb") as handle:
                    async for chunk in resp.aiter_bytes():
                        handle.write(chunk)
        except httpx.HTTPError as exc:
            raise AppException(
                code="RESULT_DOWNLOAD_ERROR",
                message=f"Could not download the Magic Hour clip: {exc}",
                status_code=502,
            )
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise AppException(
                code="RESULT_DOWNLOAD_ERROR",
                message="Magic Hour reported success but the downloaded clip was empty.",
                status_code=502,
            )
        logger.info(
            f"[magic_hour] Downloaded generated clip ({output_path.stat().st_size} bytes) -> {output_path}"
        )
