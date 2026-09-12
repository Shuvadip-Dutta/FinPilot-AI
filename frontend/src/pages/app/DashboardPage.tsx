import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { PageHeader } from '../../components/layout/PageHeader';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { SystemHealthIndicator } from '../../components/common/SystemHealthIndicator';
import { EmptyState } from '../../components/common/EmptyState';
import { LoadingSkeleton, TableRowSkeleton } from '../../components/common/LoadingSkeleton';
import { portfolioApi } from '../../api/portfolio';
import { researchApi } from '../../api/research';
import { documentsApi } from '../../api/documents';
import { Portfolio, Holding } from '../../types/portfolio';
import { ResearchSession } from '../../types/research';
import { FinancialDocument } from '../../types/documents';
import { formatCurrency, formatPercent, formatDate } from '../../utils/formatters';
import {
  BrainCircuit,
  PieChart,
  ShieldAlert,
  GitFork,
  ArrowRight,
  Database,
  History,
  FileText,
  AlertCircle,
  RefreshCw,
  Wallet,
  Globe,
  CheckCircle2,
  Clock,
  AlertTriangle,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Primary Data State
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [researchSessions, setResearchSessions] = useState<ResearchSession[]>([]);
  const [documents, setDocuments] = useState<FinancialDocument[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Partial Failure Error States
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [researchError, setResearchError] = useState<string | null>(null);
  const [documentsError, setDocumentsError] = useState<string | null>(null);

  // Parallel Fetch across authoritative endpoints
  const fetchDashboardData = useCallback(async () => {
    setIsLoading(true);
    setPortfolioError(null);
    setResearchError(null);
    setDocumentsError(null);

    const [portfolioRes, researchRes, documentsRes] = await Promise.allSettled([
      portfolioApi.getPortfolios(),
      researchApi.getSessions(),
      documentsApi.getDocuments(),
    ]);

    // 1. Process Portfolio Data
    if (portfolioRes.status === 'fulfilled') {
      setPortfolios(Array.isArray(portfolioRes.value) ? portfolioRes.value : []);
    } else {
      setPortfolioError(portfolioRes.reason?.message || 'Failed to load portfolio metrics.');
    }

    // 2. Process Research History
    if (researchRes.status === 'fulfilled') {
      setResearchSessions(Array.isArray(researchRes.value) ? researchRes.value : []);
    } else {
      setResearchError(researchRes.reason?.message || 'Failed to load research history.');
    }

    // 3. Process RAG Documents
    if (documentsRes.status === 'fulfilled') {
      setDocuments(Array.isArray(documentsRes.value) ? documentsRes.value : []);
    } else {
      setDocumentsError(documentsRes.reason?.message || 'Failed to load document corpus.');
    }

    setIsLoading(false);
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Aggregate Holdings across all user portfolios
  const allHoldings = useMemo(() => {
    const list: Array<Holding & { portfolioName: string; portfolioId: string }> = [];
    portfolios.forEach((p) => {
      (p.holdings || []).forEach((h) => {
        list.push({
          ...h,
          portfolioName: p.name,
          portfolioId: p.id,
        });
      });
    });
    return list;
  }, [portfolios]);

  // KPI 1: Total Invested Capital (sum of qty * avg_price)
  const totalInvestedCapital = useMemo(() => {
    return allHoldings.reduce((sum, h) => {
      const qty = typeof h.quantity === 'string' ? parseFloat(h.quantity) : (h.quantity || 0);
      const avg = typeof h.average_price === 'string' ? parseFloat(h.average_price) : (h.average_price || 0);
      return sum + (isNaN(qty) || isNaN(avg) ? 0 : qty * avg);
    }, 0);
  }, [allHoldings]);

  // KPI 2: Active Portfolios Count
  const activePortfoliosCount = portfolios.length;

  // KPI 3: Total Research Sessions Count
  const totalResearchCount = researchSessions.length;

  // KPI 4: RAG Indexed Chunks (sum of chunk_count for COMPLETED documents)
  const totalIndexedChunks = useMemo(() => {
    return documents.reduce((sum, doc) => {
      if (doc.ingestion_status === 'COMPLETED') {
        return sum + (doc.chunk_count || 0);
      }
      return sum;
    }, 0);
  }, [documents]);

  // Top Holdings ranked by invested value
  const topHoldings = useMemo(() => {
    const holdingsWithVal = allHoldings.map((h) => {
      const qty = typeof h.quantity === 'string' ? parseFloat(h.quantity) : (h.quantity || 0);
      const avg = typeof h.average_price === 'string' ? parseFloat(h.average_price) : (h.average_price || 0);
      const invested = isNaN(qty) || isNaN(avg) ? 0 : qty * avg;
      const alloc = totalInvestedCapital > 0 ? (invested / totalInvestedCapital) * 100 : 0;
      return {
        ...h,
        investedValue: invested,
        allocationPercentage: alloc,
        parsedQty: qty,
        parsedAvg: avg,
      };
    });

    return holdingsWithVal.sort((a, b) => b.investedValue - a.investedValue).slice(0, 5);
  }, [allHoldings, totalInvestedCapital]);

  // Market Exposure Breakdown (IN vs US based on invested capital)
  const marketExposure = useMemo(() => {
    let inTotal = 0;
    let usTotal = 0;
    allHoldings.forEach((h) => {
      const qty = typeof h.quantity === 'string' ? parseFloat(h.quantity) : (h.quantity || 0);
      const avg = typeof h.average_price === 'string' ? parseFloat(h.average_price) : (h.average_price || 0);
      const val = isNaN(qty) || isNaN(avg) ? 0 : qty * avg;
      if (h.market === 'US') {
        usTotal += val;
      } else {
        inTotal += val;
      }
    });

    const total = inTotal + usTotal;
    return {
      inAmount: inTotal,
      usAmount: usTotal,
      inPercent: total > 0 ? (inTotal / total) * 100 : 0,
      usPercent: total > 0 ? (usTotal / total) * 100 : 0,
      total,
    };
  }, [allHoldings]);

  // Latest 4 Research Sessions
  const recentSessions = useMemo(() => {
    return [...researchSessions]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 4);
  }, [researchSessions]);

  // Latest 4 Financial Documents
  const recentDocuments = useMemo(() => {
    return [...documents]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 4);
  }, [documents]);

  const getDocStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <Badge variant="success" size="sm" className="font-mono flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            Indexed
          </Badge>
        );
      case 'FAILED':
        return (
          <Badge variant="danger" size="sm" className="font-mono flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Failed
          </Badge>
        );
      case 'PROCESSING':
      case 'PENDING':
        return (
          <Badge variant="warning" size="sm" className="font-mono flex items-center gap-1 animate-pulse">
            <Clock className="w-3 h-3" />
            Processing
          </Badge>
        );
      default:
        return <Badge variant="neutral" size="sm">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Welcome Header */}
      <PageHeader
        title={`Welcome back, ${user?.username || 'Analyst'}`}
        subtitle="Executive Dashboard — Dynamic Financial Research, Portfolio Intelligence & Grounded RAG Corpus"
        badge={
          <Badge variant="success" size="sm" dot>
            Production Terminal Active
          </Badge>
        }
        actions={
          <div className="flex items-center gap-3">
            <SystemHealthIndicator />
            <Button
              variant="outline"
              size="sm"
              onClick={fetchDashboardData}
              disabled={isLoading}
              className="flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
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

      {/* PHASE 2: Dynamic KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Total Invested Capital */}
        <Card className="p-4 bg-slate-900/70 border-slate-800">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Total Invested Capital
            </div>
            <Wallet className="w-4 h-4 text-cyan-400" />
          </div>
          {isLoading ? (
            <div className="mt-2 space-y-1.5">
              <LoadingSkeleton className="h-7 w-28 rounded" />
              <LoadingSkeleton className="h-3 w-36 rounded" />
            </div>
          ) : (
            <div className="mt-2">
              <span className="text-2xl font-bold text-white font-mono">
                {formatCurrency(totalInvestedCapital, 'INR', { compact: true })}
              </span>
              <p className="text-xs text-slate-400 mt-0.5">
                Across {allHoldings.length} total holdings
              </p>
            </div>
          )}
        </Card>

        {/* KPI 2: Active Portfolios */}
        <Card className="p-4 bg-slate-900/70 border-slate-800">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Active Portfolios
            </div>
            <PieChart className="w-4 h-4 text-indigo-400" />
          </div>
          {isLoading ? (
            <div className="mt-2 space-y-1.5">
              <LoadingSkeleton className="h-7 w-16 rounded" />
              <LoadingSkeleton className="h-3 w-32 rounded" />
            </div>
          ) : (
            <div className="mt-2">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white font-mono">
                  {activePortfoliosCount}
                </span>
                <span className="text-xs text-slate-400">
                  workspaces
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic tracking
              </p>
            </div>
          )}
        </Card>

        {/* KPI 3: Research Sessions */}
        <Card className="p-4 bg-slate-900/70 border-slate-800">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Research Sessions
            </div>
            <History className="w-4 h-4 text-emerald-400" />
          </div>
          {isLoading ? (
            <div className="mt-2 space-y-1.5">
              <LoadingSkeleton className="h-7 w-16 rounded" />
              <LoadingSkeleton className="h-3 w-32 rounded" />
            </div>
          ) : (
            <div className="mt-2">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white font-mono">
                  {totalResearchCount}
                </span>
                <span className="text-xs text-slate-400">
                  syntheses
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Multi-agent LangGraph logs
              </p>
            </div>
          )}
        </Card>

        {/* KPI 4: RAG Indexed Chunks */}
        <Card className="p-4 bg-slate-900/70 border-slate-800">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              RAG Indexed Chunks
            </div>
            <Database className="w-4 h-4 text-amber-400" />
          </div>
          {isLoading ? (
            <div className="mt-2 space-y-1.5">
              <LoadingSkeleton className="h-7 w-16 rounded" />
              <LoadingSkeleton className="h-3 w-32 rounded" />
            </div>
          ) : (
            <div className="mt-2">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white font-mono">
                  {totalIndexedChunks}
                </span>
                <span className="text-xs text-slate-400">
                  dense vectors
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                From {documents.length} financial filings
              </p>
            </div>
          )}
        </Card>
      </div>

      {/* Main Analytical Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Portfolio Intelligence, Asset Allocation & Market Exposure */}
        <div className="lg:col-span-2 space-y-6">
          {/* Card: Portfolio Holdings & Allocation */}
          <Card
            title="Portfolio Holdings & Allocation"
            subtitle="Authoritative invested capital distribution across assets and international markets"
            action={
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/app/portfolio')}
                className="text-xs"
              >
                Manage Portfolios
              </Button>
            }
          >
            {portfolioError ? (
              <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg flex items-start gap-2 text-xs text-rose-300">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>{portfolioError}</div>
              </div>
            ) : isLoading ? (
              <div className="space-y-3 py-2">
                <TableRowSkeleton columns={5} />
                <TableRowSkeleton columns={5} />
                <TableRowSkeleton columns={5} />
              </div>
            ) : allHoldings.length === 0 ? (
              <EmptyState
                icon={PieChart}
                title="No Portfolio Holdings"
                description="Create your first portfolio and add stock holdings to inspect invested capital and asset weight distribution."
                actionLabel="Create Portfolio"
                onAction={() => navigate('/app/portfolio')}
              />
            ) : (
              <div className="space-y-5">
                {/* PHASE 4: Market Exposure Bar */}
                <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5 font-semibold text-slate-200">
                      <Globe className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Market Exposure</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs font-mono">
                      <span className="text-cyan-400">
                        IN: {formatPercent(marketExposure.inPercent, false)} ({formatCurrency(marketExposure.inAmount, 'INR', { compact: true })})
                      </span>
                      <span className="text-indigo-400">
                        US: {formatPercent(marketExposure.usPercent, false)} ({formatCurrency(marketExposure.usAmount, 'INR', { compact: true })})
                      </span>
                    </div>
                  </div>

                  {/* Dual-tone allocation progress bar */}
                  <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden flex">
                    <div
                      className="h-full bg-cyan-500 transition-all duration-500"
                      style={{ width: `${marketExposure.inPercent}%` }}
                      title={`India (IN): ${marketExposure.inPercent.toFixed(1)}%`}
                    />
                    <div
                      className="h-full bg-indigo-500 transition-all duration-500"
                      style={{ width: `${marketExposure.usPercent}%` }}
                      title={`US Markets: ${marketExposure.usPercent.toFixed(1)}%`}
                    />
                  </div>
                </div>

                {/* PHASE 3: Top Holdings Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold bg-slate-950/30">
                        <th className="py-2.5 px-3">Asset</th>
                        <th className="py-2.5 px-3">Market</th>
                        <th className="py-2.5 px-3 text-right">Quantity</th>
                        <th className="py-2.5 px-3 text-right">Avg Price</th>
                        <th className="py-2.5 px-3 text-right">Invested Value</th>
                        <th className="py-2.5 px-3 text-right">Weight</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {topHoldings.map((h, idx) => (
                        <tr
                          key={`${h.portfolioId}-${h.ticker}-${idx}`}
                          className="hover:bg-slate-900/40 transition-colors"
                        >
                          <td className="py-2.5 px-3 font-semibold text-white">
                            <div className="flex items-center gap-2">
                              <span>{h.ticker}</span>
                              <span className="text-[10px] text-slate-400 font-normal truncate max-w-[100px]">
                                ({h.portfolioName})
                              </span>
                            </div>
                          </td>
                          <td className="py-2.5 px-3">
                            <Badge variant={h.market === 'IN' ? 'info' : 'neutral'} size="sm" className="font-mono">
                              {h.market}
                            </Badge>
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-300">
                            {h.parsedQty.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-300">
                            {formatCurrency(h.parsedAvg, h.market === 'US' ? 'USD' : 'INR')}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-semibold text-white">
                            {formatCurrency(h.investedValue, 'INR')}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-cyan-400 font-semibold">
                            {formatPercent(h.allocationPercentage, false)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </Card>

          {/* PHASE 7: Platform Quick Actions / Launchpad */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Action 1: Research */}
            <div
              onClick={() => navigate('/app/research')}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-cyan-500/50 hover:bg-slate-900 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-cyan-950/60 border border-cyan-800/40 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform">
                  <BrainCircuit className="w-4 h-4" />
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 group-hover:translate-x-0.5 transition-all" />
              </div>
              <h4 className="text-xs font-semibold text-slate-200 group-hover:text-cyan-400 transition-colors">
                AI Research
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                Multi-agent synthesis
              </p>
            </div>

            {/* Action 2: Portfolio */}
            <div
              onClick={() => navigate('/app/portfolio')}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-indigo-500/50 hover:bg-slate-900 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-indigo-950/60 border border-indigo-800/40 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition-transform">
                  <PieChart className="w-4 h-4" />
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
              </div>
              <h4 className="text-xs font-semibold text-slate-200 group-hover:text-indigo-400 transition-colors">
                Portfolios
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                Holdings & weights
              </p>
            </div>

            {/* Action 3: Risk */}
            <div
              onClick={() => navigate('/app/risk')}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-amber-500/50 hover:bg-slate-900 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-amber-950/60 border border-amber-800/40 flex items-center justify-center text-amber-400 group-hover:scale-110 transition-transform">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-amber-400 group-hover:translate-x-0.5 transition-all" />
              </div>
              <h4 className="text-xs font-semibold text-slate-200 group-hover:text-amber-400 transition-colors">
                Risk Engine
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                Sharpe, VaR & CVaR
              </p>
            </div>

            {/* Action 4: Backtest */}
            <div
              onClick={() => navigate('/app/backtest')}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-emerald-500/50 hover:bg-slate-900 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
                  <GitFork className="w-4 h-4" />
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-0.5 transition-all" />
              </div>
              <h4 className="text-xs font-semibold text-slate-200 group-hover:text-emerald-400 transition-colors">
                Backtesting
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                Walk-forward evaluation
              </p>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Recent Analytical Activity (Research & Documents) */}
        <div className="space-y-6">
          {/* PHASE 5: Recent Research Sessions */}
          <Card
            title="Recent Research"
            subtitle="Latest multi-agent financial inquiries"
            action={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/app/research/history')}
                className="text-xs text-cyan-400 hover:text-cyan-300"
              >
                View History
              </Button>
            }
          >
            {researchError ? (
              <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg flex items-start gap-2 text-xs text-rose-300">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>{researchError}</div>
              </div>
            ) : isLoading ? (
              <div className="space-y-3 py-2">
                <LoadingSkeleton className="h-12 w-full rounded-lg" />
                <LoadingSkeleton className="h-12 w-full rounded-lg" />
              </div>
            ) : recentSessions.length === 0 ? (
              <EmptyState
                icon={History}
                title="No Research Sessions"
                description="Ask FinPilot AI your first fundamental, market, or news inquiry."
                actionLabel="New Inquiry"
                onAction={() => navigate('/app/research')}
              />
            ) : (
              <div className="space-y-2.5">
                {recentSessions.map((session) => (
                  <div
                    key={session.id}
                    onClick={() => navigate(`/app/research/${session.id}`)}
                    className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/80 hover:border-slate-700 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5 min-w-0">
                        {session.ticker && (
                          <Badge variant="info" size="sm" className="font-mono">
                            {session.ticker}
                          </Badge>
                        )}
                        {session.market && (
                          <Badge variant="neutral" size="sm" className="font-mono">
                            {session.market}
                          </Badge>
                        )}
                        <span className="text-xs font-semibold text-slate-200 truncate group-hover:text-cyan-400 transition-colors">
                          {session.user_message || session.title || 'Research Session'}
                        </span>
                      </div>
                      <Badge
                        variant={session.status === 'COMPLETED' ? 'success' : 'warning'}
                        size="sm"
                        className="font-mono text-[10px]"
                      >
                        {session.status}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span className="font-mono">{session.route || 'synthesis'}</span>
                      <span>{formatDate(session.created_at, { format: 'relative' })}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* PHASE 6: Recent Financial Documents (RAG) */}
          <Card
            title="Document Intelligence"
            subtitle="Indexed corporate disclosures & filings"
            action={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/app/documents')}
                className="text-xs text-cyan-400 hover:text-cyan-300"
              >
                Corpus Library
              </Button>
            }
          >
            {documentsError ? (
              <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg flex items-start gap-2 text-xs text-rose-300">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>{documentsError}</div>
              </div>
            ) : isLoading ? (
              <div className="space-y-3 py-2">
                <LoadingSkeleton className="h-12 w-full rounded-lg" />
                <LoadingSkeleton className="h-12 w-full rounded-lg" />
              </div>
            ) : recentDocuments.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="No Documents Indexed"
                description="Upload 10-K filings, annual reports, or research notes to ground AI agents in verified evidence."
                actionLabel="Upload Document"
                onAction={() => navigate('/app/documents')}
              />
            ) : (
              <div className="space-y-2.5">
                {recentDocuments.map((doc) => (
                  <div
                    key={doc.id}
                    onClick={() => navigate('/app/documents')}
                    className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/80 hover:border-slate-700 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                        <span className="text-xs font-semibold text-slate-200 truncate group-hover:text-cyan-400 transition-colors">
                          {doc.filename}
                        </span>
                      </div>
                      {getDocStatusBadge(doc.ingestion_status)}
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <div className="flex items-center gap-1.5 font-mono">
                        {doc.ticker && <span>{doc.ticker} •</span>}
                        <span className="text-indigo-400">{doc.chunk_count} chunks</span>
                      </div>
                      <span>{formatDate(doc.created_at, { format: 'relative' })}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
