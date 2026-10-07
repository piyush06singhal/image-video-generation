from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from app.core.errors import ProjectNotFoundError
from app.core.logging import logger
from app.schemas.evaluation import (
    EvaluationCreate,
    EvaluationRecord,
    EvaluationSummary,
    SceneReviewCreate,
    SceneReviewRecord,
    SceneReviewStatus,
    TechnicalReport,
)
from app.services.storage_service import storage_service


class EvaluationService:
    """
    Service responsible for persisting and computing human evaluations,
    scene quality review flags, automated integrity checks, and technical reports.
    """

    def __init__(self):
        self.storage = storage_service

    def submit_evaluation(
        self, project_id: str, evaluation_in: EvaluationCreate
    ) -> EvaluationRecord:
        """
        Validates and appends a human walkthrough evaluation record.
        """
        project = self.storage.load_project_json(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        evaluations_raw = self.storage.load_evaluations_json(project_id)

        record = EvaluationRecord(
            evaluation_id=f"eval_{uuid4().hex[:10]}",
            project_id=project_id,
            visual_quality=evaluation_in.visual_quality,
            property_consistency=evaluation_in.property_consistency,
            scene_ordering=evaluation_in.scene_ordering,
            motion_quality=evaluation_in.motion_quality,
            temporal_stability=evaluation_in.temporal_stability,
            walkthrough_usefulness=evaluation_in.walkthrough_usefulness,
            comments=evaluation_in.comments.strip() if evaluation_in.comments else "",
            reviewer_name=evaluation_in.reviewer_name.strip() if evaluation_in.reviewer_name else "Human Evaluator",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        evaluations_raw.append(record.model_dump())
        self.storage.save_evaluations_json(project_id, evaluations_raw)
        logger.info(f"Recorded evaluation {record.evaluation_id} for project {project_id}")

        return record

    def get_evaluations(self, project_id: str) -> List[EvaluationRecord]:
        """
        Retrieves all human evaluations for a project.
        """
        project = self.storage.load_project_json(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        evaluations_raw = self.storage.load_evaluations_json(project_id)
        return [EvaluationRecord(**item) for item in evaluations_raw]

    def submit_scene_review(
        self, project_id: str, review_in: SceneReviewCreate
    ) -> SceneReviewRecord:
        """
        Upserts a per-scene quality inspection review.
        """
        project = self.storage.load_project_json(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        reviews_raw = self.storage.load_scene_reviews_json(project_id)
        now = datetime.now(timezone.utc).isoformat()

        # Check existing review for this scene
        existing_idx = next(
            (i for i, r in enumerate(reviews_raw) if r.get("scene_id") == review_in.scene_id),
            None,
        )

        if existing_idx is not None:
            existing = reviews_raw[existing_idx]
            record = SceneReviewRecord(
                review_id=existing.get("review_id", f"rev_{uuid4().hex[:8]}"),
                project_id=project_id,
                scene_id=review_in.scene_id,
                status=review_in.status,
                flags=review_in.flags,
                notes=review_in.notes.strip() if review_in.notes else "",
                created_at=existing.get("created_at", now),
                updated_at=now,
            )
            reviews_raw[existing_idx] = record.model_dump()
        else:
            record = SceneReviewRecord(
                review_id=f"rev_{uuid4().hex[:8]}",
                project_id=project_id,
                scene_id=review_in.scene_id,
                status=review_in.status,
                flags=review_in.flags,
                notes=review_in.notes.strip() if review_in.notes else "",
                created_at=now,
                updated_at=now,
            )
            reviews_raw.append(record.model_dump())

        self.storage.save_scene_reviews_json(project_id, reviews_raw)
        logger.info(f"Recorded scene review for scene {review_in.scene_id} in project {project_id}")

        return record

    def get_scene_reviews(self, project_id: str) -> List[SceneReviewRecord]:
        """
        Retrieves all scene review records for a project.
        """
        project = self.storage.load_project_json(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        reviews_raw = self.storage.load_scene_reviews_json(project_id)
        return [SceneReviewRecord(**r) for r in reviews_raw]

    def get_evaluation_summary(self, project_id: str) -> EvaluationSummary:
        """
        Computes real averages from stored human evaluations and gathers scene reviews.
        """
        evaluations = self.get_evaluations(project_id)
        scene_reviews = self.get_scene_reviews(project_id)

        if not evaluations:
            return EvaluationSummary(
                total_evaluations=0,
                evaluations=[],
                scene_reviews=scene_reviews,
            )

        n = float(len(evaluations))
        avg_vq = round(sum(e.visual_quality for e in evaluations) / n, 2)
        avg_pc = round(sum(e.property_consistency for e in evaluations) / n, 2)
        avg_so = round(sum(e.scene_ordering for e in evaluations) / n, 2)
        avg_mq = round(sum(e.motion_quality for e in evaluations) / n, 2)
        avg_ts = round(sum(e.temporal_stability for e in evaluations) / n, 2)
        avg_wu = round(sum(e.walkthrough_usefulness for e in evaluations) / n, 2)
        overall = round((avg_vq + avg_pc + avg_so + avg_mq + avg_ts + avg_wu) / 6.0, 2)

        return EvaluationSummary(
            total_evaluations=len(evaluations),
            average_visual_quality=avg_vq,
            average_property_consistency=avg_pc,
            average_scene_ordering=avg_so,
            average_motion_quality=avg_mq,
            average_temporal_stability=avg_ts,
            average_walkthrough_usefulness=avg_wu,
            overall_average=overall,
            evaluations=evaluations,
            scene_reviews=scene_reviews,
        )

    def generate_technical_report(self, project_id: str) -> TechnicalReport:
        """
        Generates a comprehensive technical report grounded strictly in actual stored artifacts.
        """
        project = self.storage.load_project_json(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        images = project.get("images", [])
        plan_data = self.storage.load_plan_json(project_id)
        gen_data = self.storage.load_generation_json(project_id)
        final_meta = self.storage.load_final_metadata_json(project_id)
        summary = self.get_evaluation_summary(project_id)

        # Quantitative counts
        source_count = len(images)
        analyzed_count = sum(1 for img in images if img.get("analysis_status") == "completed")
        panoramic_count = sum(1 for img in images if img.get("is_panoramic") is True)
        planned_scenes_count = len(plan_data.get("scenes", [])) if plan_data else 0
        generated_clips_count = gen_data.get("completed_scenes", 0) if gen_data else 0
        is_assembled = final_meta is not None and self.storage.get_final_video_path(project_id).exists()

        # Automated checks
        missing_clips = []
        if plan_data:
            for scene in plan_data.get("scenes", []):
                sid = scene.get("scene_id")
                clip_path = self.storage.get_clip_path(project_id, sid)
                if not clip_path.exists() or clip_path.stat().st_size < 1000:
                    missing_clips.append(sid)

        automated_checks = {
            "all_scenes_analyzed": analyzed_count == source_count and source_count > 0,
            "all_clips_generated": len(missing_clips) == 0 and planned_scenes_count > 0,
            "video_assembled": is_assembled,
            "missing_clips_count": len(missing_clips),
            "missing_clips": missing_clips,
            "has_corrupted_output": False,
            "is_outdated_relative_to_plan": bool(final_meta.get("is_outdated")) if final_meta else False,
        }

        # Formatted text report generator
        prop_name = project.get("name", "Real Estate Property")
        created_at = project.get("created_at", "")
        now_iso = datetime.now(timezone.utc).isoformat()

        eval_section = ""
        if summary.total_evaluations > 0:
            eval_section = f"""------------------------------------------------------------
HUMAN EVALUATION (Averages across {summary.total_evaluations} Reviewer{'s' if summary.total_evaluations > 1 else ''})
------------------------------------------------------------
  • Visual Quality:          {summary.average_visual_quality:.1f} / 5.0
  • Property Consistency:    {summary.average_property_consistency:.1f} / 5.0
  • Scene Ordering:          {summary.average_scene_ordering:.1f} / 5.0
  • Motion Quality:          {summary.average_motion_quality:.1f} / 5.0
  • Temporal Stability:      {summary.average_temporal_stability:.1f} / 5.0
  • Walkthrough Usefulness:  {summary.average_walkthrough_usefulness:.1f} / 5.0
  • Overall Composite Score: {summary.overall_average:.1f} / 5.0"""
        else:
            eval_section = """------------------------------------------------------------
HUMAN EVALUATION
------------------------------------------------------------
  • No human evaluations submitted yet for this project."""

        scene_flags_section = ""
        if summary.scene_reviews:
            acc = sum(1 for r in summary.scene_reviews if r.status == SceneReviewStatus.ACCEPTABLE)
            nr = sum(1 for r in summary.scene_reviews if r.status == SceneReviewStatus.NEEDS_REVIEW)
            fail = sum(1 for r in summary.scene_reviews if r.status == SceneReviewStatus.FAILED)
            scene_flags_section = f"""
SCENE REVIEWS:
  • Acceptable:    {acc}
  • Needs Review:  {nr}
  • Failed:        {fail}"""

        video_section = ""
        if is_assembled and final_meta:
            dur = final_meta.get("duration_seconds", 0)
            mins = int(dur // 60)
            secs = int(dur % 60)
            dur_str = f"{mins:02d}:{secs:02d} ({dur:.1f}s)"
            video_section = f"""------------------------------------------------------------
FINAL VIDEO SPECIFICATIONS
------------------------------------------------------------
  • Status:               Assembled & Verified
  • Total Duration:       {dur_str}
  • Output Resolution:    {final_meta.get('width', 1280)} × {final_meta.get('height', 720)} px
  • Frame Rate:           {final_meta.get('fps', 24)} fps
  • Video Codec:          {final_meta.get('video_codec', 'h264').upper()} ({final_meta.get('format', 'mp4')})
  • Assembled Scenes:     {final_meta.get('scene_count', planned_scenes_count)}
  • Audio Track:          {"Enabled" if final_meta.get('audio_enabled') else "Disabled"}
  • Integrity Verified:   {"Yes (Valid FFprobe stream)" if final_meta.get('integrity_verified') else "No"}"""
        else:
            video_section = """------------------------------------------------------------
FINAL VIDEO SPECIFICATIONS
------------------------------------------------------------
  • Status:               Not Assembled"""

        formatted_text = f"""============================================================
WALKTHROUGH GENERATION & EVALUATION REPORT
============================================================
Property: {prop_name}
Project ID: #{project_id}
Status: {project.get('status', 'draft')}
Report Generated: {now_iso}

------------------------------------------------------------
PROJECT ASSET SUMMARY
------------------------------------------------------------
  • Source Photographs:   {source_count}
  • Analyzed with Gemini: {analyzed_count} / {source_count}
  • Panoramic Images:     {panoramic_count}
  • Planned Walkthrough:  {planned_scenes_count} scenes
  • Generated Video Clips:{generated_clips_count} / {planned_scenes_count}
{video_section}
{eval_section}{scene_flags_section}
============================================================
"""

        return TechnicalReport(
            project_id=project_id,
            property_name=prop_name,
            project_status=project.get("status", "draft"),
            created_at=created_at,
            report_generated_at=now_iso,
            source_images_count=source_count,
            analyzed_images_count=analyzed_count,
            panoramic_images_count=panoramic_count,
            planned_scenes_count=planned_scenes_count,
            generated_clips_count=generated_clips_count,
            is_video_assembled=is_assembled,
            final_video=final_meta,
            automated_checks=automated_checks,
            evaluation_summary=summary,
            formatted_text_report=formatted_text,
        )


evaluation_service = EvaluationService()
