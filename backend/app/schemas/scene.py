from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class SceneType(str, Enum):
    EXTERIOR = "exterior"
    ENTRANCE = "entrance"
    LIVING_ROOM = "living_room"
    KITCHEN = "kitchen"
    DINING_AREA = "dining_area"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    BALCONY = "balcony"
    HALLWAY = "hallway"
    STUDY = "study"
    UTILITY_AREA = "utility_area"
    STAIRCASE = "staircase"
    GARDEN = "garden"
    PARKING = "parking"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str) -> "SceneType":
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == normalized:
                return member
        return cls.UNKNOWN


class LightingType(str, Enum):
    NATURAL_DAYLIGHT = "natural_daylight"
    WARM_ARTIFICIAL = "warm_artificial"
    COOL_ARTIFICIAL = "cool_artificial"
    MIXED = "mixed"
    LOW_LIGHT = "low_light"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str) -> "LightingType":
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == normalized:
                return member
        return cls.UNKNOWN


class ViewType(str, Enum):
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE = "close"
    OVERHEAD = "overhead"
    EXTERIOR = "exterior"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str) -> "ViewType":
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == normalized:
                return member
        return cls.UNKNOWN


class CameraView(str, Enum):
    EYE_LEVEL = "eye_level"
    SLIGHTLY_ELEVATED = "slightly_elevated"
    LOW_ANGLE = "low_angle"
    CENTERED = "centered"
    CORNER_VIEW = "corner_view"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str) -> "CameraView":
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == normalized:
                return member
        return cls.UNKNOWN


class QualityStatus(str, Enum):
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


class ImageQualityResult(BaseModel):
    status: QualityStatus = Field(..., description="Overall image quality classification (good, acceptable, poor)")
    resolution: str = Field(..., description="Resolution string (e.g. 1920x1080)")
    brightness_score: float = Field(..., ge=0.0, le=1.0, description="Normalized brightness score (0.0 to 1.0)")
    contrast_score: float = Field(..., ge=0.0, le=1.0, description="Normalized contrast score (0.0 to 1.0)")
    sharpness_score: float = Field(..., ge=0.0, le=1.0, description="Normalized blur/sharpness estimate (0.0 to 1.0)")
    file_size: int = Field(..., ge=0, description="File size in bytes")


class SceneAnalysisResult(BaseModel):
    scene_type: SceneType = Field(..., description="Identified real-estate room/scene type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0")
    description: str = Field(..., min_length=1, description="Objective, factual description of visible elements")
    features: List[str] = Field(default_factory=list, description="List of identifiable architectural and furniture features")
    lighting: LightingType = Field(default=LightingType.UNKNOWN, description="Visible lighting condition")
    view_type: ViewType = Field(default=ViewType.UNKNOWN, description="Camera shot/view scale")
    camera_view: CameraView = Field(default=CameraView.UNKNOWN, description="Camera angle/viewpoint perspective")
    visible_connections: List[str] = Field(default_factory=list, description="Visible doors, hallways, or open passageways")
    user_corrected: bool = Field(default=False, description="Whether the scene type was manually adjusted by the user")
    analyzed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 analysis timestamp",
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        try:
            val = float(v)
            return max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            return 0.5


class SceneCorrectionPayload(BaseModel):
    scene_type: SceneType = Field(..., description="Updated room/scene classification")
    description: Optional[str] = Field(None, description="Optional updated scene description")
    features: Optional[List[str]] = Field(None, description="Optional updated features list")


class ProjectAnalysisRequest(BaseModel):
    force_reanalyze: bool = Field(default=False, description="Re-analyze images even if already completed")
    image_ids: Optional[List[str]] = Field(None, description="Optional list of specific image IDs to analyze")
