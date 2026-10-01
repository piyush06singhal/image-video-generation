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

export interface HealthStatus {
  status: string;
  service: string;
}
