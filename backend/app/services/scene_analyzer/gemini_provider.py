import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.schemas.scene import (
    CameraView,
    ImageQualityResult,
    LightingType,
    SceneAnalysisResult,
    SceneType,
    ViewType,
)
from app.services.scene_analyzer.base import BaseSceneAnalyzer

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


SCENE_ANALYSIS_PROMPT = """
You are an expert architectural and real-estate computer vision analyst.
Analyze ONLY what is visibly present and supported in the provided real-estate photograph.

RULES:
1. Do NOT invent rooms, features, or assume unseen areas.
2. Distinguish visible evidence from imagination.
3. Classify the scene into exactly one of the following standard scene types:
   - exterior
   - entrance
   - living_room
   - kitchen
   - dining_area
   - bedroom
   - bathroom
   - balcony
   - hallway
   - study
   - utility_area
   - staircase
   - garden
   - parking
   - unknown (use if evidence is ambiguous or insufficient)
4. Provide a factual, objective visual description (25-60 words).
   - Describe visible furniture, layout, materials, and architectural boundaries.
   - Strictly avoid marketing fluff and subjective superlatives (e.g. "luxurious", "stunning", "magnificent", "perfect", "spacious").
5. Extract a list of distinct visible physical items/features (e.g. "sectional sofa", "pendant light", "wooden flooring", "kitchen island", "sliding glass door").
6. Classify the visible lighting:
   - natural_daylight
   - warm_artificial
   - cool_artificial
   - mixed
   - low_light
   - unknown
7. Classify the view type:
   - wide (captures broad room view)
   - medium (captures specific zone/furniture cluster)
   - close (detail/close-up of specific fixture)
   - overhead (top-down or high-angle perspective)
   - exterior (outdoor view)
   - unknown
8. Classify the camera view angle/perspective:
   - eye_level
   - slightly_elevated
   - low_angle
   - centered
   - corner_view
   - unknown
9. List visible architectural connections (e.g. "doorway on left wall", "open archway to adjacent room", "sliding glass door to exterior") ONLY if visibly present.
10. Assign a calibrated confidence score between 0.0 and 1.0 representing classification certainty.

Return ONLY a valid JSON object with the following structure:
{
  "scene_type": "living_room",
  "confidence": 0.94,
  "description": "Wide interior view of a living room with wooden flooring, a sectional sofa centered near large windows, and an open doorway on the far right.",
  "features": ["sectional sofa", "wooden flooring", "large windows", "open doorway"],
  "lighting": "natural_daylight",
  "view_type": "wide",
  "camera_view": "corner_view",
  "visible_connections": ["open doorway on the far right"]
}
"""


