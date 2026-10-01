import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.core.errors import AppException
from app.main import app
from app.schemas.image import ImageMetadata
from app.schemas.plan import (
    CameraMotionType,
    GenerationPlan,
    PlanSource,
    PlanUpdateRequest,
    PlannedSceneUpdateItem,
    SceneNode,
    TransitionType,
)

from app.schemas.project import ProjectCreate
from app.schemas.scene import (
    CameraView,
    LightingType,
    SceneAnalysisResult,
    SceneCorrectionPayload,
    SceneType,
    ViewType,
)
from app.services.project_service import project_service
from app.services.scene_service import scene_service
from app.services.walkthrough_planner import (
    CameraPromptGenerator,
    OrderingEngine,
    SceneGraphBuilder,
    TransitionPlanner,
    walkthrough_planner,
)
from tests.helpers import create_test_image_bytes

client = TestClient(app)


def make_dummy_analyzed_image(
    image_id: str,
    scene_type: SceneType,
    confidence: float = 0.95,
    features: list = None,
    visible_connections: list = None,
    user_corrected: bool = False,
) -> ImageMetadata:
    return ImageMetadata(
        id=image_id,
        filename=f"{image_id}.jpg",
        original_filename=f"{image_id}.jpg",
        width=1920,
        height=1080,
        format="JPEG",
        file_size=250000,
        aspect_ratio=1.777,
        sha256=f"hash_{image_id}",
        analysis_status="completed",
        scene=SceneAnalysisResult(
            scene_type=scene_type,
            confidence=confidence,
            description=f"A factual view of the {scene_type.value.replace('_', ' ')}.",
            features=features or ["hardwood flooring", "window"],
            lighting=LightingType.NATURAL_DAYLIGHT,
            view_type=ViewType.WIDE,
            camera_view=CameraView.CORNER_VIEW,
            visible_connections=visible_connections or [],
            user_corrected=user_corrected,
        ),
    )


# ==========================================
# 1. Scene Graph Builder Tests
# ==========================================

def test_scene_graph_builder_nodes_and_edges():
    builder = SceneGraphBuilder()
    images = [
        make_dummy_analyzed_image("img_01", SceneType.EXTERIOR),
        make_dummy_analyzed_image("img_02", SceneType.LIVING_ROOM, visible_connections=["open archway to kitchen"]),
        make_dummy_analyzed_image("img_03", SceneType.KITCHEN),
    ]

    graph = builder.build_graph(images)
    assert len(graph.nodes) == 3
    assert graph.nodes[0].scene_type == SceneType.EXTERIOR
    assert graph.nodes[1].scene_type == SceneType.LIVING_ROOM
    assert graph.nodes[2].scene_type == SceneType.KITCHEN

    # Check for visual connection edge between living room and kitchen
    visual_edge = next(
        (e for e in graph.edges if e.type == "visual" and "kitchen" in e.evidence.lower()),
        None,
    )
    assert visual_edge is not None
    assert visual_edge.confidence >= 0.80


# ==========================================
# 2. No Hallucinated Rooms Test
# ==========================================

def test_ordering_engine_no_hallucinated_rooms():
    """
    CRITICAL REQUIREMENT: If the property only contains Kitchen, Living Room, Bedroom,
    the planner must NEVER introduce Exterior, Entrance, Dining Area, or Bathrooms.
    """
    builder = SceneGraphBuilder()
    ordering_engine = OrderingEngine()

    images = [
        make_dummy_analyzed_image("img_kitch", SceneType.KITCHEN),
        make_dummy_analyzed_image("img_living", SceneType.LIVING_ROOM),
        make_dummy_analyzed_image("img_bed", SceneType.BEDROOM),
    ]

    graph = builder.build_graph(images)
    ordered_tuples = ordering_engine.determine_order(graph)

    # Must contain EXACTLY 3 scenes
    assert len(ordered_tuples) == 3
    resulting_types = [t[0].scene_type for t in ordered_tuples]

    assert SceneType.EXTERIOR not in resulting_types
    assert SceneType.ENTRANCE not in resulting_types
    assert SceneType.DINING_AREA not in resulting_types
    assert SceneType.BATHROOM not in resulting_types

    # Proper sequence from provided subset (Living Room -> Kitchen -> Bedroom)
    assert resulting_types == [SceneType.LIVING_ROOM, SceneType.KITCHEN, SceneType.BEDROOM]


# ==========================================
# 3. Deterministic Ordering Hierarchy Test
# ==========================================

