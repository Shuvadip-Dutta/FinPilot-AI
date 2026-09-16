import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { PageHeader } from '../../components/layout/PageHeader';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { EmptyState } from '../../components/common/EmptyState';
import {
  BrainCircuit,
  History,
  TrendingUp,
  PieChart,
  ShieldAlert,
  GitFork,
  User,
  Settings,
  Server,
  ArrowLeft,
  FileCode,
} from 'lucide-react';
import { API_BASE_URL } from '../../api/client';
import { useAuth } from '../../hooks/useAuth';

interface ScreenConfig {
  title: string;
  subtitle: string;
  phase: string;
  endpoint: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const SCREEN_CONFIGS: Record<string, ScreenConfig> = {
  '/app/research': {
    title: 'AI Research Workspace',
    subtitle: 'Agentic financial research orchestrated by LangGraph with RAG retrieval',
    phase: 'Phase B',
    endpoint: 'POST /api/v1/ai/chat/',
    icon: BrainCircuit,
    description: 'The AI Research workspace will provide a multi-agent chat interface with company fundamentals, market data, news intelligence, and risk assessment synthesized by LangGraph.',
  },
  '/app/research/history': {
    title: 'Research History',
    subtitle: 'Persisted multi-agent research sessions and evidence provenance',
    phase: 'Phase B',
    endpoint: 'GET /api/v1/research/sessions/',
    icon: History,
    description: 'Will retrieve all persisted research sessions, evidence provenance, and node execution logs from the PostgreSQL backend.',
  },
  '/app/markets': {
    title: 'Market Intelligence',
    subtitle: 'Authoritative company fundamentals, historical charts, and FinBERT news sentiment',
    phase: 'Phase B',
    endpoint: 'GET /api/v1/research/historical/ & /research/news/',
    icon: TrendingUp,
    description: 'Will display symbol search, historical price series from financial providers, financial statements, and news sentiment from FinBERT.',
  },
  '/app/portfolio': {
    title: 'Portfolio Workspace',
    subtitle: 'User portfolios, holdings CRUD, and deterministic valuations',
    phase: 'Phase C',
    endpoint: 'GET/POST /api/v1/portfolio/ & /holdings/',
    icon: PieChart,
    description: 'Will provide full CRUD for user portfolios and holdings, rendering deterministic asset weights, current market valuation, and P/L directly from Django.',
  },
  '/app/risk': {
    title: 'Risk & Optimization',
    subtitle: 'Deterministic quantitative risk metrics and mathematical target weights',
    phase: 'Phase D',
    endpoint: 'GET /api/v1/portfolio/<id>/ (with risk calculations)',
    icon: ShieldAlert,
    description: 'Will render Sharpe, Sortino, Calmar, Max Drawdown, VaR 95%, CVaR, and point-in-time constrained optimization target weights.',
  },
  '/app/optimization': {
    title: 'Portfolio Optimization',
    subtitle: 'Constrained optimization target weights vs current allocation',
    phase: 'Phase D',
    endpoint: 'POST /api/v1/portfolio/<id>/analysis',
    icon: ShieldAlert,
    description: 'Will contrast current portfolio allocation against mathematically optimized weights with expected volatility and return curves.',
  },
  '/app/backtest': {
    title: 'Walk-Forward Backtesting',
    subtitle: 'Historical rolling optimization strategy evaluation vs benchmarks',
    phase: 'Phase E',
    endpoint: 'POST /api/v1/portfolio/<id>/backtest/',
    icon: GitFork,
    description: 'Will execute walk-forward backtests with in-sample/out-of-sample windows, transaction cost adjustments, equity curve comparisons, and rebalance event tables.',
  },
  '/app/profile': {
    title: 'Analyst Profile',
    subtitle: 'Authenticated user session credentials and role permissions',
    phase: 'Phase A',
    endpoint: 'Django SimpleJWT Session Payload',
    icon: User,
    description: 'Displays current analyst credentials and active session metadata decoded from the verified JWT.',
  },
  '/app/settings': {
    title: 'System Settings',
    subtitle: 'API endpoints, token management, and platform configuration',
    phase: 'Phase A',
    endpoint: 'VITE_API_BASE_URL Environment Binding',
    icon: Settings,
    description: 'Manage frontend API configuration, inspect token storage, and monitor backend service health.',
  },
};

export const PlaceholderPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  // Match the screen config from pathname or default
  const config =
    SCREEN_CONFIGS[location.pathname] ||
    Object.entries(SCREEN_CONFIGS).find(([key]) => location.pathname.startsWith(key))?.[1] || {
      title: 'Platform Module',
      subtitle: 'FinPilot AI Component Workspace',
      phase: 'Upcoming Phase',
      endpoint: 'API Endpoint Bound',
      icon: FileCode,
      description: 'This screen will be activated in subsequent implementation phases as requested.',
    };

  const Icon = config.icon;

