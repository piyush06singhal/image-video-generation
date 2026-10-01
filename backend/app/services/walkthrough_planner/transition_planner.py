from typing import List, Optional
from app.schemas.plan import ConnectionEvidence, SceneNode, TransitionInstruction, TransitionType
from app.schemas.scene import SceneType


class TransitionPlanner:
    """
    Computes inter-scene transition instructions between sequential walkthrough keyframes.
    Defaults to realistic straight cuts and conservative crossfades only when continuity is supported.
    """

    def plan_transition(
        self,
        current_node: SceneNode,
        next_node: SceneNode,
        edges: List[ConnectionEvidence],
        custom_type: Optional[TransitionType] = None,
    ) -> TransitionInstruction:
        """
        Calculates the transition instruction from current_node to next_node.
        """
        if custom_type:
            return TransitionInstruction(
                type=custom_type,
                duration_seconds=0.5 if custom_type != TransitionType.STRAIGHT_CUT else 0.0,
                reason="Transition overridden by explicit user plan setting.",
            )

        # Look for visual or shared boundary connection evidence between the two scenes
        matching_edge = next(
            (
                e
                for e in edges
                if (
                    (e.source_scene_id == current_node.scene_id and e.target_scene_id == next_node.scene_id)
                    or (e.source_scene_id == next_node.scene_id and e.target_scene_id == current_node.scene_id)
                )
            ),
            None,
        )

        if matching_edge and matching_edge.type == "visual" and matching_edge.confidence >= 0.75:
            return TransitionInstruction(
                type=TransitionType.SHORT_CROSSFADE,
                duration_seconds=0.5,
                reason=f"Short crossfade applied: visual evidence connects {current_node.label} to {next_node.label} ({matching_edge.evidence}).",
            )

        if current_node.scene_type in {SceneType.EXTERIOR, SceneType.PARKING} and next_node.scene_type in {SceneType.ENTRANCE, SceneType.LIVING_ROOM}:
            return TransitionInstruction(
                type=TransitionType.SHORT_CROSSFADE,
                duration_seconds=0.6,
                reason="Smooth entry transition: exterior approach crossing threshold into interior entrance.",
            )

        # Default conservative cut
        return TransitionInstruction(
            type=TransitionType.STRAIGHT_CUT,
            duration_seconds=0.0,
            reason=f"Standard cut between distinct photographic viewpoints ({current_node.label} → {next_node.label}).",
        )
