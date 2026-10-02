from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SceneReviewStatus(str, Enum):
    ACCEPTABLE = "acceptable"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class PanoramaUpdatePayload(BaseModel):
    is_panoramic: bool = Field(..., description="Whether to treat image as a 360 equirectangular panorama")
    panoramic_type: Optional[str] = Field(default=None, description="Optional classification: equirectangular, wide, perspective")


class EvaluationCreate(BaseModel):
    visual_quality: int = Field(..., ge=1, le=5, description="Visual Quality score (1 to 5)")
    property_consistency: int = Field(..., ge=1, le=5, description="Property Consistency score (1 to 5)")
    scene_ordering: int = Field(..., ge=1, le=5, description="Scene Ordering score (1 to 5)")
    motion_quality: int = Field(..., ge=1, le=5, description="Motion Quality score (1 to 5)")
    temporal_stability: int = Field(..., ge=1, le=5, description="Temporal Stability score (1 to 5)")
    walkthrough_usefulness: int = Field(..., ge=1, le=5, description="Walkthrough Usefulness score (1 to 5)")
    comments: Optional[str] = Field(default="", max_length=2000, description="Qualitative feedback comments")
    reviewer_name: Optional[str] = Field(default="Human Evaluator", max_length=100, description="Name or role of the evaluator")

    @field_validator(
        "visual_quality",
        "property_consistency",
        "scene_ordering",
        "motion_quality",
        "temporal_stability",
        "walkthrough_usefulness",
    )
    @classmethod
    def validate_score_range(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Evaluation scores must be integers between 1 and 5 inclusive.")
        return v


class EvaluationRecord(BaseModel):
    evaluation_id: str = Field(..., description="Unique evaluation identifier")
    project_id: str = Field(..., description="Associated project ID")
    visual_quality: int = Field(..., ge=1, le=5)
    property_consistency: int = Field(..., ge=1, le=5)
    scene_ordering: int = Field(..., ge=1, le=5)
    motion_quality: int = Field(..., ge=1, le=5)
    temporal_stability: int = Field(..., ge=1, le=5)
    walkthrough_usefulness: int = Field(..., ge=1, le=5)
    comments: str = Field(default="")
    reviewer_name: str = Field(default="Human Evaluator")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 evaluation timestamp",
    )


class SceneReviewCreate(BaseModel):
    scene_id: str = Field(..., description="Scene identifier being reviewed")
    status: SceneReviewStatus = Field(..., description="Review outcome: acceptable, needs_review, failed")
    flags: List[str] = Field(default_factory=list, description="Quality issue flags e.g. geometry_distortion, flickering, lighting_drift")
    notes: Optional[str] = Field(default="", max_length=1000, description="Review notes")


class SceneReviewRecord(BaseModel):
    review_id: str = Field(..., description="Unique review identifier")
    project_id: str = Field(..., description="Associated project ID")
    scene_id: str = Field(..., description="Scene identifier")
    status: SceneReviewStatus = Field(...)
    flags: List[str] = Field(default_factory=list)
    notes: str = Field(default="")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EvaluationSummary(BaseModel):
    total_evaluations: int = Field(0, description="Total number of submitted human evaluations")
    average_visual_quality: Optional[float] = Field(None, description="Average Visual Quality score")
    average_property_consistency: Optional[float] = Field(None, description="Average Property Consistency score")
    average_scene_ordering: Optional[float] = Field(None, description="Average Scene Ordering score")
    average_motion_quality: Optional[float] = Field(None, description="Average Motion Quality score")
    average_temporal_stability: Optional[float] = Field(None, description="Average Temporal Stability score")
    average_walkthrough_usefulness: Optional[float] = Field(None, description="Average Walkthrough Usefulness score")
    overall_average: Optional[float] = Field(None, description="Combined average across all evaluation dimensions")
    evaluations: List[EvaluationRecord] = Field(default_factory=list)
    scene_reviews: List[SceneReviewRecord] = Field(default_factory=list)


class TechnicalReport(BaseModel):
    project_id: str
    property_name: str
    project_status: str
    created_at: str
    report_generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_images_count: int
    analyzed_images_count: int
    panoramic_images_count: int
    planned_scenes_count: int
    generated_clips_count: int
    is_video_assembled: bool
    final_video: Optional[Dict[str, Any]] = None
    automated_checks: Dict[str, Any] = Field(default_factory=dict)
    evaluation_summary: EvaluationSummary
    formatted_text_report: str