def test_ordering_engine_full_hierarchy():
    builder = SceneGraphBuilder()
    ordering_engine = OrderingEngine()

    images = [
        make_dummy_analyzed_image("img_bed", SceneType.BEDROOM),
        make_dummy_analyzed_image("img_ext", SceneType.EXTERIOR),
        make_dummy_analyzed_image("img_bath", SceneType.BATHROOM),
        make_dummy_analyzed_image("img_living", SceneType.LIVING_ROOM),
        make_dummy_analyzed_image("img_kitchen", SceneType.KITCHEN),
    ]

    graph = builder.build_graph(images)
    ordered_tuples = ordering_engine.determine_order(graph)

    resulting_types = [t[0].scene_type for t in ordered_tuples]
    assert resulting_types == [
        SceneType.EXTERIOR,
        SceneType.LIVING_ROOM,
        SceneType.KITCHEN,
        SceneType.BEDROOM,
        SceneType.BATHROOM,
    ]


# ==========================================
# 4. Camera Prompt Generation & Constraints
# ==========================================

def test_camera_planner_prompts_and_safety_constraints():
    camera_planner = CameraPromptGenerator()

    living_node = SceneNode(
        scene_id="scene_01",
        image_id="img_01",
        scene_type=SceneType.LIVING_ROOM,
        label="Living Room",
        confidence=0.95,
        description="Contemporary living room with sectional sofa and windows.",
        features=["sectional sofa", "coffee table", "large windows"],
    )

    instruction = camera_planner.plan_camera(living_node)

    assert instruction.motion_type in {CameraMotionType.SLOW_FORWARD, CameraMotionType.SLIGHT_DOLLY}
    assert "Preserve the exact existing architectural layout" in instruction.prompt
    assert "sectional sofa" in instruction.prompt
    assert "do not alter room geometry" in instruction.constraints
    assert "do not add furniture" in instruction.constraints
    assert instruction.duration_seconds >= 3.0


def test_camera_planner_bathroom_restrained_motion():
    camera_planner = CameraPromptGenerator()

    bath_node = SceneNode(
        scene_id="scene_bath",
        image_id="img_bath",
        scene_type=SceneType.BATHROOM,
        label="Master Bathroom",
        confidence=0.90,
        description="Bathroom with marble tiles and glass shower enclosure.",
        features=["marble vanity", "glass shower"],
    )

    instruction = camera_planner.plan_camera(bath_node)
    # Bathrooms must have static subtle motion to avoid claustrophobic zoom
    assert instruction.motion_type == CameraMotionType.STATIC_SUBTLE_MOTION


# ==========================================
# 5. Transition Planning Test
# ==========================================

def test_transition_planner_straight_cut_vs_crossfade():
    transition_planner = TransitionPlanner()

    node_a = SceneNode(
        scene_id="scene_01",
        image_id="img_01",
        scene_type=SceneType.EXTERIOR,
        label="Exterior Facade",
        confidence=0.95,
        description="Exterior facade.",
    )
    node_b = SceneNode(
        scene_id="scene_02",
        image_id="img_02",
        scene_type=SceneType.ENTRANCE,
        label="Foyer",
        confidence=0.95,
        description="Foyer entrance.",
    )
    node_c = SceneNode(
        scene_id="scene_03",
        image_id="img_03",
        scene_type=SceneType.BEDROOM,
        label="Bedroom",
        confidence=0.95,
        description="Bedroom.",
    )

    # Exterior to Entrance gets short crossfade for threshold crossing
    t1 = transition_planner.plan_transition(node_a, node_b, edges=[])
    assert t1.type == TransitionType.SHORT_CROSSFADE

    # Entrance to Bedroom with no direct visual connection defaults to straight cut
    t2 = transition_planner.plan_transition(node_b, node_c, edges=[])
    assert t2.type == TransitionType.STRAIGHT_CUT


# ==========================================
# 6. Plan Orchestration & Validation Tests
# ==========================================

