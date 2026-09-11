import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { PageHeader } from '../../components/layout/PageHeader';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { ErrorState } from '../../components/common/ErrorState';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { RiskMetricCards } from '../../components/risk/RiskMetricCards';
import { PortfolioRiskVisualization } from '../../components/risk/PortfolioRiskVisualization';
import { MethodologyPanel } from '../../components/risk/MethodologyPanel';
import { OptimizationWorkspace } from '../../components/optimization/OptimizationWorkspace';
import { RiskAiAuditModal } from '../../components/risk/RiskAiAuditModal';
import { portfolioApi } from '../../api/portfolio';
import {
  Portfolio,
  Holding,
  PortfolioRiskResponse,
  PortfolioOptimizationResponse,
  OptimizePortfolioPayload,
  getPortfolioCurrentValue,
  getPortfolioPnLPercent,
} from '../../types/portfolio';
import { formatCurrency, formatPercent } from '../../utils/formatters';
import {
  ShieldAlert,
  Sliders,
  Cpu,
  RefreshCw,
  Sparkles,
  ArrowLeft,
  ChevronDown,
  Layers,
  BarChart3,
  Scale,
  Briefcase,
  AlertTriangle,
  GitFork,
} from 'lucide-react';

export const PortfolioRiskPage: React.FC = () => {
  const { portfolioId: paramPortfolioId } = useParams<{ portfolioId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const location = useLocation();

  // Navigation tab: 'risk' (Quantitative Risk) vs 'optimization' (Portfolio Optimization)
  const isOptimizationRoute = location.pathname.includes('/optimization');
  const initialTab = searchParams.get('tab')
    ? (searchParams.get('tab') === 'optimization' ? 'optimization' : 'risk')
    : (isOptimizationRoute ? 'optimization' : 'risk');
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<'risk' | 'optimization'>(initialTab);

  // Sync workspace tab when location path changes (e.g. navigation between /risk and /optimization)
  useEffect(() => {
    if (location.pathname.includes('/optimization')) {
      setActiveWorkspaceTab('optimization');
    } else if (location.pathname.includes('/risk')) {
      setActiveWorkspaceTab('risk');
    }
  }, [location.pathname]);

  // Portfolios list & selection
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string | number | null>(
    paramPortfolioId || null
  );
  const [currentPortfolio, setCurrentPortfolio] = useState<Portfolio | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);

  // Quantitative Risk & Optimization states
  const [riskData, setRiskData] = useState<PortfolioRiskResponse | null>(null);
  const [optimizationData, setOptimizationData] = useState<PortfolioOptimizationResponse | null>(null);

  // Loading & error states
  const [isLoadingPortfolios, setIsLoadingPortfolios] = useState<boolean>(true);
  const [isLoadingRisk, setIsLoadingRisk] = useState<boolean>(false);
  const [isOptimizing, setIsOptimizing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // AI Modal state
  const [isAiAuditOpen, setIsAiAuditOpen] = useState<boolean>(false);

  // Sync workspace tab with URL query parameter
  const handleTabChange = (tab: 'risk' | 'optimization') => {
    setActiveWorkspaceTab(tab);
    setSearchParams({ tab });
  };

  // 1. Initial load: retrieve all user portfolios
  useEffect(() => {
    const fetchPortfolios = async () => {
      setIsLoadingPortfolios(true);
      try {
        const list = await portfolioApi.getPortfolios();
        setPortfolios(list);

        // Determine active portfolio
        if (paramPortfolioId) {
          const match = list.find(
            (p) => String(p.id) === String(paramPortfolioId) || (p as any).slug === paramPortfolioId
          );
          if (match) {
            setSelectedPortfolioId(match.id);
            setCurrentPortfolio(match);
          } else if (list.length > 0) {
            setSelectedPortfolioId(list[0].id);
            setCurrentPortfolio(list[0]);
          }
        } else if (list.length > 0) {
          setSelectedPortfolioId(list[0].id);
          setCurrentPortfolio(list[0]);
        }
      } catch (err: any) {
        console.error('Error fetching portfolios:', err);
        setError('Failed to load user portfolios. Please ensure you are authenticated.');
      } finally {
        setIsLoadingPortfolios(false);
      }
    };

    fetchPortfolios();
  }, [paramPortfolioId]);

  // 2. Load Portfolio details, holdings, and quantitative risk data
  const loadPortfolioRiskData = useCallback(async (id: string | number) => {
    setIsLoadingRisk(true);
    setError(null);

    try {
      // Parallel fetch: portfolio details, holdings, and risk metrics from backend
      const [portfolioRes, holdingsRes, riskRes] = await Promise.allSettled([
        portfolioApi.getPortfolio(id),
        portfolioApi.getHoldings(id),
        portfolioApi.getPortfolioRisk(id),
      ]);

      if (portfolioRes.status === 'fulfilled') {
        setCurrentPortfolio(portfolioRes.value);
      }
      if (holdingsRes.status === 'fulfilled') {
        setHoldings(holdingsRes.value);
      }

      if (riskRes.status === 'fulfilled') {
        setRiskData(riskRes.value);
      } else {
        console.warn('Backend risk endpoint failed or returned empty:', riskRes.reason);
        // We do not invent mock numbers; let the UI display missing state gracefully
        setRiskData(null);
      }
    } catch (err: any) {
      console.error('Failed to load portfolio quantitative data:', err);
      setError(err?.message || 'Failed to retrieve quantitative metrics from backend.');
    } finally {
      setIsLoadingRisk(false);
    }
  }, []);

  useEffect(() => {
    if (selectedPortfolioId) {
      loadPortfolioRiskData(selectedPortfolioId);
    }
  }, [selectedPortfolioId, loadPortfolioRiskData]);

  // Handle switching portfolios
  const handlePortfolioSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newId = e.target.value;
    setSelectedPortfolioId(newId);
    const found = portfolios.find((p) => String(p.id) === String(newId));
    if (found) {
      setCurrentPortfolio(found);
    }
    setOptimizationData(null); // Reset optimization results for different portfolio
  };

  // Run mathematical optimization
  const handleRunOptimization = async (payload: OptimizePortfolioPayload) => {
    if (!selectedPortfolioId) return;
    setIsOptimizing(true);
    setError(null);

    try {
      const optRes = await portfolioApi.optimizePortfolio(selectedPortfolioId, payload);
      setOptimizationData(optRes);
    } catch (err: any) {
      console.error('Optimization execution error:', err);
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Failed to solve mathematical portfolio optimization. Please verify constraints.'
      );
    } finally {
      setIsOptimizing(false);
    }
  };

  const totalValue = getPortfolioCurrentValue(currentPortfolio);
  const pnlPercent = getPortfolioPnLPercent(currentPortfolio);
  const currency = currentPortfolio?.currency || 'INR';

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <PageHeader
        title="Portfolio Risk & Optimization Workspace"
        subtitle="Authoritative quantitative risk profiling and mathematical target allocation solver"
        badge={
          <Badge variant="info" size="sm" className="font-mono">
            Phase D Engine
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2.5 flex-wrap">
            {selectedPortfolioId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate(`/app/portfolio/${selectedPortfolioId}`)}
                leftIcon={<Briefcase className="w-3.5 h-3.5" />}
              >
                View Holdings Ledger
              </Button>
            )}

            {selectedPortfolioId && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(`/app/portfolio/${selectedPortfolioId}/backtest`)}
                className="border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/10"
                leftIcon={<GitFork className="w-3.5 h-3.5 text-indigo-400" />}
              >
                Walk-Forward Backtest
              </Button>
            )}

            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsAiAuditOpen(true)}
              leftIcon={<Sparkles className="w-3.5 h-3.5 text-cyan-400" />}
            >
              AI Risk Audit
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => selectedPortfolioId && loadPortfolioRiskData(selectedPortfolioId)}
              disabled={isLoadingRisk}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoadingRisk ? 'animate-spin' : ''}`} />}
            >
              Refresh Data
            </Button>
          </div>
        }
      />

      {/* Portfolio Selector & Valuation Bar */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 shrink-0">
            <Briefcase className="w-5 h-5" />
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Active Portfolio
              </span>
              {portfolios.length > 1 && (
                <span className="text-[10px] text-slate-500">
                  ({portfolios.length} available)
                </span>
              )}
            </div>

            {isLoadingPortfolios ? (
              <div className="h-6 w-48 bg-slate-800 animate-pulse rounded" />
            ) : portfolios.length > 0 ? (
              <div className="relative">
                <select
                  value={selectedPortfolioId ? String(selectedPortfolioId) : ''}
                  onChange={handlePortfolioSelect}
                  className="bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-1.5 text-sm font-semibold text-slate-100 pr-8 focus:outline-none focus:border-cyan-500 cursor-pointer appearance-none min-w-[220px]"
                >
                  {portfolios.map((p) => (
                    <option key={p.id} value={String(p.id)}>
                      {p.name} ({p.currency || 'INR'})
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            ) : (
              <span className="text-sm font-medium text-slate-400">No Portfolios Found</span>
            )}
          </div>
        </div>

        {/* Valuation & Holdings Count Pill */}
        {currentPortfolio && (
          <div className="flex items-center gap-4 text-xs border-t md:border-t-0 md:border-l border-slate-800 pt-3 md:pt-0 md:pl-4">
            <div>
              <span className="text-[11px] text-slate-400 block">Current Ledger Valuation</span>
              <span className="text-base font-bold font-mono text-slate-200">
                {totalValue !== null ? formatCurrency(totalValue, currency) : '—'}
              </span>
            </div>

            <div>
              <span className="text-[11px] text-slate-400 block">Total P&L</span>
              <span
                className={`text-base font-bold font-mono ${
                  pnlPercent !== null && pnlPercent >= 0
                    ? 'text-emerald-400'
                    : pnlPercent !== null
                    ? 'text-rose-400'
                    : 'text-slate-400'
                }`}
              >
                {pnlPercent !== null ? formatPercent(pnlPercent, true) : '—'}
              </span>
            </div>

            <div>
              <span className="text-[11px] text-slate-400 block">Assets</span>
              <span className="text-base font-bold font-mono text-cyan-400">
                {holdings.length}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-sm">Action Notice</span>
            <p className="text-xs text-rose-300/90">{error}</p>
          </div>
        </div>
      )}

      {/* Primary Workspace Tab Switcher */}
      <div className="border-b border-slate-800">
        <div className="flex space-x-8">
          <button
            type="button"
            onClick={() => handleTabChange('risk')}
            className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
              activeWorkspaceTab === 'risk'
                ? 'border-cyan-400 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>Quantitative Risk Workspace</span>
            <Badge variant="neutral" size="sm" className="font-mono text-[10px]">
              Authoritative
            </Badge>
          </button>

          <button
            type="button"
            onClick={() => handleTabChange('optimization')}
            className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
              activeWorkspaceTab === 'optimization'
                ? 'border-emerald-400 text-emerald-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sliders className="w-4 h-4" />
            <span>Portfolio Optimization</span>
            <Badge variant="neutral" size="sm" className="font-mono text-[10px]">
              Markowitz Solver
            </Badge>
          </button>
        </div>
      </div>

      {/* TAB 1: Quantitative Risk Profile Workspace */}
      {activeWorkspaceTab === 'risk' && (
        <div className="space-y-6">
          {/* Risk Metric Cards (Sharpe, Sortino, VaR 95%, CVaR 95%, Max Drawdown, etc.) */}
          <RiskMetricCards
            riskData={riskData}
            isLoading={isLoadingRisk}
          />

          {/* Current Portfolio Risk Visualization (Drawdown Underwater Chart, Cumulative Return, Contributions) */}
          <PortfolioRiskVisualization
            riskData={riskData}
            portfolioName={currentPortfolio?.name}
            currency={currency}
          />

          {/* Methodology & Formulations Panel */}
          <MethodologyPanel />
        </div>
      )}

      {/* TAB 2: Portfolio Optimization Workspace */}
      {activeWorkspaceTab === 'optimization' && (
        <div className="space-y-6">
          <OptimizationWorkspace
            portfolio={currentPortfolio}
            holdings={holdings}
            optimizationData={optimizationData}
            onRunOptimization={handleRunOptimization}
            isLoading={isOptimizing}
            onOpenAiAudit={() => setIsAiAuditOpen(true)}
          />

          {/* Methodology & Formulations Panel (also available here for clear context distinction) */}
          <MethodologyPanel />
        </div>
      )}

      {/* AI Risk Audit Modal */}
      <RiskAiAuditModal
        isOpen={isAiAuditOpen}
        onClose={() => setIsAiAuditOpen(false)}
        portfolio={currentPortfolio}
        riskData={riskData}
        optimizationData={optimizationData}
      />
    </div>
  );
};
