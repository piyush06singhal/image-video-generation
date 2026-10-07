from typing import Dict, List, Optional, Set, Tuple
from app.schemas.image import ImageMetadata
from app.schemas.plan import ConnectionEvidence, SceneGraph, SceneNode
from app.schemas.scene import SceneType

# Standard spatial adjacency affinity matrix for residential properties
STANDARD_ADJACENCIES: Set[Tuple[SceneType, SceneType]] = {
    (SceneType.EXTERIOR, SceneType.ENTRANCE),
    (SceneType.EXTERIOR, SceneType.GARDEN),
    (SceneType.EXTERIOR, SceneType.PARKING),
    (SceneType.ENTRANCE, SceneType.HALLWAY),
    (SceneType.ENTRANCE, SceneType.LIVING_ROOM),
    (SceneType.LIVING_ROOM, SceneType.DINING_AREA),
    (SceneType.LIVING_ROOM, SceneType.BALCONY),
    (SceneType.LIVING_ROOM, SceneType.HALLWAY),
    (SceneType.DINING_AREA, SceneType.KITCHEN),
    (SceneType.KITCHEN, SceneType.UTILITY_AREA),
    (SceneType.HALLWAY, SceneType.BEDROOM),
    (SceneType.HALLWAY, SceneType.BATHROOM),
    (SceneType.HALLWAY, SceneType.STUDY),
    (SceneType.HALLWAY, SceneType.STAIRCASE),
    (SceneType.BEDROOM, SceneType.BATHROOM),
    (SceneType.BEDROOM, SceneType.BALCONY),
}

POSITION_HINTS: Dict[SceneType, str] = {
    SceneType.EXTERIOR: "outdoor_front",
    SceneType.PARKING: "outdoor_front",
    SceneType.GARDEN: "outdoor_exterior",
    SceneType.ENTRANCE: "primary_entry",
    SceneType.HALLWAY: "circulation",
    SceneType.LIVING_ROOM: "communal_primary",
    SceneType.DINING_AREA: "communal_dining",
    SceneType.KITCHEN: "service_kitchen",
    SceneType.UTILITY_AREA: "service_utility",
    SceneType.STUDY: "semi_private_workspace",
    SceneType.BEDROOM: "private_living",
    SceneType.BATHROOM: "private_sanitary",
    SceneType.BALCONY: "outdoor_terrace",
    SceneType.STAIRCASE: "vertical_circulation",
    SceneType.UNKNOWN: "unspecified",
}

SCENE_LABELS: Dict[SceneType, str] = {
    SceneType.EXTERIOR: "Exterior Facade",
    SceneType.ENTRANCE: "Foyer / Main Entrance",
    SceneType.LIVING_ROOM: "Living Room",
    SceneType.DINING_AREA: "Dining Area",
    SceneType.KITCHEN: "Kitchen",
    SceneType.BEDROOM: "Bedroom",
    SceneType.BATHROOM: "Bathroom",
    SceneType.BALCONY: "Balcony / Terrace",
    SceneType.HALLWAY: "Hallway / Corridor",
    SceneType.STUDY: "Study / Home Office",
    SceneType.UTILITY_AREA: "Utility / Laundry Area",
    SceneType.STAIRCASE: "Staircase",
    SceneType.GARDEN: "Garden / Patio",
    SceneType.PARKING: "Garage / Driveway",
    SceneType.UNKNOWN: "Unclassified Space",
}


