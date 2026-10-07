from typing import Dict, List, Optional
from app.schemas.plan import CameraInstruction, CameraMotionType, SceneNode
from app.schemas.scene import SceneType

# Deterministic baseline motion type mapping per room type and view scale
DEFAULT_ROOM_MOTIONS: Dict[SceneType, CameraMotionType] = {
    SceneType.EXTERIOR: CameraMotionType.EXTERIOR_FORWARD,
    SceneType.PARKING: CameraMotionType.EXTERIOR_FORWARD,
    SceneType.GARDEN: CameraMotionType.SLOW_FORWARD,
    SceneType.ENTRANCE: CameraMotionType.SLOW_FORWARD,
    SceneType.HALLWAY: CameraMotionType.SLOW_FORWARD,
    SceneType.LIVING_ROOM: CameraMotionType.SLOW_FORWARD,
    SceneType.DINING_AREA: CameraMotionType.SLIGHT_DOLLY,
    SceneType.KITCHEN: CameraMotionType.PAN_RIGHT,
    SceneType.UTILITY_AREA: CameraMotionType.STATIC_SUBTLE_MOTION,
    SceneType.STUDY: CameraMotionType.SLIGHT_DOLLY,
    SceneType.BEDROOM: CameraMotionType.SLOW_FORWARD,
    SceneType.BATHROOM: CameraMotionType.STATIC_SUBTLE_MOTION,
    SceneType.BALCONY: CameraMotionType.SLOW_FORWARD,
    SceneType.STAIRCASE: CameraMotionType.SLOW_FORWARD,
    SceneType.UNKNOWN: CameraMotionType.STATIC_SUBTLE_MOTION,
}

STANDARD_PRESERVATION_CONSTRAINTS: List[str] = [
    "do not alter room geometry",
    "do not add furniture",
    "do not remove visible furniture",
    "do not change wall positions",
    "do not change windows or doors",
    "avoid excessive camera motion",
    "avoid visual distortion",
]


class CameraPromptGenerator:
    """
    Generates conservative, cinematic camera motion instructions and constraint prompts
    for image-to-video generation models. Emphasizes architectural fidelity.
    """

    def plan_camera(
        self,
        node: SceneNode,
        custom_motion: Optional[CameraMotionType] = None,
        custom_prompt: Optional[str] = None,
    ) -> CameraInstruction:
        """
        Determines the optimal motion strategy and compiles a generation-ready prompt.
        """
        motion_type = custom_motion or self._determine_motion_type(node)

        if custom_prompt and custom_prompt.strip():
            prompt = custom_prompt.strip()
        else:
            prompt = self._build_prompt(node, motion_type)

        duration = self._determine_duration(node.scene_type)

        return CameraInstruction(
            motion_type=motion_type,
            prompt=prompt,
            constraints=list(STANDARD_PRESERVATION_CONSTRAINTS),
            duration_seconds=duration,
        )

    def _determine_motion_type(self, node: SceneNode) -> CameraMotionType:
        """
        Selects conservative camera motion tailored to room type and view scale.
        """
        scene_type = node.scene_type

        # Default by scene type
        base_motion = DEFAULT_ROOM_MOTIONS.get(scene_type, CameraMotionType.STATIC_SUBTLE_MOTION)

        # Refine based on specific view characteristics if present
        if scene_type == SceneType.KITCHEN:
            # Lateral pan works best for wide kitchens
            return CameraMotionType.PAN_RIGHT
        elif scene_type == SceneType.BATHROOM:
            # Bathrooms have tight physical space; avoid forward zoom
            return CameraMotionType.STATIC_SUBTLE_MOTION
        elif scene_type == SceneType.BALCONY:
            # Slow push toward exterior view
            return CameraMotionType.SLOW_FORWARD
        elif scene_type in {SceneType.EXTERIOR, SceneType.PARKING}:
            return CameraMotionType.EXTERIOR_FORWARD

        return base_motion

    def _build_prompt(self, node: SceneNode, motion_type: CameraMotionType) -> str:
        """
        Synthesizes a structured cinematic prompt with mandatory preservation instructions.
        """
        space_name = node.scene_type.value.replace("_", " ")

        motion_descriptions = {
            CameraMotionType.SLOW_FORWARD: f"Slow, restrained forward camera movement into the {space_name}",
            CameraMotionType.SLOW_BACKWARD: f"Slow, smooth backward camera movement revealing the {space_name}",
            CameraMotionType.PAN_LEFT: f"Smooth, cinematic horizontal camera pan to the left across the {space_name}",
            CameraMotionType.PAN_RIGHT: f"Smooth, cinematic horizontal camera pan to the right across the {space_name}",
            CameraMotionType.SLIGHT_DOLLY: f"Gentle forward dolly glide with subtle perspective stabilization through the {space_name}",
            CameraMotionType.STATIC_SUBTLE_MOTION: f"Static camera with subtle organic breathing motion preserving the {space_name}",
            CameraMotionType.GENTLE_ORBIT: f"Gentle, conservative arc camera motion around the center of the {space_name}",
            CameraMotionType.EXTERIOR_FORWARD: f"Slow, stately forward camera track approaching the property facade",
            CameraMotionType.UNKNOWN: f"Slow, stabilized camera motion showcasing the space",
        }

        action_clause = motion_descriptions.get(
            motion_type, f"Slow stabilized camera motion through the {space_name}"
        )

        # Include key visible features to anchor model attention
        feature_context = ""
        if node.features:
            top_features = ", ".join(node.features[:3])
            feature_context = f", highlighting the {top_features}"

        prompt = (
            f"{action_clause}{feature_context}. "
            f"Preserve the exact existing architectural layout, wall boundaries, furniture placement, "
            f"materials, windows, and natural lighting. Maintain realistic perspective and avoid introducing "
            f"new objects, artifacts, or camera distortion."
        )

        return prompt

    def _determine_duration(self, scene_type: SceneType) -> float:
        """
        Assigns standard shot duration based on room scale.
        """
        if scene_type in {SceneType.EXTERIOR, SceneType.LIVING_ROOM}:
            return 4.5
        elif scene_type in {SceneType.BATHROOM, SceneType.UTILITY_AREA}:
            return 3.5
        return 4.0
