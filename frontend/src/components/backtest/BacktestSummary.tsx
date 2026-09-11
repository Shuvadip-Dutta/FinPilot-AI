import React from 'react';
import {
  TrendingUp,
  DollarSign,
  Percent,
  RefreshCw,
  Award,
  Sparkles,
  ShieldAlert,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import {
  BacktestResponse,
  getBacktestFinalValue,
  getBacktestTotalCosts,
  getBacktestTotalTurnover,
  getBacktestStrategyMetrics,
  getBacktestBuyAndHoldMetrics,
  getBacktestBenchmarkMetrics,
  getBacktestCAGR,
  getBacktestSharpe,
  getBacktestMaxDrawdown,
  getBacktestTotalReturn,
} from '../../types/portfolio';
import { Badge } from '../common/Badge';
import { formatCurrency, formatPercent } from '../../utils/formatters';

export interface BacktestSummaryProps {
  response: BacktestResponse | null;
  currency?: string;
  initialCapital?: number;
  className?: string;
}

export const BacktestSummary: React.FC<BacktestSummaryProps> = ({
  response,
  currency = 'INR',
  initialCapital = 100000,
  className = '',
}) => {
  if (!response) return null;

  const finalValue = getBacktestFinalValue(response);
  const totalCosts = getBacktestTotalCosts(response);
  const totalTurnover = getBacktestTotalTurnover(response);

  const strat = getBacktestStrategyMetrics(response);
  const bnh = getBacktestBuyAndHoldMetrics(response);
  const bm = getBacktestBenchmarkMetrics(response);

  const stratTotalReturn = getBacktestTotalReturn(strat);
  const stratCAGR = getBacktestCAGR(strat);
  const stratSharpe = getBacktestSharpe(strat);
  const stratMaxDd = getBacktestMaxDrawdown(strat);

  const bmTotalReturn = getBacktestTotalReturn(bm);
  const bmCAGR = getBacktestCAGR(bm);

  const bnhTotalReturn = getBacktestTotalReturn(bnh);

  const rebalanceCount =
    strat?.rebalance_count ??
    (Array.isArray(response.rebalance_events) ? response.rebalance_events.length : null);

  // Format helper for return percentages that might be either decimal (0.15) or percent (15)
  const formatRet = (val: number | null | undefined) => {
    if (val === null || val === undefined) return 'N/A';
    const num = Number(val);
    if (isNaN(num)) return 'N/A';
    const normalized = Math.abs(num) > 1.5 ? num : num * 100;
    return `${num >= 0 ? '+' : ''}${normalized.toFixed(2)}%`;
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Top Banner KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* 1. Final Portfolio Value */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="font-semibold uppercase tracking-wider text-[11px]">Final Portfolio Value</span>
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold font-mono text-white tracking-tight">
            {finalValue !== null ? formatCurrency(finalValue, currency) : 'N/A'}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5">
            <span>Base Capital:</span>
            <span className="font-mono text-slate-300">{formatCurrency(initialCapital, currency)}</span>
          </div>
        </div>

        {/* 2. Strategy Total Return */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="font-semibold uppercase tracking-wider text-[11px]">Strategy Total Return</span>
            <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div
            className={`text-2xl font-extrabold font-mono tracking-tight flex items-center gap-1 ${
              (stratTotalReturn ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {(stratTotalReturn ?? 0) >= 0 ? (
              <ArrowUpRight className="w-5 h-5 inline shrink-0" />
            ) : (
              <ArrowDownRight className="w-5 h-5 inline shrink-0" />
            )}
            {formatRet(stratTotalReturn)}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-2">
            <span>CAGR:</span>
            <span className="font-mono font-semibold text-cyan-300">{formatRet(stratCAGR)}</span>
          </div>
        </div>

        {/* 3. Risk-Adjusted Sharpe */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="font-semibold uppercase tracking-wider text-[11px]">Walk-Forward Sharpe</span>
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold font-mono text-white tracking-tight">
            {stratSharpe !== null ? stratSharpe.toFixed(2) : 'N/A'}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-2">
            <span>Max Drawdown:</span>
            <span className="font-mono font-semibold text-rose-400">
              {stratMaxDd !== null ? formatRet(stratMaxDd) : 'N/A'}
            </span>
          </div>
        </div>

        {/* 4. Total Costs & Turnover */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="font-semibold uppercase tracking-wider text-[11px]">Friction & Costs</span>
            <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
              <Percent className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold font-mono text-amber-400 tracking-tight">
            {totalCosts !== null ? formatCurrency(totalCosts, currency) : 'N/A'}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-2">
            <span>Cumulative Turnover:</span>
            <span className="font-mono text-slate-300">
              {totalTurnover !== null ? `${(totalTurnover * (totalTurnover < 2 ? 100 : 1)).toFixed(1)}%` : 'N/A'}
            </span>
          </div>
        </div>

        {/* 5. Rebalances & Engine Mode */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="font-semibold uppercase tracking-wider text-[11px]">Rebalance Events</span>
            <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400">
              <RefreshCw className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold font-mono text-white tracking-tight">
            {rebalanceCount !== null ? rebalanceCount : 'N/A'}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-1.5">
            <span>Engine:</span>
            <Badge variant="default" size="sm">
              Walk-Forward QP
            </Badge>
          </div>
        </div>
      </div>

      {/* Comparative Headline Bar */}
      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between flex-wrap gap-4 text-xs">
        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-cyan-400 shadow-xs shadow-cyan-400/50" />
            <span className="text-slate-400">Strategy (Rolling WF):</span>
            <strong className="font-mono text-cyan-300">{formatRet(stratTotalReturn)}</strong>
          </div>

          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-amber-400 shadow-xs shadow-amber-400/50" />
            <span className="text-slate-400">Buy & Hold:</span>
            <strong className="font-mono text-amber-300">{formatRet(bnhTotalReturn)}</strong>
          </div>

          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-purple-400 shadow-xs shadow-purple-400/50" />
            <span className="text-slate-400">Benchmark ({response.benchmark || '^NSEI'}):</span>
            <strong className="font-mono text-purple-300">{formatRet(bmTotalReturn)}</strong>
          </div>
        </div>

        <div className="text-[11px] text-slate-400 font-mono">
          Span: <span className="text-slate-200">{response.start_date || 'Inception'}</span> &rarr;{' '}
          <span className="text-slate-200">{response.end_date || 'Termination'}</span>
        </div>
      </div>
    </div>
  );
};
