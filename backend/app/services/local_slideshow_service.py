from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import os
import tempfile

import cv2

from app.core.errors import AppException, ProjectNotFoundError
from app.schemas.assembly import AssembledSceneInfo, FinalVideoMetadata
from app.services.storage_service import storage_service
from app.services.video_assembler.ffmpeg_engine import ffmpeg_engine
from app.services.video_assembler.service import VideoAssemblerService
from app.services.walkthrough_planner.planner_service import walkthrough_planner


class LocalSlideshowService:
    """Creates a deterministic walkthrough when remote video generation is unavailable."""

    def create(self, project_id: str, seconds_per_scene: float = 3.0) -> FinalVideoMetadata:
        project = storage_service.load_project_json(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        plan = walkthrough_planner.get_or_create_plan(project_id)
        if not plan.scenes:
            raise AppException("EMPTY_PLAN", "Cannot create a slideshow without planned scenes.", 400)

        image_by_id = {image["id"]: image for image in project.get("images", [])}
        final_dir = storage_service.get_project_final_dir(project_id)
        final_dir.mkdir(parents=True, exist_ok=True)
        raw_fd, raw_name = tempfile.mkstemp(suffix=".mp4", dir=final_dir)
        os.close(raw_fd)
        raw_path = Path(raw_name)
        output_path = storage_service.get_final_video_path(project_id)
        writer = cv2.VideoWriter(
            str(raw_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            24.0,
            (1280, 720),
        )
        scenes = []
        try:
            for scene in sorted(plan.scenes, key=lambda item: item.order):
                image = image_by_id.get(scene.image_id)
                source = storage_service.get_project_uploads_dir(project_id) / image["filename"] if image else None
                frame = cv2.imread(str(source)) if source else None
                if frame is None:
                    raise AppException(
                        "SOURCE_IMAGE_ERROR",
                        f"Source image for {scene.label} is unavailable.",
                        404,
                    )
                source_h, source_w = frame.shape[:2]
                scale = min(1280 / source_w, 720 / source_h)
                scaled = cv2.resize(
                    frame,
                    (max(1, int(source_w * scale)), max(1, int(source_h * scale))),
                    interpolation=cv2.INTER_AREA,
                )
                frame = cv2.copyMakeBorder(
                    scaled,
                    (720 - scaled.shape[0]) // 2,
                    720 - scaled.shape[0] - (720 - scaled.shape[0]) // 2,
                    (1280 - scaled.shape[1]) // 2,
                    1280 - scaled.shape[1] - (1280 - scaled.shape[1]) // 2,
                    cv2.BORDER_CONSTANT,
                    value=(13, 10, 8),
                )
                for _ in range(max(1, int(seconds_per_scene * 24))):
                    writer.write(frame)
                scenes.append(
                    AssembledSceneInfo(
                        scene_id=scene.scene_id,
                        image_id=scene.image_id,
                        order=scene.order,
                        label=scene.label,
                        scene_type=scene.scene_type.value if hasattr(scene.scene_type, "value") else str(scene.scene_type),
                        duration_seconds=seconds_per_scene,
                        clip_filename=source.name if source else "",
                    )
                )
        finally:
            writer.release()

        ffmpeg_engine.normalize_clip(raw_path, output_path, 1280, 720, 24.0)
        raw_path.unlink(missing_ok=True)
        plan_hash = VideoAssemblerService().compute_plan_fingerprint(plan)
        metadata = FinalVideoMetadata(
            project_id=project_id,
            video_url=f"/api/projects/{project_id}/final-video/file",
            download_url=f"/api/projects/{project_id}/final-video/download",
            duration_seconds=round(len(scenes) * seconds_per_scene, 2),
            width=1280,
            height=720,
            fps=24.0,
            file_size_bytes=output_path.stat().st_size,
            scene_count=len(scenes),
            scenes_in_order=scenes,
            plan_version=plan.plan_version,
            plan_hash=plan_hash,
        )
        storage_service.save_final_metadata_json(project_id, metadata.model_dump())
        return metadata


local_slideshow_service = LocalSlideshowService()
