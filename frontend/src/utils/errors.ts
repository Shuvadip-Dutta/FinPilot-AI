import { ApiError } from '../types/api';

/**
 * Standard friendly fallback messages for HTTP status codes
 */
const STATUS_MESSAGES: Record<number, string> = {
  400: 'Please review your input.',
  401: 'Your session has expired. Please sign in again.',
  403: 'You do not have permission to access this resource.',
  404: 'Resource not found.',
  409: 'A conflict occurred with the current state of the resource.',
  422: 'Unable to process the submitted data.',
  429: 'Too many requests. Please try again shortly.',
  500: 'FinPilot could not complete this request right now.',
  502: 'FinPilot could not complete this request right now (Bad Gateway).',
  503: 'FinPilot service is currently unavailable. Please try again soon.',
  504: 'FinPilot request timed out at gateway.',
};

/**
 * Normalizes any error (Response, network error, or unexpected payload) into a clean ApiError object
 */
export async function parseApiError(response: Response): Promise<ApiError> {
  const status = response.status;
  let parsedJson: unknown = null;

  try {
    const text = await response.text();
    if (text) {
      parsedJson = JSON.parse(text);
    }
  } catch {
    // Response was not JSON
  }

  let detail: string | undefined;
  const errors: Record<string, string[] | string> = {};

  if (parsedJson && typeof parsedJson === 'object') {
    const data = parsedJson as Record<string, unknown>;

    // Handle Django standard error shapes
    if (typeof data.detail === 'string') {
      detail = data.detail;
    } else if (typeof data.message === 'string') {
      detail = data.message;
    } else if (typeof data.error === 'string') {
      detail = data.error;
    }

    // Handle DRF serializer validation errors: { field: ["Error 1", "Error 2"], non_field_errors: [...] }
    for (const [key, value] of Object.entries(data)) {
      if (Array.isArray(value)) {
        errors[key] = value.map(v => String(v));
      } else if (typeof value === 'string') {
        errors[key] = value;
      }
    }

    // Extract first error message if no explicit detail found
    if (!detail) {
      if (Array.isArray(data.non_field_errors) && data.non_field_errors.length > 0) {
        detail = String(data.non_field_errors[0]);
      } else {
        const firstField = Object.keys(errors)[0];
        if (firstField) {
          const val = errors[firstField];
          const errorMsg = Array.isArray(val) ? val[0] : val;
          detail = `${firstField.replace(/_/g, ' ')}: ${errorMsg}`;
        }
      }
    }
  }

  const defaultMessage =
    status >= 500
      ? 'FinPilot could not complete this request right now.'
      : STATUS_MESSAGES[status] || `Request failed with status code ${status}.`;

  return {
    status,
    message: detail || defaultMessage,
    detail,
    errors: Object.keys(errors).length > 0 ? errors : undefined,
    isNetworkError: false,
    isTimeout: false,
  };
}

/**
 * Creates an ApiError for client-side network failures or timeouts
 */
export function createClientError(type: 'network' | 'timeout' | 'generic', error?: unknown): ApiError {
  if (type === 'timeout') {
    return {
      status: 0,
      message: 'The request timed out. Please check your connection and try again.',
      isTimeout: true,
    };
  }

  if (type === 'network') {
    return {
      status: 0,
      message: 'Unable to connect to the FinPilot server. Please ensure the Django backend is running at http://127.0.0.1:8000.',
      isNetworkError: true,
    };
  }

  const message = error instanceof Error ? error.message : 'An unexpected error occurred.';
  return {
    status: 0,
    message,
  };
}
