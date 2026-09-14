import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '../../components/layout/PageHeader';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { portfolioApi } from '../../api/portfolio';
import {
  Portfolio,
  Holding,
  BacktestPayload,
  BacktestResponse,
} from '../../types/portfolio';
import { BacktestConfigForm } from '../../components/backtest/BacktestConfigForm';
import { BacktestSummary } from '../../components/backtest/BacktestSummary';
import { MetricComparison } from '../../components/backtest/MetricComparison';
import { EquityCurve } from '../../components/backtest/EquityCurve';
import { DrawdownChart } from '../../components/backtest/DrawdownChart';
import { RebalanceTable } from '../../components/backtest/RebalanceTable';
import { BacktestMethodologyPanel } from '../../components/backtest/MethodologyPanel';
import { BacktestErrorState } from '../../components/backtest/BacktestErrorState';
import {
  GitFork,
  Briefcase,
  Sliders,
  TrendingUp,
  ShieldAlert,
  Calendar,
  Layers,
  BookOpen,
  ArrowLeft,
  RotateCcw,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';

export const BacktestPage: React.FC = () => {
  const { portfolioId: paramPortfolioId } = useParams<{ portfolioId?: string }>();
  const navigate = useNavigate();

  // Portfolios & Selection
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string | number | null>(
    paramPortfolioId || null
  );
  const [currentPortfolio, setCurrentPortfolio] = useState<Portfolio | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [isLoadingPortfolios, setIsLoadingPortfolios] = useState(true);

  // Backtest Execution State
  const [isRunningBacktest, setIsRunningBacktest] = useState(false);
  const [backtestResponse, setBacktestResponse] = useState<BacktestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | undefined>(undefined);
  const [activeTab, setActiveTab] = useState<
    'overview' | 'drawdown' | 'metrics' | 'rebalance' | 'methodology'
  >('overview');

  // 1. Fetch user portfolios
  useEffect(() => {
    const fetchPortfolios = async () => {
      setIsLoadingPortfolios(true);
      setError(null);
      try {
        const list = await portfolioApi.getPortfolios();
        setPortfolios(list);

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
        setError('Failed to load user portfolios. Please check your credentials or network connectivity.');
      } finally {
        setIsLoadingPortfolios(false);
      }
    };

    fetchPortfolios();
  }, [paramPortfolioId]);

  // 2. Fetch Holdings for the active portfolio
  useEffect(() => {
    if (!selectedPortfolioId) return;

    const fetchHoldings = async () => {
      try {
        const h = await portfolioApi.getHoldings(selectedPortfolioId);
        setHoldings(h);
      } catch (err: any) {
        console.warn('Could not fetch portfolio holdings:', err);
        setHoldings([]);
      }
    };

    fetchHoldings();
  }, [selectedPortfolioId]);

  // Switch active portfolio
  const handlePortfolioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newId = e.target.value;
    setSelectedPortfolioId(newId);
    const found = portfolios.find((p) => String(p.id) === String(newId));
    if (found) {
      setCurrentPortfolio(found);
    }
    setBacktestResponse(null);
    setError(null);
    setErrorStatus(undefined);
  };

  // Run Walk-Forward Backtest
  const handleExecuteBacktest = async (payload: BacktestPayload) => {
    if (!selectedPortfolioId) {
      setError('Please select an active portfolio first.');
      return;
    }

    setIsRunningBacktest(true);
    setBacktestResponse(null);
    setError(null);
    setErrorStatus(undefined);

    try {
      const response = await portfolioApi.runBacktest(selectedPortfolioId, payload);
      setBacktestResponse(response);
      setActiveTab('overview');
    } catch (err: any) {
      console.error('Backtest execution failed:', err);
      const status = err?.status || err?.response?.status;
      setErrorStatus(status);
      const detail =
        err?.response?.data?.error ||
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Historical walk-forward evaluation could not be completed on the backend.';
      setError(detail);
    } finally {
      setIsRunningBacktest(false);
    }
  };

  const currency = currentPortfolio?.currency || 'INR';

  return (
    <div className="space-y-6 pb-16">
      {/* Page Header */}
      <PageHeader
        title="Walk-Forward Backtest Workspace"
        subtitle="Historical rolling out-of-sample portfolio re-optimization and benchmark evaluation"
        badge={
          <Badge variant="info" size="sm" className="font-mono">
            Phase E Engine
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
                Portfolio Ledger
              </Button>
            )}
            {selectedPortfolioId && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(`/app/portfolio/${selectedPortfolioId}/risk`)}
                leftIcon={<ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />}
              >
                Risk Profile
              </Button>
            )}
            {selectedPortfolioId && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(`/app/portfolio/${selectedPortfolioId}/optimization`)}
                leftIcon={<Sliders className="w-3.5 h-3.5 text-emerald-400" />}
              >
                Optimize
              </Button>
            )}
          </div>
        }
      />

      {/* Portfolio Selector Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex items-center justify-between flex-wrap gap-4 shadow-md">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="p-2 rounded-xl bg-slate-800 text-cyan-400">
            <Briefcase className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
              Active Evaluation Target
            </span>
            <div className="flex items-center gap-2 mt-0.5">
              {isLoadingPortfolios ? (
                <span className="text-xs text-slate-400">Loading portfolios...</span>
              ) : portfolios.length === 0 ? (
                <span className="text-xs text-rose-400">No portfolios found</span>
              ) : (
                <select
                  value={selectedPortfolioId ? String(selectedPortfolioId) : ''}
                  onChange={handlePortfolioChange}
                  disabled={isRunningBacktest}
                  className="bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white font-semibold focus:outline-none focus:border-cyan-500"
                >
                  {portfolios.map((p) => (
                    <option key={p.id} value={String(p.id)}>
                      {p.name} ({p.currency || 'INR'}) — {p.holdings?.length ?? p.holdings_count ?? 0} holdings
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2 text-slate-400">
            <span>Holdings:</span>
            <strong className="text-white font-mono">{holdings.length}</strong>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <span>Base Currency:</span>
            <strong className="text-cyan-300 font-mono">{currency}</strong>
          </div>
          {backtestResponse && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setBacktestResponse(null);
                setError(null);
              }}
              leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
            >
              New Backtest Config
            </Button>
          )}
        </div>
      </div>

      {/* Loading Experience: Running Historical Evaluation */}
      {isRunningBacktest && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center shadow-2xl max-w-xl mx-auto space-y-5 animate-pulse">
          <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto text-cyan-400">
            <GitFork className="w-7 h-7 animate-spin" />
          </div>
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-white">
              Running Historical Walk-Forward Evaluation...
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
              Calibrating covariance matrices, solving sequential quadratic programs, applying transaction friction, and recording out-of-sample events on the authoritative backend engine.
            </p>
          </div>
          <div className="flex items-center justify-center gap-2 text-[11px] font-mono text-cyan-400">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            <span>Please wait while the server processes multiple historical intervals</span>
          </div>
        </div>
      )}

      {/* Error State */}
      {!isRunningBacktest && error && (
        <BacktestErrorState
          error={error}
          status={errorStatus}
          onRetry={() => setError(null)}
          onResetConfig={() => setError(null)}
          onCreatePortfolio={() => navigate('/app/portfolio')}
        />
      )}

      {/* Empty State: No Portfolio */}
      {!isRunningBacktest && !isLoadingPortfolios && portfolios.length === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center max-w-md mx-auto shadow-xl space-y-4">
          <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
            <Briefcase className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-white">Create a Portfolio Before Running a Backtest</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Historical walk-forward backtesting requires an active portfolio with registered asset holdings to construct covariance matrices and generate rebalance schedules.
          </p>
          <Button
            variant="primary"
            size="md"
            onClick={() => navigate('/app/portfolio')}
            leftIcon={<Briefcase className="w-4 h-4" />}
          >
            Go to Portfolios
          </Button>
        </div>
      )}

      {/* Step 1: Configuration Form (Shown when no results or user wants to reconfigure) */}
      {!isRunningBacktest && !backtestResponse && portfolios.length > 0 && (
        <div className="space-y-6">
          <BacktestConfigForm
            portfolioCurrency={currency}
            portfolioHoldingsCount={holdings.length}
            isLoading={isRunningBacktest}
            onExecute={handleExecuteBacktest}
          />

          <BacktestMethodologyPanel defaultExpanded={false} />
        </div>
      )}

      {/* Step 2: Backtest Results Dashboard (Shown when results are populated) */}
      {!isRunningBacktest && backtestResponse && (
        <div className="space-y-6">
          {/* Top KPI Summary */}
          <BacktestSummary
            response={backtestResponse}
            currency={currency}
            initialCapital={Number(backtestResponse.initial_capital || 100000)}
          />

          {/* Sub-Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto text-xs">
            <button
              type="button"
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-2 rounded-lg font-semibold flex items-center gap-2 transition-colors whitespace-nowrap ${
                activeTab === 'overview'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <TrendingUp className="w-4 h-4" />
              <span>Equity Curve Trajectory</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('drawdown')}
              className={`px-4 py-2 rounded-lg font-semibold flex items-center gap-2 transition-colors whitespace-nowrap ${
                activeTab === 'drawdown'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Underwater Drawdown</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('metrics')}
              className={`px-4 py-2 rounded-lg font-semibold flex items-center gap-2 transition-colors whitespace-nowrap ${
                activeTab === 'metrics'
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Performance & Risk Comparison</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('rebalance')}
              className={`px-4 py-2 rounded-lg font-semibold flex items-center gap-2 transition-colors whitespace-nowrap ${
                activeTab === 'rebalance'
                  ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <GitFork className="w-4 h-4" />
              <span>Rebalance Schedule</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('methodology')}
              className={`px-4 py-2 rounded-lg font-semibold flex items-center gap-2 transition-colors whitespace-nowrap ${
                activeTab === 'methodology'
                  ? 'bg-slate-800 text-slate-200 border border-slate-700'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              <span>Methodology & Disclaimers</span>
            </button>
          </div>

          {/* Active Tab Panel */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <EquityCurve
                response={backtestResponse}
                currency={currency}
                initialCapital={Number(backtestResponse.initial_capital || 100000)}
              />

              {/* Side-by-side metric comparison teaser */}
              <MetricComparison
                response={backtestResponse}
                currency={currency}
              />
            </div>
          )}

          {activeTab === 'drawdown' && (
            <div className="space-y-6">
              <DrawdownChart response={backtestResponse} />
              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-400 leading-relaxed space-y-2">
                <h5 className="font-bold text-white flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  <span>Interpreting the Underwater Drawdown Curve</span>
                </h5>
                <p>
                  The underwater drawdown graph visualizes the percentage drop from the highest peak equity value (High-Water Mark) at every point in time. When the curve touches 0%, the portfolio is at an all-time cumulative peak. The trough depths and horizontal lengths illustrate maximum capital vulnerability and recovery durations.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'metrics' && (
            <div className="space-y-6">
              <MetricComparison
                response={backtestResponse}
                currency={currency}
              />
            </div>
          )}

          {activeTab === 'rebalance' && (
            <div className="space-y-6">
              <RebalanceTable
                response={backtestResponse}
                currency={currency}
              />
            </div>
          )}

          {activeTab === 'methodology' && (
            <div className="space-y-6">
              <BacktestMethodologyPanel defaultExpanded={true} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
