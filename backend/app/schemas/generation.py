from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.plan import CameraMotionType


class GenerationJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SceneGenerationStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectGenerationStatus(str, Enum):
    READY = "ready"
    GENERATING = "generating"
    PARTIALLY_COMPLETED = "partially_completed"
    COMPLETED = "completed"
    FAILED = "failed"


class QualityAssessment(str, Enum):
    ACCEPTABLE = "acceptable"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class VideoClipMetadata(BaseModel):
    scene_id: str = Field(..., description="Target walkthrough scene ID")
    image_id: str = Field(..., description="Source photographic image ID")
    clip_filename: str = Field(..., description="Stored video filename (e.g. clip_scene_abc123.mp4)")
    clip_path: str = Field(..., description="Relative local storage path")
    clip_url: str = Field(..., description="HTTP streaming URL for playback")
    duration_seconds: float = Field(..., ge=0.0, description="Measured video duration in seconds")
    width: int = Field(..., ge=1, description="Video width in pixels")
    height: int = Field(..., ge=1, description="Video height in pixels")
    fps: float = Field(default=24.0, description="Frames per second")
    format: str = Field(default="mp4", description="Video container format")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")
    provider: str = Field(..., description="Generation provider name")
    model: str = Field(..., description="Generation model name")
    camera_motion: CameraMotionType = Field(..., description="Applied camera motion type")
    prompt: str = Field(..., description="Executed prompt sent to video model")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 generation completion timestamp",
    )
    quality: QualityAssessment = Field(default=QualityAssessment.ACCEPTABLE, description="Automated quality check status")


class GenerationJob(BaseModel):
    job_id: str = Field(..., description="Unique generation job identifier")
    project_id: str = Field(..., description="Project ID")
    scene_id: str = Field(..., description="Scene ID being generated")
    image_id: str = Field(..., description="Source image ID")
    status: GenerationJobStatus = Field(default=GenerationJobStatus.QUEUED, description="Current job execution state")
    provider: str = Field(..., description="Video provider name")
    provider_job_id: Optional[str] = Field(None, description="Remote provider operation ID")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )
    started_at: Optional[str] = Field(None, description="ISO 8601 execution start timestamp")
    completed_at: Optional[str] = Field(None, description="ISO 8601 completion or failure timestamp")
    error: Optional[str] = Field(None, description="Human-readable error message if failed")
    error_code: Optional[str] = Field(None, description="Categorized application error code")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    result_clip: Optional[VideoClipMetadata] = Field(None, description="Generated clip metadata upon completion")


class SceneGenerationSummary(BaseModel):
    scene_id: str = Field(..., description="Scene ID")
    order: int = Field(..., description="1-indexed sequence order in walkthrough")
    label: str = Field(..., description="Scene label e.g. Living Room")
    scene_type: str = Field(..., description="Classified scene type")
    thumbnail_url: Optional[str] = Field(None, description="Image thumbnail URL")
    status: SceneGenerationStatus = Field(default=SceneGenerationStatus.PENDING, description="Scene generation state")
    job_id: Optional[str] = Field(None, description="Active or last generation job ID")
    clip: Optional[VideoClipMetadata] = Field(None, description="Completed video clip metadata")
    last_error: Optional[str] = Field(None, description="Last failure reason if any")
    camera_motion: Optional[CameraMotionType] = Field(None, description="Planned camera motion")


class ProjectGenerationOverview(BaseModel):
    project_id: str = Field(..., description="Project ID")
    status: ProjectGenerationStatus = Field(default=ProjectGenerationStatus.READY, description="Overall project generation status")
    total_scenes: int = Field(default=0, description="Total scenes in plan")
    completed_scenes: int = Field(default=0, description="Count of completed clips")
    generating_scenes: int = Field(default=0, description="Count of actively generating scenes")
    failed_scenes: int = Field(default=0, description="Count of failed scenes")
    pending_scenes: int = Field(default=0, description="Count of pending scenes")
    total_duration_seconds: float = Field(default=0.0, description="Total duration of completed clips in seconds")
    scenes: List[SceneGenerationSummary] = Field(default_factory=list, description="List of scene generation statuses")
    active_jobs: List[GenerationJob] = Field(default_factory=list, description="Active or recent generation jobs")


class GenerateRequest(BaseModel):
    scene_ids: Optional[List[str]] = Field(None, description="Specific scene IDs to generate; if omitted, generates all eligible scenes")
    force_regenerate: bool = Field(default=False, description="Whether to re-generate already completed clips")


class RegenerateSceneRequest(BaseModel):
    custom_motion_type: Optional[CameraMotionType] = Field(None, description="Optional override camera motion type")
    custom_prompt: Optional[str] = Field(None, description="Optional override generation prompt")
