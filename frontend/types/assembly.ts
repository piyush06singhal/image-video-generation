export type AssemblyJobStatus = "queued" | "processing" | "completed" | "failed";

export type AssemblyProgressStage =
  | "validating_clips"
  | "normalizing_clips"
  | "assembling_walkthrough"
  | "processing_audio"
  | "validating_final_video"
  | "completed"
  | "failed";

export interface AssembledSceneInfo {
  scene_id: string;
  image_id: string;
  order: number;
  label: string;
  scene_type: string;
  duration_seconds: number;
  clip_filename: string;
  transition_to_next: string;
}

export interface FinalVideoMetadata {
  project_id: string;
  filename: string;
  video_url: string;
  download_url: string;
  duration_seconds: number;
  width: number;
  height: number;
  fps: number;
  format: string;
  video_codec: string;
  audio_codec?: string | null;
  audio_enabled: boolean;
  file_size_bytes: number;
  scene_count: number;
  scenes_in_order: AssembledSceneInfo[];
  plan_version: number;
  plan_hash: string;
  is_outdated: boolean;
  created_at: string;
}

export interface AssemblyConfig {
  output_resolution?: "720p" | "1080p";
  output_fps?: number;
  crossfade_duration_seconds?: number;
  intro_title_enabled?: boolean;
  intro_duration_seconds?: number;
  audio_enabled?: boolean;
  audio_volume?: number;
}

export interface AssemblyRequest {
  config?: AssemblyConfig;
  force_reassemble?: boolean;
}

export interface AssemblyJob {
  job_id: string;
  project_id: string;
  status: AssemblyJobStatus;
  stage: AssemblyProgressStage;
  stage_message: string;
  progress_percentage: number;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  error_category?: string | null;
  result?: FinalVideoMetadata | null;
}
