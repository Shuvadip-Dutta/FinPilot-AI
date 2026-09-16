import React from 'react';
import {
  PortfolioOptimizationResponse,
  OptimizationMetrics,
  getOptExpectedReturn,
  getOptVolatility,
  getOptSharpe,
  getOptCurrentExpectedReturn,
  getOptCurrentVolatility,
  getOptCurrentSharpe,
} from '../../types/portfolio';
import { formatPercent, formatRatio } from '../../utils/formatters';
import { TrendingUp, Activity, Shield, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

export interface OptimizationMetricsCardProps {
  optimizationData: PortfolioOptimizationResponse | null;
  isLoading?: boolean;
}

export const OptimizationMetricsCard: React.FC<OptimizationMetricsCardProps> = ({
  optimizationData,
  isLoading = false,
}) => {
  const currentReturn = getOptCurrentExpectedReturn(optimizationData);
  const optReturn = getOptExpectedReturn(optimizationData);

  const currentVol = getOptCurrentVolatility(optimizationData);
  const optVol = getOptVolatility(optimizationData);

  const currentSharpe = getOptCurrentSharpe(optimizationData);
  const optSharpe = getOptSharpe(optimizationData);

  const returnDelta =
    currentReturn !== null && optReturn !== null ? optReturn - currentReturn : null;
  const volDelta =
    currentVol !== null && optVol !== null ? optVol - currentVol : null;
  const sharpeDelta =
    currentSharpe !== null && optSharpe !== null ? optSharpe - currentSharpe : null;

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={`opt-skeleton-${i}`}
            className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 animate-pulse space-y-3"
          >
            <div className="h-4 w-28 bg-slate-800 rounded" />
            <div className="h-7 w-20 bg-slate-800 rounded" />
            <div className="h-3 w-36 bg-slate-800/60 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const renderDelta = (
    delta: number | null,
    format: 'percent' | 'ratio',
    favorableDirection: 'positive' | 'negative'
  ) => {
    if (delta === null) return <span className="text-slate-500">—</span>;

    const isZero = Math.abs(delta) < 0.0001;
    if (isZero) {
      return (
        <span className="text-slate-400 inline-flex items-center gap-0.5 font-mono text-xs">
          <Minus className="w-3 h-3" /> 0.00
        </span>
      );
    }

    const isFavorable =
      (favorableDirection === 'positive' && delta > 0) ||
      (favorableDirection === 'negative' && delta < 0);

    const colorClass = isFavorable ? 'text-emerald-400' : 'text-amber-400';
    const Icon = delta > 0 ? ArrowUpRight : ArrowDownRight;

    return (
      <span className={`inline-flex items-center gap-0.5 font-mono text-xs font-semibold ${colorClass}`}>
        <Icon className="w-3.5 h-3.5" />
        {format === 'percent' ? formatPercent(delta, true, 2) : (delta > 0 ? `+${delta.toFixed(2)}` : delta.toFixed(2))}
      </span>
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary">
          Optimization Outcome Metrics
        </h4>
        <span className="text-[11px] font-mono text-text-muted">
          Current vs Mathematically Optimized
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Expected Return */}
        <div className="p-4 rounded-xl bg-surface border border-border-theme flex flex-col justify-between shadow-card">
          <div>
            <div className="flex items-center justify-between text-text-muted text-xs mb-2">
              <span className="font-medium">Expected Annual Return</span>
              <TrendingUp className="w-4 h-4 text-accent-primary" />
            </div>

            <div className="grid grid-cols-2 gap-3 mb-2">
              <div>
                <span className="text-[10px] text-text-muted block uppercase">Current</span>
                <span className="text-lg font-bold font-mono text-text-primary">
                  {currentReturn !== null ? formatPercent(currentReturn, false) : '—'}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-status-positive block uppercase">Optimized</span>
                <span className="text-lg font-bold font-mono text-status-positive">
                  {optReturn !== null ? formatPercent(optReturn, false) : '—'}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-border-theme flex items-center justify-between text-xs">
            <span className="text-text-muted">Expected Shift:</span>
            {renderDelta(returnDelta, 'percent', 'positive')}
          </div>
        </div>

        {/* Volatility (Total Risk) */}
        <div className="p-4 rounded-xl bg-surface border border-border-theme flex flex-col justify-between shadow-card">
          <div>
            <div className="flex items-center justify-between text-text-muted text-xs mb-2">
              <span className="font-medium">Annualized Volatility (σ)</span>
              <Activity className="w-4 h-4 text-status-info" />
            </div>

            <div className="grid grid-cols-2 gap-3 mb-2">
              <div>
                <span className="text-[10px] text-text-muted block uppercase">Current</span>
                <span className="text-lg font-bold font-mono text-text-primary">
                  {currentVol !== null ? formatPercent(currentVol, false) : '—'}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-status-positive block uppercase">Optimized</span>
                <span className="text-lg font-bold font-mono text-status-positive">
                  {optVol !== null ? formatPercent(optVol, false) : '—'}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-border-theme flex items-center justify-between text-xs">
            <span className="text-text-muted">Variance Shift:</span>
            {renderDelta(volDelta, 'percent', 'negative')}
          </div>
        </div>

        {/* Sharpe Ratio */}
        <div className="p-4 rounded-xl bg-surface border border-border-theme flex flex-col justify-between shadow-card">
          <div>
            <div className="flex items-center justify-between text-text-muted text-xs mb-2">
              <span className="font-medium">Sharpe Ratio</span>
              <Shield className="w-4 h-4 text-status-warning" />
            </div>

            <div className="grid grid-cols-2 gap-3 mb-2">
              <div>
                <span className="text-[10px] text-text-muted block uppercase">Current</span>
                <span className="text-lg font-bold font-mono text-text-primary">
                  {currentSharpe !== null ? formatRatio(currentSharpe, 2) : '—'}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-status-positive block uppercase">Optimized</span>
                <span className="text-lg font-bold font-mono text-status-positive">
                  {optSharpe !== null ? formatRatio(optSharpe, 2) : '—'}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-border-theme flex items-center justify-between text-xs">
            <span className="text-text-muted">Risk-Adjusted Gain:</span>
            {renderDelta(sharpeDelta, 'ratio', 'positive')}
          </div>
        </div>
      </div>
    </div>
  );
};
