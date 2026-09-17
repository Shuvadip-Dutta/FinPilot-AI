import { ApiError, RequestOptions } from '../types/api';
import { TokenRefreshResponse } from '../types/auth';
import { createClientError, parseApiError } from '../utils/errors';
import { storage } from '../utils/storage';

// Base API URL from environment variable or fallback to specified default
const RAW_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || 'http://127.0.0.1:8000/api/v1/';
export const API_BASE_URL = RAW_BASE_URL.endsWith('/') ? RAW_BASE_URL : `${RAW_BASE_URL}/`;

// Token refresh mutex state to prevent race conditions across concurrent requests
let isRefreshing = false;
let refreshSubscribers: Array<(newToken: string | null) => void> = [];

function onRefreshed(token: string | null) {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
}

function addRefreshSubscriber(callback: (token: string | null) => void) {
  refreshSubscribers.push(callback);
}

/**
 * Executes a token refresh request to the Django SimpleJWT endpoint: POST /auth/token/refresh/
 */
async function performTokenRefresh(): Promise<string | null> {
  const refreshToken = storage.getRefreshToken();
  if (!refreshToken) {
    storage.clearAuth();
    return null;
  }

  try {
    const refreshUrl = `${API_BASE_URL}auth/token/refresh/`;
    const response = await fetch(refreshUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!response.ok) {
      storage.clearAuth();
      return null;
    }

    const data: TokenRefreshResponse = await response.json();
    if (data.access) {
      storage.setAccessToken(data.access);
      if (data.refresh) {
        storage.setRefreshToken(data.refresh);
      }
      window.dispatchEvent(
        new CustomEvent('auth:token-refreshed', { detail: { access: data.access } })
      );
      return data.access;
    }
    storage.clearAuth();
    return null;
  } catch (error) {
    console.error('Failed to refresh authentication token:', error);
    storage.clearAuth();
    return null;
  }
}

/**
 * Core HTTP Request Client
 */
async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { skipAuth = false, timeoutMs = 30000, params, ...fetchOptions } = options;

  // Build full URL
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  let url = `${API_BASE_URL}${cleanEndpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
  }

  // Build request headers
  const headers = new Headers(fetchOptions.headers || {});
  if (!headers.has('Content-Type') && !(fetchOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Attach access token if not skipped
  if (!skipAuth) {
    const accessToken = storage.getAccessToken();
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`);
    }
  }

  // Setup abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    // Handle 401 Unauthorized (attempt token refresh and retry)
    if (
      response.status === 401 &&
      !skipAuth &&
      !endpoint.includes('auth/token') &&
      !endpoint.includes('auth/register')
    ) {
      const refreshToken = storage.getRefreshToken();
      if (!refreshToken) {
        storage.clearAuth();
        throw await parseApiError(response);
      }

      if (!isRefreshing) {
        isRefreshing = true;
        const newAccessToken = await performTokenRefresh();
        isRefreshing = false;
        onRefreshed(newAccessToken);

        if (!newAccessToken) {
          // Refresh failed, user must log in again
          window.dispatchEvent(new CustomEvent('auth:expired'));
          throw await parseApiError(response);
        }

        // Retry original request with new token
        headers.set('Authorization', `Bearer ${newAccessToken}`);
        const retryResponse = await fetch(url, {
          ...fetchOptions,
          headers,
        });

        if (!retryResponse.ok) {
          throw await parseApiError(retryResponse);
        }

        if (retryResponse.status === 204) {
          return null as T;
        }
        return (await retryResponse.json()) as T;
      }

      // If already refreshing, queue this request until refresh completes
      return new Promise<T>((resolve, reject) => {
        addRefreshSubscriber(async (newToken) => {
          if (!newToken) {
            reject({
              status: 401,
              message: 'Session expired. Please sign in again.',
            } as ApiError);
            return;
          }

          try {
            headers.set('Authorization', `Bearer ${newToken}`);
            const retryResponse = await fetch(url, {
              ...fetchOptions,
              headers,
            });

            if (!retryResponse.ok) {
              reject(await parseApiError(retryResponse));
              return;
            }

            if (retryResponse.status === 204) {
              resolve(null as T);
              return;
            }

            resolve((await retryResponse.json()) as T);
          } catch (err) {
            reject(createClientError('network', err));
          }
        });
      });
    }

    if (!response.ok) {
      throw await parseApiError(response);
    }

    // 204 No Content
    if (response.status === 204) {
      return null as T;
    }

    return (await response.json()) as T;
  } catch (error: unknown) {
    clearTimeout(timeoutId);

    if (error && typeof error === 'object' && 'status' in error) {
      throw error as ApiError;
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw createClientError('timeout');
    }

    if (error instanceof TypeError) {
      throw createClientError('network', error);
    }

    throw createClientError('generic', error);
  }
}

/**
 * Public HTTP Client Methods
 */
export const apiClient = {
  get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return request<T>(endpoint, { ...options, method: 'GET' });
  },

  post<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>(endpoint, {
      ...options,
      method: 'POST',
      body:
        body !== undefined
          ? body instanceof FormData
            ? body
            : JSON.stringify(body)
          : undefined,
    });
  },

  put<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body:
        body !== undefined
          ? body instanceof FormData
            ? body
            : JSON.stringify(body)
          : undefined,
    });
  },

  patch<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body:
        body !== undefined
          ? body instanceof FormData
            ? body
            : JSON.stringify(body)
          : undefined,
    });
  },

  delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return request<T>(endpoint, { ...options, method: 'DELETE' });
  },

  getBaseUrl(): string {
    return API_BASE_URL;
  },
};
