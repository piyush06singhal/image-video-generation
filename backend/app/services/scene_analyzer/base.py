from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.schemas.scene import ImageQualityResult, SceneAnalysisResult


class BaseSceneAnalyzer(ABC):
    """
    Abstract interface for multimodal real estate visual scene analysis.
    Decouples core business logic from specific AI vision providers.
    """

    @abstractmethod
    async def analyze_image(
        self, image_path: Path, quality_info: Optional[ImageQualityResult] = None
    ) -> SceneAnalysisResult:
        """
        Analyzes a single real estate property photograph and extracts structured scene metadata.
        """
        pass