class SceneGraphBuilder:
    """
    Constructs a lightweight topological scene graph hypothesis from analyzed property images.
    Adheres strictly to available visual evidence without assuming exact 3D geometry.
    """

    def build_graph(self, images: List[ImageMetadata]) -> SceneGraph:
        """
        Transforms validated image metadata into SceneNodes and calculates candidate relationship edges.
        """
        nodes: List[SceneNode] = []
        edges: List[ConnectionEvidence] = []

        # 1. Create SceneNodes from analyzed images
        room_counter: Dict[SceneType, int] = {}
        for img in images:
            scene_data = img.scene
            scene_type = scene_data.scene_type if scene_data else SceneType.UNKNOWN
            room_counter[scene_type] = room_counter.get(scene_type, 0) + 1
            count = room_counter[scene_type]

            base_label = SCENE_LABELS.get(scene_type, scene_type.value.replace("_", " ").title())
            display_label = f"{base_label} {count}" if room_counter[scene_type] > 1 or scene_type == SceneType.BEDROOM else base_label

            scene_id = f"scene_{img.id.replace('img_', '')[:8]}"

            nodes.append(
                SceneNode(
                    scene_id=scene_id,
                    image_id=img.id,
                    scene_type=scene_type,
                    label=display_label,
                    confidence=scene_data.confidence if scene_data else 0.5,
                    user_confirmed=scene_data.user_corrected if scene_data else False,
                    description=scene_data.description if scene_data else (img.original_filename or "Photograph"),
                    features=scene_data.features if scene_data else [],
                    visible_connections=scene_data.visible_connections if scene_data else [],
                    position_hint=POSITION_HINTS.get(scene_type, "interior"),
                    thumbnail_url=img.thumbnail_url or img.file_url,
                    original_filename=img.original_filename,
                )
            )

        # 2. Extract Candidate Relationship Edges
        node_count = len(nodes)
        for i in range(node_count):
            for j in range(i + 1, node_count):
                node_a = nodes[i]
                node_b = nodes[j]

                evidence, confidence, edge_type = self._evaluate_relationship(node_a, node_b)
                if evidence:
                    edges.append(
                        ConnectionEvidence(
                            source_scene_id=node_a.scene_id,
                            target_scene_id=node_b.scene_id,
                            evidence=evidence,
                            confidence=confidence,
                            type=edge_type,
                        )
                    )

        return SceneGraph(nodes=nodes, edges=edges)

    def _evaluate_relationship(
        self, node_a: SceneNode, node_b: SceneNode
    ) -> Tuple[Optional[str], float, str]:
        """
        Determines if an evidentiary connection exists between two scene nodes.
        Prioritizes visible passages and direct feature continuity over generic semantic rules.
        """
        # Case A: Visible Connection Evidence in Node A or Node B
        # e.g., Node A mentions doorway/passage to Node B's room type
        type_b_str = node_b.scene_type.value.replace("_", " ")
        type_a_str = node_a.scene_type.value.replace("_", " ")

        for conn in node_a.visible_connections:
            if type_b_str in conn.lower():
                return (
                    f"Direct visual passage identified in {node_a.label}: '{conn}' leading to {node_b.label}.",
                    0.88,
                    "visual",
                )

        for conn in node_b.visible_connections:
            if type_a_str in conn.lower():
                return (
                    f"Direct visual passage identified in {node_b.label}: '{conn}' leading to {node_a.label}.",
                    0.88,
                    "visual",
                )

        # Case B: Architectural Shared Features
        # e.g. sliding glass door connecting interior living to balcony/terrace
        features_a = set(f.lower() for f in node_a.features)
        features_b = set(f.lower() for f in node_b.features)
        shared_arch = features_a.intersection(features_b)

        transitional_markers = {"sliding glass door", "sliding doors", "french doors", "archway", "open doorway", "staircase"}
        shared_transitions = shared_arch.intersection(transitional_markers)

        if shared_transitions:
            marker = list(shared_transitions)[0]
            return (
                f"Shared transitional architectural boundary ({marker}) identified in both scenes.",
                0.78,
                "visual",
            )

        # Case C: Standard Residential Semantic Adjacency
        pair_forward = (node_a.scene_type, node_b.scene_type)
        pair_backward = (node_b.scene_type, node_a.scene_type)

        if pair_forward in STANDARD_ADJACENCIES or pair_backward in STANDARD_ADJACENCIES:
            return (
                f"Standard spatial adjacency grouping between {node_a.label} and {node_b.label}.",
                0.65,
                "semantic",
            )

        return None, 0.0, "none"
