"""Graceful-degradation wrapper for image-to-video providers.

Wraps a *primary* (remote, high-fidelity but quota-limited) provider and a
*fallback* (local, always-available) provider. When the primary fails with a
recoverable capacity error — rate limit / quota / safety block / auth — the clip
is produced locally instead of failing the whole walkthrough.

This is what lets a free-tier deployment keep working: Veo is used while quota
lasts, and a Ken Burns clip is produced for the rest, automatically.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Set

from app.core.errors import AppException
from app.core.logging import logger
from app.services.video_generation.base import ImageToVideoProvider, ProviderResult


# Capacity-class failures that should degrade to the local provider rather than
# failing the job. Structural errors (missing source image, invalid request)
# still propagate so genuine bugs are not masked.
DEFAULT_FALLBACK_CODES: Set[str] = {
    "PROVIDER_RATE_LIMIT",
    "AI_RATE_LIMIT",
    "PROVIDER_CONTENT_BLOCKED",
    "PROVIDER_AUTH_ERROR",
    "PROVIDER_TIMEOUT",
    "UNKNOWN_GENERATION_ERROR",
    # A remote provider that is selected but not fully configured (missing API key or
    # an unreachable image URL) should degrade, not dead-end the whole walkthrough.
    "PROVIDER_NOT_CONFIGURED",
}


class FallbackProvider(ImageToVideoProvider):
    """Tries `primary`; on a capacity failure, transparently uses `fallback`."""

    def __init__(
        self,
        primary: ImageToVideoProvider,
        fallback: ImageToVideoProvider,
        fallback_codes: Optional[Set[str]] = None,
    ):
        self.primary = primary
        self.fallback = fallback
        self.fallback_codes = fallback_codes or DEFAULT_FALLBACK_CODES

    def get_provider_name(self) -> str:
        return self.primary.get_provider_name()

    def get_model_name(self) -> str:
        return self.primary.get_model_name()

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
        try:
            return await self.primary.generate_clip(
                source_image_path=source_image_path,
                prompt=prompt,
                negative_prompt=negative_prompt,
                duration_seconds=duration_seconds,
                camera_motion=camera_motion,
                output_path=output_path,
                options=options,
            )
        except AppException as exc:
            if exc.code not in self.fallback_codes:
                raise
            logger.warning(
                f"[fallback] Primary provider '{self.primary.get_provider_name()}' failed "
                f"with {exc.code}; degrading to '{self.fallback.get_provider_name()}'."
            )
            # The render options must survive the degrade: a vertical reel should
            # still be rendered vertically even when the clip comes from the
            # local renderer. The option dict already names the concrete frame
            # size, so no aspect translation is needed here.
            return await self.fallback.generate_clip(
                source_image_path=source_image_path,
                prompt=prompt,
                negative_prompt=negative_prompt,
                duration_seconds=duration_seconds,
                camera_motion=camera_motion,
                output_path=output_path,
                options=options,
            )