def test_generate_and_update_plan_lifecycle():
    # 1. Create Project
    proj = project_service.create_project(ProjectCreate(name="Coastal Penthouse"))

    # 2. Add Images
    img_data1 = create_test_image_bytes(width=1024, height=768, color="blue")
    img_data2 = create_test_image_bytes(width=1024, height=768, color="green")
    img_data3 = create_test_image_bytes(width=1024, height=768, color="red")

    batch_res = project_service.add_images(
        proj.id,
        [
            ("living.jpg", img_data1),
            ("kitchen.jpg", img_data2),
            ("bedroom.jpg", img_data3),
        ],
    )
    assert batch_res.total_accepted == 3

    # Manually attach scene data for unit test isolation
    for img in batch_res.uploaded:
        stype = SceneType.LIVING_ROOM if "living" in img.original_filename else (
            SceneType.KITCHEN if "kitchen" in img.original_filename else SceneType.BEDROOM
        )
        scene_service.update_image_scene(proj.id, img.id, SceneCorrectionPayload(scene_type=stype))

    # 3. Generate Baseline Plan
    plan = walkthrough_planner.get_or_create_plan(proj.id)
    assert plan.plan_version == 1
    assert plan.source == PlanSource.AI
    assert len(plan.scenes) == 3
    assert [s.scene_type for s in plan.scenes] == [SceneType.LIVING_ROOM, SceneType.KITCHEN, SceneType.BEDROOM]

    # 4. User Reorder & Edit Plan
    # Swap position of Kitchen (first) and Living Room (second)
    scene_kitch_id = next(s.scene_id for s in plan.scenes if s.scene_type == SceneType.KITCHEN)
    scene_living_id = next(s.scene_id for s in plan.scenes if s.scene_type == SceneType.LIVING_ROOM)
    scene_bed_id = next(s.scene_id for s in plan.scenes if s.scene_type == SceneType.BEDROOM)

    update_payload = PlanUpdateRequest(
        scenes=[
            PlannedSceneUpdateItem(scene_id=scene_kitch_id, order=1, label="Chef Kitchen", motion_type=CameraMotionType.PAN_LEFT),
            PlannedSceneUpdateItem(scene_id=scene_living_id, order=2, label="Main Lounge"),
            PlannedSceneUpdateItem(scene_id=scene_bed_id, order=3),
        ],
        removed_scene_ids=[],
    )

    updated_plan = walkthrough_planner.update_user_plan(proj.id, update_payload)
    assert updated_plan.plan_version == 2
    assert updated_plan.source == PlanSource.USER
    assert updated_plan.scenes[0].scene_id == scene_kitch_id
    assert updated_plan.scenes[0].label == "Chef Kitchen"
    assert updated_plan.scenes[0].camera.motion_type == CameraMotionType.PAN_LEFT
    assert updated_plan.scenes[1].scene_id == scene_living_id


# ==========================================
# 7. Invalid Plan Update Rejection Tests
# ==========================================

def test_update_plan_rejects_duplicate_or_unknown_scenes():
    proj = project_service.create_project(ProjectCreate(name="Suburban House"))
    img_data = create_test_image_bytes(width=800, height=600)
    batch_res = project_service.add_images(proj.id, [("room.jpg", img_data)])

    plan = walkthrough_planner.get_or_create_plan(proj.id)
    valid_scene_id = plan.scenes[0].scene_id

    # Duplicate order numbers
    with pytest.raises(AppException) as exc_dup:
        walkthrough_planner.update_user_plan(
            proj.id,
            PlanUpdateRequest(
                scenes=[
                    PlannedSceneUpdateItem(scene_id=valid_scene_id, order=1),
                    PlannedSceneUpdateItem(scene_id=valid_scene_id, order=1),
                ]
            ),
        )
    assert exc_dup.value.status_code == 422

    # Unknown scene ID
    with pytest.raises(AppException) as exc_unk:
        walkthrough_planner.update_user_plan(
            proj.id,
            PlanUpdateRequest(
                scenes=[
                    PlannedSceneUpdateItem(scene_id="scene_nonexistent_999", order=1),
                ]
            ),
        )
    assert exc_unk.value.status_code == 404


# ==========================================
# 8. API Endpoints E2E Tests
# ==========================================

def test_api_plan_routes():
    # 1. Create Project via API
    create_res = client.post("/api/projects", json={"name": "Skyline Duplex"})
    assert create_res.status_code == 201
    proj_id = create_res.json()["data"]["id"]

    # 2. Upload image
    img_bytes = create_test_image_bytes(width=1000, height=800)
    client.post(
        f"/api/projects/{proj_id}/images",
        files={"files": ("foyer.jpg", img_bytes, "image/jpeg")},
    )

    # 3. GET /api/projects/{proj_id}/plan
    plan_res = client.get(f"/api/projects/{proj_id}/plan")
    assert plan_res.status_code == 200
    plan_data = plan_res.json()["data"]
    assert plan_data["plan_version"] == 1
    assert len(plan_data["scenes"]) == 1
    scene_id = plan_data["scenes"][0]["scene_id"]

    # 4. PUT /api/projects/{proj_id}/plan
    put_res = client.put(
        f"/api/projects/{proj_id}/plan",
        json={
            "scenes": [
                {
                    "scene_id": scene_id,
                    "order": 1,
                    "label": "Grand Entrance Foyer",
                    "motion_type": "slow_forward",
                }
            ],
            "removed_scene_ids": [],
        },
    )
    assert put_res.status_code == 200
    updated_plan_data = put_res.json()["data"]
    assert updated_plan_data["plan_version"] == 2
    assert updated_plan_data["source"] == "user"
    assert updated_plan_data["scenes"][0]["label"] == "Grand Entrance Foyer"

    # 5. POST /api/projects/{proj_id}/plan/rebuild
    rebuild_res = client.post(f"/api/projects/{proj_id}/plan/rebuild")
    assert rebuild_res.status_code == 200
    rebuilt_plan_data = rebuild_res.json()["data"]
    assert rebuilt_plan_data["plan_version"] == 3
    assert rebuilt_plan_data["source"] == "ai"
