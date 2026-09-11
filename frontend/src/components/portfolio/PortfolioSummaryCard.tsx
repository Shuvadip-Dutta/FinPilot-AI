import React from 'react';
import {
  Portfolio,
  getPortfolioCurrentValue,
  getPortfolioInvestedValue,
  getPortfolioPnL,
  getPortfolioPnLPercent,
  getPortfolioCashBalance,
} from '../../types/portfolio';
import { formatCurrency, formatPercent } from '../../utils/formatters';
import { TrendingUp, TrendingDown, DollarSign, Wallet, PieChart, Layers } from 'lucide-react';

export interface PortfolioSummaryCardProps {
  portfolio: Portfolio | null;
  holdingsCount?: number;
  className?: string;
}

export const PortfolioSummaryCard: React.FC<PortfolioSummaryCardProps> = ({
  portfolio,
  holdingsCount,
  className = '',
}) => {
  const currency = portfolio?.currency || 'INR';

  // Read backend-calculated metrics strictly without recalculating in React
  const currentValue = getPortfolioCurrentValue(portfolio);
  const investedValue = getPortfolioInvestedValue(portfolio);
  const pnl = getPortfolioPnL(portfolio);
  const pnlPercent = getPortfolioPnLPercent(portfolio);
  const cashBalance = getPortfolioCashBalance(portfolio);

  const isProfitable = pnl !== null ? pnl >= 0 : null;
  const count = holdingsCount ?? portfolio?.holdings_count ?? portfolio?.total_holdings ?? portfolio?.holdings?.length ?? 0;

  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
      {/* Total Current Valuation */}
      <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-xs flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Current Valuation
          </span>
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <PieChart className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
            {formatCurrency(currentValue, currency)}
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            Backend evaluated market value
          </p>
        </div>
      </div>

      {/* Invested Value */}
      <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-xs flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Invested Value
          </span>
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <DollarSign className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
            {formatCurrency(investedValue, currency)}
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
            Total cost basis
          </p>
        </div>
      </div>

      {/* Net P/L & P/L % */}
      <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-xs flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Total Profit / Loss
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
                ? 'text-slate-300'
                : isProfitable
                ? 'text-emerald-400'
                : 'text-rose-400'
            }`}
          >
            <span>{formatCurrency(pnl, currency)}</span>
            {pnlPercent !== null && (
              <span className="text-sm font-semibold">
                ({formatPercent(pnlPercent, true)})
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
            <span
              className={`inline-block w-1.5 h-1.5 rounded-full ${
                isProfitable === null
                  ? 'bg-slate-500'
                  : isProfitable
                  ? 'bg-emerald-400'
                  : 'bg-rose-400'
              }`}
            ></span>
            Unrealized return on investment
          </p>
        </div>
      </div>

      {/* Cash Balance or Holdings Count */}
      <div className="bg-slate-900/80 border border-slate-800/90 rounded-xl p-5 shadow-xs flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {cashBalance !== null ? 'Cash Balance' : 'Active Positions'}
          </span>
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            {cashBalance !== null ? <Wallet className="w-4 h-4" /> : <Layers className="w-4 h-4" />}
          </div>
        </div>
        <div className="mt-3">
          {cashBalance !== null ? (
            <>
              <div className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
                {formatCurrency(cashBalance, currency)}
              </div>
              <p className="text-xs text-slate-400 mt-1 flex items-center justify-between">
                <span>Unallocated cash</span>
                <span className="text-slate-400 font-mono">{count} positions</span>
              </p>
            </>
          ) : (
            <>
              <div className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
                {count} {count === 1 ? 'Holding' : 'Holdings'}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Portfolio active assets
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
