import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { PageHeader } from '../../components/layout/PageHeader';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { SystemHealthIndicator } from '../../components/common/SystemHealthIndicator';
import {
  BrainCircuit,
  PieChart,
  ShieldAlert,
  GitFork,
  ArrowRight,
  Server,
  Layers,
  Cpu,
  Database,
  History,
  TrendingUp,
  Search,
} from 'lucide-react';
import { API_BASE_URL } from '../../api/client';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      {/* Top Welcome Header */}
      <PageHeader
        title={`Welcome back, ${user?.username || 'Analyst'}`}
        subtitle="FinPilot AI Terminal — Agentic Financial Research, Quantitative Risk & Portfolio Optimization Engine"
        badge={
          <Badge variant="success" size="sm" dot>
            Production Terminal Active
          </Badge>
        }
        actions={
          <div className="flex items-center gap-3">
            <SystemHealthIndicator />
            <Button
              variant="primary"
              size="sm"
              leftIcon={<BrainCircuit className="w-4 h-4" />}
              onClick={() => navigate('/app/research')}
            >
              Ask FinPilot AI
            </Button>
          </div>
        }
      />

      {/* Architecture System Status Banner */}
      <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-cyan-950/20 border border-slate-800/90 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-start gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">
                Django REST Backend Integration
              </span>
              <Badge variant="success" size="sm">
                Configured
              </Badge>
            </div>
            <p className="text-xs text-slate-400 mt-0.5 font-mono">
              Target Base URL: <span className="text-cyan-400">{API_BASE_URL}</span>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 font-mono text-xs text-slate-300">
          <div className="px-2.5 py-1 rounded bg-slate-950/80 border border-slate-800 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>LangGraph Agents</span>
          </div>
          <div className="px-2.5 py-1 rounded bg-slate-950/80 border border-slate-800 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span>Deterministic Quant</span>
          </div>
          <div className="px-2.5 py-1 rounded bg-slate-950/80 border border-slate-800 flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-emerald-400" />
            <span>PostgreSQL + Qdrant RAG</span>
          </div>
        </div>
      </div>

      {/* Platform Pillars / Quick Navigation Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Pillar 1: AI Research */}
        <Card
          className="hover:border-cyan-500/40 transition-colors group cursor-pointer"
          onClick={() => navigate('/app/research')}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="w-9 h-9 rounded-lg bg-cyan-950/60 border border-cyan-800/40 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition-transform">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <Badge variant="info" size="sm">Active</Badge>
          </div>
          <h3 className="text-sm font-semibold text-slate-100 group-hover:text-cyan-400 transition-colors">
            AI Research Workspace
          </h3>
          <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
            Multi-agent financial synthesis: company fundamentals, market data, news & risk analysis.
          </p>
          <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-cyan-400 font-medium">
            <span>Open Research</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </Card>

        {/* Pillar 2: Portfolio Intelligence */}
        <Card
          className="hover:border-indigo-500/40 transition-colors group cursor-pointer"
          onClick={() => navigate('/app/portfolio')}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-950/60 border border-indigo-800/40 flex items-center justify-center text-indigo-400 group-hover:scale-105 transition-transform">
              <PieChart className="w-5 h-5" />
            </div>
            <Badge variant="info" size="sm">Active</Badge>
          </div>
          <h3 className="text-sm font-semibold text-slate-100 group-hover:text-indigo-400 transition-colors">
            Portfolio Management
          </h3>
          <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
            Deterministic valuation, holdings tracking, and real-time asset weight allocation.
          </p>
          <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-indigo-400 font-medium">
            <span>Manage Portfolios</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </Card>

        {/* Pillar 3: Quantitative Risk */}
        <Card
          className="hover:border-amber-500/40 transition-colors group cursor-pointer"
          onClick={() => navigate('/app/risk')}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="w-9 h-9 rounded-lg bg-amber-950/60 border border-amber-800/40 flex items-center justify-center text-amber-400 group-hover:scale-105 transition-transform">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <Badge variant="warning" size="sm">Active</Badge>
          </div>
          <h3 className="text-sm font-semibold text-slate-100 group-hover:text-amber-400 transition-colors">
            Risk & Optimization
          </h3>
          <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
            Sharpe, Sortino, VaR 95%, CVaR, Max Drawdown and mathematical target weights.
          </p>
          <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-amber-400 font-medium">
            <span>Inspect Risk</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </Card>

        {/* Pillar 4: Walk-Forward Backtest */}
        <Card
          className="hover:border-emerald-500/40 transition-colors group cursor-pointer"
          onClick={() => navigate('/app/backtest')}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition-transform">
              <GitFork className="w-5 h-5" />
            </div>
            <Badge variant="success" size="sm">Active</Badge>
          </div>
          <h3 className="text-sm font-semibold text-slate-100 group-hover:text-emerald-400 transition-colors">
            Walk-Forward Backtesting
          </h3>
          <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
            Historical strategy evaluation vs. Buy & Hold baseline and NIFTY 50 benchmark.
          </p>
          <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-emerald-400 font-medium">
            <span>Configure Backtest</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </Card>
      </div>

      {/* Main Grid: Phase A Implementation Summary & Architecture Separation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Phase A Foundation Blueprint */}
        <div className="lg:col-span-2 space-y-6">
          <Card
            title="Integrated Platform Engines"
            subtitle="Core architecture verified and connected with live Django REST API endpoints"
          >
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                  <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-1 font-mono">
                    <span className="w-2 h-2 rounded-full bg-cyan-400" />
                    Authentication Engine
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Django SimpleJWT integration with automatic 401 interceptor, token rotation, and concurrency mutex.
                  </p>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                  <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-1 font-mono">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    Centralized API Client
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Typed fetch client binding to <code className="text-cyan-300 font-mono text-[11px]">{API_BASE_URL}</code> with friendly error normalization.
                  </p>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                  <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-1 font-mono">
                    <span className="w-2 h-2 rounded-full bg-indigo-400" />
                    Application Shell
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Collapsible desktop sidebar, mobile drawer, top navigation with search trigger, and live health monitor.
                  </p>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
                  <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-1 font-mono">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    Route Structure
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Protected route hierarchy with loading fallbacks, public auth guards, and complete URL mapping.
                  </p>
                </div>
              </div>

              {/* Research CTA Box */}
              <div className="mt-4 p-4 rounded-xl bg-gradient-to-r from-cyan-950/40 via-slate-900 to-slate-900 border border-cyan-800/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div>
                  <h4 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                    <Search className="w-4 h-4 text-cyan-400" />
                    AI Financial Synthesis
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Query LangGraph multi-agent synthesis, SEC/SEBI evidence citations, and provenances.
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => navigate('/app/research')}
                >
                  Open Research Workspace
                </Button>
              </div>
            </div>
          </Card>

          {/* Quick Shortcuts */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <button
              onClick={() => navigate('/app/research/history')}
              className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 text-left transition-all cursor-pointer group"
            >
              <History className="w-4 h-4 text-cyan-400 mb-2 group-hover:scale-110 transition-transform" />
              <p className="text-xs font-semibold text-slate-200">Research History</p>
              <p className="text-[11px] text-slate-400 mt-0.5">View persisted sessions</p>
            </button>

            <button
              onClick={() => navigate('/app/markets')}
              className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 text-left transition-all cursor-pointer group"
            >
              <TrendingUp className="w-4 h-4 text-emerald-400 mb-2 group-hover:scale-110 transition-transform" />
              <p className="text-xs font-semibold text-slate-200">Market Intelligence</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Historical prices & news</p>
            </button>

            <button
              onClick={() => navigate('/app/portfolio')}
              className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 text-left transition-all cursor-pointer group"
            >
              <PieChart className="w-4 h-4 text-indigo-400 mb-2 group-hover:scale-110 transition-transform" />
              <p className="text-xs font-semibold text-slate-200">Portfolio Workspaces</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Holdings & allocation</p>
            </button>
          </div>
        </div>

        {/* Right 1 Col: Architectural Discipline & Guidelines */}
        <div className="space-y-6">
          <Card
            title="Architectural Boundary"
            subtitle="Strict frontend-backend separation"
          >
            <div className="space-y-3.5 text-xs text-slate-300">
              <div className="border-l-2 border-cyan-500 pl-3 py-0.5">
                <p className="font-semibold text-slate-100">Deterministic Python Backend</p>
                <p className="text-slate-400 mt-0.5 leading-relaxed">
                  All metrics (Sharpe, VaR, weights, backtesting) are strictly authoritative from Django.
                </p>
              </div>

              <div className="border-l-2 border-indigo-500 pl-3 py-0.5">
                <p className="font-semibold text-slate-100">LangGraph Agent Orchestration</p>
                <p className="text-slate-400 mt-0.5 leading-relaxed">
                  Financial, Market, News, and Risk agents orchestrated server-side.
                </p>
              </div>

              <div className="border-l-2 border-emerald-500 pl-3 py-0.5">
                <p className="font-semibold text-slate-100">Zero Client-Side Math Duplication</p>
                <p className="text-slate-400 mt-0.5 leading-relaxed">
                  React acts purely as an analytical presentation and interaction layer.
                </p>
              </div>

              <div className="border-l-2 border-amber-500 pl-3 py-0.5">
                <p className="font-semibold text-slate-100">No Mock Infrastructure</p>
                <p className="text-slate-400 mt-0.5 leading-relaxed">
                  Direct communication over REST to Django with SimpleJWT authentication.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
