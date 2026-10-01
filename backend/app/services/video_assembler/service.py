import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.errors import AppException, ProjectNotFoundError
from app.core.logging import logger
from app.schemas.assembly import (
    AssembledSceneInfo,
    AssemblyConfig,
    AssemblyJob,
    AssemblyJobStatus,
    AssemblyProgressStage,
    AssemblyRequest,
    FinalVideoMetadata,
)
from app.schemas.plan import GenerationPlan, PlannedScene
from app.services.storage_service import storage_service
from app.services.video_assembler.ffmpeg_engine import ffmpeg_engine


class AssemblyValidationError(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="ASSEMBLY_VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class VideoAssemblerService:
    """
    Orchestrates Phase 5: Video Assembly, Transitions, and Final Walkthrough Video generation.
    Preserves strict scene ordering from user-approved GenerationPlan.
    """

    def __init__(self, storage=None):
        self._jobs: Dict[str, AssemblyJob] = {}
        self.storage = storage or storage_service

    def compute_plan_fingerprint(self, plan: GenerationPlan) -> str:
        """
        Creates a cryptographic fingerprint of the plan to detect subsequent plan edits.
        """
        tokens = []
        for s in plan.scenes:
            trans_str = s.transition_to_next.type.value if s.transition_to_next else "none"
            tokens.append(f"{s.scene_id}:{s.order}:{s.camera.motion_type.value}:{trans_str}")
        raw = "|".join(tokens)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def validate_required_clips(
        self, project_id: str, plan: GenerationPlan
    ) -> List[Tuple[PlannedScene, Path, Dict[str, Any]]]:
        """
        Verifies that every approved scene in the plan has a readable, uncorrupted video clip.
        Fails with clear descriptive messages if any clip is missing or invalid.
        """
        if not plan.scenes:
            raise AssemblyValidationError("Cannot assemble walkthrough: generation plan contains no scenes.")

        ordered_scenes = sorted(plan.scenes, key=lambda s: s.order)
        validated_items: List[Tuple[PlannedScene, Path, Dict[str, Any]]] = []

        for scene in ordered_scenes:
            clip_path = self.storage.get_clip_path(project_id, scene.scene_id)
            if not clip_path.exists():
                raise AssemblyValidationError(
                    f"Walkthrough cannot be assembled because the {scene.label} clip is unavailable.",
                    details={"scene_id": scene.scene_id, "label": scene.label, "expected_path": str(clip_path)},
                )

            try:
                meta = ffmpeg_engine.probe_video(clip_path)
                if meta["duration_seconds"] <= 0:
                    raise ValueError("Zero duration video clip")
                validated_items.append((scene, clip_path, meta))
            except Exception as e:
                logger.error(f"Validation failed for scene {scene.label} ({clip_path}): {e}")
                raise AssemblyValidationError(
                    f"Walkthrough cannot be assembled because the {scene.label} clip is corrupted or unreadable.",
                    details={"scene_id": scene.scene_id, "label": scene.label, "error": str(e)},
                )

        return validated_items

    def get_final_metadata(self, project_id: str) -> Optional[FinalVideoMetadata]:
        """
        Retrieves final video metadata and checks if it is outdated relative to current plan.
        """
        raw_meta = self.storage.load_final_metadata_json(project_id)
        if not raw_meta:
            return None

        meta = FinalVideoMetadata(**raw_meta)
        video_file = self.storage.get_final_video_path(project_id)
        if not video_file.exists():
            return None

        # Check if plan has changed since assembly
        plan_dict = self.storage.load_plan_json(project_id)
        if plan_dict:
            try:
                plan = GenerationPlan(**plan_dict)
                current_hash = self.compute_plan_fingerprint(plan)
                if current_hash != meta.plan_hash or plan.plan_version != meta.plan_version:
                    meta.is_outdated = True
            except Exception:
                pass

        return meta

    def get_assembly_job(self, project_id: str, job_id: Optional[str] = None) -> Optional[AssemblyJob]:
        """
        Returns active in-memory job or persisted assembly record.
        """
        if job_id and job_id in self._jobs:
            return self._jobs[job_id]

        for j in self._jobs.values():
            if j.project_id == project_id:
                return j

        # Check persisted assembly.json
        raw = self.storage.load_assembly_json(project_id)
        if raw:
            return AssemblyJob(**raw)
        return None

    def assemble_walkthrough(
        self, project_id: str, request: Optional[AssemblyRequest] = None
    ) -> AssemblyJob:
        """
        Executes complete assembly pipeline:
        1. Validates plan and all clips
        2. Normalizes clips to consistent resolution/framerate
        3. Builds optional title intro and transitions
        4. Concatenates into final/walkthrough.mp4
        5. Validates final output with ffprobe and stores metadata.json
        """
        req = request or AssemblyRequest()
        cfg = req.config or AssemblyConfig()

        # Load project and plan
        proj_data = self.storage.load_project_json(project_id)
        if not proj_data:
            raise ProjectNotFoundError(project_id)

        plan_data = self.storage.load_plan_json(project_id)
        if not plan_data:
            raise AssemblyValidationError(f"Project {project_id} does not have an approved generation plan.")

        plan = GenerationPlan(**plan_data)
        plan_hash = self.compute_plan_fingerprint(plan)

        # Check if already assembled and valid
        if not req.force_reassemble:
            existing_meta = self.get_final_metadata(project_id)
            if existing_meta and not existing_meta.is_outdated:
                logger.info(f"Reusing existing up-to-date walkthrough for {project_id}")
                job = AssemblyJob(
                    job_id=str(uuid.uuid4()),
                    project_id=project_id,
                    status=AssemblyJobStatus.COMPLETED,
                    stage=AssemblyProgressStage.COMPLETED,
                    stage_message="Walkthrough already assembled and up to date.",
                    progress_percentage=100,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    result=existing_meta,
                )
                return job

        job_id = f"job_assembly_{uuid.uuid4().hex[:10]}"
        job = AssemblyJob(
            job_id=job_id,
            project_id=project_id,
            status=AssemblyJobStatus.PROCESSING,
            stage=AssemblyProgressStage.VALIDATING,
            stage_message="Validating required scene clips...",
            progress_percentage=10,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._jobs[job_id] = job

        temp_dir = self.storage.get_project_final_dir(project_id) / f"temp_{job_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # ── Step 1: Clip Validation (0-20%) ──
            validated_clips = self.validate_required_clips(project_id, plan)
            job.stage = AssemblyProgressStage.NORMALIZING
            job.stage_message = f"Normalizing {len(validated_clips)} scene clips..."
            job.progress_percentage = 25

            # Determine target resolution from first clip or config
            first_meta = validated_clips[0][2]
            target_w = first_meta["width"] or 1280
            target_h = first_meta["height"] or 720
            target_fps = cfg.output_fps or 24.0

            # ── Step 2: Normalization (20-40%) ──
            normalized_clips: List[Path] = []
            transitions: List[str] = []
            assembled_scene_info: List[AssembledSceneInfo] = []

            # Optional title intro
            if cfg.intro_title_enabled:
                title_text = proj_data.get("name", "Luxury Property Walkthrough")
                intro_path = temp_dir / "intro.mp4"
                ffmpeg_engine.create_title_intro_clip(
                    title=title_text,
                    output_path=intro_path,
                    duration=cfg.intro_duration_seconds,
                    width=target_w,
                    height=target_h,
                    fps=target_fps,
                )
                normalized_clips.append(intro_path)
                transitions.append("straight_cut")

            for idx, (scene, clip_path, meta) in enumerate(validated_clips):
                norm_out = temp_dir / f"norm_scene_{idx + 1:02d}_{scene.scene_id}.mp4"
                ffmpeg_engine.normalize_clip(
                    input_path=clip_path,
                    output_path=norm_out,
                    target_width=target_w,
                    target_height=target_h,
                    target_fps=target_fps,
                )
                normalized_clips.append(norm_out)

                # Collect transition instruction
                trans_type = "straight_cut"
                if scene.transition_to_next:
                    trans_type = scene.transition_to_next.type.value
                transitions.append(trans_type)

                assembled_scene_info.append(
                    AssembledSceneInfo(
                        scene_id=scene.scene_id,
                        image_id=scene.image_id,
                        order=scene.order,
                        label=scene.label,
                        scene_type=scene.scene_type.value,
                        duration_seconds=meta["duration_seconds"],
                        clip_filename=clip_path.name,
                        transition_to_next=trans_type,
                    )
                )

            # ── Step 3: Assembly (40-80%) ──
            job.stage = AssemblyProgressStage.ASSEMBLING
            job.stage_message = "Assembling walkthrough sequence and transitions..."
            job.progress_percentage = 60

            assembled_raw = temp_dir / "assembled_raw.mp4"
            ffmpeg_engine.concatenate_clips(
                clip_paths=normalized_clips,
                output_path=assembled_raw,
                transitions=transitions[:-1] if transitions else None,
                crossfade_duration=cfg.crossfade_duration_seconds,
            )

            # ── Step 4: Audio Processing if enabled (80-90%) ──
            final_target_mp4 = self.storage.get_final_video_path(project_id)
            final_target_mp4.parent.mkdir(parents=True, exist_ok=True)

            if cfg.audio_enabled:
                job.stage = AssemblyProgressStage.AUDIO_PROCESSING
                job.stage_message = "Mixing background audio..."
                job.progress_percentage = 85

                # Audio mix
                # If custom audio not provided, move forward with raw
                shutil.copy2(assembled_raw, final_target_mp4)
            else:
                shutil.copy2(assembled_raw, final_target_mp4)

            # ── Step 5: Final Validation & Metadata Extraction (90-100%) ──
            job.stage = AssemblyProgressStage.FINAL_VALIDATION
            job.stage_message = "Validating final walkthrough MP4..."
            job.progress_percentage = 95

            final_probe = ffmpeg_engine.probe_video(final_target_mp4)
            if final_probe["duration_seconds"] <= 0 or final_probe["file_size_bytes"] <= 0:
                raise AssemblyValidationError("Final walkthrough video validation failed: empty output.")

            final_metadata = FinalVideoMetadata(
                project_id=project_id,
                filename="walkthrough.mp4",
                video_url=f"/api/projects/{project_id}/final-video/file",
                download_url=f"/api/projects/{project_id}/final-video/download",
                duration_seconds=final_probe["duration_seconds"],
                width=final_probe["width"],
                height=final_probe["height"],
                fps=final_probe["fps"],
                format="mp4",
                video_codec=final_probe["video_codec"],
                audio_codec=None,
                audio_enabled=cfg.audio_enabled,
                file_size_bytes=final_probe["file_size_bytes"],
                scene_count=len(assembled_scene_info),
                scenes_in_order=assembled_scene_info,
                plan_version=plan.plan_version,
                plan_hash=plan_hash,
                is_outdated=False,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            self.storage.save_final_metadata_json(project_id, final_metadata.model_dump())

            # Mark project status as completed
            proj_data["status"] = "completed"
            self.storage.save_project_json(project_id, proj_data)

            job.status = AssemblyJobStatus.COMPLETED
            job.stage = AssemblyProgressStage.COMPLETED
            job.stage_message = "Walkthrough video successfully assembled."
            job.progress_percentage = 100
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.result = final_metadata

            self.storage.save_assembly_json(project_id, job.model_dump())
            return job

        except Exception as e:
            logger.error(f"Assembly failed for project {project_id}: {e}")
            job.status = AssemblyJobStatus.FAILED
            job.stage = AssemblyProgressStage.FAILED
            job.stage_message = f"Assembly failed: {str(e)}"
            job.error = str(e)
            job.error_category = "ASSEMBLY_ERROR"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            self.storage.save_assembly_json(project_id, job.model_dump())

            # Mark project status
            proj_data["status"] = "assembly_failed"
            self.storage.save_project_json(project_id, proj_data)
            raise

        finally:
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp assembly directory {temp_dir}: {e}")


video_assembler_service = VideoAssemblerService()
