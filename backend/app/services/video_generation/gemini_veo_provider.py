import asyncio
import os
from pathlib import Path
import time
from typing import Any, Dict, Optional, Tuple
import httpx
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.services.video_generation.base import ImageToVideoProvider, ProviderResult


class GeminiVeoProvider(ImageToVideoProvider):
    """
    Real Image-to-Video generation provider using Google Gemini GenAI SDK / Veo models.
    Translates architectural source images and Phase 3 camera motion prompts into real video clips.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = (
            api_key
            or settings.VIDEO_API_KEY
            or settings.GEMINI_API_KEY
            or settings.GOOGLE_API_KEY
        )
        self.model_name = model_name or settings.VIDEO_MODEL or "veo-2.0-generate-001"
        self._client: Optional[genai.Client] = None
        self._submission_lock = asyncio.Lock()
        self._last_submission_at = 0.0

    def _get_client(self) -> genai.Client:
        if not self.api_key:
            raise AppException(
                code="PROVIDER_AUTH_ERROR",
                message=(
                    "Video generation requires a configured Gemini / Video API key. "
                    "Please set GEMINI_API_KEY or VIDEO_API_KEY in backend/.env"
                ),
                status_code=401,
            )
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def get_provider_name(self) -> str:
        return "gemini_veo"

    def get_model_name(self) -> str:
        return self.model_name

    def _classify_error(self, err: Exception) -> Tuple[str, str, int]:
        err_str = str(err).lower()
        if "429" in err_str or "quota" in err_str or "rate limit" in err_str or "resource_exhausted" in err_str:
            return (
                "PROVIDER_RATE_LIMIT",
                "Video generation quota exceeded. The free tier has limited capacity — please wait 1–2 minutes and retry.",
                429,
            )
        if "model output must contain" in err_str or "output text or tool calls" in err_str or "blocked" in err_str or "safety" in err_str:
            return (
                "PROVIDER_CONTENT_BLOCKED",
                "The video generation model returned an empty response, likely due to a safety filter or prompt rejection. Try regenerating with a simpler prompt.",
                422,
            )
        if "auth" in err_str or "key" in err_str or "permission" in err_str or "unauthenticated" in err_str or "401" in err_str or "403" in err_str:
            return (
                "PROVIDER_AUTH_ERROR",
                "Authentication failed with the video generation provider. Please verify your API key.",
                401,
            )
        if "timeout" in err_str or "deadline" in err_str:
            return (
                "PROVIDER_TIMEOUT",
                "Video generation timed out while waiting for remote generation to complete.",
                504,
            )
        if "invalid" in err_str or "argument" in err_str or "bad request" in err_str or "400" in err_str:
            return (
                "INVALID_GENERATION_REQUEST",
                f"Video generation provider rejected request parameters: {str(err)}",
                400,
            )
        return (
            "UNKNOWN_GENERATION_ERROR",
            f"Video generation error: {str(err)}",
            500,
        )

    async def _submit_generation(
        self,
        client: genai.Client,
        image_input: types.Image,
        prompt: str,
        gen_config: types.GenerateVideosConfig,
    ) -> Any:
        """Submit one Veo operation at a paced rate with bounded retry."""
        attempts = max(1, settings.VIDEO_RATE_LIMIT_RETRY_ATTEMPTS)
        async with self._submission_lock:
            for attempt in range(1, attempts + 1):
                elapsed = time.monotonic() - self._last_submission_at
                wait_for = settings.VIDEO_SUBMISSION_INTERVAL_SECONDS - elapsed
                if wait_for > 0:
                    await asyncio.sleep(wait_for)

                try:
                    operation = await asyncio.to_thread(
                        client.models.generate_videos,
                        model=self.model_name,
                        source=types.GenerateVideosSource(
                            prompt=prompt,
                            image=image_input,
                        ),
                        config=gen_config,
                    )
                    self._last_submission_at = time.monotonic()
                    return operation
                except Exception as exc:
                    self._last_submission_at = time.monotonic()
                    error_text = str(exc).lower()
                    is_rate_limited = any(
                        marker in error_text
                        for marker in ("429", "quota", "rate limit", "resource_exhausted")
                    )
                    if not is_rate_limited or attempt >= attempts:
                        raise

                    backoff = settings.VIDEO_RATE_LIMIT_BACKOFF_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        "Veo submission rate-limited (attempt %s/%s); retrying in %.1fs",
                        attempt,
                        attempts,
                        backoff,
                    )
                    await asyncio.sleep(backoff)

        raise RuntimeError("Veo submission retry loop ended unexpectedly")

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
        """
        Submits generation request to Google GenAI Veo, polls operation until complete,
        and saves the validated output video artifact to output_path.

        ``options`` is accepted for contract parity but only its duration is
        honoured: Veo exposes no frame-size, fps or colour-grade control, so the
        assembler applies the look and the output format afterwards. This is
        recorded in the result metadata so the UI can be honest about it.
        """
        options = options or {}
        if not source_image_path.exists():
            raise AppException(
                code="SOURCE_IMAGE_ERROR",
                message=f"Source property image file not found at: {source_image_path}",
                status_code=404,
            )

        client = self._get_client()

        # Veo 3.1 accepts discrete duration increments of 4, 6, or 8 seconds
        if duration_seconds <= 5.0:
            bounded_duration = 4
        elif duration_seconds <= 7.0:
            bounded_duration = 6
        else:
            bounded_duration = 8

        logger.info(
            f"Initiating image-to-video generation for {source_image_path.name} with model {self.model_name} (duration={bounded_duration}s)..."
        )

        try:
            # 1. Load source image for GenAI SDK
            image_input = types.Image.from_file(location=str(source_image_path))

            # 2. Configure video generation params (Developer API compatible)
            # NOTE: enhance_prompt, fps, person_generation are NOT supported in Developer API
            config_args: Dict[str, Any] = {
                "number_of_videos": 1,
                "duration_seconds": bounded_duration,
                "aspect_ratio": settings.VIDEO_ASPECT_RATIO,
            }
            gen_config = types.GenerateVideosConfig(**config_args)

            # 3. Submit asynchronous generation operation
            # Prompt is kept concise to avoid safety filter rejections
            logger.info(f"Generation prompt ({len(prompt)} chars): {prompt[:120]}...")
            operation = await self._submit_generation(
                client=client,
                image_input=image_input,
                prompt=prompt,
                gen_config=gen_config,
            )

            provider_job_id = getattr(operation, "name", str(time.time()))
            logger.info(f"Video generation operation created: {provider_job_id}. Polling for completion...")

            # 4. Asynchronous polling loop
            poll_interval = settings.VIDEO_POLL_INTERVAL_SECONDS
            poll_timeout = settings.VIDEO_POLL_TIMEOUT_SECONDS
            start_time = time.time()

            while not operation.done:
                elapsed = time.time() - start_time
                if elapsed > poll_timeout:
                    raise AppException(
                        code="PROVIDER_TIMEOUT",
                        message=f"Video generation timed out after {int(elapsed)} seconds.",
                        status_code=504,
                    )

                await asyncio.sleep(poll_interval)

                operation = await asyncio.to_thread(
                    client.operations.get,
                    operation=operation,
                )

            # 5. Check for operation errors
            if hasattr(operation, "error") and operation.error:
                error_msg = str(operation.error)
                logger.error(f"Remote operation {provider_job_id} failed: {error_msg}")
                err_code, user_msg, status_code = self._classify_error(Exception(error_msg))
                raise AppException(
                    code=err_code,
                    message=user_msg,
                    status_code=status_code,
                )

            # 6. Retrieve and save video payload
            response = getattr(operation, "response", None)
            generated_videos = getattr(response, "generated_videos", None) if response else None

            if not generated_videos:
                # This can happen when the model output is blocked/empty
                logger.error(
                    f"Operation {provider_job_id} completed but returned no videos. "
                    "This typically indicates a content safety filter rejection or empty model output."
                )
                raise AppException(
                    code="PROVIDER_CONTENT_BLOCKED",
                    message=(
                        "The video generation model returned no output. "
                        "This is usually caused by a safety filter or an overly complex prompt. "
                        "Try regenerating — the scene will use a simplified prompt on retry."
                    ),
                    status_code=422,
                )

            generated_video = generated_videos[0].video
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if getattr(generated_video, "video_bytes", None):
                logger.info(f"Saving video from video_bytes ({len(generated_video.video_bytes)} bytes)...")
                with open(output_path, "wb") as f:
                    f.write(generated_video.video_bytes)
            elif getattr(generated_video, "uri", None):
                # Download from GCS/signed URI
                logger.info(f"Downloading video from URI: {generated_video.uri}")
                async with httpx.AsyncClient(timeout=120.0) as http_client:
                    r = await http_client.get(generated_video.uri)
                    r.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(r.content)
            else:
                raise AppException(
                    code="RESULT_DOWNLOAD_ERROR",
                    message="No download URI or video bytes provided in completed response.",
                    status_code=500,
                )

            logger.info(f"Successfully downloaded generated video to: {output_path}")

            return ProviderResult(
                provider_job_id=provider_job_id,
                output_video_path=output_path,
                provider_name=self.get_provider_name(),
                model_name=self.get_model_name(),
                duration_seconds=float(bounded_duration),
                raw_metadata={
                    "operation_name": provider_job_id,
                    # Veo ignores frame size / fps / grade; the assembler applies them.
                    "options_applied": ["duration_seconds"],
                    "options_ignored": [
                        k
                        for k in ("width", "height", "fps", "aspect_ratio", "resolution")
                        if options.get(k) is not None
                    ],
                    "synthetic_pixels": True,
                },
            )

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Image-to-video generation failed: {e}")
            err_code, user_msg, status_code = self._classify_error(e)
            raise AppException(
                code=err_code,
                message=user_msg,
                status_code=status_code,
            )
