export type SceneType =
  | "exterior"
  | "entrance"
  | "living_room"
  | "kitchen"
  | "dining_area"
  | "bedroom"
  | "bathroom"
  | "balcony"
  | "hallway"
  | "study"
  | "utility_area"
  | "staircase"
  | "garden"
  | "parking"
  | "unknown";

export const SCENE_TYPE_LABELS: Record<SceneType, string> = {
  exterior: "Exterior",
  entrance: "Entrance",
  living_room: "Living Room",
  kitchen: "Kitchen",
  dining_area: "Dining Area",
  bedroom: "Bedroom",
  bathroom: "Bathroom",
  balcony: "Balcony",
  hallway: "Hallway",
  study: "Study / Home Office",
  utility_area: "Utility Area",
  staircase: "Staircase",
  garden: "Garden",
  parking: "Parking / Garage",
  unknown: "Unknown",
};

export type LightingType =
  | "natural_daylight"
  | "warm_artificial"
  | "cool_artificial"
  | "mixed"
  | "low_light"
  | "unknown";

export const LIGHTING_LABELS: Record<LightingType, string> = {
  natural_daylight: "Natural Daylight",
  warm_artificial: "Warm Artificial",
  cool_artificial: "Cool Artificial",
  mixed: "Mixed Lighting",
  low_light: "Low Light",
  unknown: "Unknown Lighting",
};

export type ViewType =
  | "wide"
  | "medium"
  | "close"
  | "overhead"
  | "exterior"
  | "unknown";

export const VIEW_TYPE_LABELS: Record<ViewType, string> = {
  wide: "Wide View",
  medium: "Medium View",
  close: "Close-up",
  overhead: "Overhead",
  exterior: "Exterior View",
  unknown: "Unknown View",
};

export type CameraView =
  | "eye_level"
  | "slightly_elevated"
  | "low_angle"
  | "centered"
  | "corner_view"
  | "unknown";

export const CAMERA_VIEW_LABELS: Record<CameraView, string> = {
  eye_level: "Eye Level",
  slightly_elevated: "Slightly Elevated",
  low_angle: "Low Angle",
  centered: "Centered",
  corner_view: "Corner Perspective",
  unknown: "Unknown Perspective",
};

export type QualityStatus = "good" | "acceptable" | "poor";

export interface ImageQualityResult {
  status: QualityStatus;
  resolution: string;
  brightness_score: number;
  contrast_score: number;
  sharpness_score: number;
  file_size: number;
}

export interface SceneAnalysisResult {
  scene_type: SceneType;
  confidence: number;
  description: string;
  features: string[];
  lighting: LightingType;
  view_type: ViewType;
  camera_view: CameraView;
  visible_connections: string[];
  user_corrected: boolean;
  analyzed_at: string;
}

export interface SceneCorrectionPayload {
  scene_type: SceneType;
  description?: string;
  features?: string[];
}
