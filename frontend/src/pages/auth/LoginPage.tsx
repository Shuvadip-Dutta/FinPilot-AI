import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import {
  Sparkles,
  Lock,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  Server,
  ArrowRight,
} from 'lucide-react';
import { API_BASE_URL } from '../../api/client';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const stateFrom = (location.state as { from?: { pathname?: string } | string })?.from;
  const targetRoute =
    typeof stateFrom === 'string'
      ? stateFrom
      : stateFrom?.pathname || '/app/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Please enter both username and password.');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await login({ username: username.trim(), password });
      navigate(targetRoute, { replace: true });
    } catch (err: unknown) {
      const apiErr = err as {
        status?: number;
        message?: string;
        detail?: string;
        isNetworkError?: boolean;
      };

      if (apiErr.status === 401) {
        setError(apiErr.detail || apiErr.message || 'Invalid username or password. Please verify your credentials.');
      } else if (apiErr.status === 400) {
        setError(apiErr.detail || apiErr.message || 'Invalid request. Please review your credentials.');
      } else if (apiErr.status && apiErr.status >= 500) {
        setError(`Backend server error (${apiErr.status}). Please verify the Django logs.`);
      } else {
        setError(
          apiErr.message ||
          apiErr.detail ||
          'Authentication failed. Please check your credentials or verify the Django backend is running.'
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoFill = () => {
    setUsername('analyst');
    setPassword('finpilot2025');
  };

  return (
    <div className="min-h-screen bg-[#0b0f17] flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Subtle background ambient glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-10 right-1/4 w-80 h-80 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 mb-3">
            <Sparkles className="w-6 h-6 text-slate-950 stroke-[2.5]" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
            FINPILOT <span className="text-cyan-400 font-mono text-xs font-semibold px-2 py-0.5 rounded-sm bg-cyan-950/80 border border-cyan-800/50">AI</span>
          </h1>
          <p className="mt-1 text-xs text-slate-400 font-mono">
            Agentic Financial Research & Portfolio Intelligence
          </p>
        </div>

        {/* Login Card */}
        <div className="mt-8 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-slate-100">Sign in to Terminal</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Enter your credentials to access research models and portfolio engines.
            </p>
          </div>

          {error && (
            <div
              className="mb-5 p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300 animate-in fade-in"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">{error}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Username"
              id="username"
              type="text"
              autoComplete="username"
              required
              placeholder="e.g. analyst or shuvadip"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              leftIcon={<User className="w-4 h-4" />}
            />

            <Input
              label="Password"
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              leftIcon={<Lock className="w-4 h-4" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="p-1 text-slate-400 hover:text-slate-200 focus:outline-none cursor-pointer"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              }
            />

            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                size="md"
                className="w-full font-semibold"
                isLoading={isLoading}
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Sign In
              </Button>
            </div>
          </form>

          {/* Quick Demo Pre-fill Button for development convenience */}
          <div className="mt-4 pt-4 border-t border-slate-800/80 flex items-center justify-between">
            <button
              type="button"
              onClick={handleDemoFill}
              className="text-[11px] text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <span>Quick fill sample credentials</span>
            </button>

            <Link
              to="/register"
              className="text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
            >
              Don&apos;t have an account? <span className="text-cyan-400 font-medium">Register</span>
            </Link>
          </div>
        </div>

        {/* Backend Target Indicator */}
        <div className="mt-6 flex items-center justify-center gap-2 text-[11px] text-slate-400 font-mono">
          <Server className="w-3.5 h-3.5 text-slate-400" />
          <span>Django REST Endpoint:</span>
          <span className="text-slate-400 bg-slate-900/90 px-2 py-0.5 rounded border border-slate-800">
            {API_BASE_URL}
          </span>
        </div>
      </div>
    </div>
  );
};
