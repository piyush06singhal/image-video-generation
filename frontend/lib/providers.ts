/**
 * Presentation helpers for the image-to-video engines.
 *
 * Phase 4 is provider-swappable
 * (`auto` | `json2video` | `magic_hour` | `gemini_veo` | `kenburns`), so the UI
 * must never hardcode an engine name. It also has to be able to tell when a
 * clip came from the *local fallback* rather than the configured provider — that
 * happens whenever a remote provider is rate-limited, out of quota, blocked, or
 * misconfigured, and it is the single most confusing thing for a user otherwise.
 */

export type RenderEngineKind = "generative" | "plate" | "unknown";

export interface RenderEngine {
  /** Canonical provider id as reported by the backend. */
  id: string;
  /** Short human label, e.g. "Veo 3.1" or "Local renderer". */
  label: string;
  /** Longer descriptor for stat cards. */
  description: string;
  /**
   * `generative` engines synthesize new pixels (and can therefore drift from the
   * listing). `plate` engines move a camera over the real photograph, so the result
   * is pixel-exact by construction.
   */
  kind: RenderEngineKind;
}

const ENGINES: Record<string, RenderEngine> = {
  gemini_veo: {
    id: "gemini_veo",
    label: "Gemini Veo",
    description: "Generative image-to-video diffusion",
    kind: "generative",
  },
  json2video: {
    id: "json2video",
    label: "JSON2Video",
    description: "Cloud render over the real photos",
    kind: "plate",
  },
  magic_hour: {
    id: "magic_hour",
    label: "Magic Hour",
    description: "Generative image-to-video (Kling / LTX / Veo)",
    kind: "generative",
  },
  local_kenburns: {
    id: "local_kenburns",
    label: "Local renderer",
    description: "On-device cinematic camera motion",
    kind: "plate",
  },
};

const UNKNOWN_ENGINE: RenderEngine = {
  id: "unknown",
  label: "Unknown engine",
  description: "Unrecognized render provider",
  kind: "unknown",
};

export function describeEngine(providerId?: string | null): RenderEngine {
  if (!providerId) return UNKNOWN_ENGINE;
  return ENGINES[providerId] ?? { ...UNKNOWN_ENGINE, id: providerId, label: providerId };
}

/** True when a clip was rendered by the local fallback rather than the active engine. */
export function isLocalFallback(clipProvider?: string | null, activeProvider?: string | null): boolean {
  if (!clipProvider || !activeProvider) return false;
  return clipProvider !== activeProvider;
}

/**
 * How many clips did NOT come from the configured engine. Zero means the whole
 * walkthrough was rendered by the engine the operator chose.
 */
export function countFallbackClips(
  clips: Array<{ provider?: string | null } | null | undefined>,
  activeProvider?: string | null,
): number {
  return clips.filter((clip) => isLocalFallback(clip?.provider, activeProvider)).length;
}
