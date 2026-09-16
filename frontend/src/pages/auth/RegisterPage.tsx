import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import {
  Sparkles,
  Lock,
  User,
  Mail,
  Eye,
  EyeOff,
  AlertCircle,
  Server,
  ArrowRight,
} from 'lucide-react';
import { API_BASE_URL } from '../../api/client';
import { ApiError } from '../../types/api';

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    // Client-side validations
    if (!username.trim()) {
      setError('Username is required.');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setError('Please provide a valid email address.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== passwordConfirm) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password,
        password_confirm: passwordConfirm,
      });
      navigate('/login', {
        state: {
          registered: true,
          username: username.trim(),
        },
        replace: true,
      });
    } catch (err: unknown) {
      const apiErr = err as ApiError;

      if (apiErr.isNetworkError) {
        setError('Unable to connect to the FinPilot server. Please ensure the Django backend is running at ' + API_BASE_URL);
      } else if (apiErr.errors) {
        const fieldMap: Record<string, string> = {};
        for (const [key, val] of Object.entries(apiErr.errors)) {
          fieldMap[key] = Array.isArray(val) ? val[0] : String(val);
        }
        setFieldErrors(fieldMap);

        if (apiErr.detail) {
          setError(apiErr.detail);
        } else if (apiErr.message) {
          setError(apiErr.message);
        } else {
          setError('Please review and resolve the errors highlighted below.');
        }
      } else if (apiErr.status && apiErr.status >= 500) {
        setError(`Backend server error (${apiErr.status}). Please verify the Django logs.`);
      } else if (apiErr.detail) {
        setError(apiErr.detail);
      } else if (apiErr.message) {
        setError(apiErr.message);
      } else {
        setError('Registration could not be completed. Please review your input.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-app flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Subtle background ambient glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-accent-soft/40 rounded-full blur-3xl pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center">
          <div className="w-12 h-12 rounded-2xl bg-accent-primary flex items-center justify-center shadow-xs mb-3">
            <Sparkles className="w-6 h-6 text-accent-text stroke-[2.5]" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-text-primary flex items-center gap-2">
            FINPILOT <span className="text-accent-primary font-mono text-xs font-semibold px-2 py-0.5 rounded-sm bg-accent-soft border border-accent-primary/30">AI</span>
          </h1>
          <p className="mt-1 text-xs text-text-muted font-mono">
            Create an Analyst Account
          </p>
        </div>

        {/* Register Card */}
        <div className="mt-8 bg-surface border border-border-theme rounded-2xl p-6 sm:p-8 shadow-card">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-text-primary">Register New Account</h2>
            <p className="text-xs text-text-muted mt-0.5">
              Access the LangGraph research workflows and quantitative portfolio engines.
            </p>
          </div>

          {error && (
            <div
              className="mb-5 p-3 rounded-lg bg-status-negative-soft border border-status-negative/30 flex items-start gap-2.5 text-xs text-status-negative animate-in fade-in"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 text-status-negative shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">{error}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Username"
              id="reg-username"
              type="text"
              autoComplete="username"
              required
              placeholder="e.g. quant_analyst"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              error={fieldErrors.username}
              leftIcon={<User className="w-4 h-4" />}
            />

            <Input
              label="Email Address"
              id="reg-email"
              type="email"
              autoComplete="email"
              required
              placeholder="analyst@domain.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={fieldErrors.email}
              leftIcon={<Mail className="w-4 h-4" />}
            />

            <Input
              label="Password"
              id="reg-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={fieldErrors.password}
              leftIcon={<Lock className="w-4 h-4" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="p-1 text-text-muted hover:text-text-primary focus:outline-none cursor-pointer"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              }
            />

            <Input
              label="Confirm Password"
              id="reg-password-confirm"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              required
              placeholder="••••••••"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              error={fieldErrors.password_confirm}
              leftIcon={<Lock className="w-4 h-4" />}
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
                Create Account
              </Button>
            </div>
          </form>

          <div className="mt-5 pt-4 border-t border-border-subtle text-center">
            <Link
              to="/login"
              className="text-xs text-text-muted hover:text-text-primary transition-colors"
            >
              Already have an account? <span className="text-accent-primary font-medium">Sign In</span>
            </Link>
          </div>
        </div>

        {/* Backend Target Indicator */}
        <div className="mt-6 flex items-center justify-center gap-2 text-[11px] text-text-muted font-mono">
          <Server className="w-3.5 h-3.5 text-text-muted" />
          <span>Django Auth Endpoint:</span>
          <span className="text-text-secondary bg-surface-secondary px-2 py-0.5 rounded border border-border-theme">
            {API_BASE_URL}auth/register/
          </span>
        </div>
      </div>
    </div>
  );
};
