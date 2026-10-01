from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AssemblyJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AssemblyProgressStage(str, Enum):
    VALIDATING = "validating_clips"
    NORMALIZING = "normalizing_clips"
    ASSEMBLING = "assembling_walkthrough"
    AUDIO_PROCESSING = "processing_audio"
    FINAL_VALIDATION = "validating_final_video"
    COMPLETED = "completed"
    FAILED = "failed"


class AssembledSceneInfo(BaseModel):
    scene_id: str = Field(..., description="Walkthrough scene ID")
    image_id: str = Field(..., description="Source image ID")
    order: int = Field(..., description="1-indexed sequence order")
    label: str = Field(..., description="Scene label e.g. Living Room")
    scene_type: str = Field(..., description="Classified scene type")
    duration_seconds: float = Field(..., ge=0.0, description="Duration in seconds")
    clip_filename: str = Field(..., description="Source clip filename")
    transition_to_next: Optional[str] = Field(default="straight_cut", description="Applied transition")


class FinalVideoMetadata(BaseModel):
    project_id: str = Field(..., description="Project ID")
    filename: str = Field(default="walkthrough.mp4", description="Stored walkthrough filename")
    video_url: str = Field(..., description="Streaming URL for video playback")
    download_url: str = Field(..., description="Direct download URL for final MP4")
    duration_seconds: float = Field(..., ge=0.0, description="Total walkthrough duration in seconds")
    width: int = Field(..., ge=1, description="Video width in pixels")
    height: int = Field(..., ge=1, description="Video height in pixels")
    fps: float = Field(default=24.0, description="Frames per second")
    format: str = Field(default="mp4", description="Container format")
    video_codec: str = Field(default="h264", description="Video compression codec")
    audio_codec: Optional[str] = Field(None, description="Audio codec if audio present")
    audio_enabled: bool = Field(default=False, description="Whether background soundtrack is active")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")
    scene_count: int = Field(..., ge=1, description="Number of assembled scenes")
    scenes_in_order: List[AssembledSceneInfo] = Field(default_factory=list, description="Ordered scene breakdown")
    plan_version: int = Field(default=1, description="Generation plan version used for assembly")
    plan_hash: str = Field(..., description="Cryptographic fingerprint of the source plan")
    is_outdated: bool = Field(default=False, description="True if generation plan was edited after assembly")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 assembly timestamp",
    )


class AssemblyConfig(BaseModel):
    intro_title_enabled: bool = Field(default=True, description="Whether to include a short 1-2s title card intro")
    intro_duration_seconds: float = Field(default=1.5, ge=0.5, le=4.0, description="Intro duration in seconds")
    crossfade_duration_seconds: float = Field(default=0.35, ge=0.2, le=1.0, description="Crossfade duration if used")
    audio_enabled: bool = Field(default=False, description="Whether to add subtle background music")
    audio_volume: float = Field(default=0.25, ge=0.0, le=1.0, description="Audio volume scale")
    output_fps: float = Field(default=24.0, description="Target output framerate")
    output_resolution: Optional[str] = Field(None, description="e.g. 1280x720 or 1920x1080")


class AssemblyRequest(BaseModel):
    config: Optional[AssemblyConfig] = Field(default_factory=AssemblyConfig, description="Assembly configuration")
    force_reassemble: bool = Field(default=False, description="Force reassembly even if a valid final video exists")


class AssemblyJob(BaseModel):
    job_id: str = Field(..., description="Unique assembly job ID")
    project_id: str = Field(..., description="Project ID")
    status: AssemblyJobStatus = Field(default=AssemblyJobStatus.QUEUED, description="Assembly status")
    stage: AssemblyProgressStage = Field(default=AssemblyProgressStage.VALIDATING, description="Current pipeline stage")
    stage_message: str = Field(default="Validating scene clips...", description="Human-readable progress description")
    progress_percentage: int = Field(default=0, ge=0, le=100, description="Stage-based progress percentage")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )
    started_at: Optional[str] = Field(None, description="ISO 8601 start timestamp")
    completed_at: Optional[str] = Field(None, description="ISO 8601 completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")
    error_category: Optional[str] = Field(None, description="Categorized error reason")
    result: Optional[FinalVideoMetadata] = Field(None, description="Final video metadata upon completion")
