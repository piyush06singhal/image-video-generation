export type MotionIntensity = "subtle" | "balanced" | "bold";

export type TransitionStyle =
  | "straight_cut"
  | "crossfade"
  | "fade_to_black"
  | "slide_left"
  | "wipe_up"
  | "blur_dissolve"
  | "smooth_left";

export type ColorGrade =
  | "none"
  | "warm_luxury"
  | "golden_hour"
  | "cool_modern"
  | "cinematic_teal"
  | "noir";

export type AspectRatio = "16:9" | "9:16" | "1:1";

export type MusicStyle = "none" | "ambient" | "uplifting" | "minimal_piano";

export type ResolutionTier = "720p" | "1080p" | "1440p";

export interface RenderOptions {
  preset: string;
  scene_duration_seconds: number;
  motion_intensity: MotionIntensity;
  camera_variety: boolean;
  depth_parallax: boolean;
  motion_blur: boolean;
  transition_style: TransitionStyle;
  transition_duration_seconds: number;
  aspect_ratio: AspectRatio;
  resolution: ResolutionTier;
  fps: number;
  intro_title_enabled: boolean;
  intro_title_text?: string | null;
  intro_duration_seconds: number;
  outro_enabled: boolean;
  outro_duration_seconds: number;
  outro_text?: string | null;
  room_labels_enabled: boolean;
  room_counter: boolean;
  brand_text?: string | null;
  color_grade: ColorGrade;
  vignette: boolean;
  film_grain: boolean;
  cinematic_bloom: boolean;
  letterbox: boolean;
  music_enabled: boolean;
  music_style: MusicStyle;
  music_volume: number;
}

export interface RenderPresetInfo {
  id: string;
  label: string;
  description: string;
  options: Partial<RenderOptions>;
  recommended: boolean;
}

export interface RenderOptionsUpdate {
  preset?: string;
  options?: Partial<RenderOptions>;
  replace?: boolean;
}

/** Base landscape dimensions per quality tier — mirrors the backend table. */
export const RESOLUTION_TIERS: Record<ResolutionTier, [number, number]> = {
  "720p": [1280, 720],
  "1080p": [1920, 1080],
  "1440p": [2560, 1440],
};

/** Resolves an aspect ratio + tier into concrete pixels, matching the backend. */
export function targetDimensions(aspect: AspectRatio, tier: ResolutionTier): [number, number] {
  const [baseW, baseH] = RESOLUTION_TIERS[tier] ?? RESOLUTION_TIERS["1080p"];
  if (aspect === "9:16") return [baseH, Math.round((baseH * 16) / 9)];
  if (aspect === "1:1") return [baseH, baseH];
  return [baseW, baseH];
}

/**
 * Whether a change to these options invalidates already-generated clips.
 * Mirrors `RenderOptions.generation_signature()` on the backend: anything in
 * here reshapes the clips themselves, so the studio must warn before spending
 * time or provider quota regenerating them.
 */
export const CLIP_AFFECTING_FIELDS: (keyof RenderOptions)[] = [
  "scene_duration_seconds",
  "aspect_ratio",
  "resolution",
  "fps",
  "motion_intensity",
  "camera_variety",
  "depth_parallax",
  "motion_blur",
];

export function optionsAffectClips(a: RenderOptions, b: RenderOptions): boolean {
  return CLIP_AFFECTING_FIELDS.some((field) => a[field] !== b[field]);
}

export const ASPECT_LABELS: Record<AspectRatio, string> = {
  "16:9": "Landscape",
  "9:16": "Vertical Reel",
  "1:1": "Square",
};

export const GRADE_LABELS: Record<ColorGrade, string> = {
  none: "Untouched",
  warm_luxury: "Warm Luxury",
  golden_hour: "Golden Hour",
  cool_modern: "Cool Modern",
  cinematic_teal: "Cinematic Teal",
  noir: "Noir",
};

/** Swatch colours used for the grade picker preview chips. */
export const GRADE_SWATCHES: Record<ColorGrade, string> = {
  none: "linear-gradient(135deg,#7d8794,#4a5461)",
  warm_luxury: "linear-gradient(135deg,#e8b06a,#8a5a2b)",
  golden_hour: "linear-gradient(135deg,#ffd08a,#a85f1e)",
  cool_modern: "linear-gradient(135deg,#9fc6e8,#3c5a78)",
  cinematic_teal: "linear-gradient(135deg,#e0a15f,#12545c)",
  noir: "linear-gradient(135deg,#e6e6e6,#2a2a2a)",
};

export const TRANSITION_LABELS: Record<TransitionStyle, string> = {
  straight_cut: "Hard Cut",
  crossfade: "Cross Dissolve",
  fade_to_black: "Fade Through Black",
  slide_left: "Slide",
  wipe_up: "Wipe Up",
  blur_dissolve: "Blur Dissolve",
  smooth_left: "Motion Dissolve",
};

export const MOTION_LABELS: Record<MotionIntensity, string> = {
  subtle: "Subtle",
  balanced: "Balanced",
  bold: "Bold",
};

export const MUSIC_LABELS: Record<MusicStyle, string> = {
  none: "Silent",
  ambient: "Ambient Score",
  uplifting: "Uplifting Theme",
  minimal_piano: "Minimal Piano",
};

/**
 * Human-readable summary of the engine's headline production features, so the
 * studio can explain what a preset will actually do rather than just offering a
 * wall of switches.
 */
export const REALISM_LABELS = {
  depth_parallax: {
    label: "2.5D Depth Parallax",
    hint: "Estimates per-pixel depth so near objects move further than far ones.",
  },
  motion_blur: {
    label: "Motion Blur",
    hint: "Trailing-shutter blur on fast movement, the way a real camera renders it.",
  },
  cinematic_bloom: {
    label: "Highlight Bloom",
    hint: "Halation: only true highlights glow, smeared wide like a fast lens.",
  },
  letterbox: {
    label: "Cinematic Bars",
    hint: "Scope-style bars. Landscape output only.",
  },
  room_counter: {
    label: "Room Counter & Progress",
    hint: "Adds “03 / 08” and a progress line to each lower-third.",
  },
} as const;
