import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
import uuid

from app.core.config import settings
from app.core.errors import AppException, ProjectNotFoundError
from app.core.logging import logger
from app.schemas.generation import (
    GenerateRequest,
    GenerationJob,
    GenerationJobStatus,
    ProjectGenerationOverview,
    ProjectGenerationStatus,
    QualityAssessment,
    RegenerateSceneRequest,
    SceneGenerationStatus,
    SceneGenerationSummary,
    VideoClipMetadata,
)
from app.schemas.plan import CameraMotionType, GenerationPlan, PlannedScene
from app.schemas.project import ProjectStatus
from app.services.storage_service import storage_service
from app.services.video_generation.base import ImageToVideoProvider
from app.services.video_generation.gemini_veo_provider import GeminiVeoProvider
from app.services.video_generation.video_validator import VideoValidator
from app.services.walkthrough_planner.planner_service import walkthrough_planner


class VideoGenerationService:
    """
    Core orchestrator for Phase 4: Image-to-Video Generation.
    Consumes the Phase 3 GenerationPlan, manages background job execution with concurrency limits,
    persists job & clip metadata, and enables single-scene retries and overrides.
    """

    def __init__(self, provider: Optional[ImageToVideoProvider] = None):
        self.storage = storage_service
        self.provider = provider or GeminiVeoProvider()
        self.validator = VideoValidator()
        self._concurrency_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_GENERATIONS)
        self._active_tasks: Dict[str, asyncio.Task] = {}

    async def recover_pending_jobs(self) -> None:
        """Resume queued jobs after an API process restart."""
        for project_dir in self.storage.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            project_id = project_dir.name
            saved_gen = self.storage.load_generation_json(project_id) or {}
            jobs = [GenerationJob(**j) for j in saved_gen.get("jobs", [])]
            if not jobs:
                continue
            plan_data = self.storage.load_plan_json(project_id)
            if not plan_data:
                continue
            plan = GenerationPlan(**plan_data)
            scenes = {scene.scene_id: scene for scene in plan.scenes}
            changed = False
            for job in jobs:
                if job.status == GenerationJobStatus.PROCESSING:
                    job.status = GenerationJobStatus.QUEUED
                    job.started_at = None
                    changed = True
                if job.status not in (GenerationJobStatus.QUEUED, GenerationJobStatus.PAUSED):
                    continue
                scene = scenes.get(job.scene_id)
                if not scene or job.job_id in self._active_tasks:
                    continue
                if job.status == GenerationJobStatus.PAUSED:
                    continue
                self._active_tasks[job.job_id] = asyncio.create_task(
                    self._execute_generation_job(project_id, job.job_id, scene)
                )
            if changed:
                saved_gen["jobs"] = [job.model_dump() for job in jobs]
                self.storage.save_generation_json(project_id, saved_gen)

    def _build_cinematic_prompt(
        self,
        scene: PlannedScene,
        custom_prompt: Optional[str] = None,
    ) -> str:
        """
        Constructs the image-to-video generation prompt from Phase 3 metadata.
        Kept concise and direct to avoid safety filter rejections from Veo.
        """
        if custom_prompt and custom_prompt.strip():
            return custom_prompt.strip()

        cam = scene.camera
        # Keep prompt concise — long prompts with many constraints can trigger content filters
        return (
            f"Smooth cinematic walkthrough of this {scene.label}. "
            f"{cam.prompt}. "
            "Preserve all furniture, walls, and lighting from the source image. "
            "Realistic interior property video, stable camera, no distortion."
        )

    def _build_negative_constraints(self, scene: PlannedScene) -> Optional[str]:
        """
        Negative constraints are not passed to the API as the Developer API
        does not reliably support negative_prompt for Veo 3.1.
        Kept here for future provider compatibility.
        """
        return None

    def get_or_create_overview(self, project_id: str) -> ProjectGenerationOverview:
        """
        Retrieves current generation state overview for a project.
        Synthesizes status across all planned scenes from Phase 3 plan.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        plan = walkthrough_planner.get_or_create_plan(project_id)
        saved_gen = self.storage.load_generation_json(project_id) or {}
        saved_jobs = {j["job_id"]: GenerationJob(**j) for j in saved_gen.get("jobs", [])}
        saved_clips = {c["scene_id"]: VideoClipMetadata(**c) for c in saved_gen.get("clips", [])}

        scene_summaries: List[SceneGenerationSummary] = []
        completed_count = 0
        generating_count = 0
        failed_count = 0
        pending_count = 0
        total_duration = 0.0

        for scene in plan.scenes:
            clip = saved_clips.get(scene.scene_id)
            # Find most recent job for this scene
            scene_jobs = [j for j in saved_jobs.values() if j.scene_id == scene.scene_id]
            latest_job = max(scene_jobs, key=lambda x: x.created_at) if scene_jobs else None

            if clip and self.storage.get_clip_path(project_id, scene.scene_id).exists():
                status = SceneGenerationStatus.COMPLETED
                completed_count += 1
                total_duration += clip.duration_seconds
            elif latest_job and latest_job.status in (GenerationJobStatus.QUEUED, GenerationJobStatus.PROCESSING):
                status = SceneGenerationStatus.GENERATING
                generating_count += 1
            elif latest_job and latest_job.status == GenerationJobStatus.FAILED:
                status = SceneGenerationStatus.FAILED
                failed_count += 1
            elif latest_job and latest_job.status == GenerationJobStatus.PAUSED:
                status = SceneGenerationStatus.PAUSED
                failed_count += 1
            else:
                status = SceneGenerationStatus.PENDING
                pending_count += 1

            scene_summaries.append(
                SceneGenerationSummary(
                    scene_id=scene.scene_id,
                    order=scene.order,
                    label=scene.label,
                    scene_type=scene.scene_type.value if hasattr(scene.scene_type, "value") else str(scene.scene_type),
                    thumbnail_url=scene.thumbnail_url,
                    status=status,
                    job_id=latest_job.job_id if latest_job else None,
                    clip=clip,
                    last_error=(
                        latest_job.error
                        if latest_job and latest_job.status in (
                            GenerationJobStatus.FAILED,
                            GenerationJobStatus.PAUSED,
                        )
                        else None
                    ),
                    camera_motion=scene.camera.motion_type,
                )
            )

        # Determine overall project generation status
        total_scenes = len(plan.scenes)
        if total_scenes == 0:
            overall_status = ProjectGenerationStatus.READY
        elif generating_count > 0:
            overall_status = ProjectGenerationStatus.GENERATING
        elif completed_count == total_scenes:
            overall_status = ProjectGenerationStatus.COMPLETED
        elif any(scene.status == SceneGenerationStatus.PAUSED for scene in scene_summaries):
            overall_status = ProjectGenerationStatus.PAUSED
        elif completed_count > 0 or failed_count > 0:
            overall_status = ProjectGenerationStatus.PARTIALLY_COMPLETED
        else:
            overall_status = ProjectGenerationStatus.READY

        return ProjectGenerationOverview(
            project_id=project_id,
            status=overall_status,
            total_scenes=total_scenes,
            completed_scenes=completed_count,
            generating_scenes=generating_count,
            failed_scenes=failed_count,
            pending_scenes=pending_count,
            total_duration_seconds=round(total_duration, 2),
            scenes=scene_summaries,
            active_jobs=list(saved_jobs.values()),
        )

    async def generate_clips(
        self,
        project_id: str,
        request: Optional[GenerateRequest] = None,
    ) -> ProjectGenerationOverview:
        """
        Initiates generation for all pending/failed scenes in the plan, or specified scene_ids.
        Reuses completed clips unless force_regenerate is True.
        """
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            raise ProjectNotFoundError(project_id)

        plan = walkthrough_planner.get_or_create_plan(project_id)
        if not plan.scenes:
            raise AppException(
                code="EMPTY_PLAN",
                message="Cannot generate clips: Walkthrough plan has no scenes.",
                status_code=400,
            )

        target_scene_ids = set(request.scene_ids) if (request and request.scene_ids) else None
        force_regen = request.force_regenerate if request else False
        if (
            target_scene_ids is not None
            and len(target_scene_ids) > settings.MAX_SCENES_PER_GENERATION_REQUEST
        ):
            raise AppException(
                code="SCENE_REQUEST_LIMIT",
                message=(
                    f"You can generate at most {settings.MAX_SCENES_PER_GENERATION_REQUEST} "
                    "scenes in one request."
                ),
                status_code=413,
            )

        saved_gen = self.storage.load_generation_json(project_id) or {"jobs": [], "clips": []}
        saved_clips = {c["scene_id"]: VideoClipMetadata(**c) for c in saved_gen.get("clips", [])}
        jobs_list = [GenerationJob(**j) for j in saved_gen.get("jobs", [])]
        active_scene_ids = {
            job.scene_id
            for job in jobs_list
            if job.status in (
                GenerationJobStatus.QUEUED,
                GenerationJobStatus.PROCESSING,
                GenerationJobStatus.PAUSED,
            )
        }

        scenes_to_launch: List[PlannedScene] = []
        for scene in plan.scenes:
            if target_scene_ids is not None and scene.scene_id not in target_scene_ids:
                continue

            clip_exists = (
                scene.scene_id in saved_clips
                and self.storage.get_clip_path(project_id, scene.scene_id).exists()
            )
            if clip_exists and not force_regen:
                logger.info(f"Reusing existing completed clip for scene {scene.scene_id}")
                continue
            if scene.scene_id in active_scene_ids:
                logger.info(f"Skipping scene {scene.scene_id}: an existing job is already active or paused.")
                continue

            scenes_to_launch.append(scene)

        if not scenes_to_launch:
            logger.info(f"All requested scenes for project {project_id} are already completed.")
            return self.get_or_create_overview(project_id)

        # Create jobs and schedule background tasks
        for scene in scenes_to_launch:
            job_id = f"job_{uuid.uuid4().hex[:12]}"
            job = GenerationJob(
                job_id=job_id,
                project_id=project_id,
                scene_id=scene.scene_id,
                image_id=scene.image_id,
                status=GenerationJobStatus.QUEUED,
                provider=self.provider.get_provider_name(),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            jobs_list.append(job)

            # Spawn background execution
            task = asyncio.create_task(
                self._execute_generation_job(
                    project_id=project_id,
                    job_id=job_id,
                    scene=scene,
                )
            )
            self._active_tasks[job_id] = task

        # Persist jobs and update project status
        saved_gen["jobs"] = [j.model_dump() for j in jobs_list]
        self.storage.save_generation_json(project_id, saved_gen)

        project_data["status"] = ProjectStatus.GENERATING.value
        project_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.save_project_json(project_id, project_data)

        return self.get_or_create_overview(project_id)

    async def _execute_generation_job(
        self,
        project_id: str,
        job_id: str,
        scene: PlannedScene,
        custom_prompt: Optional[str] = None,
        custom_motion: Optional[CameraMotionType] = None,
    ) -> None:
        """
        Executes a single scene generation job with concurrency control, downloading, validation, and persistence.
        """
        async with self._concurrency_semaphore:
            logger.info(f"Starting execution of generation job {job_id} for scene {scene.scene_id} ({scene.label})...")
            self._update_job_status(project_id, job_id, status=GenerationJobStatus.PROCESSING, started_at=datetime.now(timezone.utc).isoformat())

            try:
                # 1. Resolve source image path
                image_path = self.storage.get_project_uploads_dir(project_id) / f"{scene.image_id}_{scene.original_filename}"
                if not image_path.exists():
                    # Fallback to finding by image_id prefix
                    matches = list(self.storage.get_project_uploads_dir(project_id).glob(f"{scene.image_id}*"))
                    if matches:
                        image_path = matches[0]
                    else:
                        raise AppException(
                            code="SOURCE_IMAGE_ERROR",
                            message=f"Source image for {scene.label} not found on disk.",
                            status_code=404,
                        )

                # 2. Build prompt & negative constraints
                motion_type = custom_motion or scene.camera.motion_type
                prompt = self._build_cinematic_prompt(scene, custom_prompt=custom_prompt)
                neg_prompt = self._build_negative_constraints(scene)
                target_duration = scene.camera.duration_seconds

                output_clip_path = self.storage.get_clip_path(project_id, scene.scene_id)
                output_clip_path.parent.mkdir(parents=True, exist_ok=True)

                # 3. Call Image-to-Video Provider
                provider_res = await self.provider.generate_clip(
                    source_image_path=image_path,
                    prompt=prompt,
                    negative_prompt=neg_prompt,
                    duration_seconds=target_duration,
                    camera_motion=motion_type.value if hasattr(motion_type, "value") else str(motion_type),
                    output_path=output_clip_path,
                )

                # 4. Validate output video file with OpenCV/container inspection
                is_valid, meta, quality, val_err = self.validator.validate_and_extract_metadata(output_clip_path)
                if not is_valid:
                    raise AppException(
                        code="VIDEO_VALIDATION_ERROR",
                        message=f"Generated video validation failed: {val_err}",
                        status_code=500,
                    )

                # 5. Assemble VideoClipMetadata
                clip_filename = output_clip_path.name
                clip_url = f"/api/projects/{project_id}/clips/{scene.scene_id}/file"

                clip_metadata = VideoClipMetadata(
                    scene_id=scene.scene_id,
                    image_id=scene.image_id,
                    clip_filename=clip_filename,
                    clip_path=str(output_clip_path.relative_to(self.storage.storage_dir)),
                    clip_url=clip_url,
                    duration_seconds=meta["duration_seconds"],
                    width=meta["width"],
                    height=meta["height"],
                    fps=meta["fps"],
                    format=meta["format"],
                    file_size_bytes=meta["file_size_bytes"],
                    provider=provider_res.provider_name,
                    model=provider_res.model_name,
                    camera_motion=motion_type,
                    prompt=prompt,
                    generated_at=datetime.now(timezone.utc).isoformat(),
                    quality=quality,
                )

                # 6. Save clip metadata and update job as completed
                self._save_completed_clip(project_id, clip_metadata)
                self._update_job_status(
                    project_id,
                    job_id,
                    status=GenerationJobStatus.COMPLETED,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    provider_job_id=provider_res.provider_job_id,
                    result_clip=clip_metadata,
                )
                logger.info(f"Generation job {job_id} successfully finished for scene {scene.scene_id}!")

            except AppException as ae:
                logger.error(f"Generation job {job_id} failed with AppException: {ae.code} - {ae.message}")
                job_status = (
                    GenerationJobStatus.PAUSED
                    if ae.code in {"PROVIDER_RATE_LIMIT", "AI_RATE_LIMIT"}
                    and any(term in ae.message.lower() for term in ("quota", "rate limit", "resource exhausted"))
                    else GenerationJobStatus.FAILED
                )
                self._update_job_status(
                    project_id,
                    job_id,
                    status=job_status,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    error=ae.message,
                    error_code=ae.code,
                )
            except Exception as ex:
                logger.error(f"Generation job {job_id} failed with unexpected exception: {ex}")
                self._update_job_status(
                    project_id,
                    job_id,
                    status=GenerationJobStatus.FAILED,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    error=str(ex),
                    error_code="UNKNOWN_GENERATION_ERROR",
                )
            finally:
                self._update_project_status_after_job(project_id)

    def _update_job_status(
        self,
        project_id: str,
        job_id: str,
        status: GenerationJobStatus,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        provider_job_id: Optional[str] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        result_clip: Optional[VideoClipMetadata] = None,
    ) -> None:
        saved_gen = self.storage.load_generation_json(project_id) or {"jobs": [], "clips": []}
        jobs = saved_gen.get("jobs", [])
        for j in jobs:
            if j.get("job_id") == job_id:
                j["status"] = status.value
                if started_at:
                    j["started_at"] = started_at
                if completed_at:
                    j["completed_at"] = completed_at
                if provider_job_id:
                    j["provider_job_id"] = provider_job_id
                if error is not None:
                    j["error"] = error
                if error_code is not None:
                    j["error_code"] = error_code
                if result_clip:
                    j["result_clip"] = result_clip.model_dump()
                break
        saved_gen["jobs"] = jobs
        self.storage.save_generation_json(project_id, saved_gen)

    def _save_completed_clip(self, project_id: str, clip: VideoClipMetadata) -> None:
        saved_gen = self.storage.load_generation_json(project_id) or {"jobs": [], "clips": []}
        clips = saved_gen.get("clips", [])
        # Replace existing clip for scene if present
        clips = [c for c in clips if c.get("scene_id") != clip.scene_id]
        clips.append(clip.model_dump())
        saved_gen["clips"] = clips
        self.storage.save_generation_json(project_id, saved_gen)

    def _update_project_status_after_job(self, project_id: str) -> None:
        overview = self.get_or_create_overview(project_id)
        project_data = self.storage.load_project_json(project_id)
        if not project_data:
            return

        if overview.status == ProjectGenerationStatus.COMPLETED:
            project_data["status"] = ProjectStatus.COMPLETED.value
        elif overview.status in (ProjectGenerationStatus.PARTIALLY_COMPLETED, ProjectGenerationStatus.GENERATING):
            project_data["status"] = ProjectStatus.GENERATING.value
        elif overview.status == ProjectGenerationStatus.FAILED:
            project_data["status"] = ProjectStatus.FAILED.value

        project_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.save_project_json(project_id, project_data)

    async def retry_job(self, project_id: str, job_id: str) -> GenerationJob:
        """
        Retries a specific failed job without touching other scenes.
        """
        saved_gen = self.storage.load_generation_json(project_id) or {"jobs": [], "clips": []}
        jobs = [GenerationJob(**j) for j in saved_gen.get("jobs", [])]
        target_job = next((j for j in jobs if j.job_id == job_id), None)
        if not target_job:
            raise AppException(code="JOB_NOT_FOUND", message=f"Job '{job_id}' not found.", status_code=404)

        if target_job.retry_count >= settings.MAX_GENERATION_RETRIES:
            raise AppException(
                code="MAX_RETRIES_EXCEEDED",
                message=f"Job '{job_id}' has reached the maximum allowed retry limit ({settings.MAX_GENERATION_RETRIES}).",
                status_code=400,
            )
        if target_job.status in (GenerationJobStatus.QUEUED, GenerationJobStatus.PROCESSING):
            return target_job

        plan = walkthrough_planner.get_or_create_plan(project_id)
        target_scene = next((s for s in plan.scenes if s.scene_id == target_job.scene_id), None)
        if not target_scene:
            raise AppException(
                code="SCENE_NOT_FOUND",
                message=f"Scene '{target_job.scene_id}' is no longer in current plan.",
                status_code=404,
            )

        # Reset job state
        target_job.status = GenerationJobStatus.QUEUED
        target_job.retry_count += 1
        target_job.error = None
        target_job.error_code = None
        target_job.started_at = None
        target_job.completed_at = None

        saved_gen["jobs"] = [j.model_dump() for j in jobs]
        self.storage.save_generation_json(project_id, saved_gen)

        # Launch background execution
        task = asyncio.create_task(
            self._execute_generation_job(
                project_id=project_id,
                job_id=job_id,
                scene=target_scene,
            )
        )
        self._active_tasks[job_id] = task

        return target_job

    async def regenerate_scene(
        self,
        project_id: str,
        scene_id: str,
        request: Optional[RegenerateSceneRequest] = None,
    ) -> GenerationJob:
        """
        Regenerates a specific scene with optional custom camera motion or prompt override.
        """
        plan = walkthrough_planner.get_or_create_plan(project_id)
        target_scene = next((s for s in plan.scenes if s.scene_id == scene_id), None)
        if not target_scene:
            raise AppException(code="SCENE_NOT_FOUND", message=f"Scene '{scene_id}' not found in plan.", status_code=404)

        # Remove old clip from disk and metadata
        self.storage.delete_clip_file(project_id, scene_id)
        saved_gen = self.storage.load_generation_json(project_id) or {"jobs": [], "clips": []}
        saved_gen["clips"] = [c for c in saved_gen.get("clips", []) if c.get("scene_id") != scene_id]

        new_job_id = f"job_{uuid.uuid4().hex[:12]}"
        new_job = GenerationJob(
            job_id=new_job_id,
            project_id=project_id,
            scene_id=scene_id,
            image_id=target_scene.image_id,
            status=GenerationJobStatus.QUEUED,
            provider=self.provider.get_provider_name(),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        jobs_list = [GenerationJob(**j) for j in saved_gen.get("jobs", [])]
        jobs_list.append(new_job)
        saved_gen["jobs"] = [j.model_dump() for j in jobs_list]
        self.storage.save_generation_json(project_id, saved_gen)

        custom_prompt = request.custom_prompt if request else None
        custom_motion = request.custom_motion_type if request else None

        task = asyncio.create_task(
            self._execute_generation_job(
                project_id=project_id,
                job_id=new_job_id,
                scene=target_scene,
                custom_prompt=custom_prompt,
                custom_motion=custom_motion,
            )
        )
        self._active_tasks[new_job_id] = task

        return new_job

    def get_job_status(self, project_id: str, job_id: str) -> GenerationJob:
        saved_gen = self.storage.load_generation_json(project_id) or {"jobs": [], "clips": []}
        for j in saved_gen.get("jobs", []):
            if j.get("job_id") == job_id:
                return GenerationJob(**j)
        raise AppException(code="JOB_NOT_FOUND", message=f"Generation job '{job_id}' not found.", status_code=404)

    def get_clip_file_path(self, project_id: str, scene_id: str) -> Path:
        clip_path = self.storage.get_clip_path(project_id, scene_id)
        if not clip_path.exists():
            raise AppException(
                code="CLIP_NOT_FOUND",
                message=f"Generated video clip for scene '{scene_id}' does not exist on disk.",
                status_code=404,
            )
        return clip_path


video_generation_service = VideoGenerationService()
