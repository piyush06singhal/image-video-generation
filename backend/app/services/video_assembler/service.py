import hashlib
import asyncio
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
from app.schemas.render_options import RenderOptions
from app.services.render_options_service import render_options_service
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
    Orchestrates Phase 5: Video Assembly, Transitions, and Final Walkthrough Video.

    Preserves strict scene ordering from the user-approved GenerationPlan and
    applies the project's :class:`RenderOptions` to the finished cut.

    Pipeline:

    1. validate every required clip is present and decodable
    2. resolve the target frame (aspect ratio x resolution) and fps
    3. build the intro card over a blurred plate of the first room
    4. conform each clip, burning an optional lower-third room label
    5. build the outro card over the last room
    6. concatenate with the chosen transition
    7. grade the whole cut in one pass (colour, vignette, grain)
    8. synthesise and mix the score
    9. probe the result and persist honest metadata
    """

    def __init__(self, storage=None):
        self._jobs: Dict[str, AssemblyJob] = {}
        self._assembly_tasks: Dict[str, asyncio.Task] = {}
        self.storage = storage or storage_service

    async def queue_assembly(
        self, project_id: str, request: Optional[AssemblyRequest] = None
    ) -> AssemblyJob:
        """Start assembly outside the HTTP request so Render can keep polling it."""
        active = [
            job
            for job in self._jobs.values()
            if job.project_id == project_id
            and job.status in (AssemblyJobStatus.QUEUED, AssemblyJobStatus.PROCESSING)
        ]
        if active:
            return max(active, key=lambda job: job.created_at)

        job = AssemblyJob(
            job_id=f"job_assembly_{uuid.uuid4().hex[:10]}",
            project_id=project_id,
            status=AssemblyJobStatus.QUEUED,
            stage=AssemblyProgressStage.VALIDATING,
            stage_message="Assembly queued; validating required scene clips...",
            progress_percentage=0,
        )
        self._jobs[job.job_id] = job
        self.storage.save_assembly_json(project_id, job.model_dump(mode="json"))
        self._assembly_tasks[job.job_id] = asyncio.create_task(
            asyncio.to_thread(self._run_queued_assembly, project_id, request, job.job_id)
        )
        return job

    def _run_queued_assembly(
        self,
        project_id: str,
        request: Optional[AssemblyRequest],
        job_id: str,
    ) -> AssemblyJob:
        """Run queued assembly and persist failures that occur before the pipeline starts."""
        try:
            return self.assemble_walkthrough(project_id, request, _job_id=job_id)
        except Exception as exc:
            job = self._jobs[job_id]
            job.status = AssemblyJobStatus.FAILED
            job.stage = AssemblyProgressStage.FAILED
            job.stage_message = f"Assembly failed: {exc}"
            job.error = str(exc)
            job.error_category = getattr(exc, "code", "ASSEMBLY_ERROR")
            job.completed_at = datetime.now(timezone.utc).isoformat()
            self.storage.save_assembly_json(project_id, job.model_dump(mode="json"))
            return job
        finally:
            try:
                self.storage.sync_project(project_id)
            except Exception as exc:
                logger.error("Failed to persist completed assembly for %s: %s", project_id, exc)
            self._assembly_tasks.pop(job_id, None)

    # ── fingerprints ─────────────────────────────────────────────────────
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

    # ── validation ───────────────────────────────────────────────────────
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

    # ── options resolution ───────────────────────────────────────────────
    def _resolve_options(
        self, project_id: str, request: Optional[AssemblyRequest]
    ) -> RenderOptions:
        """Project options, with any inline override persisted first."""
        if request and request.render_options:
            render_options_service.save(project_id, request.render_options)

        options = render_options_service.get(project_id)
        cfg: Optional[AssemblyConfig] = request.config if request else None
        if cfg is None:
            return options

        # Only fields the caller actually set (non-None) override the project
        # options; the empty default config must not silently reset everything.
        overrides: Dict[str, Any] = {}
        if cfg.intro_title_enabled is not None:
            overrides["intro_title_enabled"] = cfg.intro_title_enabled
        if cfg.intro_duration_seconds is not None:
            overrides["intro_duration_seconds"] = cfg.intro_duration_seconds
        if cfg.crossfade_duration_seconds is not None:
            overrides["transition_duration_seconds"] = cfg.crossfade_duration_seconds
        if cfg.audio_enabled is not None:
            overrides["music_enabled"] = cfg.audio_enabled
        if cfg.audio_volume is not None:
            overrides["music_volume"] = cfg.audio_volume
        if cfg.output_fps is not None:
            overrides["fps"] = int(cfg.output_fps)
        if cfg.output_resolution:
            # Legacy "1920x1080" string: honoured as an explicit frame size, then
            # re-expressed through the option fields the engine actually reads.
            try:
                width_str, height_str = cfg.output_resolution.lower().split("x")
                width, height = int(width_str), int(height_str)
                overrides["aspect_ratio"] = "16:9" if width >= height else "9:16"
                overrides["resolution"] = {1920: "1080p", 1280: "720p", 2560: "1440p"}.get(
                    width, options.resolution
                )
            except (ValueError, AttributeError):
                logger.warning(f"Ignoring unparseable output_resolution '{cfg.output_resolution}'")

        if not overrides:
            return options
        return options.model_copy(update=overrides)

    # ── metadata ─────────────────────────────────────────────────────────
    def get_final_metadata(self, project_id: str) -> Optional[FinalVideoMetadata]:
        """
        Retrieves final video metadata and checks if it is outdated relative to the
        current plan *or* the current render options.
        """
        raw_meta = self.storage.load_final_metadata_json(project_id)
        if not raw_meta:
            return None

        meta = FinalVideoMetadata(**raw_meta)
        video_file = self.storage.get_final_video_path(project_id)
        if not video_file.exists():
            return None

        plan_dict = self.storage.load_plan_json(project_id)
        if plan_dict:
            try:
                plan = GenerationPlan(**plan_dict)
                current_hash = self.compute_plan_fingerprint(plan)
                if current_hash != meta.plan_hash or plan.plan_version != meta.plan_version:
                    meta.is_outdated = True
            except Exception as exc:
                # Fail closed: an unreadable plan means we cannot prove the video is
                # current, and reporting a stale walkthrough as up to date is exactly
                # what this check exists to catch.
                logger.warning(
                    f"Could not check the final video for {project_id} against an "
                    f"unreadable plan ({exc}); marking it outdated."
                )
                meta.is_outdated = True

        current_options_hash = render_options_service.get(project_id).assembly_signature()
        if meta.render_options_hash != current_options_hash:
            meta.is_outdated = True

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

        raw = self.storage.load_assembly_json(project_id)
        if raw:
            return AssemblyJob(**raw)
        return None

    # ── helpers ──────────────────────────────────────────────────────────
    def _source_image_path(self, project_id: str, scene: PlannedScene) -> Optional[Path]:
        """Locates the original uploaded photo behind a scene, for card backdrops."""
        uploads = self.storage.get_project_uploads_dir(project_id)
        if not uploads.exists():
            return None
        if scene.original_filename:
            candidate = uploads / f"{scene.image_id}_{scene.original_filename}"
            if candidate.exists():
                return candidate
        matches = sorted(uploads.glob(f"{scene.image_id}*"))
        return matches[0] if matches else None

    # ── main pipeline ────────────────────────────────────────────────────
    def assemble_walkthrough(
        self,
        project_id: str,
        request: Optional[AssemblyRequest] = None,
        _job_id: Optional[str] = None,
    ) -> AssemblyJob:
        req = request or AssemblyRequest()
        options = self._resolve_options(project_id, request)

        proj_data = self.storage.load_project_json(project_id)
        if not proj_data:
            raise ProjectNotFoundError(project_id)

        plan_data = self.storage.load_plan_json(project_id)
        if not plan_data:
            raise AssemblyValidationError(f"Project {project_id} does not have an approved generation plan.")

        plan = GenerationPlan(**plan_data)
        plan_hash = self.compute_plan_fingerprint(plan)
        options_hash = options.assembly_signature()

        if not req.force_reassemble:
            existing_meta = self.get_final_metadata(project_id)
            if existing_meta and not existing_meta.is_outdated:
                logger.info(f"Reusing existing up-to-date walkthrough for {project_id}")
                return AssemblyJob(
                    job_id=str(uuid.uuid4()),
                    project_id=project_id,
                    status=AssemblyJobStatus.COMPLETED,
                    stage=AssemblyProgressStage.COMPLETED,
                    stage_message="Walkthrough already assembled and up to date.",
                    progress_percentage=100,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    result=existing_meta,
                )

        if _job_id and _job_id in self._jobs:
            job_id = _job_id
            job = self._jobs[job_id]
            job.status = AssemblyJobStatus.PROCESSING
            job.stage_message = "Validating required scene clips..."
            job.progress_percentage = 10
            job.started_at = datetime.now(timezone.utc).isoformat()
        else:
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
            validated_clips = self.validate_required_clips(project_id, plan)
            target_w, target_h = options.dimensions()
            target_fps = float(options.fps)
            logger.info(
                f"Assembling {project_id} with preset='{options.preset}' "
                f"{target_w}x{target_h}@{target_fps} grade={options.color_grade.value} "
                f"transition={options.transition_style.value} music={options.music_enabled}"
            )

            job.stage = AssemblyProgressStage.NORMALIZING
            job.stage_message = f"Conforming {len(validated_clips)} scene clips to {target_w}x{target_h}..."
            job.progress_percentage = 25

            normalized_clips: List[Path] = []
            assembled_scene_info: List[AssembledSceneInfo] = []

            # ── intro card, over a blurred plate of the opening room ──
            if options.intro_title_enabled:
                title = options.intro_title_text or proj_data.get("name") or "Luxury Property Walkthrough"
                first_scene = validated_clips[0][0]
                ffmpeg_engine.create_title_intro_clip(
                    title=title,
                    output_path=temp_dir / "intro.mp4",
                    duration=options.intro_duration_seconds,
                    width=target_w,
                    height=target_h,
                    fps=target_fps,
                    backdrop_image_path=self._source_image_path(project_id, first_scene),
                    brand_text=options.brand_text,
                )
                normalized_clips.append(temp_dir / "intro.mp4")

            # ── per-scene conform (+ optional burned-in room label) ──
            for idx, (scene, clip_path, meta) in enumerate(validated_clips):
                conformed = temp_dir / f"norm_scene_{idx + 1:02d}_{scene.scene_id}.mp4"
                if options.room_labels_enabled:
                    total_rooms = len(validated_clips)
                    ffmpeg_engine.apply_room_label(
                        input_path=clip_path,
                        output_path=conformed,
                        label=scene.label,
                        width=target_w,
                        height=target_h,
                        fps=target_fps,
                        counter=(
                            f"{idx + 1:02d} / {total_rooms:02d}" if options.room_counter else None
                        ),
                        progress=((idx + 1) / total_rooms) if options.room_counter else None,
                    )
                else:
                    ffmpeg_engine.normalize_clip(
                        input_path=clip_path,
                        output_path=conformed,
                        target_width=target_w,
                        target_height=target_h,
                        target_fps=target_fps,
                    )
                normalized_clips.append(conformed)

                assembled_scene_info.append(
                    AssembledSceneInfo(
                        scene_id=scene.scene_id,
                        image_id=scene.image_id,
                        order=scene.order,
                        label=scene.label,
                        scene_type=scene.scene_type.value,
                        duration_seconds=meta["duration_seconds"],
                        clip_filename=clip_path.name,
                        transition_to_next=options.transition_style.value,
                    )
                )

            # ── outro card, over a blurred plate of the closing room ──
            if options.outro_enabled:
                last_scene = validated_clips[-1][0]
                outro_title = options.outro_text or proj_data.get("name") or "Thank You"
                ffmpeg_engine.create_outro_card(
                    output_path=temp_dir / "outro.mp4",
                    title=outro_title,
                    duration=options.outro_duration_seconds,
                    width=target_w,
                    height=target_h,
                    fps=target_fps,
                    backdrop_image_path=self._source_image_path(project_id, last_scene),
                    brand_text=options.brand_text,
                )
                normalized_clips.append(temp_dir / "outro.mp4")

            # ── transitions ──
            job.stage = AssemblyProgressStage.ASSEMBLING
            job.stage_message = f"Cutting {len(normalized_clips)} segments with {options.transition_style.value}..."
            job.progress_percentage = 60

            assembled_raw = temp_dir / "assembled_raw.mp4"
            ffmpeg_engine.concatenate_clips(
                clip_paths=normalized_clips,
                output_path=assembled_raw,
                crossfade_duration=options.transition_duration_seconds,
                transition_style=options.transition_style.value,
            )

            # ── single grading/conform pass ──
            graded_path = temp_dir / "graded.mp4"
            ffmpeg_engine.grade_and_conform(
                input_path=assembled_raw,
                output_path=graded_path,
                width=target_w,
                height=target_h,
                fps=target_fps,
                color_grade=options.color_grade.value,
                vignette=options.vignette,
                film_grain=options.film_grain,
                letterbox=options.letterbox,
                bloom=options.cinematic_bloom,
            )

            final_target_mp4 = self.storage.get_final_video_path(project_id)
            final_target_mp4.parent.mkdir(parents=True, exist_ok=True)

            # ── score ──
            audio_codec: Optional[str] = None
            if options.music_enabled and options.music_style.value != "none":
                job.stage = AssemblyProgressStage.AUDIO_PROCESSING
                job.stage_message = "Synthesising and mixing the score..."
                job.progress_percentage = 85

                picture_meta = ffmpeg_engine.probe_video(graded_path)
                bed = temp_dir / "score.m4a"
                try:
                    ffmpeg_engine.synthesize_music(
                        duration_seconds=picture_meta["duration_seconds"],
                        style=options.music_style.value,
                        output_path=bed,
                        volume=options.music_volume,
                        # The assembly recorded exactly where it cut, so the
                        # sound design lands on the picture instead of near it.
                        cut_times=ffmpeg_engine.last_transition_times(),
                        opening_riser=options.intro_title_enabled,
                        final_impact=options.outro_enabled,
                    )
                    ffmpeg_engine.add_background_audio(
                        video_path=graded_path,
                        audio_path=bed,
                        output_path=final_target_mp4,
                        volume=options.music_volume,
                    )
                    audio_codec = ffmpeg_engine.probe_audio_codec(final_target_mp4)
                except AppException as exc:
                    # A silent film is still a usable listing video, so a score
                    # failure degrades rather than killing an otherwise good render.
                    logger.error(f"Score mixing failed ({exc.code}: {exc.message}); shipping silent cut.")
                    shutil.copy2(graded_path, final_target_mp4)
                    audio_codec = None
            else:
                shutil.copy2(graded_path, final_target_mp4)

            # ── final validation ──
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
                # Report the codec actually present in the container instead of
                # hardcoding None, which used to misrepresent a scored cut.
                audio_codec=audio_codec,
                audio_enabled=bool(audio_codec),
                file_size_bytes=final_probe["file_size_bytes"],
                scene_count=len(assembled_scene_info),
                scenes_in_order=assembled_scene_info,
                plan_version=plan.plan_version,
                plan_hash=plan_hash,
                render_options_hash=options_hash,
                render_options=options,
                is_outdated=False,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            self.storage.save_final_metadata_json(project_id, final_metadata.model_dump(mode="json"))

            proj_data["status"] = "completed"
            self.storage.save_project_json(project_id, proj_data)

            job.status = AssemblyJobStatus.COMPLETED
            job.stage = AssemblyProgressStage.COMPLETED
            job.stage_message = "Walkthrough video successfully assembled."
            job.progress_percentage = 100
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.result = final_metadata

            self.storage.save_assembly_json(project_id, job.model_dump(mode="json"))
            return job

        except Exception as e:
            logger.error(f"Assembly failed for project {project_id}: {e}")
            job.status = AssemblyJobStatus.FAILED
            job.stage = AssemblyProgressStage.FAILED
            job.stage_message = f"Assembly failed: {str(e)}"
            job.error = str(e)
            job.error_category = getattr(e, "code", "ASSEMBLY_ERROR")
            job.completed_at = datetime.now(timezone.utc).isoformat()
            self.storage.save_assembly_json(project_id, job.model_dump(mode="json"))

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
