import { ImageQualityResult, SceneAnalysisResult } from "./scene";

export type ImageStatus = "uploaded" | "validated" | "rejected";
export type AnalysisStatus = "pending" | "processing" | "completed" | "failed";

export interface ImageMetadata {
  id: string;
  filename: string;
  original_filename: string;
  width: number;
  height: number;
  format: string;
  file_size: number;
  aspect_ratio: number;
  sha256: string;
  status: ImageStatus;
  upload_timestamp: string;
  file_url?: string | null;
  thumbnail_url?: string | null;

  // Phase 2: Analysis & Quality
  analysis_status?: AnalysisStatus;
  scene?: SceneAnalysisResult | null;
  quality?: ImageQualityResult | null;
  analysis_error?: string | null;
  analysis_image_url?: string | null;
}

export interface RejectedImage {
  filename: string;
  code: string;
  message: string;
}

export interface ImageBatchUploadResult {
  project_id: string;
  total_received: number;
  total_accepted: number;
  total_rejected: number;
  uploaded: ImageMetadata[];
  rejected: RejectedImage[];
}

export interface StagedImage {
  id: string;
  file?: File;
  previewUrl: string;
  name: string;
  size: number;
  width?: number;
  height?: number;
  aspectRatio?: number;
  status: "staged" | "uploading" | "validated" | "error";
  errorMessage?: string;
  serverData?: ImageMetadata;
}
