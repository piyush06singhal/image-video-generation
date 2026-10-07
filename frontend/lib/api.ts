import { ApiResponse, HealthStatus } from "@/types/api";
import { ImageBatchUploadResult, ImageMetadata } from "@/types/image";
import { Project } from "@/types/project";
import { SceneCorrectionPayload } from "@/types/scene";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

// Sent as X-API-Key when the backend sets API_ACCESS_KEY. Media (`<img>`/`<video>`) URLs
// cannot carry headers, which is why the backend leaves the /file, /download and
// /thumbnail routes ungated.
const API_ACCESS_KEY = process.env.NEXT_PUBLIC_API_KEY || "";
const NETWORK_RETRY_DELAYS_MS = [250, 750];

/** True when this build was shipped with a shared API key. */
export const hasApiKey = Boolean(API_ACCESS_KEY);

/**
 * Explains a 401 in terms the operator can act on.
 *
 * A key mismatch is the single most common cross-machine failure: the backend's
 * `.env` is git-ignored, so a fresh clone starts with `API_ACCESS_KEY` unset on one
 * side and set on the other. Without this hint the symptom is an opaque 401 that
 * looks exactly like a broken server.
 */
function unauthorizedHint(): string {
  if (!API_ACCESS_KEY) {
    return (
      `This frontend build has no NEXT_PUBLIC_API_KEY, but the backend at ${API_BASE_URL} ` +
      "is refusing unauthenticated requests. Add NEXT_PUBLIC_API_KEY to frontend/.env.local " +
      "with the same value as API_ACCESS_KEY in backend/.env, then restart the dev server " +
      "(NEXT_PUBLIC_* values are inlined at build time)."
    );
  }
  return (
    "NEXT_PUBLIC_API_KEY does not match the backend's API_ACCESS_KEY. Copy the exact " +
    "value from backend/.env into frontend/.env.local and restart the dev server."
  );
}

export class ApiError extends Error {
  code: string;
  details?: unknown;

  constructor(code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.details = details;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  for (let attempt = 0; attempt <= NETWORK_RETRY_DELAYS_MS.length; attempt += 1) {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...(API_ACCESS_KEY ? { "X-API-Key": API_ACCESS_KEY } : {}),
          ...(options.headers || {}),
        },
      });

      let json: ApiResponse<T>;
      try {
        json = await response.json();
      } catch {
        throw new ApiError(
          "INVALID_SERVER_RESPONSE",
          `Server returned non-JSON response with HTTP status ${response.status}.`
        );
      }

      if (!response.ok || !json.success || json.error) {
        const code = json.error?.code || `HTTP_${response.status}`;
        const message =
          json.error?.message ||
          `Request failed with status ${response.status}: ${response.statusText}`;
        if (response.status === 401 || code === "UNAUTHORIZED") {
          throw new ApiError(code, `${message} ${unauthorizedHint()}`, json.error?.details);
        }
        throw new ApiError(code, message, json.error?.details);
      }

      return json.data as T;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      if (attempt < NETWORK_RETRY_DELAYS_MS.length) {
        await new Promise((resolve) =>
          setTimeout(resolve, NETWORK_RETRY_DELAYS_MS[attempt])
        );
        continue;
      }

      // Browsers intentionally hide CORS and DNS failures from JavaScript. Include
      // the actual endpoint and origin so a deployment problem is distinguishable
      // from a stopped FastAPI process.
      const browserOrigin =
        typeof window !== "undefined" ? window.location.origin : "unknown origin";
      throw new ApiError(
        "SERVER_UNAVAILABLE",
        `The browser could not reach ${url} from ${browserOrigin}. ` +
          "This is usually a CORS, API URL, or deployment configuration problem; " +
          "verify that the Vercel build uses the Render URL and that the backend " +
          "allows this frontend origin."
      );
    }
  }

  throw new ApiError("SERVER_UNAVAILABLE", `Unable to reach ${url}.`);
}

