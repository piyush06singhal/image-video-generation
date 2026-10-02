export type SceneReviewStatus = "acceptable" | "needs_review" | "failed";

export interface EvaluationCreate {
  visual_quality: number;
  property_consistency: number;
  scene_ordering: number;
  motion_quality: number;
  temporal_stability: number;
  walkthrough_usefulness: number;
  comments?: string;
  reviewer_name?: string;
}

export interface EvaluationRecord {
  evaluation_id: string;
  project_id: string;
  visual_quality: number;
  property_consistency: number;
  scene_ordering: number;
  motion_quality: number;
  temporal_stability: number;
  walkthrough_usefulness: number;
  comments: string;
  reviewer_name: string;
  created_at: string;
}

export interface SceneReviewCreate {
  scene_id: string;
  status: SceneReviewStatus;
  flags?: string[];
  notes?: string;
}

export interface SceneReviewRecord {
  review_id: string;
  project_id: string;
  scene_id: string;
  status: SceneReviewStatus;
  flags: string[];
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface EvaluationSummary {
  total_evaluations: number;
  average_visual_quality: number | null;
  average_property_consistency: number | null;
  average_scene_ordering: number | null;
  average_motion_quality: number | null;
  average_temporal_stability: number | null;
  average_walkthrough_usefulness: number | null;
  overall_average: number | null;
  evaluations: EvaluationRecord[];
  scene_reviews: SceneReviewRecord[];
}

export interface TechnicalReport {
  project_id: string;
  property_name: string;
  project_status: string;
  created_at: string;
  report_generated_at: string;
  source_images_count: number;
  analyzed_images_count: number;
  panoramic_images_count: number;
  planned_scenes_count: number;
  generated_clips_count: number;
  is_video_assembled: boolean;
  final_video?: {
    duration_seconds: number;
    width: number;
    height: number;
    fps: number;
    video_codec: string;
    format: string;
    scene_count: number;
    audio_enabled: boolean;
    integrity_verified?: boolean;
    is_outdated?: boolean;
  } | null;
  automated_checks: {
    all_scenes_analyzed: boolean;
    all_clips_generated: boolean;
    video_assembled: boolean;
    missing_clips_count: number;
    missing_clips: string[];
    has_corrupted_output: boolean;
    is_outdated_relative_to_plan: boolean;
  };
  evaluation_summary: EvaluationSummary;
  formatted_text_report: string;
}
