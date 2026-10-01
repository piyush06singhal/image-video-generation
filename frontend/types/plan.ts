import { SceneType } from "./scene";

export type CameraMotionType =
  | "slow_forward"
  | "slow_backward"
  | "pan_left"
  | "pan_right"
  | "slight_dolly"
  | "static_subtle_motion"
  | "gentle_orbit"
  | "exterior_forward"
  | "unknown";

export const CAMERA_MOTION_LABELS: Record<CameraMotionType, string> = {
  slow_forward: "Slow Forward Movement",
  slow_backward: "Slow Backward Pull",
  pan_left: "Smooth Pan Left",
  pan_right: "Smooth Pan Right",
  slight_dolly: "Slight Forward Dolly",
  static_subtle_motion: "Static Subtle Drift",
  gentle_orbit: "Gentle Arc Orbit",
  exterior_forward: "Exterior Forward Track",
  unknown: "Restrained Camera Movement",
};

export type TransitionType =
  | "straight_cut"
  | "short_crossfade"
  | "visual_match"
  | "fade";

export const TRANSITION_LABELS: Record<TransitionType, string> = {
  straight_cut: "Straight Cut",
  short_crossfade: "Short Crossfade (0.5s)",
  visual_match: "Visual Match Cut",
  fade: "Fade to Black",
};

export type PlanSource = "ai" | "user";

export interface SceneNode {
  scene_id: string;
  image_id: string;
  scene_type: SceneType;
  label: string;
  confidence: number;
  user_confirmed: boolean;
  description: string;
  features: string[];
  visible_connections: string[];
  position_hint?: string | null;
  thumbnail_url?: string | null;
  original_filename?: string | null;
}

export interface ConnectionEvidence {
  source_scene_id: string;
  target_scene_id: string;
  evidence: string;
  confidence: number;
  type: string;
}

export interface SceneGraph {
  nodes: SceneNode[];
  edges: ConnectionEvidence[];
}

export interface CameraInstruction {
  motion_type: CameraMotionType;
  prompt: string;
  constraints: string[];
  duration_seconds: number;
}

export interface TransitionInstruction {
  type: TransitionType;
  duration_seconds: number;
  reason?: string | null;
}

export interface PlannedScene {
  order: number;
  scene_id: string;
  image_id: string;
  scene_type: SceneType;
  label: string;
  reason: string;
  camera: CameraInstruction;
  transition_to_next?: TransitionInstruction | null;
  thumbnail_url?: string | null;
  original_filename?: string | null;
  user_confirmed: boolean;
}

export interface GenerationPlan {
  plan_id: string;
  project_id: string;
  plan_version: number;
  source: PlanSource;
  created_at: string;
  updated_at: string;
  scenes: PlannedScene[];
  removed_scene_ids: string[];
  scene_graph?: SceneGraph | null;
  total_estimated_duration_seconds: number;
}

export interface PlannedSceneUpdateItem {
  scene_id: string;
  order: number;
  label?: string;
  motion_type?: CameraMotionType;
  camera_prompt?: string;
  transition_type?: TransitionType;
  user_confirmed?: boolean;
}

export interface PlanUpdateRequest {
  scenes: PlannedSceneUpdateItem[];
  removed_scene_ids?: string[];
}
