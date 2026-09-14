import React, { useState } from 'react';
import {
  Portfolio,
  Holding,
  PortfolioOptimizationResponse,
  OptimizePortfolioPayload,
  OptimizedAssetWeight,
  getPortfolioCurrentValue,
} from '../../types/portfolio';
import { OptimizationMetricsCard } from './OptimizationMetricsCard';
import { AllocationComparisonChart } from './AllocationComparisonChart';
import { AllocationComparisonTable } from './AllocationComparisonTable';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import {
  Sliders,
  Play,
  RotateCcw,
  Sparkles,
  AlertCircle,
  HelpCircle,
  Cpu,
  CheckCircle2,
  ArrowRight,
  Shield,
  Layers,
  Scale,
} from 'lucide-react';

export interface OptimizationWorkspaceProps {
  portfolio: Portfolio | null;
  holdings: Holding[];
  optimizationData: PortfolioOptimizationResponse | null;
  onRunOptimization: (payload: OptimizePortfolioPayload) => Promise<void>;
  isLoading?: boolean;
  onOpenAiAudit?: () => void;
  className?: string;
}

export const OptimizationWorkspace: React.FC<OptimizationWorkspaceProps> = ({
  portfolio,
  holdings,
  optimizationData,
  onRunOptimization,
  isLoading = false,
  onOpenAiAudit,
  className = '',
}) => {
  // Derive minimum mathematically feasible max-weight percentage from active holdings count
  const minAllowedCap = holdings.length > 0 ? Math.ceil(100 / holdings.length) : 50;

  // Optimization parameters (Authoritative backend solver strictly implements Sharpe ratio maximization)
  const objective: 'max_sharpe' = 'max_sharpe';
  const [maxWeight, setMaxWeight] = useState<number>(() =>
    holdings.length > 0 ? Math.max(35, Math.ceil(100 / holdings.length)) : 35
  );
  const [minWeight, setMinWeight] = useState<number>(0); // 0% floor
  const [riskFreeRate, setRiskFreeRate] = useState<number>(6.5); // 6.5% RBI / treasury benchmark
  const [validationError, setValidationError] = useState<string | null>(null);

  // Track initialization/portfolio switching: do not overwrite deliberate user changes on same portfolio,
  // but ensure maxWeight remains mathematically feasible when holdings change.
  const lastPortfolioIdRef = React.useRef<string | number | undefined>(portfolio?.id);
  React.useEffect(() => {
    if (portfolio?.id !== lastPortfolioIdRef.current) {
      lastPortfolioIdRef.current = portfolio?.id;
      const targetMin = holdings.length > 0 ? Math.ceil(100 / holdings.length) : 50;
      setMaxWeight(Math.max(35, targetMin));
      setValidationError(null);
    } else if (holdings.length > 0) {
      const targetMin = Math.ceil(100 / holdings.length);
      if (maxWeight < targetMin) {
        setMaxWeight(targetMin);
        setValidationError(null);
      }
    }
  }, [portfolio?.id, holdings.length]);

  const portfolioValue = getPortfolioCurrentValue(portfolio);
  const currency = portfolio?.currency || 'INR';

  // Handle run optimization
  const handleExecute = async () => {
    if (holdings.length > 0 && (maxWeight / 100) * holdings.length < 1.0) {
      setValidationError(
        `Max Asset Weight Cap (${maxWeight}%) is mathematically infeasible for ${holdings.length} holdings. The upper bound must be at least ${minAllowedCap}% so that total weights can sum to 100%.`
      );
      return;
    }
    setValidationError(null);

    const payload: OptimizePortfolioPayload = {
      objective: 'max_sharpe',
      max_weight: maxWeight / 100,
      min_weight: minWeight / 100,
      risk_free_rate: riskFreeRate / 100,
    };
    await onRunOptimization(payload);
  };

  // Derive comparisons array from optimization response or fallback
  const comparisons: OptimizedAssetWeight[] = React.useMemo(() => {
    if (optimizationData?.weight_comparisons && optimizationData.weight_comparisons.length > 0) {
      return optimizationData.weight_comparisons;
    }
    if (optimizationData?.comparisons && optimizationData.comparisons.length > 0) {
      return optimizationData.comparisons;
    }

    // If optimized_weights or target_weights is a dictionary: Record<string, number>
    const optWeights = optimizationData?.optimized_weights ?? optimizationData?.target_weights ?? optimizationData?.weights;
    if (optWeights && typeof optWeights === 'object') {
      return holdings.map((h) => {
        const ticker = h.ticker || h.symbol || 'UNKNOWN';
        const curAlloc =
          h.allocation_percentage ?? h.allocation ?? h.weight ?? 0;
        const cur = typeof curAlloc === 'string' ? parseFloat(curAlloc) : curAlloc;
        const target = optWeights[ticker] !== undefined ? optWeights[ticker] * 100 : 0;
        return {
          ticker,
          name: h.name || h.company_name,
          current_weight: Number(cur.toFixed(2)),
          target_weight: Number(target.toFixed(2)),
          weight_difference: Number((target - cur).toFixed(2)),
        };
      });
    }

    return [];
  }, [optimizationData, holdings]);

  return (
    <div id="optimization-workspace" className={`space-y-6 ${className}`}>
      {/* Triad Distinction Banner */}
      <div className="p-4 rounded-xl bg-slate-950/80 border border-emerald-500/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 shrink-0 mt-0.5">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold tracking-wider uppercase text-emerald-300">
                Mathematical Allocation Optimizer
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800/60">
                Backend Markowitz Pipeline
              </span>
            </div>
            <div className="mt-1 flex flex-col sm:flex-row sm:items-center gap-2 text-xs text-slate-300">
              <span className="font-semibold text-slate-200">
                OPTIMIZATION:
              </span>
              <span className="text-slate-400">
                "What allocation the mathematical optimizer prefers under its assumptions and constraints."
              </span>
            </div>
          </div>
        </div>

        <div className="text-[11px] text-slate-400 border-l border-slate-800 md:pl-4 max-w-sm leading-relaxed">
          Optimized weights are theoretical targets derived mathematically from covariance matrices. They do not guarantee superior future returns or eliminate downside market risk.
        </div>
      </div>

      {/* Optimizer Controls Panel */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              <span>Optimizer Parameters & Constraints</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Configure boundary constraints and mathematical target functions
            </p>
          </div>

          <div className="flex items-center gap-2">
            {onOpenAiAudit && (
              <Button
                variant="secondary"
                size="sm"
                onClick={onOpenAiAudit}
                leftIcon={<Sparkles className="w-3.5 h-3.5 text-cyan-400" />}
                className="border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10"
              >
                AI Rebalance Audit
              </Button>
            )}

            <Button
              variant="primary"
              size="sm"
              onClick={handleExecute}
              disabled={isLoading || holdings.length === 0}
              leftIcon={<Play className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
            >
              {isLoading ? 'Solving Optimum...' : 'Run Mathematical Optimization'}
            </Button>
          </div>
        </div>

        {/* Feasibility Alert Notice */}
        {validationError && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-start gap-2.5 text-xs">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <span className="font-semibold text-rose-200">Constraint Feasibility Notice</span>
              <p className="text-rose-300/90">{validationError}</p>
            </div>
          </div>
        )}

        {/* Form Controls Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          {/* Objective Selector */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-slate-300 block">
                Optimization Objective
              </label>
              <span className="text-[10px] font-mono text-emerald-400 font-medium">Backend Active</span>
            </div>
            <select
              value="max_sharpe"
              disabled
              className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none cursor-not-allowed opacity-90"
            >
              <option value="max_sharpe">Maximize Sharpe Ratio (Tangency)</option>
              <option value="min_volatility" disabled>Minimize Volatility (Backend Unsupported)</option>
              <option value="risk_parity" disabled>Equal Risk Parity (Backend Unsupported)</option>
              <option value="target_return" disabled>Constrained Min Variance (Backend Unsupported)</option>
            </select>
            <span className="text-[10px] text-slate-400 block leading-tight">
              Authoritative backend engine exclusively optimizes Sharpe ratio under bounded simplex constraints.
            </span>
          </div>

          {/* Max Single Asset Weight */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-slate-300">
                Max Asset Weight Cap
              </label>
              <span className="font-mono text-cyan-400 font-bold">{maxWeight}%</span>
            </div>
            <input
              type="range"
              min={minAllowedCap}
              max="100"
              step="1"
              value={maxWeight}
              onChange={(e) => {
                setMaxWeight(Number(e.target.value));
                setValidationError(null);
              }}
              className="w-full accent-cyan-400 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
            >
            </input>
            <span className="text-[10px] text-slate-500 block">
              Upper bound constraint (min {minAllowedCap}% for {holdings.length} assets to sum to 100%)
            </span>
          </div>

          {/* Min Single Asset Weight */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-slate-300">
                Min Asset Weight Floor
              </label>
              <span className="font-mono text-cyan-400 font-bold">{minWeight}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="20"
              step="1"
              value={minWeight}
              onChange={(e) => setMinWeight(Number(e.target.value))}
              className="w-full accent-cyan-400 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
            >
            </input>
            <span className="text-[10px] text-slate-500 block">
              Lower bound weight constraint (long-only)
            </span>
          </div>

          {/* Risk-Free Rate */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-slate-300">
                Risk-Free Rate (Rf)
              </label>
              <span className="font-mono text-slate-300 font-bold">{riskFreeRate}%</span>
            </div>
            <input
              type="number"
              step="0.25"
              min="0"
              max="20"
              value={riskFreeRate}
              onChange={(e) => setRiskFreeRate(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-1.5 text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
            />
            <span className="text-[10px] text-slate-500 block">
              Benchmark risk-free hurdle (e.g. 91-day T-bill)
            </span>
          </div>
        </div>

        {/* Short Selling Warning / Long-Only Guard */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-xs">
          <div className="flex items-center gap-2">
            <label className="inline-flex items-center gap-2 opacity-60 cursor-not-allowed">
              <input
                type="checkbox"
                checked={false}
                disabled
                className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0 w-3.5 h-3.5 cursor-not-allowed"
              />
              <span className="text-slate-400">Allow Short Selling (Unconstrained Weights)</span>
            </label>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-950/60 text-amber-400 border border-amber-800/40">
              Unsupported (Long-Only Only)
            </span>
          </div>

          <span className="text-[11px] text-slate-400 italic">
            Deterministic Long-Only Portfolio (0% ≤ w_i ≤ Cap, Σ w_i = 100%)
          </span>
        </div>
      </div>

      {/* Optimization Metrics Comparison Card */}
      <OptimizationMetricsCard
        optimizationData={optimizationData}
        isLoading={isLoading}
      />

      {/* Allocation Comparison Chart (Side-by-side Bar Chart) */}
      <AllocationComparisonChart
        comparisons={comparisons}
      />

      {/* Allocation Comparison Table */}
      <AllocationComparisonTable
        comparisons={comparisons}
        portfolioValue={portfolioValue}
        currency={currency}
      />
    </div>
  );
};
