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
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
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
      navigate('/app/dashboard', { replace: true });
    } catch (err: unknown) {
      const apiErr = err as {
        message?: string;
        detail?: string;
        errors?: Record<string, string[] | string>;
      };

      if (apiErr.errors) {
        const fieldMap: Record<string, string> = {};
        for (const [key, val] of Object.entries(apiErr.errors)) {
          fieldMap[key] = Array.isArray(val) ? val[0] : String(val);
        }
        setFieldErrors(fieldMap);
      }

      if (apiErr.detail) {
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
    <div className="min-h-screen bg-[#0b0f17] flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Subtle background ambient glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

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
            Create an Analyst Account
          </p>
        </div>

        {/* Register Card */}
        <div className="mt-8 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-slate-100">Register New Account</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Access the LangGraph research workflows and quantitative portfolio engines.
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
                  className="p-1 text-slate-400 hover:text-slate-200 focus:outline-none cursor-pointer"
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

          <div className="mt-5 pt-4 border-t border-slate-800/80 text-center">
            <Link
              to="/login"
              className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              Already have an account? <span className="text-cyan-400 font-medium">Sign In</span>
            </Link>
          </div>
        </div>

        {/* Backend Target Indicator */}
        <div className="mt-6 flex items-center justify-center gap-2 text-[11px] text-slate-400 font-mono">
          <Server className="w-3.5 h-3.5 text-slate-400" />
          <span>Django Auth Endpoint:</span>
          <span className="text-slate-400 bg-slate-900/90 px-2 py-0.5 rounded border border-slate-800">
            {API_BASE_URL}auth/register/
          </span>
        </div>
      </div>
    </div>
  );
};
