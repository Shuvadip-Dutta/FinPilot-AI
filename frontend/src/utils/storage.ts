import { AuthTokens, User } from '../types/auth';

const ACCESS_TOKEN_KEY = 'finpilot_access_token';
const REFRESH_TOKEN_KEY = 'finpilot_refresh_token';
const USER_DATA_KEY = 'finpilot_user_data';

export const storage = {
  getAccessToken(): string | null {
    try {
      return localStorage.getItem(ACCESS_TOKEN_KEY);
    } catch {
      return null;
    }
  },

  setAccessToken(token: string): void {
    try {
      localStorage.setItem(ACCESS_TOKEN_KEY, token);
    } catch (e) {
      console.warn('Unable to store access token', e);
    }
  },

  getRefreshToken(): string | null {
    try {
      return localStorage.getItem(REFRESH_TOKEN_KEY);
    } catch {
      return null;
    }
  },

  setRefreshToken(token: string): void {
    try {
      localStorage.setItem(REFRESH_TOKEN_KEY, token);
    } catch (e) {
      console.warn('Unable to store refresh token', e);
    }
  },

  getTokens(): AuthTokens | null {
    const access = this.getAccessToken();
    const refresh = this.getRefreshToken();
    if (!access || !refresh) return null;
    return { access, refresh };
  },

  setTokens(tokens: AuthTokens): void {
    this.setAccessToken(tokens.access);
    this.setRefreshToken(tokens.refresh);
  },

  getUser(): User | null {
    try {
      const data = localStorage.getItem(USER_DATA_KEY);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },

  setUser(user: User): void {
    try {
      localStorage.setItem(USER_DATA_KEY, JSON.stringify(user));
    } catch (e) {
      console.warn('Unable to store user data', e);
    }
  },

  clearAuth(): void {
    try {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      localStorage.removeItem(USER_DATA_KEY);
    } catch (e) {
      console.warn('Unable to clear auth storage', e);
    }
  }
};
