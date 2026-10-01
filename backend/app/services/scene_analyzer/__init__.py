from app.core.config import settings
from app.services.scene_analyzer.base import BaseSceneAnalyzer
from app.services.scene_analyzer.gemini_provider import GeminiSceneAnalyzer


def get_scene_analyzer() -> BaseSceneAnalyzer:
    """
    Factory resolving the active scene analyzer provider based on configuration.
    """
    provider_name = settings.AI_PROVIDER.lower()
    if provider_name == "gemini":
        return GeminiSceneAnalyzer()
    # Defaults to Gemini provider
    return GeminiSceneAnalyzer()
