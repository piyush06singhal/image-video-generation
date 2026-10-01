from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from tests.helpers import create_test_image_bytes
from app.core.errors import AppException
from app.schemas.image import AnalysisStatus
from app.schemas.scene import (
    CameraView,
    ImageQualityResult,
    LightingType,
    QualityStatus,
    SceneAnalysisResult,
    SceneCorrectionPayload,
    SceneType,
    ViewType,
)
from app.services.image_preprocessor import ImagePreprocessor
from app.services.scene_analyzer.gemini_provider import GeminiSceneAnalyzer


def test_scene_analysis_schema_validation():
    result = SceneAnalysisResult(
        scene_type=SceneType.LIVING_ROOM,
        confidence=0.95,
        description="A bright living room with wooden flooring and a sectional sofa.",
        features=["sectional sofa", "wooden flooring", "bay windows"],
        lighting=LightingType.NATURAL_DAYLIGHT,
        view_type=ViewType.WIDE,
        camera_view=CameraView.CORNER_VIEW,
        visible_connections=["doorway on right"],
    )
    assert result.scene_type == SceneType.LIVING_ROOM
    assert result.confidence == 0.95
    assert len(result.features) == 3
    assert result.user_corrected is False


def test_malformed_ai_response_parsing():
    analyzer = GeminiSceneAnalyzer()

    # Valid with markdown codeblock
    raw_markdown = """```json
    {
      "scene_type": "kitchen",
      "confidence": 0.88,
      "description": "Modern kitchen with granite countertops and stainless steel refrigerator.",
      "features": ["granite countertop", "refrigerator"],
      "lighting": "warm_artificial",
      "view_type": "medium",
      "camera_view": "eye_level",
      "visible_connections": []
    }
    ```"""
    parsed = analyzer._parse_and_validate_response(raw_markdown, "kitchen.jpg")
    assert parsed.scene_type == SceneType.KITCHEN
    assert parsed.confidence == 0.88
    assert parsed.lighting == LightingType.WARM_ARTIFICIAL

    # Invalid JSON string should raise AppException
    invalid_raw = "This is not json at all."
    with pytest.raises(AppException) as exc_info:
        analyzer._parse_and_validate_response(invalid_raw, "bad.jpg")
    assert exc_info.value.code == "MALFORMED_AI_RESPONSE"


def test_invalid_scene_type_falls_back_to_unknown():
    analyzer = GeminiSceneAnalyzer()
    raw = """{
      "scene_type": "space_station_cockpit",
      "confidence": 0.5,
      "description": "Unidentifiable room.",
      "features": [],
      "lighting": "alien_glow",
      "view_type": "unknown",
      "camera_view": "unknown"
    }"""
    parsed = analyzer._parse_and_validate_response(raw, "weird.jpg")
    assert parsed.scene_type == SceneType.UNKNOWN
    assert parsed.lighting == LightingType.UNKNOWN


def test_image_quality_analysis_metrics(tmp_path):
    preprocessor = ImagePreprocessor()

    # Standard well-lit image
    good_bytes = create_test_image_bytes(width=1920, height=1080, color=(150, 150, 150))
    analysis_file = tmp_path / "analysis_good.jpg"
    _, quality = preprocessor.prepare_analysis_image(good_bytes, analysis_file)

    assert analysis_file.exists()
    assert quality.resolution == "1920x1080"
    assert 0.0 <= quality.brightness_score <= 1.0
    assert 0.0 <= quality.contrast_score <= 1.0
    assert 0.0 <= quality.sharpness_score <= 1.0
    assert quality.status in [QualityStatus.GOOD, QualityStatus.ACCEPTABLE]


def test_project_scene_analysis_flow(client):
    # 1. Create project & upload images
    proj_resp = client.post("/api/projects", json={"name": "Analysis Test Property"})
    project_id = proj_resp.json()["data"]["id"]

    img1 = create_test_image_bytes(width=1280, height=720, color=(200, 100, 50))
    img2 = create_test_image_bytes(width=1000, height=800, color=(50, 150, 200))
    files = [
        ("files", ("living.jpg", img1, "image/jpeg")),
        ("files", ("bedroom.jpg", img2, "image/jpeg")),
    ]
    client.post(f"/api/projects/{project_id}/images", files=files)

    # 2. Mock AI provider response
    mock_result_1 = SceneAnalysisResult(
        scene_type=SceneType.LIVING_ROOM,
        confidence=0.92,
        description="Spacious living room area with daylight.",
        features=["sofa", "hardwood floor"],
        lighting=LightingType.NATURAL_DAYLIGHT,
        view_type=ViewType.WIDE,
        camera_view=CameraView.CORNER_VIEW,
    )
    mock_result_2 = SceneAnalysisResult(
        scene_type=SceneType.BEDROOM,
        confidence=0.89,
        description="Master bedroom with window.",
        features=["bed frame", "curtains"],
        lighting=LightingType.WARM_ARTIFICIAL,
        view_type=ViewType.MEDIUM,
        camera_view=CameraView.EYE_LEVEL,
    )

    with patch("app.services.scene_analyzer.gemini_provider.GeminiSceneAnalyzer.analyze_image") as mock_ai:
        mock_ai.side_effect = [mock_result_1, mock_result_2]

        analyze_resp = client.post(f"/api/projects/{project_id}/analyze")
        assert analyze_resp.status_code == 200
        json_data = analyze_resp.json()
        assert json_data["success"] is True
        proj = json_data["data"]
        assert proj["status"] == "analyzed"
        assert len(proj["images"]) == 2

        img_a = proj["images"][0]
        assert img_a["analysis_status"] == AnalysisStatus.COMPLETED.value
        assert img_a["scene"]["scene_type"] == SceneType.LIVING_ROOM.value
        assert img_a["quality"]["status"] in ["good", "acceptable"]
        assert "analysis_image_url" in img_a


