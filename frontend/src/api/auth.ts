import { apiClient } from './client';
import { AuthTokens, LoginCredentials, RegisterPayload, User } from '../types/auth';
import { HealthResponse } from '../types/api';

export const authApi = {
  /**
   * Logs in with username and password, returning JWT access and refresh tokens
   */
  async login(credentials: LoginCredentials): Promise<AuthTokens> {
    return apiClient.post<AuthTokens>('auth/token/', credentials, { skipAuth: true });
  },

  /**
   * Registers a new account with Django REST Framework
   */
  async register(payload: RegisterPayload): Promise<{ user?: User; message?: string; detail?: string } & Partial<AuthTokens>> {
    return apiClient.post('auth/register/', payload, { skipAuth: true });
  },

  /**
   * Refreshes the JWT access token using the stored refresh token
   */
  async refresh(refreshToken: string): Promise<{ access: string; refresh?: string }> {
    return apiClient.post('auth/token/refresh/', { refresh: refreshToken }, { skipAuth: true });
  },

  /**
   * Checks the Django backend health status: GET /health/
   */
  async getHealth(): Promise<HealthResponse> {
    return apiClient.get<HealthResponse>('health/', { skipAuth: true, timeoutMs: 5000 });
  },
};
