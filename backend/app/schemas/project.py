from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from app.schemas.image import ImageMetadata


class ProjectStatus(str, Enum):
    CREATED = "created"
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    # Future lifecycle states (Phase 2+)
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    PARTIALLY_ANALYZED = "partially_analyzed"
    PLANNED = "planned"
    GENERATING = "generating"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, description="Real estate property name")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Property name cannot be blank or only whitespace.")
        return trimmed


class ProjectResponse(BaseModel):
    id: str = Field(..., description="Unique project ID e.g. project_20261001_abc123")
    name: str = Field(..., description="Property name")
    status: ProjectStatus = Field(default=ProjectStatus.CREATED, description="Current project lifecycle status")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 update timestamp",
    )
    images: List[ImageMetadata] = Field(default_factory=list, description="List of validated images")
    image_count: int = Field(0, description="Total number of uploaded images")
