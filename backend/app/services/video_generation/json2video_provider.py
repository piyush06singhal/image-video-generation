"""Cloud-rendering image-to-video provider backed by the JSON2Video API.

JSON2Video is a **rendering** engine, not a diffusion model: it composites real
assets (images, video, text, audio) into an MP4 from a JSON description. For
real-estate walkthroughs that is a strong fit, because like the local Ken Burns
provider it pans/zooms the *actual photograph* — the property can never be
hallucinated, refurnished or morphed.

It is the middle option between the two extremes:

* ``gemini_veo`` — true generative AI video. Highest "wow" factor, but a hard
  free-tier wall and the accuracy risk of diffusion inventing furniture.
* ``json2video`` — cloud render of the real photos with professional pan/zoom,
  easing and transitions. Generous free tier (600s of rendered video), no local
  GPU/CPU cost, and the render engine is maintained for you.
* ``kenburns`` — the same idea rendered locally with OpenCV + FFmpeg. Zero cost,
  zero network, works fully offline.

Integration requirement: JSON2Video's renderers download each asset **by URL**,
so this backend must be reachable from the public internet. Set ``PUBLIC_BASE_URL``
(a tunnel or deployed host) and this provider hands over the existing
``/api/projects/{project_id}/images/{image_id}/file`` URL for each source photo.
When that is unset the provider raises ``PROVIDER_NOT_CONFIGURED``, which the
:class:`FallbackProvider` degrades cleanly instead of failing the job.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional

# A render that fails because *our* payload is malformed is a bug in this provider, not
# a capacity problem, so it must not be silently masked by the local fallback.
_PAYLOAD_ERROR_RE = re.compile(
    r"is not (an? )?(integer|number|string|valid|allowed)|"
    r"property '.*'|movie/scenes|unknown (property|element)",
    re.IGNORECASE,
)

import httpx

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.schemas.render_options import JSON2VIDEO_NAMED_SIZES
from app.services.video_generation.base import ImageToVideoProvider, ProviderResult

# Uploaded photos are stored as ``storage/projects/<pid>/uploads/img_<hex>_<orig>``
# and the image id is the ``img_<hex>`` prefix — exactly what the existing
# ``/images/{image_id}/file`` route expects.
_STORED_NAME_RE = re.compile(r"^(?P<image_id>img_[0-9a-f]+)_")

_FINAL_STATUSES = {"done", "error", "timeout"}

# Camera motion -> JSON2Video element effects. ``pan`` moves the crop window across
# the frame and ``zoom`` pushes in (positive) or pulls out (negative); combining
# them makes the pan happen while zooming, per the JSON2Video image element spec.
# Values are intentionally conservative so the move reads as a cinematic glide
# rather than a lurch.
#
# NOTE: ``zoom`` must be an INTEGER. The published docs describe it as a number in
# the range -10..10, but the live validator rejects any float with
# "Property 'zoom' is not an integer in movie/scenes[0]/elements[0]", and that
# rejection only arrives asynchronously on the status poll. ``pan-distance`` is a
# float (0.01-0.5).
_MOTION_EFFECTS: Dict[str, Dict[str, Any]] = {
    "slow_forward": {"pan": "top", "zoom": 2, "pan-distance": 0.06},
    "exterior_forward": {"pan": "top", "zoom": 2, "pan-distance": 0.06},
    "slight_dolly": {"pan": "top", "zoom": 2, "pan-distance": 0.06},
    "slow_backward": {"pan": "bottom", "zoom": -2, "pan-distance": 0.05},
    "pan_left": {"pan": "left", "zoom": 1, "pan-distance": 0.14},
    "pan_right": {"pan": "right", "zoom": 1, "pan-distance": 0.14},
    "gentle_orbit": {"pan": "top-right", "zoom": 1, "pan-distance": 0.08},
    "static_subtle_motion": {"zoom": 1},
}
_DEFAULT_EFFECTS: Dict[str, Any] = {"pan": "top", "zoom": 1, "pan-distance": 0.07}

# Rotation used when the project requests camera variety: consecutive rooms get a
# different direction so the walkthrough does not repeat one move.
_VARIETY_EFFECTS: List[Dict[str, Any]] = [
    {"pan": "left", "zoom": 2, "pan-distance": 0.14},
    {"pan": "top", "zoom": 3, "pan-distance": 0.07},
    {"pan": "right", "zoom": 2, "pan-distance": 0.14},
    {"pan": "top-right", "zoom": 3, "pan-distance": 0.10},
    {"pan": "bottom", "zoom": -2, "pan-distance": 0.06},
    {"pan": "top-left", "zoom": 3, "pan-distance": 0.10},
]

# Multiplier applied to the base zoom / pan distance per motion intensity.
_INTENSITY_TRAVEL = {"subtle": 0.55, "balanced": 1.0, "bold": 1.7}

# The free plan caps output at Full HD, and the docs state width/height are
# "bound by the account plan's maximum resolution". Rendering a larger canvas
# would be rejected, so the cloud render is clamped and the assembler upscales.
_CLOUD_MAX_LONG_SIDE = 1920


def _clamp_zoom(value: Any) -> int:
    """JSON2Video requires an integer zoom in -10..10 (floats are rejected at poll time)."""
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        return 1
    return max(-10, min(10, numeric))


def _clamp_pan_distance(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.07
    return round(max(0.01, min(0.5, numeric)), 3)


def _resolve_size(options: Dict[str, Any]) -> Dict[str, Any]:
    """Builds the movie-level sizing keys from the render options.

    Uses JSON2Video's named sizes when one matches exactly, otherwise a `custom`
    resolution with explicit width/height so portrait and square reels are rendered
    natively by the cloud engine instead of being cropped later.
    """
    width = int(options.get("width") or 1920)
    height = int(options.get("height") or 1080)
    if max(width, height) > _CLOUD_MAX_LONG_SIDE:
        scale = _CLOUD_MAX_LONG_SIDE / max(width, height)
        width, height = int(width * scale), int(height * scale)
    # Keep dimensions even so H.264 is happy.
    width += width % 2
    height += height % 2

    size: Dict[str, Any] = {"fps": int(options.get("fps") or 30)}
    named = JSON2VIDEO_NAMED_SIZES.get((width, height))
    if named:
        size["resolution"] = named
    else:
        size.update({"resolution": "custom", "width": width, "height": height})
    return size


class JSON2VideoProvider(ImageToVideoProvider):
    """Renders each scene as a cinematic move over the real photograph, in the cloud."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        resolution: Optional[str] = None,
        public_base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        # `is None` rather than `or`: an explicitly empty key/base URL means "deliberately
        # unset" and must not silently fall back to whatever is in the environment.
        self.api_key = api_key if api_key is not None else settings.JSON2VIDEO_API_KEY
        self.api_url = (api_url or settings.JSON2VIDEO_API_URL).rstrip("/")
        self.resolution = resolution or settings.JSON2VIDEO_RESOLUTION
        base = public_base_url if public_base_url is not None else settings.PUBLIC_BASE_URL
        self.public_base_url = (base or "").rstrip("/")
        self.poll_interval = float(settings.JSON2VIDEO_POLL_INTERVAL_SECONDS)
        self.timeout_seconds = float(settings.JSON2VIDEO_TIMEOUT_SECONDS)
        self.max_retries = int(settings.JSON2VIDEO_MAX_RETRIES)
        self.backoff_base = float(settings.JSON2VIDEO_BACKOFF_SECONDS)
        # Injectable so tests can drive a MockTransport without touching the network.
        self._injected_client = client

    def get_provider_name(self) -> str:
        return "json2video"

    def get_model_name(self) -> str:
        return f"json2video-{self.resolution}"

    # ── helpers ──────────────────────────────────────────────────────────
    @asynccontextmanager
    async def _client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._injected_client is not None:
            yield self._injected_client
            return
        async with httpx.AsyncClient(timeout=60.0) as client:
            yield client

    def _resolve_public_image_url(self, source_image_path: Path) -> str:
        """Maps a stored upload path onto the backend's existing image-file route."""
        # .../projects/<project_id>/<anything>/<stored_filename>
        parts = source_image_path.parts
        try:
            project_id = parts[parts.index("projects") + 1]
        except (ValueError, IndexError):
            raise AppException(
                code="SOURCE_IMAGE_ERROR",
                message=f"Stored upload path is not inside a project directory: {source_image_path}",
                status_code=422,
            )

        match = _STORED_NAME_RE.match(source_image_path.stem)
        if not match:
            raise AppException(
                code="SOURCE_IMAGE_ERROR",
                message=f"Unexpected stored upload filename: {source_image_path.name}",
                status_code=422,
            )

        image_id = match.group("image_id")
        return f"{self.public_base_url}/api/projects/{project_id}/images/{image_id}/file"

    def _resolve_effects(self, camera_motion: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Selects and scales the pan/zoom effect for one scene."""
        motion = (camera_motion or "").strip().lower()
        intensity = str(options.get("motion_intensity") or "balanced")
        variety = bool(options.get("camera_variety", False))
        scene_index = int(options.get("scene_index") or 0)

        if variety and scene_index > 0:
            base = _VARIETY_EFFECTS[(scene_index - 1) % len(_VARIETY_EFFECTS)]
        else:
            base = _MOTION_EFFECTS.get(motion, _DEFAULT_EFFECTS)

        travel = _INTENSITY_TRAVEL.get(intensity, 1.0)
        effects: Dict[str, Any] = {
            "pan-distance": _clamp_pan_distance(float(base.get("pan-distance", 0.07)) * travel),
        }
        if base.get("pan"):
            effects["pan"] = base["pan"]
        if base.get("zoom") is not None:
            zoom = float(base["zoom"]) * travel
            # Never let scaling collapse the move to zero.
            if base["zoom"] != 0 and abs(zoom) < 1:
                zoom = 1 if base["zoom"] > 0 else -1
            effects["zoom"] = _clamp_zoom(zoom)
        effects["move-name"] = f"{base.get('pan') or 'static'}-{base.get('zoom') or 0}"
        return effects

    def _build_movie_json(
        self,
        public_image_url: str,
        duration_seconds: float,
        camera_motion: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        options = options or {}
        effects = self._resolve_effects(camera_motion, options)
        element: Dict[str, Any] = {
            "type": "image",
            "src": public_image_url,
            "duration": round(float(duration_seconds), 2),
            "resize": "cover",
            # No per-clip fades: the assembler owns the transitions, and clipping a
            # fade onto every clip on top of a crossfade produced a visible dip
            # through black at each join.
            "cache": True,
            **effects,
        }
        movie: Dict[str, Any] = {
            "client-data": {
                "provider": "cineestate",
                "camera_motion": camera_motion,
                "scene_index": options.get("scene_index", 0),
                "motion_intensity": options.get("motion_intensity", "balanced"),
            },
            "quality": "high",
            "scenes": [{"elements": [element]}],
            **_resolve_size(options),
        }
        return movie

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
                    "JSON2Video is selected but JSON2VIDEO_API_KEY is not set. "
                    "Add a key from https://json2video.com/get-api-key/ or set "
                    "VIDEO_PROVIDER=kenburns for the fully local renderer."
                ),
                status_code=503,
            )
        if not self.public_base_url:
            raise AppException(
                code="PROVIDER_NOT_CONFIGURED",
                message=(
                    "JSON2Video needs to download the source photos, so PUBLIC_BASE_URL must "
                    "point at a publicly reachable address for this backend (a tunnel or the "
                    "deployed host). Set it, or use VIDEO_PROVIDER=kenburns."
                ),
                status_code=503,
            )
        if not source_image_path.exists():
            raise AppException(
                code="SOURCE_IMAGE_ERROR",
                message=f"Source property image file not found at: {source_image_path}",
                status_code=404,
            )

        duration = max(1.0, float(duration_seconds or 4.0))
        public_url = self._resolve_public_image_url(source_image_path)
        movie_json = self._build_movie_json(public_url, duration, camera_motion, options)
        headers = {"x-api-key": self.api_key}

        async with self._client() as client:
            project_id = await self._submit(client, headers, movie_json)
            logger.info(f"[json2video] Render queued: project={project_id} ({source_image_path.name})")
            movie = await self._await_render(client, headers, project_id)
            await self._download(client, movie["url"], output_path)

        return ProviderResult(
            provider_job_id=project_id,
            output_video_path=output_path,
            provider_name=self.get_provider_name(),
            model_name=self.get_model_name(),
            duration_seconds=float(movie.get("duration") or duration),
            raw_metadata={
                "project": project_id,
                "resolution": movie_json.get("resolution"),
                "requested_size": f"{movie_json.get('width') or options.get('width')}x"
                f"{movie_json.get('height') or options.get('height')}",
                "fps": movie_json.get("fps"),
                "camera_motion": camera_motion,
                "motion_intensity": options.get("motion_intensity", "balanced"),
                "move": movie_json["scenes"][0]["elements"][0].get("move-name"),
                "rendering_time_seconds": movie.get("rendering_time"),
                "source_url": public_url,
                "synthetic_pixels": False,
            },
        )

    async def _submit(
        self, client: httpx.AsyncClient, headers: Dict[str, str], movie_json: Dict[str, Any]
    ) -> str:
        # The JSON2Video docs call out 5xx as "no movie was created; retry with
        # exponential backoff". Without this, a transient blip silently degrades the
        # clip to the local renderer instead of just retrying.
        resp: Optional[httpx.Response] = None
        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await client.post(self.api_url, headers=headers, json=movie_json)
            except httpx.HTTPError as exc:
                last_error = str(exc)
                resp = None
            else:
                if resp.status_code < 500:
                    break
                last_error = f"HTTP {resp.status_code}"

            if attempt < self.max_retries:
                delay = self.backoff_base * (2 ** (attempt - 1))
                logger.warning(
                    f"[json2video] submit attempt {attempt}/{self.max_retries} failed "
                    f"({last_error}); retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        if resp is None:
            raise AppException(
                code="PROVIDER_TIMEOUT",
                message=(
                    f"Could not reach the JSON2Video API after {self.max_retries} attempts: "
                    f"{last_error}"
                ),
                status_code=503,
            )

        if resp.status_code == 401:
            raise AppException(
                code="PROVIDER_RATE_LIMIT",
                message=(
                    "JSON2Video rejected the render (HTTP 401). This usually means the render "
                    "quota for the plan is exhausted or the API key is invalid."
                ),
                status_code=429,
            )
        if resp.status_code == 413:
            raise AppException(
                code="PROVIDER_REQUEST_REJECTED",
                message="JSON2Video rejected the render payload as too large.",
                status_code=413,
            )
        if resp.status_code >= 500:
            raise AppException(
                code="UNKNOWN_GENERATION_ERROR",
                message=(
                    f"JSON2Video server error ({resp.status_code}) persisted after "
                    f"{self.max_retries} attempts; no render was created."
                ),
                status_code=502,
            )
        if resp.status_code >= 400:
            raise AppException(
                code="PROVIDER_REQUEST_REJECTED",
                message=f"JSON2Video rejected the render request: {resp.text[:300]}",
                status_code=resp.status_code,
            )

        body = resp.json()
        if not body.get("success") or not body.get("project"):
            raise AppException(
                code="UNKNOWN_GENERATION_ERROR",
                message=f"JSON2Video returned an unexpected submission response: {body}",
                status_code=502,
            )
        return str(body["project"])

    async def _await_render(
        self, client: httpx.AsyncClient, headers: Dict[str, str], project_id: str
    ) -> Dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        consecutive_errors = 0
        while True:
            try:
                resp = await client.get(
                    self.api_url, headers=headers, params={"project": project_id, "format": "simple"}
                )
            except httpx.HTTPError as exc:
                # A dropped connection mid-render must not kill a job that is still
                # rendering server-side; keep polling until the deadline.
                consecutive_errors += 1
                logger.warning(
                    f"[json2video] poll for {project_id} failed ({exc}); "
                    f"attempt {consecutive_errors}"
                )
                if time.monotonic() >= deadline:
                    raise AppException(
                        code="PROVIDER_TIMEOUT",
                        message=(
                            f"Lost contact with JSON2Video while polling project {project_id} "
                            f"and exceeded the {self.timeout_seconds:.0f}s budget."
                        ),
                        status_code=503,
                    )
                await asyncio.sleep(self.poll_interval)
                continue

            if resp.status_code == 401:
                raise AppException(
                    code="PROVIDER_RATE_LIMIT",
                    message="JSON2Video returned HTTP 401 while polling; the API key or quota is not valid.",
                    status_code=429,
                )
            if resp.status_code >= 500:
                # Transient server-side error; the render may still be in flight.
                consecutive_errors += 1
                logger.warning(
                    f"[json2video] poll for {project_id} returned {resp.status_code}; "
                    f"attempt {consecutive_errors}"
                )
                if time.monotonic() >= deadline:
                    raise AppException(
                        code="UNKNOWN_GENERATION_ERROR",
                        message=f"JSON2Video polling kept failing ({resp.status_code}) until the timeout.",
                        status_code=502,
                    )
                await asyncio.sleep(self.poll_interval)
                continue
            if resp.status_code >= 400:
                raise AppException(
                    code="UNKNOWN_GENERATION_ERROR",
                    message=f"JSON2Video polling failed: {resp.status_code} {resp.text[:200]}",
                    status_code=502,
                )

            movie = (resp.json() or {}).get("movie") or {}
            status = str(movie.get("status") or "").lower()

            if status == "done" and movie.get("url"):
                return movie
            if status == "error":
                detail = str(movie.get("message") or "unknown error")
                # Malformed-payload rejections arrive here (not on the POST), so classify
                # them as structural: they mean this provider built a bad request and the
                # local fallback would only hide the defect.
                if _PAYLOAD_ERROR_RE.search(detail):
                    raise AppException(
                        code="PROVIDER_REQUEST_REJECTED",
                        message=f"JSON2Video rejected the movie payload: {detail}",
                        status_code=422,
                    )
                raise AppException(
                    code="UNKNOWN_GENERATION_ERROR",
                    message=f"JSON2Video render failed: {detail}",
                    status_code=502,
                )
            if status == "timeout":
                raise AppException(
                    code="PROVIDER_TIMEOUT",
                    message="JSON2Video render timed out (older than 15 minutes).",
                    status_code=504,
                )

            if time.monotonic() >= deadline:
                raise AppException(
                    code="PROVIDER_TIMEOUT",
                    message=(
                        f"JSON2Video render for project {project_id} did not finish within "
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
                message=f"Could not download the rendered walkthrough clip from JSON2Video: {exc}",
                status_code=502,
            )
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise AppException(
                code="RESULT_DOWNLOAD_ERROR",
                message="JSON2Video reported success but the downloaded clip was empty.",
                status_code=502,
            )
        logger.info(f"[json2video] Downloaded rendered clip ({output_path.stat().st_size} bytes) -> {output_path}")
