from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ProviderResult:
    """Encapsulates the raw artifact produced by an image-to-video provider."""
    provider_job_id: str
    output_video_path: Path
    provider_name: str
    model_name: str
    duration_seconds: float
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


class ImageToVideoProvider(ABC):
    """
    Abstract contract for image-to-video diffusion providers.
    Isolates vendor-specific SDK and REST API mechanisms from core application logic.
    """

    @abstractmethod
    async def generate_clip(
        self,
        source_image_path: Path,
        prompt: str,
        negative_prompt: Optional[str],
        duration_seconds: float,
        camera_motion: str,
        output_path: Path,
    ) -> ProviderResult:
        """
        Executes real image-to-video generation, polls asynchronous operations to completion,
        downloads the resulting video artifact, and saves it to output_path.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the canonical name of this provider."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Returns the configured model name."""
        pass
