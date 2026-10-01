from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from app.schemas.scene import SceneType


class CameraMotionType(str, Enum):
    SLOW_FORWARD = "slow_forward"
    SLOW_BACKWARD = "slow_backward"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    SLIGHT_DOLLY = "slight_dolly"
    STATIC_SUBTLE_MOTION = "static_subtle_motion"
    GENTLE_ORBIT = "gentle_orbit"
    EXTERIOR_FORWARD = "exterior_forward"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str) -> "CameraMotionType":
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == normalized:
                return member
        return cls.UNKNOWN


CAMERA_MOTION_LABELS: Dict[CameraMotionType, str] = {
    CameraMotionType.SLOW_FORWARD: "Slow Forward Movement",
    CameraMotionType.SLOW_BACKWARD: "Slow Backward Pull",
    CameraMotionType.PAN_LEFT: "Smooth Pan Left",
    CameraMotionType.PAN_RIGHT: "Smooth Pan Right",
    CameraMotionType.SLIGHT_DOLLY: "Slight Forward Dolly",
    CameraMotionType.STATIC_SUBTLE_MOTION: "Static Subtle Drift",
    CameraMotionType.GENTLE_ORBIT: "Gentle Arc Orbit",
    CameraMotionType.EXTERIOR_FORWARD: "Exterior Forward Approach",
    CameraMotionType.UNKNOWN: "Restrained Camera Movement",
}


class TransitionType(str, Enum):
    STRAIGHT_CUT = "straight_cut"
    SHORT_CROSSFADE = "short_crossfade"
    VISUAL_MATCH = "visual_match"
    FADE = "fade"

    @classmethod
    def from_str(cls, value: str) -> "TransitionType":
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == normalized:
                return member
        return cls.STRAIGHT_CUT


class PlanSource(str, Enum):
    AI = "ai"
    USER = "user"


# ==========================================
# Scene Graph Models
# ==========================================

