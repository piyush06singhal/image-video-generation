from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator
from app.schemas.scene import ImageQualityResult, SceneAnalysisResult


class ImageStatus(str, Enum):
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    REJECTED = "rejected"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageMetadata(BaseModel):
    id: str = Field(..., description="Unique server-generated image identifier")
    filename: str = Field(..., description="Stored safe filename")
    original_filename: str = Field(..., description="Original client filename")
    width: int = Field(..., ge=1, description="Image width in pixels")
    height: int = Field(..., ge=1, description="Image height in pixels")
    format: str = Field(..., description="Image format e.g. JPEG, PNG, WEBP")
    file_size: int = Field(..., ge=0, description="Image file size in bytes")
    aspect_ratio: float = Field(..., description="Image aspect ratio (width / height)")
    sha256: Optional[str] = Field(None, description="SHA-256 hash of the image content for duplicate detection")
    status: ImageStatus = Field(default=ImageStatus.VALIDATED, description="Validation status")
    upload_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 upload timestamp",
    )
    file_url: Optional[str] = Field(None, description="API URL to download or view original image")
    thumbnail_url: Optional[str] = Field(None, description="API URL to view derived thumbnail")

    @field_validator("aspect_ratio", mode="before")
    @classmethod
    def coerce_aspect_ratio(cls, v: Any) -> float:
        """Accept both float and legacy 'W:H' string format from stored data."""
        if isinstance(v, str) and ":" in v:
            parts = v.split(":")
            try:
                return float(parts[0]) / float(parts[1])
            except (ValueError, ZeroDivisionError):
                return 1.0
        return float(v)
    
    # Phase 2: Analysis & Quality extensions
    analysis_status: AnalysisStatus = Field(
        default=AnalysisStatus.PENDING, description="Current scene understanding analysis status"
    )
    scene: Optional[SceneAnalysisResult] = Field(
        default=None, description="Structured visual scene understanding result"
    )
    quality: Optional[ImageQualityResult] = Field(
        default=None, description="Calculated image quality metrics"
    )
    analysis_error: Optional[str] = Field(
        default=None, description="Human-readable error description if analysis failed"
    )
    analysis_image_url: Optional[str] = Field(
        default=None, description="API URL to view normalized analysis-ready image"
    )


class RejectedImage(BaseModel):
    filename: str
    code: str
    message: str


class ImageBatchUploadResult(BaseModel):
    project_id: str
    total_received: int
    total_accepted: int
    total_rejected: int
    uploaded: List[ImageMetadata]
    rejected: List[RejectedImage]