/**
 * Configuration problems the health probe can detect before the first real request.
 *
 * Returns human-readable, actionable sentences — or an empty array when the
 * deployment looks coherent. Deliberately advisory: the studio still works when
 * this returns entries.
 */
export function getConfigurationWarnings(
  health: HealthStatus | null | undefined
): string[] {
  if (!health) return [];
  const warnings: string[] = [];

  if (health.auth_required && !hasApiKey) {
    warnings.push(
      `The backend at ${API_BASE_URL} requires an API key, but this build has no ` +
        "NEXT_PUBLIC_API_KEY. Every request will be rejected with 401. Set " +
        "NEXT_PUBLIC_API_KEY in frontend/.env.local to the same value as " +
        "API_ACCESS_KEY in backend/.env and restart the dev server."
    );
  }

  if (health.configured && health.configured.ai_vision === false) {
    warnings.push(
      "No GEMINI_API_KEY was loaded by the backend, so AI scene understanding " +
        "(Phase 2) is unavailable. Copy backend/.env.example to backend/.env and add " +
        "your key."
    );
  }

  if (
    health.video_provider === "kenburns" &&
    health.video_provider_setting &&
    health.video_provider_setting.toLowerCase() !== "auto" &&
    health.video_provider_setting.toLowerCase() !== "kenburns"
  ) {
    warnings.push(
      `VIDEO_PROVIDER is set to "${health.video_provider_setting}" but no usable ` +
        "credentials were found, so clips fall back to the local renderer."
    );
  }

  if (health.setup_hint) {
    warnings.push(health.setup_hint);
  }

  return warnings;
}