class SceneNode(BaseModel):
    scene_id: str = Field(..., description="Unique scene node identifier")
    image_id: str = Field(..., description="Source image identifier from Phase 1/2")
    scene_type: SceneType = Field(..., description="Classified room/space type")
    label: str = Field(..., description="Human-readable scene name (e.g. Living Room)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    user_confirmed: bool = Field(default=False, description="Whether user explicitly validated or edited the scene")
    description: str = Field(..., description="Factual visual description from scene analysis")
    features: List[str] = Field(default_factory=list, description="Identified architectural/furniture elements")
    visible_connections: List[str] = Field(default_factory=list, description="Visible doorways or passages")
    position_hint: Optional[str] = Field(None, description="Heuristic or topological placement tag (e.g. entry, interior, private, outdoor)")
    thumbnail_url: Optional[str] = Field(None, description="Preview URL for UI rendering")
    original_filename: Optional[str] = Field(None, description="Original filename")


class ConnectionEvidence(BaseModel):
    source_scene_id: str = Field(..., description="Originating scene ID")
    target_scene_id: str = Field(..., description="Destination scene ID")
    evidence: str = Field(..., description="Reasoning for inferred relationship (e.g. 'visible open archway', 'common hallway access')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Estimated relationship confidence")
    type: str = Field(default="visual", description="Type of evidence: 'visual', 'semantic', 'user'")


class SceneGraph(BaseModel):
    nodes: List[SceneNode] = Field(default_factory=list, description="All active scene nodes")
    edges: List[ConnectionEvidence] = Field(default_factory=list, description="Candidate relationship edges")


# ==========================================
# Camera & Transition Instruction Models
# ==========================================

class CameraInstruction(BaseModel):
    motion_type: CameraMotionType = Field(..., description="Standardized motion strategy")
    prompt: str = Field(..., description="Cinematic camera instruction prompt for image-to-video model")
    constraints: List[str] = Field(
        default_factory=lambda: [
            "do not alter room geometry",
            "do not add furniture",
            "do not remove visible furniture",
            "do not change wall positions",
            "do not change windows or doors",
            "avoid excessive camera motion",
            "avoid visual distortion",
        ],
        description="Preservation rules and negative constraints",
    )
    duration_seconds: float = Field(default=4.0, ge=1.0, le=15.0, description="Target clip duration in seconds")


class TransitionInstruction(BaseModel):
    type: TransitionType = Field(default=TransitionType.STRAIGHT_CUT, description="Inter-scene transition type")
    duration_seconds: float = Field(default=0.5, ge=0.0, le=3.0, description="Transition blend duration in seconds")
    reason: Optional[str] = Field(None, description="Factual justification for selected transition")


# ==========================================
# Planned Scene & Generation Plan Contract
# ==========================================

class PlannedScene(BaseModel):
    order: int = Field(..., ge=1, description="1-indexed sequence order in walkthrough")
    scene_id: str = Field(..., description="Unique scene node ID")
    image_id: str = Field(..., description="Source image ID")
    scene_type: SceneType = Field(..., description="Room/scene classification")
    label: str = Field(..., description="Display label for the scene")
    reason: str = Field(..., description="Deterministic reasoning for placing this scene at this position")
    camera: CameraInstruction = Field(..., description="Generated camera motion strategy and prompt")
    transition_to_next: Optional[TransitionInstruction] = Field(
        None, description="Transition plan to the subsequent scene in sequence (null for final scene)"
    )
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL for UI rendering")
    original_filename: Optional[str] = Field(None, description="Source original filename")
    user_confirmed: bool = Field(default=False, description="Whether user explicitly confirmed or edited this scene")


class GenerationPlan(BaseModel):
    plan_id: str = Field(..., description="Unique plan identifier")
    project_id: str = Field(..., description="Associated project ID")
    plan_version: int = Field(default=1, ge=1, description="Sequential plan version counter")
    source: PlanSource = Field(default=PlanSource.AI, description="Source of plan: 'ai' or 'user'")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 update timestamp",
    )
    scenes: List[PlannedScene] = Field(default_factory=list, description="Ordered walkthrough sequence")
    removed_scene_ids: List[str] = Field(default_factory=list, description="Scenes excluded from walkthrough by user")
    scene_graph: Optional[SceneGraph] = Field(None, description="Full candidate scene graph representation")
    total_estimated_duration_seconds: float = Field(
        default=0.0, description="Calculated total walkthrough video duration in seconds"
    )

    @field_validator("scenes")
    @classmethod
    def validate_scenes_unique_order(cls, scenes: List[PlannedScene]) -> List[PlannedScene]:
        seen_orders = set()
        seen_ids = set()
        for s in scenes:
            if s.order in seen_orders:
                raise ValueError(f"Duplicate sequence order '{s.order}' detected in plan.")
            if s.scene_id in seen_ids:
                raise ValueError(f"Duplicate scene ID '{s.scene_id}' detected in plan.")
            seen_orders.add(s.order)
            seen_ids.add(s.scene_id)
        return scenes


# ==========================================
# User Plan Update Request Schemas
# ==========================================

class PlannedSceneUpdateItem(BaseModel):
    scene_id: str = Field(..., description="Scene ID to update")
    order: int = Field(..., ge=1, description="New 1-indexed sequence order")
    label: Optional[str] = Field(None, description="Optional updated human label")
    motion_type: Optional[CameraMotionType] = Field(None, description="Optional updated camera motion type")
    camera_prompt: Optional[str] = Field(None, description="Optional custom camera prompt")
    transition_type: Optional[TransitionType] = Field(None, description="Optional custom transition type")
    user_confirmed: Optional[bool] = Field(None, description="Explicit user confirmation flag")


class PlanUpdateRequest(BaseModel):
    scenes: List[PlannedSceneUpdateItem] = Field(..., min_length=1, description="Updated ordered scenes list")
    removed_scene_ids: Optional[List[str]] = Field(default_factory=list, description="IDs of scenes removed from walkthrough")