class GeminiSceneAnalyzer(BaseSceneAnalyzer):
    """
    Real multimodal scene analysis provider powered by Google Gemini Vision models.
    """

    def __init__(self):
        self.model_name = settings.AI_MODEL
        self.timeout = settings.AI_REQUEST_TIMEOUT_SECONDS

    def _get_api_key(self) -> str:
        """Retrieves and validates API key from config or environment."""
        key = (
            settings.GEMINI_API_KEY
            or settings.GOOGLE_API_KEY
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not key or not key.strip():
            raise AppException(
                code="AI_PROVIDER_NOT_CONFIGURED",
                message="Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env",
                status_code=503,
            )
        return key.strip()

    def _create_client(self) -> Any:
        if not GENAI_AVAILABLE:
            raise AppException(
                code="AI_DEPENDENCY_MISSING",
                message="google-genai library is not installed in backend environment.",
                status_code=500,
            )
        api_key = self._get_api_key()
        return genai.Client(api_key=api_key)

    async def analyze_image(
        self, image_path: Path, quality_info: Optional[ImageQualityResult] = None
    ) -> SceneAnalysisResult:
        """
        Submits the real property image to Gemini multimodal API and returns validated structured scene metadata.
        """
        if not image_path.exists():
            raise AppException(
                code="IMAGE_FILE_MISSING",
                message=f"Analysis image file not found on disk at {image_path}",
                status_code=404,
            )

        client = self._create_client()

        # Read actual image bytes
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        if len(img_bytes) == 0:
            raise AppException(
                code="EMPTY_IMAGE_FILE",
                message="Image file to analyze is empty (0 bytes).",
                status_code=400,
            )

        logger.info(
            f"Submitting image {image_path.name} ({len(img_bytes)} bytes) to vision model for scene understanding"
        )

        # Fallback candidate models in priority order to overcome free tier spikes
        candidate_models = [self.model_name, "gemini-2.0-flash", "gemini-1.5-flash"]
        # Deduplicate while preserving order
        candidate_models = list(dict.fromkeys([m for m in candidate_models if m]))

        last_error = None
        raw_text = None

        for model in candidate_models:
            # Try up to 3 attempts per model with exponential backoff
            for attempt in range(1, 4):
                try:
                    logger.info(f"Invoking {model} (attempt {attempt}/3) for {image_path.name}...")
                    response = client.models.generate_content(
                        model=model,
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                            SCENE_ANALYSIS_PROMPT,
                        ],
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json",
                        ),
                    )
                    raw_text = response.text or ""
                    if raw_text:
                        break
                except Exception as e:
                    err_str = str(e)
                    last_error = e
                    logger.warning(f"Attempt {attempt}/3 failed with model {model} for {image_path.name}: {err_str}")

                    if "API_KEY_INVALID" in err_str or "PERMISSION_DENIED" in err_str:
                        raise AppException(
                            code="AI_AUTH_ERROR",
                            message="AI vision provider authentication failed. Please verify your GEMINI_API_KEY.",
                            status_code=401,
                        )

                    # For 429, 503, or RESOURCE_EXHAUSTED: apply exponential backoff
                    if "429" in err_str or "503" in err_str or "RESOURCE_EXHAUSTED" in err_str or "UNAVAILABLE" in err_str:
                        import asyncio
                        backoff = (2 ** attempt) + 0.5
                        logger.info(f"Rate/demand limit detected. Backing off for {backoff:.1f}s before retry...")
                        await asyncio.sleep(backoff)
                    else:
                        break  # Unrecoverable error on this attempt, try next model

            if raw_text:
                break

        if not raw_text:
            err_msg = str(last_error) if last_error else "All AI model candidates failed."
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                raise AppException(
                    code="AI_RATE_LIMIT",
                    message="AI vision provider rate limit exceeded. Please wait a few moments and try again.",
                    status_code=429,
                )
            raise AppException(
                code="AI_ANALYSIS_FAILED",
                message=f"Scene analysis request failed: {err_msg}",
                status_code=502,
            )

        return self._parse_and_validate_response(raw_text, image_path.name)

    def _parse_and_validate_response(
        self, raw_text: str, filename: str
    ) -> SceneAnalysisResult:
        """
        Parses JSON output from LLM and strictly validates against Pydantic SceneAnalysisResult.
        """
        # Clean potential markdown formatting
        clean_text = raw_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        try:
            data: Dict[str, Any] = json.loads(clean_text)
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON response for {filename}: {raw_text[:200]}")
            raise AppException(
                code="MALFORMED_AI_RESPONSE",
                message="AI provider returned an unparseable response.",
                status_code=502,
                details={"raw_response": raw_text[:500]},
            )

        # Normalize and map enumerated values
        raw_scene = str(data.get("scene_type", "unknown"))
        scene_type = SceneType.from_str(raw_scene)

        raw_lighting = str(data.get("lighting", "unknown"))
        lighting = LightingType.from_str(raw_lighting)

        raw_view = str(data.get("view_type", "unknown"))
        view_type = ViewType.from_str(raw_view)

        raw_cam = str(data.get("camera_view", "unknown"))
        camera_view = CameraView.from_str(raw_cam)

        raw_conf = data.get("confidence", 0.8)
        try:
            confidence = max(0.0, min(1.0, float(raw_conf)))
        except (ValueError, TypeError):
            confidence = 0.75

        description = str(data.get("description", "")).strip()
        if not description:
            description = f"A {scene_type.value.replace('_', ' ')} view of the property."

        raw_features = data.get("features", [])
        features = [str(f).strip() for f in raw_features if str(f).strip()]

        raw_connections = data.get("visible_connections", [])
        connections = [str(c).strip() for c in raw_connections if str(c).strip()]

        return SceneAnalysisResult(
            scene_type=scene_type,
            confidence=confidence,
            description=description,
            features=features,
            lighting=lighting,
            view_type=view_type,
            camera_view=camera_view,
            visible_connections=connections,
            user_corrected=False,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )
