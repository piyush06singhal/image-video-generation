from datetime import datetime, timezone
import uuid
from typing import Dict, List, Optional, Set
from app.core.errors import AppException, ProjectNotFoundError
from app.core.logging import logger
from app.schemas.image import ImageMetadata
from app.schemas.plan import (
    CameraInstruction,
    CameraMotionType,
    GenerationPlan,
    PlannedScene,
    PlanSource,
    PlanUpdateRequest,
    SceneGraph,
    SceneNode,
    TransitionInstruction,
    TransitionType,
)
from app.schemas.project import ProjectStatus
from app.services.storage_service import storage_service
from app.services.walkthrough_planner.camera_planner import CameraPromptGenerator
from app.services.walkthrough_planner.ordering_engine import OrderingEngine
from app.services.walkthrough_planner.scene_graph_builder import SceneGraphBuilder
from app.services.walkthrough_planner.transition_planner import TransitionPlanner


class WalkthroughPlannerService:
    """
    Central orchestration service for Phase 3 Walkthrough Planning.
    Creates, validates, updates, and persists the GenerationPlan contract.
    """

    def __init__(self):
        self.storage = storage_service
        self.graph_builder = SceneGraphBuilder()
        self.ordering_engine = OrderingEngine()
        self.camera_planner = CameraPromptGenerator()
        self.transition_planner = TransitionPlanner()

    def get_or_create_plan(self, project_id: str) -> GenerationPlan:
        """
        Retrieves the existing saved GenerationPlan for a project, or generates
        a new baseline AI plan if none currently exists.
        """
        existing_plan = self._load_persisted_plan(project_id)
        if existing_plan:
            return existing_plan

        return self.generate_baseline_plan(project_id)

    def generate_baseline_plan(
        self,
        project_id: str,
        force_rebuild: bool = False,
    ) -> GenerationPlan:
        """
        Constructs a complete GenerationPlan from current project scene understanding metadata.
        Respects existing user scene corrections while recalculating the optimal walkthrough route.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        raw_images = project_data.get("images", [])
        if not raw_images:
            raise AppException(
                code="NO_IMAGES_TO_PLAN",
                message="Cannot generate walkthrough plan: this project contains no uploaded images.",
                status_code=400,
            )

        images = [ImageMetadata(**img) for img in raw_images]

        # 1. Build Scene Graph
        scene_graph = self.graph_builder.build_graph(images)

        # 2. Determine Walkthrough Order
        ordered_tuples = self.ordering_engine.determine_order(scene_graph)

        # 3. Assemble Planned Scenes with Camera & Transition instructions
        planned_scenes: List[PlannedScene] = []
        node_sequence = [t[0] for t in ordered_tuples]

        for idx, (node, placement_reason) in enumerate(ordered_tuples):
            order_num = idx + 1
            camera_inst = self.camera_planner.plan_camera(node)

            transition_inst: Optional[TransitionInstruction] = None
            if idx < len(node_sequence) - 1:
                next_node = node_sequence[idx + 1]
                transition_inst = self.transition_planner.plan_transition(
                    current_node=node,
                    next_node=next_node,
                    edges=scene_graph.edges,
                )

            planned_scenes.append(
                PlannedScene(
                    order=order_num,
                    scene_id=node.scene_id,
                    image_id=node.image_id,
                    scene_type=node.scene_type,
                    label=node.label,
                    reason=placement_reason,
                    camera=camera_inst,
                    transition_to_next=transition_inst,
                    thumbnail_url=node.thumbnail_url,
                    original_filename=node.original_filename,
                    user_confirmed=node.user_confirmed,
                )
            )

        # 4. Calculate Total Duration
        total_duration = sum(s.camera.duration_seconds for s in planned_scenes)

        existing_plan = self._load_persisted_plan(project_id)
        current_version = (existing_plan.plan_version + 1) if (existing_plan and force_rebuild) else 1

        plan = GenerationPlan(
            plan_id=f"plan_{project_id[:16]}_v{current_version}",
            project_id=project_id,
            plan_version=current_version,
            source=PlanSource.AI,
            scenes=planned_scenes,
            removed_scene_ids=[],
            scene_graph=scene_graph,
            total_estimated_duration_seconds=total_duration,
        )

        # Persist and update project status
        self._persist_plan(project_id, plan)
        project_data["status"] = ProjectStatus.PLANNED.value
        project_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.save_project_json(project_id, project_data)

        logger.info(
            f"Generated baseline walkthrough plan for project {project_id} (version {current_version}, {len(planned_scenes)} scenes)"
        )
        return plan

    def update_user_plan(
        self,
        project_id: str,
        update_request: PlanUpdateRequest,
    ) -> GenerationPlan:
        """
        Applies manual user adjustments to scene ordering, labels, camera motions, and exclusions.
        Increments plan version and sets source to 'user'.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        raw_images = project_data.get("images", [])
        images = [ImageMetadata(**img) for img in raw_images]
        image_map: Dict[str, ImageMetadata] = {img.id: img for img in images}


        current_plan = self.get_or_create_plan(project_id)
        scene_graph = current_plan.scene_graph or self.graph_builder.build_graph(images)
        node_map: Dict[str, SceneNode] = {n.scene_id: n for n in scene_graph.nodes}

        # 1. Validation: ensure all scene IDs in update request exist in node_map
        requested_scene_ids = [item.scene_id for item in update_request.scenes]
        removed_ids = set(update_request.removed_scene_ids or [])

        # Check for duplicates in active scene list
        if len(requested_scene_ids) != len(set(requested_scene_ids)):
            raise AppException(
                code="DUPLICATE_SCENES_IN_PLAN",
                message="Cannot update plan: duplicate scene IDs detected in requested order.",
                status_code=422,
            )

        # Check that removed scenes are not in active list
        for sid in requested_scene_ids:
            if sid in removed_ids:
                raise AppException(
                    code="INVALID_PLAN_EXCLUSION",
                    message=f"Scene '{sid}' cannot be simultaneously active and excluded in the plan.",
                    status_code=422,
                )

        # Validate existence of every requested scene
        for sid in requested_scene_ids:
            if sid not in node_map:
                raise AppException(
                    code="UNKNOWN_SCENE_ID",
                    message=f"Scene ID '{sid}' does not correspond to any analyzed image in this project.",
                    status_code=404,
                )

        # Validate order sequence uniqueness
        order_numbers = [item.order for item in update_request.scenes]
        if len(order_numbers) != len(set(order_numbers)):
            raise AppException(
                code="DUPLICATE_ORDER_NUMBERS",
                message="Scene order numbers must be distinct sequential integers.",
                status_code=422,
            )

        # Sort update items by requested order
        sorted_update_items = sorted(update_request.scenes, key=lambda x: x.order)

        # 2. Rebuild Planned Scenes preserving or updating custom camera/transition specs
        updated_planned_scenes: List[PlannedScene] = []
        for idx, item in enumerate(sorted_update_items):
            node = node_map[item.scene_id]
            norm_order = idx + 1

            # Update display label if specified
            display_label = item.label.strip() if (item.label and item.label.strip()) else node.label

            # Custom motion type or prompt
            camera_inst = self.camera_planner.plan_camera(
                node=node,
                custom_motion=item.motion_type,
                custom_prompt=item.camera_prompt,
            )

            # Transition to next scene
            transition_inst: Optional[TransitionInstruction] = None
            if idx < len(sorted_update_items) - 1:
                next_item = sorted_update_items[idx + 1]
                next_node = node_map[next_item.scene_id]
                transition_inst = self.transition_planner.plan_transition(
                    current_node=node,
                    next_node=next_node,
                    edges=scene_graph.edges,
                    custom_type=item.transition_type,
                )

            is_confirmed = True if item.user_confirmed is None else item.user_confirmed

            updated_planned_scenes.append(
                PlannedScene(
                    order=norm_order,
                    scene_id=node.scene_id,
                    image_id=node.image_id,
                    scene_type=node.scene_type,
                    label=display_label,
                    reason=f"Positioned at shot #{norm_order} per user walkthrough configuration.",
                    camera=camera_inst,
                    transition_to_next=transition_inst,
                    thumbnail_url=node.thumbnail_url,
                    original_filename=node.original_filename,
                    user_confirmed=is_confirmed,
                )
            )

        total_duration = sum(s.camera.duration_seconds for s in updated_planned_scenes)
        new_version = current_plan.plan_version + 1

        new_plan = GenerationPlan(
            plan_id=f"plan_{project_id[:16]}_v{new_version}",
            project_id=project_id,
            plan_version=new_version,
            source=PlanSource.USER,
            created_at=current_plan.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            scenes=updated_planned_scenes,
            removed_scene_ids=list(removed_ids),
            scene_graph=scene_graph,
            total_estimated_duration_seconds=total_duration,
        )

        self._persist_plan(project_id, new_plan)
        logger.info(
            f"Updated walkthrough plan for project {project_id} (version {new_version}, source=user, {len(updated_planned_scenes)} active scenes)"
        )
        return new_plan

    def _persist_plan(self, project_id: str, plan: GenerationPlan) -> None:
        """Saves GenerationPlan to project storage path."""
        plan_dict = plan.model_dump()
        self.storage.save_plan_json(project_id, plan_dict)

    def _load_persisted_plan(self, project_id: str) -> Optional[GenerationPlan]:
        """Loads GenerationPlan from project storage path if available."""
        plan_dict = self.storage.load_plan_json(project_id)
        if not plan_dict:
            return None
        try:
            return GenerationPlan(**plan_dict)
        except Exception as e:
            logger.warning(f"Failed to deserialize existing plan for {project_id}: {e}")
            return None


walkthrough_planner = WalkthroughPlannerService()
