from typing import Dict, List, Optional, Set, Tuple
from app.schemas.plan import ConnectionEvidence, SceneGraph, SceneNode
from app.schemas.scene import SceneType

# Deterministic default walkthrough hierarchy ranks (lower number = earlier in walkthrough)
SCENE_HIERARCHY_RANK: Dict[SceneType, int] = {
    SceneType.EXTERIOR: 10,
    SceneType.PARKING: 15,
    SceneType.ENTRANCE: 20,
    SceneType.HALLWAY: 25,
    SceneType.LIVING_ROOM: 30,
    SceneType.DINING_AREA: 40,
    SceneType.KITCHEN: 50,
    SceneType.UTILITY_AREA: 55,
    SceneType.STAIRCASE: 60,
    SceneType.STUDY: 65,
    SceneType.BEDROOM: 70,
    SceneType.BATHROOM: 80,
    SceneType.BALCONY: 90,
    SceneType.GARDEN: 95,
    SceneType.UNKNOWN: 100,
}


class OrderingEngine:
    """
    Computes a deterministic, coherent walkthrough sequence from available scene nodes.
    Guarantees that NO unsupplied rooms or hallucinated spaces are ever introduced.
    """

    def determine_order(
        self,
        scene_graph: SceneGraph,
        user_preferred_order: Optional[List[str]] = None,
    ) -> List[Tuple[SceneNode, str]]:
        """
        Orders the scene nodes into a natural property walkthrough trajectory.
        Returns a list of (SceneNode, placement_reason) tuples.
        """
        nodes = scene_graph.nodes
        if not nodes:
            return []

        # If user explicitly provided a complete or partial order list, prioritize user order
        if user_preferred_order:
            ordered_nodes = self._apply_user_order(nodes, user_preferred_order)
            return ordered_nodes

        # 1. Base sort by architectural hierarchy rank, then by confidence descending
        sorted_nodes = sorted(
            nodes,
            key=lambda n: (
                SCENE_HIERARCHY_RANK.get(n.scene_type, 100),
                -n.confidence,
                n.scene_id,
            ),
        )

        # 2. Refine sequence with visual connection graph edges
        refined_sequence = self._refine_with_connections(sorted_nodes, scene_graph.edges)

        # 3. Generate transparent placement reasoning for each scene
        result: List[Tuple[SceneNode, str]] = []
        for idx, node in enumerate(refined_sequence):
            reason = self._generate_placement_reason(idx, node, refined_sequence, scene_graph.edges)
            result.append((node, reason))

        return result

    def _apply_user_order(
        self, nodes: List[SceneNode], user_order_ids: List[str]
    ) -> List[Tuple[SceneNode, str]]:
        """
        Arranges nodes matching user-specified IDs first, appending any unranked nodes at the end.
        """
        node_map = {n.scene_id: n for n in nodes}
        ordered: List[Tuple[SceneNode, str]] = []
        seen = set()

        for idx, sid in enumerate(user_order_ids):
            if sid in node_map and sid not in seen:
                node = node_map[sid]
                ordered.append((node, f"Placed at position {idx + 1} per explicit user plan configuration."))
                seen.add(sid)

        # Append any remaining scenes that were not in user_order_ids
        for node in nodes:
            if node.scene_id not in seen:
                ordered.append((node, "Appended sequence item preserving project inventory."))

        return ordered

    def _refine_with_connections(
        self, sorted_nodes: List[SceneNode], edges: List[ConnectionEvidence]
    ) -> List[SceneNode]:
        """
        Adjusts initial hierarchy ordering so that rooms with strong visual connections are kept adjacent.
        """
        if len(sorted_nodes) <= 2:
            return sorted_nodes

        # Build adjacency map for fast visual edge lookup
        visual_connections: Dict[str, Set[str]] = {}
        for edge in edges:
            if edge.type == "visual" and edge.confidence >= 0.75:
                visual_connections.setdefault(edge.source_scene_id, set()).add(edge.target_scene_id)
                visual_connections.setdefault(edge.target_scene_id, set()).add(edge.source_scene_id)

        # Start with the naturally sorted list
        sequence: List[SceneNode] = [sorted_nodes[0]]
        remaining = sorted_nodes[1:]

        while remaining:
            current_node = sequence[-1]
            current_id = current_node.scene_id

            # Check if any remaining node has a direct visual connection to the current node
            connected_candidates = [
                n for n in remaining if n.scene_id in visual_connections.get(current_id, set())
            ]

            if connected_candidates:
                # Pick the connected candidate that best matches hierarchy order
                best_next = min(
                    connected_candidates,
                    key=lambda n: SCENE_HIERARCHY_RANK.get(n.scene_type, 100),
                )
                sequence.append(best_next)
                remaining.remove(best_next)
            else:
                # No direct visual connection found, take next by standard hierarchy
                next_node = remaining.pop(0)
                sequence.append(next_node)

        return sequence

    def _generate_placement_reason(
        self,
        index: int,
        node: SceneNode,
        sequence: List[SceneNode],
        edges: List[ConnectionEvidence],
    ) -> str:
        """
        Builds a concise, transparent explanation for why this scene is in this position.
        """
        if index == 0:
            if node.scene_type in {SceneType.EXTERIOR, SceneType.ENTRANCE, SceneType.PARKING}:
                return f"Initial property establishing shot: {node.label} serves as the natural walkthrough entry point."
            return f"Initial walkthrough shot: {node.label} selected as primary starting viewpoint from available photographs."

        prev_node = sequence[index - 1]

        # Check if connected by an explicit visual edge
        matching_edge = next(
            (
                e
                for e in edges
                if (e.source_scene_id == prev_node.scene_id and e.target_scene_id == node.scene_id)
                or (e.source_scene_id == node.scene_id and e.target_scene_id == prev_node.scene_id)
            ),
            None,
        )

        if matching_edge and matching_edge.type == "visual":
            return f"Sequenced after {prev_node.label} due to identified visual connection: {matching_edge.evidence}"

        # Standard topological room progression explanation
        return f"Sequenced after {prev_node.label} following natural residential walkthrough hierarchy ({prev_node.label} → {node.label})."