export const api = {
  baseUrl: API_BASE_URL,
  hasAccessKey: hasApiKey,

  async checkHealth(): Promise<HealthStatus> {
    return request<HealthStatus>("/api/health");
  },

  async createProject(name: string): Promise<Project> {
    return request<Project>("/api/projects", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name }),
    });
  },

  async getProject(projectId: string): Promise<Project> {
    return request<Project>(`/api/projects/${projectId}`);
  },

  async uploadImages(
    projectId: string,
    files: File[]
  ): Promise<ImageBatchUploadResult> {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }

    return request<ImageBatchUploadResult>(`/api/projects/${projectId}/images`, {
      method: "POST",
      body: formData,
    });
  },

  async getImages(projectId: string): Promise<ImageMetadata[]> {
    return request<ImageMetadata[]>(`/api/projects/${projectId}/images`);
  },

  async deleteImage(projectId: string, imageId: string): Promise<boolean> {
    await request<{ deleted: boolean }>(
      `/api/projects/${projectId}/images/${imageId}`,
      {
        method: "DELETE",
      }
    );
    return true;
  },

  // Phase 2 Endpoints
  async analyzeProject(
    projectId: string,
    forceReanalyze: boolean = false,
    imageIds?: string[]
  ): Promise<Project> {
    return request<Project>(`/api/projects/${projectId}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        force_reanalyze: forceReanalyze,
        image_ids: imageIds || null,
      }),
    });
  },

  async updateImageScene(
    projectId: string,
    imageId: string,
    payload: SceneCorrectionPayload
  ): Promise<ImageMetadata> {
    return request<ImageMetadata>(
      `/api/projects/${projectId}/images/${imageId}/scene`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }
    );
  },

  getImageUrl(projectId: string, imageId: string): string {
    return `${API_BASE_URL}/api/projects/${projectId}/images/${imageId}/file`;
  },

  getThumbnailUrl(projectId: string, imageId: string): string {
    return `${API_BASE_URL}/api/projects/${projectId}/images/${imageId}/thumbnail`;
  },

  getAnalysisImageUrl(projectId: string, imageId: string): string {
    return `${API_BASE_URL}/api/projects/${projectId}/images/${imageId}/analysis-file`;
  },

  // Phase 3 Endpoints: Walkthrough Planning
  async getPlan(projectId: string): Promise<import("@/types/plan").GenerationPlan> {
    return request<import("@/types/plan").GenerationPlan>(`/api/projects/${projectId}/plan`);
  },

  async rebuildPlan(projectId: string): Promise<import("@/types/plan").GenerationPlan> {
    return request<import("@/types/plan").GenerationPlan>(`/api/projects/${projectId}/plan/rebuild`, {
      method: "POST",
    });
  },

  async updatePlan(
    projectId: string,
    updatePayload: import("@/types/plan").PlanUpdateRequest
  ): Promise<import("@/types/plan").GenerationPlan> {
    return request<import("@/types/plan").GenerationPlan>(`/api/projects/${projectId}/plan`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updatePayload),
    });
  },

  // Render options: the cinematic style controls shared by Phase 4 and Phase 5.
  async getRenderPresets(): Promise<import("@/types/render-options").RenderPresetInfo[]> {
    return request<import("@/types/render-options").RenderPresetInfo[]>(
      `/api/projects/render-options/presets`
    );
  },

  async getRenderOptions(
    projectId: string
  ): Promise<import("@/types/render-options").RenderOptions> {
    return request<import("@/types/render-options").RenderOptions>(
      `/api/projects/${projectId}/render-options`
    );
  },

  async updateRenderOptions(
    projectId: string,
    payload: import("@/types/render-options").RenderOptionsUpdate
  ): Promise<import("@/types/render-options").RenderOptions> {
    return request<import("@/types/render-options").RenderOptions>(
      `/api/projects/${projectId}/render-options`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }
    );
  },

  // Phase 4 Endpoints: Video Generation
  async getGenerationOverview(
    projectId: string
  ): Promise<import("@/types/generation").ProjectGenerationOverview> {
    return request<import("@/types/generation").ProjectGenerationOverview>(
      `/api/projects/${projectId}/generation`
    );
  },

  async generateClips(
    projectId: string,
    payload?: import("@/types/generation").GenerateClipsPayload
  ): Promise<import("@/types/generation").ProjectGenerationOverview> {
    return request<import("@/types/generation").ProjectGenerationOverview>(
      `/api/projects/${projectId}/generate`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: payload ? JSON.stringify(payload) : undefined,
      }
    );
  },

  async retryJob(
    projectId: string,
    jobId: string
  ): Promise<import("@/types/generation").GenerationJob> {
    return request<import("@/types/generation").GenerationJob>(
      `/api/projects/${projectId}/generation/jobs/${jobId}/retry`,
      {
        method: "POST",
      }
    );
  },

  async regenerateSceneClip(
    projectId: string,
    sceneId: string,
    payload?: import("@/types/generation").RegenerateScenePayload
  ): Promise<import("@/types/generation").GenerationJob> {
    return request<import("@/types/generation").GenerationJob>(
      `/api/projects/${projectId}/scenes/${sceneId}/regenerate`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: payload ? JSON.stringify(payload) : undefined,
      }
    );
  },

  async createLocalSlideshow(
    projectId: string
  ): Promise<import("@/types/assembly").FinalVideoMetadata> {
    return request<import("@/types/assembly").FinalVideoMetadata>(
      `/api/projects/${projectId}/local-slideshow`,
      { method: "POST" }
    );
  },

  getClipUrl(projectId: string, sceneId: string): string {
    return `${API_BASE_URL}/api/projects/${projectId}/clips/${sceneId}/file`;
  },

  // Phase 5 Endpoints: Video Assembly & Final Walkthrough
  async assembleWalkthrough(
    projectId: string,
    payload?: import("@/types/assembly").AssemblyRequest
  ): Promise<import("@/types/assembly").AssemblyJob> {
    return request<import("@/types/assembly").AssemblyJob>(
      `/api/projects/${projectId}/assemble`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: payload ? JSON.stringify(payload) : undefined,
      }
    );
  },

  async getAssemblyStatus(
    projectId: string
  ): Promise<import("@/types/assembly").AssemblyJob | null> {
    return request<import("@/types/assembly").AssemblyJob | null>(
      `/api/projects/${projectId}/assembly`
    );
  },

  async getFinalVideoMetadata(
    projectId: string
  ): Promise<import("@/types/assembly").FinalVideoMetadata | null> {
    return request<import("@/types/assembly").FinalVideoMetadata | null>(
      `/api/projects/${projectId}/final-video`
    );
  },

  getFinalVideoUrl(projectId: string): string {
    return `${API_BASE_URL}/api/projects/${projectId}/final-video/file`;
  },

  getFinalVideoDownloadUrl(projectId: string): string {
    return `${API_BASE_URL}/api/projects/${projectId}/final-video/download`;
  },

  getSceneClipDownloadUrl(projectId: string, sceneId: string): string {
    return `${API_BASE_URL}/api/projects/${projectId}/clips/${sceneId}/download`;
  },

  // Phase 6 Endpoints: Immersive Viewing, Panorama Classification & Human Evaluation
  async updateImagePanorama(
    projectId: string,
    imageId: string,
    isPanoramic: boolean,
    panoramicType?: string
  ): Promise<import("@/types/image").ImageMetadata> {
    return request<import("@/types/image").ImageMetadata>(
      `/api/projects/${projectId}/images/${imageId}/panorama`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          is_panoramic: isPanoramic,
          panoramic_type: panoramicType,
        }),
      }
    );
  },

  async submitEvaluation(
    projectId: string,
    payload: import("@/types/evaluation").EvaluationCreate
  ): Promise<import("@/types/evaluation").EvaluationRecord> {
    return request<import("@/types/evaluation").EvaluationRecord>(
      `/api/projects/${projectId}/evaluations`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }
    );
  },

  async getEvaluations(
    projectId: string
  ): Promise<import("@/types/evaluation").EvaluationSummary> {
    return request<import("@/types/evaluation").EvaluationSummary>(
      `/api/projects/${projectId}/evaluations`
    );
  },

  async submitSceneReview(
    projectId: string,
    payload: import("@/types/evaluation").SceneReviewCreate
  ): Promise<import("@/types/evaluation").SceneReviewRecord> {
    return request<import("@/types/evaluation").SceneReviewRecord>(
      `/api/projects/${projectId}/scene-reviews`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }
    );
  },

  async getSceneReviews(
    projectId: string
  ): Promise<import("@/types/evaluation").SceneReviewRecord[]> {
    return request<import("@/types/evaluation").SceneReviewRecord[]>(
      `/api/projects/${projectId}/scene-reviews`
    );
  },

  async getTechnicalReport(
    projectId: string
  ): Promise<import("@/types/evaluation").TechnicalReport> {
    return request<import("@/types/evaluation").TechnicalReport>(
      `/api/projects/${projectId}/report`
    );
  },

  async getTechnicalReportText(projectId: string): Promise<string> {
    const url = `${API_BASE_URL}/api/projects/${projectId}/report/text`;
    // Raw fetch because the payload is plain text, but it still has to carry the
    // shared key — this route is not one of the media exemptions, so an
    // unauthenticated call 401s in any keyed deployment.
    const res = await fetch(url, {
      headers: API_ACCESS_KEY ? { "X-API-Key": API_ACCESS_KEY } : {},
    });
    if (!res.ok) {
      throw new ApiError(
        res.status === 401 ? "UNAUTHORIZED" : `HTTP_${res.status}`,
        res.status === 401
          ? `Could not download the technical report. ${unauthorizedHint()}`
          : `Could not download the technical report (HTTP ${res.status}).`
      );
    }
    return res.text();
  },

  async deleteProject(
    projectId: string,
    confirm: boolean = true
  ): Promise<{ deleted: boolean; project_id: string; message: string }> {
    return request<{ deleted: boolean; project_id: string; message: string }>(
      `/api/projects/${projectId}?confirm=${confirm}`,
      {
        method: "DELETE",
      }
    );
  },
};
