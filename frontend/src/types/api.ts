/**
 * API types and error interfaces for Django REST Framework integration
 */

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
  errors?: Record<string, string[] | string>;
  isNetworkError?: boolean;
  isTimeout?: boolean;
}

export interface HealthResponse {
  status: 'ok' | 'healthy' | 'degraded' | 'unavailable' | string;
  service?: string;
  database?: string;
  vector_store?: string;
  version?: string;
  timestamp?: string;
  [key: string]: unknown;
}

export interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  timeoutMs?: number;
  params?: Record<string, string | number | boolean | undefined | null>;
}