def test_skip_already_completed_analysis(client):
    proj_resp = client.post("/api/projects", json={"name": "Skip Test Property"})
    project_id = proj_resp.json()["data"]["id"]

    img_bytes = create_test_image_bytes(width=800, height=600)
    files = [("files", ("room.jpg", img_bytes, "image/jpeg"))]
    client.post(f"/api/projects/{project_id}/images", files=files)

    mock_scene = SceneAnalysisResult(
        scene_type=SceneType.DINING_AREA,
        confidence=0.85,
        description="Dining area with table.",
        features=["dining table", "chairs"],
    )

    with patch("app.services.scene_analyzer.gemini_provider.GeminiSceneAnalyzer.analyze_image") as mock_ai:
        mock_ai.return_value = mock_scene

        # 1st call: AI invoked
        client.post(f"/api/projects/{project_id}/analyze")
        assert mock_ai.call_count == 1

        # 2nd call without force: AI should NOT be called
        client.post(f"/api/projects/{project_id}/analyze")
        assert mock_ai.call_count == 1  # Still 1, didn't call again!

        # 3rd call with force_reanalyze: AI invoked
        client.post(
            f"/api/projects/{project_id}/analyze",
            json={"force_reanalyze": True},
        )
        assert mock_ai.call_count == 2


def test_manual_scene_correction(client):
    proj_resp = client.post("/api/projects", json={"name": "Correction Property"})
    project_id = proj_resp.json()["data"]["id"]

    img_bytes = create_test_image_bytes(width=800, height=600)
    files = [("files", ("room_to_correct.jpg", img_bytes, "image/jpeg"))]
    up_resp = client.post(f"/api/projects/{project_id}/images", files=files)
    image_id = up_resp.json()["data"]["uploaded"][0]["id"]

    # Initial AI analysis classifies as bedroom
    mock_scene = SceneAnalysisResult(
        scene_type=SceneType.BEDROOM,
        confidence=0.78,
        description="Room with single bed.",
        features=["bed", "lamp"],
    )
    with patch("app.services.scene_analyzer.gemini_provider.GeminiSceneAnalyzer.analyze_image") as mock_ai:
        mock_ai.return_value = mock_scene
        client.post(f"/api/projects/{project_id}/analyze")

    # User manually corrects scene type to 'study'
    patch_resp = client.patch(
        f"/api/projects/{project_id}/images/{image_id}/scene",
        json={
            "scene_type": "study",
            "description": "Converted home office and study room.",
            "features": ["desk", "bookshelf", "office chair"],
        },
    )
    assert patch_resp.status_code == 200
    patched_img = patch_resp.json()["data"]
    assert patched_img["scene"]["scene_type"] == "study"
    assert patched_img["scene"]["user_corrected"] is True
    assert patched_img["scene"]["confidence"] == 1.0
    assert patched_img["scene"]["description"] == "Converted home office and study room."

    # Verify persisted on fresh GET
    get_proj = client.get(f"/api/projects/{project_id}")
    saved_img = get_proj.json()["data"]["images"][0]
    assert saved_img["scene"]["scene_type"] == "study"
    assert saved_img["scene"]["user_corrected"] is True


def test_failed_analysis_error_handling(client):
    proj_resp = client.post("/api/projects", json={"name": "Error Property"})
    project_id = proj_resp.json()["data"]["id"]

    img_bytes = create_test_image_bytes(width=800, height=600)
    files = [("files", ("room_fail.jpg", img_bytes, "image/jpeg"))]
    client.post(f"/api/projects/{project_id}/images", files=files)

    with patch("app.services.scene_analyzer.gemini_provider.GeminiSceneAnalyzer.analyze_image") as mock_ai:
        mock_ai.side_effect = AppException(
            code="AI_RATE_LIMIT",
            message="Rate limit exceeded.",
            status_code=429,
        )

        resp = client.post(f"/api/projects/{project_id}/analyze")
        assert resp.status_code == 200
        proj = resp.json()["data"]
        assert proj["status"] == "failed"
        img = proj["images"][0]
        assert img["analysis_status"] == "failed"
        assert "Rate limit exceeded" in img["analysis_error"]
