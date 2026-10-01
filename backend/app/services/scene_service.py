from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.config import settings
from app.core.errors import (
    AppException,
    ImageNotFoundError,
    ProjectNotFoundError,
)
from app.core.logging import logger
from app.schemas.image import AnalysisStatus, ImageMetadata
from app.schemas.project import ProjectResponse, ProjectStatus
from app.schemas.scene import (
    CameraView,
    LightingType,
    SceneAnalysisResult,
    SceneCorrectionPayload,
    SceneType,
    ViewType,
)
from app.services.image_preprocessor import image_preprocessor
from app.services.scene_analyzer import get_scene_analyzer
from app.services.storage_service import storage_service


class SceneService:
    """
    Orchestrates real visual scene understanding, quality evaluation, manual corrections,
    and structured metadata persistence.
    """

    def __init__(self):
        self.storage = storage_service
        self.preprocessor = image_preprocessor

    async def analyze_project(
        self,
        project_id: str,
        force_reanalyze: bool = False,
        image_ids: Optional[List[str]] = None,
    ) -> ProjectResponse:
        """
        Executes real multimodal scene understanding across project photographs.
        Avoids redundant re-analysis when results already exist.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        images = project_data.get("images", [])
        if not images:
            raise AppException(
                code="NO_IMAGES_TO_ANALYZE",
                message="Cannot run scene analysis: this project contains no uploaded images.",
                status_code=400,
            )

        analyzer = get_scene_analyzer()
        processed_dir = self.storage.get_project_processed_dir(project_id)
        uploads_dir = self.storage.get_project_uploads_dir(project_id)

        # Set project status to analyzing during processing
        project_data["status"] = ProjectStatus.ANALYZING.value
        project_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.save_project_json(project_id, project_data)

        target_set = set(image_ids) if image_ids else None
        completed_count = 0
        failed_count = 0

        for img in images:
            img_id = img["id"]
            if target_set and img_id not in target_set:
                continue

            current_status = img.get("analysis_status", AnalysisStatus.PENDING.value)
            is_already_completed = current_status == AnalysisStatus.COMPLETED.value
            scene_dict = img.get("scene") or {}
            is_user_corrected = scene_dict.get("user_corrected", False)

            # Skip if already completed and not forced, preserving user manual corrections
            if is_already_completed and not force_reanalyze:
                logger.info(f"Image {img_id} already analyzed. Skipping redundant AI call.")
                completed_count += 1
                continue

            # Original image path
            orig_path = uploads_dir / img["filename"]
            if not orig_path.exists():
                logger.warning(f"Original image file missing for {img_id}: {orig_path}")
                img["analysis_status"] = AnalysisStatus.FAILED.value
                img["analysis_error"] = "Original image file missing from storage."
                failed_count += 1
                continue

            try:
                # 1. Read bytes
                with open(orig_path, "rb") as f:
                    file_bytes = f.read()

                # 2. Preprocess to analysis-ready normalized file & calculate quality
                analysis_path = processed_dir / f"analysis_{img_id}.jpg"
                _, quality_result = self.preprocessor.prepare_analysis_image(
                    file_bytes=file_bytes,
                    output_path=analysis_path,
                )
                img["quality"] = quality_result.model_dump()
                img["analysis_image_url"] = (
                    f"{settings.API_PREFIX}/projects/{project_id}/images/{img_id}/analysis-file"
                )

                # 3. Invoke real Multimodal Vision Model
                img["analysis_status"] = AnalysisStatus.PROCESSING.value
                scene_result = await analyzer.analyze_image(
                    image_path=analysis_path,
                    quality_info=quality_result,
                )

                # 4. If user had previously corrected the scene and we are not forcing total reset, keep correction
                if is_user_corrected and not force_reanalyze:
                    scene_result.scene_type = SceneType.from_str(
                        img["scene"].get("scene_type", scene_result.scene_type.value)
                    )
                    scene_result.user_corrected = True

                img["scene"] = scene_result.model_dump()
                img["analysis_status"] = AnalysisStatus.COMPLETED.value
                img["analysis_error"] = None
                completed_count += 1
                logger.info(
                    f"Successfully analyzed {img['original_filename']}: {scene_result.scene_type.value} (conf={scene_result.confidence:.2f})"
                )

            except AppException as app_err:
                logger.warning(f"Analysis failed for {img_id}: {app_err.message} ({app_err.code})")
                img["analysis_status"] = AnalysisStatus.FAILED.value
                img["analysis_error"] = app_err.message
                failed_count += 1
            except Exception as e:
                logger.error(f"Unexpected error analyzing {img_id}: {e}")
                img["analysis_status"] = AnalysisStatus.FAILED.value
                img["analysis_error"] = "An unexpected error occurred during visual analysis."
                failed_count += 1

        # Determine overall project status
        total_images = len(images)
        if completed_count == total_images:
            project_data["status"] = ProjectStatus.ANALYZED.value
        elif completed_count > 0:
            project_data["status"] = ProjectStatus.PARTIALLY_ANALYZED.value
        else:
            project_data["status"] = ProjectStatus.FAILED.value

        project_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.save_project_json(project_id, project_data)

        logger.info(
            f"Project {project_id} analysis finished: {completed_count} completed, {failed_count} failed"
        )
        return ProjectResponse(**project_data)

    def update_image_scene(
        self,
        project_id: str,
        image_id: str,
        correction: SceneCorrectionPayload,
    ) -> ImageMetadata:
        """
        Applies a user manual scene correction, marking it as user_confirmed.
        Does NOT trigger external AI APIs.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        target_img = None
        for img in project_data.get("images", []):
            if img["id"] == image_id:
                target_img = img
                break

        if not target_img:
            raise ImageNotFoundError(image_id, project_id)

        existing_scene = target_img.get("scene") or {}
        now_str = datetime.now(timezone.utc).isoformat()

        # Build updated scene result
        updated_scene = SceneAnalysisResult(
            scene_type=correction.scene_type,
            confidence=1.0,  # User confirmed classification
            description=correction.description
            or existing_scene.get(
                "description",
                f"User-confirmed {correction.scene_type.value.replace('_', ' ')} view.",
            ),
            features=correction.features
            if correction.features is not None
            else existing_scene.get("features", []),
            lighting=LightingType.from_str(existing_scene.get("lighting", "unknown")),
            view_type=ViewType.from_str(existing_scene.get("view_type", "unknown")),
            camera_view=CameraView.from_str(existing_scene.get("camera_view", "unknown")),
            visible_connections=existing_scene.get("visible_connections", []),
            user_corrected=True,
            analyzed_at=now_str,
        )

        target_img["scene"] = updated_scene.model_dump()
        target_img["analysis_status"] = AnalysisStatus.COMPLETED.value
        target_img["analysis_error"] = None

        project_data["updated_at"] = now_str
        self.storage.save_project_json(project_id, project_data)
        logger.info(
            f"User manually corrected image {image_id} scene type to '{correction.scene_type.value}'"
        )

        return ImageMetadata(**target_img)

    def get_analysis_image_path(self, project_id: str, image_id: str) -> Path:
        """
        Locates the normalized analysis-ready image in storage/projects/{project_id}/processed/.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        for img in project_data.get("images", []):
            if img["id"] == image_id:
                path = (
                    self.storage.get_project_processed_dir(project_id)
                    / f"analysis_{image_id}.jpg"
                )
                if path.exists():
                    return path
                # Fallback to original if analysis image was not generated yet
                orig_path = (
                    self.storage.get_project_uploads_dir(project_id) / img["filename"]
                )
                if orig_path.exists():
                    return orig_path
                raise ImageNotFoundError(image_id, project_id)

        raise ImageNotFoundError(image_id, project_id)


scene_service = SceneService()
