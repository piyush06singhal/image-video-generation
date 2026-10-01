import { ApiResponse, HealthStatus } from "@/types/api";
import { ImageBatchUploadResult, ImageMetadata } from "@/types/image";
import { Project } from "@/types/project";
import { SceneCorrectionPayload } from "@/types/scene";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

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

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
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
      throw new ApiError(code, message, json.error?.details);
    }

    return json.data as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network or connection failure
    throw new ApiError(
      "SERVER_UNAVAILABLE",
      "Unable to connect to the backend server. Please verify that FastAPI is running on " +
        API_BASE_URL
    );
  }
}

export const api = {
  baseUrl: API_BASE_URL,

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
};

