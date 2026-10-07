export interface ErrorDetail {
  code: string;
  message: string;
  details?: unknown;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ErrorDetail | null;
}

/** Per-provider configuration flags reported by `GET /api/health`. */
export interface HealthConfiguration {
  ai_vision?: boolean;
  any_remote_video_provider?: boolean;
  magic_hour?: boolean;
  json2video?: boolean;
  json2video_source_url?: boolean;
}

/**
 * `GET /api/health`.
 *
 * This endpoint is exempt from the API-key guard, so the studio can always read it
 * — including when the key is wrong, which is exactly when the extra fields below
 * matter. It never contains secret *values*, only which providers are configured.
 */
export interface HealthStatus {
  status: string;
  service: string;
  version?: string;
  /** Provider actually selected by the current configuration (`kenburns`, `magic_hour`, …). */
  video_provider?: string;
  /** Raw `VIDEO_PROVIDER` setting, before alias resolution. */
  video_provider_setting?: string;
  fallback_to_local?: boolean;
  /** True when the backend will reject requests without `X-API-Key`. */
  auth_required?: boolean;
  /** Environment files the backend actually loaded, as repo-relative names. */
  env_files?: string[];
  storage_dir?: string;
  is_serverless?: boolean;
  configured?: HealthConfiguration;
  /** Present only when the backend found no environment file at all. */
  setup_hint?: string;
}
