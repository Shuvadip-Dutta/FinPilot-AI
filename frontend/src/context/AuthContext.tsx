import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { authApi } from '../api/auth';
import { AuthTokens, LoginCredentials, RegisterPayload, User } from '../types/auth';
import { storage } from '../utils/storage';

interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Safely decodes base64url encoded JWT payload
 */
function decodeJwt(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function getInitialSession(): { tokens: AuthTokens | null; user: User | null } {
  const storedTokens = storage.getTokens();
  if (!storedTokens) {
    return { tokens: null, user: null };
  }

  const payload = decodeJwt(storedTokens.access);
  if (payload) {
    const exp = typeof payload.exp === 'number' ? payload.exp * 1000 : 0;
    if (exp && exp < Date.now() && !storedTokens.refresh) {
      storage.clearAuth();
      return { tokens: null, user: null };
    }

    let storedUser = storage.getUser();
    if (!storedUser) {
      storedUser = {
        id: (payload.user_id as string | number) || (payload.id as string | number) || '1',
        username: (payload.username as string) || 'Analyst',
        email: (payload.email as string) || '',
      };
      storage.setUser(storedUser);
    }
    return { tokens: storedTokens, user: storedUser };
  }

  return { tokens: storedTokens, user: storage.getUser() };
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [initialSession] = useState(getInitialSession);
  const [tokens, setTokens] = useState<AuthTokens | null>(initialSession.tokens);
  const [user, setUser] = useState<User | null>(initialSession.user);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const logout = useCallback(() => {
    storage.clearAuth();
    setTokens(null);
    setUser(null);
    setError(null);
  }, []);

  // Listen for 401 unrecoverable refresh expiration
  useEffect(() => {
    const handleAuthExpired = () => {
      logout();
      setError('Your session has expired. Please sign in again.');
    };

    window.addEventListener('auth:expired', handleAuthExpired);
    return () => {
      window.removeEventListener('auth:expired', handleAuthExpired);
    };
  }, [logout]);

  const login = async (credentials: LoginCredentials) => {
    setError(null);
    try {
      const tokensResponse = await authApi.login(credentials);
      storage.setTokens(tokensResponse);
      setTokens(tokensResponse);

      // Extract user info from token payload or credentials
      const payload = decodeJwt(tokensResponse.access);
      const authenticatedUser: User = {
        id: (payload?.user_id as string | number) || (payload?.id as string | number) || Date.now(),
        username: (payload?.username as string) || credentials.username,
        email: (payload?.email as string) || `${credentials.username}@finpilot.ai`,
      };

      storage.setUser(authenticatedUser);
      setUser(authenticatedUser);
    } catch (err: unknown) {
      const apiErr = err as { message?: string; detail?: string };
      setError(apiErr.detail || apiErr.message || 'Invalid username or password.');
      throw err;
    }
  };

  const register = async (payload: RegisterPayload) => {
    setError(null);
    try {
      const res = await authApi.register(payload);

      // If backend directly returns tokens on register
      if (res.access && res.refresh) {
        const authTokens: AuthTokens = { access: res.access, refresh: res.refresh };
        storage.setTokens(authTokens);
        setTokens(authTokens);

        const tokenPayload = decodeJwt(res.access);
        const newUser: User = res.user || {
          id: (tokenPayload?.user_id as string | number) || '1',
          username: payload.username,
          email: payload.email,
        };
        storage.setUser(newUser);
        setUser(newUser);
      } else {
        // Backend register succeeded, now log in to acquire JWT token pair
        await login({
          username: payload.username,
          password: payload.password,
        });
      }
    } catch (err: unknown) {
      const apiErr = err as { message?: string; detail?: string };
      setError(apiErr.detail || apiErr.message || 'Registration failed. Please check your details and try again.');
      throw err;
    }
  };

  const value: AuthContextType = {
    user,
    tokens,
    isAuthenticated: Boolean(tokens?.access),
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
