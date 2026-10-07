"""Provider selection for Phase 4 image-to-video generation.

Before this factory existed, `settings.VIDEO_PROVIDER` was declared but never
read, so the single hardcoded `GeminiVeoProvider` could not be swapped. The
factory makes the backend configurable at runtime via the environment.

Available providers:

* ``kenburns``   — fully local cinematic camera motion (OpenCV + FFmpeg). Free,
                   offline, deterministic, and never hallucinates the property.
* ``json2video`` — cloud renderer that pans/zooms the real photos. Free tier is
                   generous and it offloads CPU, but it needs the backend to be
                   publicly reachable so it can fetch the source images.
* ``gemini_veo`` — true generative AI video via Google Veo. Highest fidelity,
                   hardest free-tier limits, and the accuracy risk of diffusion
                   inventing furniture and geometry that is not in the listing.
* ``auto``       — prefer the best configured remote provider and degrade to the
                   local renderer on quota/block/configuration failures, so a
                   walkthrough is always produced.
"""

from app.core.config import settings
from app.core.logging import logger
from app.services.video_generation.base import ImageToVideoProvider
from app.services.video_generation.fallback_provider import FallbackProvider
from app.services.video_generation.gemini_veo_provider import GeminiVeoProvider
from app.services.video_generation.json2video_provider import JSON2VideoProvider
from app.services.video_generation.kenburns_provider import KenBurnsProvider

_LOCAL_ALIASES = {"kenburns", "ken_burns", "local", "cinematic", "local_kenburns"}
_VEO_ALIASES = {"gemini_veo", "veo", "gemini", "gemini-veo"}
_JSON2VIDEO_ALIASES = {"json2video", "json2_video", "j2v", "json"}


def _has_veo_credentials() -> bool:
    return bool(settings.VIDEO_API_KEY or settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY)


def _auto_primary() -> ImageToVideoProvider:
    """Picks the best *configured* remote provider, else the local renderer."""
    if settings.JSON2VIDEO_API_KEY and settings.PUBLIC_BASE_URL:
        return JSON2VideoProvider()
    if _has_veo_credentials():
        return GeminiVeoProvider()
    return KenBurnsProvider()


def build_video_provider() -> ImageToVideoProvider:
    """Constructs the configured image-to-video provider."""
    name = (settings.VIDEO_PROVIDER or "auto").strip().lower()

    if name in _LOCAL_ALIASES:
        logger.info("Video provider: local cinematic Ken Burns (no API required).")
        return KenBurnsProvider()

    if name in _VEO_ALIASES:
        logger.info("Video provider: Google Gemini Veo.")
        return GeminiVeoProvider()

    if name in _JSON2VIDEO_ALIASES:
        logger.info("Video provider: JSON2Video cloud renderer.")
        primary: ImageToVideoProvider = JSON2VideoProvider()
        if settings.VIDEO_FALLBACK_TO_LOCAL:
            return FallbackProvider(primary, KenBurnsProvider())
        return primary

    # "auto" (and any unrecognized value): best configured remote, local safety net.
    primary = _auto_primary()
    if isinstance(primary, KenBurnsProvider) or not settings.VIDEO_FALLBACK_TO_LOCAL:
        logger.info(f"Video provider: auto -> {primary.get_provider_name()}.")
        return primary

    logger.info(
        f"Video provider: auto -> {primary.get_provider_name()} "
        "(local Ken Burns fallback on quota/blocked/config errors)."
    )
    return FallbackProvider(primary, KenBurnsProvider())