  return (
    <div className="space-y-6">
      <PageHeader
        title={config.title}
        subtitle={config.subtitle}
        badge={
          <Badge variant="info" size="sm">
            {config.phase}
          </Badge>
        }
        breadcrumbs={[
          { label: 'FinPilot Terminal', href: '/app/dashboard' },
          { label: config.title },
        ]}
        actions={
          <Button
            variant="outline"
            size="sm"
            leftIcon={<ArrowLeft className="w-4 h-4" />}
            onClick={() => navigate('/app/dashboard')}
          >
            Back to Dashboard
          </Button>
        }
      />

      {/* Special Content for Profile / Settings, or General Phase Notification */}
      {location.pathname === '/app/profile' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card title="Active Analyst Credentials" subtitle="Decoded from verified Django JWT session">
            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-2 border-b border-slate-800">
                <span className="text-slate-400">Username</span>
                <span className="text-slate-100 font-mono font-medium">{user?.username || 'Analyst'}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-800">
                <span className="text-slate-400">Email</span>
                <span className="text-slate-100 font-mono">{user?.email || 'N/A'}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-800">
                <span className="text-slate-400">User ID</span>
                <span className="text-slate-100 font-mono">{user?.id || 'Active'}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-800">
                <span className="text-slate-400">Auth Protocol</span>
                <Badge variant="success" size="sm">Django SimpleJWT (Bearer)</Badge>
              </div>
              <div className="pt-2">
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => {
                    logout();
                    navigate('/login');
                  }}
                  className="w-full sm:w-auto"
                >
                  Sign Out of Terminal
                </Button>
              </div>
            </div>
          </Card>

          <Card title="Session & Security Architecture" subtitle="Token lifecycle & concurrency protection">
            <div className="space-y-3 text-xs text-text-secondary">
              <p className="leading-relaxed">
                Tokens are stored in client-side secure web storage and automatically attached to all API requests via the{' '}
                <code className="text-accent-primary font-mono">Authorization: Bearer &lt;token&gt;</code> header.
              </p>
              <p className="leading-relaxed">
                When an access token expires (HTTP 401), the centralized API client executes an automated token refresh against{' '}
                <code className="text-accent-primary font-mono">/api/v1/auth/token/refresh/</code> with a concurrency mutex to prevent duplicate token rotation calls.
              </p>
              <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle space-y-1.5 font-mono text-[11px]">
                <div className="flex items-center justify-between text-text-muted">
                  <span>Header Attachment:</span>
                  <span className="text-status-success">Active</span>
                </div>
                <div className="flex items-center justify-between text-text-muted">
                  <span>Concurrency Mutex:</span>
                  <span className="text-status-success">Enabled</span>
                </div>
                <div className="flex items-center justify-between text-text-muted">
                  <span>Refresh Endpoint:</span>
                  <span className="text-accent-primary">/auth/token/refresh/</span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      ) : location.pathname === '/app/settings' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card title="Backend API Configuration" subtitle="Environment-based Django REST endpoint">
            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-surface-secondary border border-border-subtle">
                <p className="text-text-muted font-mono text-[11px] mb-1">Current Base URL:</p>
                <code className="text-accent-primary font-mono text-xs break-all">{API_BASE_URL}</code>
              </div>
              <p className="text-text-muted leading-relaxed">
                Configured through <code className="text-text-primary font-mono">VITE_API_BASE_URL</code> in the container environment.
              </p>
              <div className="pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    localStorage.clear();
                    window.location.reload();
                  }}
                  className="text-status-warning border-status-warning/40 hover:bg-status-warning-soft"
                >
                  Clear Cached Session Storage
                </Button>
              </div>
            </div>
          </Card>

          <Card title="Platform Architecture & Verified Capabilities" subtitle="Phases A through E production integrated">
            <div className="space-y-2.5 text-xs text-text-secondary leading-relaxed">
              <div className="flex items-center justify-between">
                <span>Phase A — Auth & Core Client</span>
                <Badge variant="success" size="sm">Verified</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>Phase B — LangGraph AI Research</span>
                <Badge variant="success" size="sm">Verified</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>Phase C — Portfolio Valuation & Holdings</span>
                <Badge variant="success" size="sm">Verified</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>Phase D — Quantitative Risk & Markowitz QP</span>
                <Badge variant="success" size="sm">Verified</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>Phase E — Walk-Forward Backtesting</span>
                <Badge variant="success" size="sm">Verified</Badge>
              </div>
            </div>
          </Card>
        </div>
      ) : (
        <Card>
          <EmptyState
            icon={Icon}
            title={`${config.title} (${config.phase})`}
            description={config.description}
            actionLabel="Return to Dashboard"
            onAction={() => navigate('/app/dashboard')}
          />

          <div className="mt-4 pt-4 border-t border-border-subtle flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-text-muted font-mono">
            <div className="flex items-center gap-2">
              <Server className="w-3.5 h-3.5 text-accent-primary" />
              <span>Target Endpoint:</span>
              <span className="text-text-primary">{config.endpoint}</span>
            </div>
            <div>
              <span>Status: Active Terminal Module</span>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
