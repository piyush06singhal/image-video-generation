export type GenerationJobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'paused' | 'cancelled';

export type SceneGenerationStatus = 'pending' | 'generating' | 'completed' | 'failed' | 'paused';

export type ProjectGenerationStatus = 'ready' | 'generating' | 'partially_completed' | 'completed' | 'failed' | 'paused';

export type QualityAssessment = 'acceptable' | 'needs_review' | 'failed';

export interface VideoClipMetadata {
  scene_id: string;
  image_id: string;
  clip_filename: string;
  clip_path: string;
  clip_url: string;
  duration_seconds: number;
  width: number;
  height: number;
  fps: number;
  format: string;
  file_size_bytes: number;
  provider: string;
  model: string;
  camera_motion: string;
  prompt: string;
  generated_at: string;
  quality: QualityAssessment;
  /** Fingerprint of the render options this clip was rendered with. */
  render_signature?: string | null;
}

export interface GenerationJob {
  job_id: string;
  project_id: string;
  scene_id: string;
  image_id: string;
  status: GenerationJobStatus;
  provider: string;
  provider_job_id?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  error_code?: string;
  retry_count: number;
  result_clip?: VideoClipMetadata;
}

export interface SceneGenerationSummary {
  scene_id: string;
  order: number;
  label: string;
  scene_type: string;
  thumbnail_url?: string;
  status: SceneGenerationStatus;
  job_id?: string;
  clip?: VideoClipMetadata;
  last_error?: string;
  camera_motion?: string;
}

export interface ProjectGenerationOverview {
  project_id: string;
  status: ProjectGenerationStatus;
  total_scenes: number;
  completed_scenes: number;
  generating_scenes: number;
  failed_scenes: number;
  pending_scenes: number;
  total_duration_seconds: number;
  /** Configured engine for this run; compare to each clip's `provider` to spot fallbacks. */
  active_provider?: string | null;
  active_model?: string | null;
  /** Creative settings this project will render with. */
  render_options?: import('@/types/render-options').RenderOptions | null;
  /** True when completed clips were rendered with different settings than the project now has. */
  clips_outdated?: boolean;
  scenes: SceneGenerationSummary[];
  active_jobs: GenerationJob[];
}

export interface GenerateClipsPayload {
  scene_ids?: string[];
  force_regenerate?: boolean;
  render_options?: import('@/types/render-options').RenderOptions;
}

export interface RegenerateScenePayload {
  custom_motion_type?: string;
  custom_prompt?: string;
}
