import React from 'react';
import {
  Portfolio,
  PortfolioStructuredValuation,
  getPortfolioInvestedValue,
} from '../../types/portfolio';
import { formatCurrency, formatPercent } from '../../utils/formatters';
import { TrendingUp, TrendingDown, DollarSign, PieChart, Layers, Sparkles } from 'lucide-react';

export interface PortfolioSummaryCardProps {
  portfolio: Portfolio | null;
  holdingsCount?: number;
  aiValuation?: PortfolioStructuredValuation | null;
  className?: string;
}

export const PortfolioSummaryCard: React.FC<PortfolioSummaryCardProps> = ({
  portfolio,
  holdingsCount,
  aiValuation,
  className = '',
}) => {
  // Invested value calculated from persisted ledger: quantity * average_price
  const investedValue = getPortfolioInvestedValue(portfolio);
  const count = holdingsCount ?? portfolio?.holdings?.length ?? 0;

  // Live valuation available only if AI analysis has been run
  const liveValuation = aiValuation?.current_value ?? null;
  const livePnl = aiValuation?.profit_loss ?? null;
  const livePnlPercent = aiValuation?.profit_loss_percentage ?? null;
  const isProfitable = livePnl !== null ? livePnl >= 0 : null;

  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
      {/* Total Invested Capital (Cost Basis) */}
      <div className="bg-surface border border-border-theme rounded-xl p-5 shadow-card flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
            Total Invested Capital
          </span>
          <div className="w-8 h-8 rounded-lg bg-accent-soft border border-accent-primary/20 flex items-center justify-center text-accent-primary">
            <DollarSign className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-text-primary tracking-tight">
            {investedValue !== null ? formatCurrency(investedValue, 'INR') : '—'}
          </div>
          <p className="text-xs text-text-muted mt-1 flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-primary"></span>
            Authoritative cost basis from holdings
          </p>
        </div>
      </div>

      {/* Live Market Valuation (Authoritative from AI Analysis) */}
      <div className="bg-surface border border-border-theme rounded-xl p-5 shadow-card flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
            Live Market Valuation
          </span>
          <div className="w-8 h-8 rounded-lg bg-accent-soft border border-accent-primary/20 flex items-center justify-center text-accent-primary">
            <PieChart className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-text-primary tracking-tight">
            {liveValuation !== null ? formatCurrency(liveValuation, 'INR') : '—'}
          </div>
          <p className="text-xs text-text-muted mt-1 flex items-center gap-1.5">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${liveValuation !== null ? 'bg-accent-primary' : 'bg-text-muted'}`}></span>
            {liveValuation !== null ? 'Live quote valuation' : 'Run AI Analysis for live quotes'}
          </p>
        </div>
      </div>

      {/* Net Profit / Loss */}
      <div className="bg-surface border border-border-theme rounded-xl p-5 shadow-card flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
            Unrealized P/L
          </span>
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              isProfitable === null
                ? 'bg-surface-secondary text-text-muted'
                : isProfitable
                ? 'bg-status-positive-soft border border-status-positive/20 text-status-positive'
                : 'bg-status-negative-soft border border-status-negative/20 text-status-negative'
            }`}
          >
            {isProfitable === null ? (
              <TrendingUp className="w-4 h-4" />
            ) : isProfitable ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
          </div>
        </div>
        <div className="mt-3">
          <div
            className={`text-2xl font-bold font-mono tracking-tight flex items-baseline gap-2 ${
              isProfitable === null
                ? 'text-text-muted'
                : isProfitable
                ? 'text-status-positive'
                : 'text-status-negative'
            }`}
          >
            <span>{livePnl !== null ? formatCurrency(livePnl, 'INR') : '—'}</span>
            {livePnlPercent !== null && (
              <span className="text-sm font-semibold">
                ({formatPercent(livePnlPercent, true)})
              </span>
            )}
          </div>
          <p className="text-xs text-text-muted mt-1 flex items-center gap-1.5">
            <span
              className={`inline-block w-1.5 h-1.5 rounded-full ${
                isProfitable === null
                  ? 'bg-text-muted'
                  : isProfitable
                  ? 'bg-status-positive'
                  : 'bg-status-negative'
              }`}
            ></span>
            {livePnl !== null ? 'Live quote return' : 'Requires AI Analysis'}
          </p>
        </div>
      </div>

      {/* Holdings Count */}
      <div className="bg-surface border border-border-theme rounded-xl p-5 shadow-card flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
            Active Holdings
          </span>
          <div className="w-8 h-8 rounded-lg bg-accent-soft border border-accent-primary/20 flex items-center justify-center text-accent-primary">
            <Layers className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-text-primary tracking-tight">
            {count} {count === 1 ? 'Position' : 'Positions'}
          </div>
          <p className="text-xs text-text-muted mt-1 flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-accent-primary" />
            <span>Persisted ledger assets</span>
          </p>
        </div>
      </div>
    </div>
  );
};
