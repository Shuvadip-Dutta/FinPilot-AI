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
      <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-xs flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Total Invested Capital
          </span>
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <DollarSign className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
            {investedValue !== null ? formatCurrency(investedValue, 'INR') : '—'}
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
            Authoritative cost basis from holdings
          </p>
        </div>
      </div>

      {/* Live Market Valuation (Authoritative from AI Analysis) */}
      <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-xs flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Live Market Valuation
          </span>
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <PieChart className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
            {liveValuation !== null ? formatCurrency(liveValuation, 'INR') : '—'}
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${liveValuation !== null ? 'bg-cyan-400' : 'bg-slate-600'}`}></span>
            {liveValuation !== null ? 'Live quote valuation' : 'Run AI Analysis for live quotes'}
          </p>
        </div>
      </div>

      {/* Net Profit / Loss */}
      <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-xs flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Unrealized P/L
          </span>
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              isProfitable === null
                ? 'bg-slate-800 text-slate-400'
                : isProfitable
                ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                : 'bg-rose-500/10 border border-rose-500/20 text-rose-400'
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
                ? 'text-slate-400'
                : isProfitable
                ? 'text-emerald-400'
                : 'text-rose-400'
            }`}
          >
            <span>{livePnl !== null ? formatCurrency(livePnl, 'INR') : '—'}</span>
            {livePnlPercent !== null && (
              <span className="text-sm font-semibold">
                ({formatPercent(livePnlPercent, true)})
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
            <span
              className={`inline-block w-1.5 h-1.5 rounded-full ${
                isProfitable === null
                  ? 'bg-slate-600'
                  : isProfitable
                  ? 'bg-emerald-400'
                  : 'bg-rose-400'
              }`}
            ></span>
            {livePnl !== null ? 'Live quote return' : 'Requires AI Analysis'}
          </p>
        </div>
      </div>

      {/* Holdings Count */}
      <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-xs flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Active Holdings
          </span>
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <Layers className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
            {count} {count === 1 ? 'Position' : 'Positions'}
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-cyan-400" />
            <span>Persisted ledger assets</span>
          </p>
        </div>
      </div>
    </div>
  );
};
