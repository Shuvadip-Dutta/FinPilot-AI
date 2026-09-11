import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  RefreshCw,
  ArrowRight,
  DollarSign,
  Percent,
  Layers,
} from 'lucide-react';
import {
  BacktestResponse,
  RebalanceEvent,
  getBacktestRebalanceEvents,
} from '../../types/portfolio';
import { Badge } from '../common/Badge';
import { formatCurrency, formatDate } from '../../utils/formatters';

export interface RebalanceTableProps {
  response: BacktestResponse | null;
  currency?: string;
  className?: string;
}

export const RebalanceTable: React.FC<RebalanceTableProps> = ({
  response,
  currency = 'INR',
  className = '',
}) => {
  const events = getBacktestRebalanceEvents(response);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0); // expand first by default

  if (!response || events.length === 0) {
    return (
      <div className={`bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center ${className}`}>
        <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center mx-auto mb-3 text-slate-500">
          <RefreshCw className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-semibold text-slate-200 mb-1">No Rebalance Events Recorded</h4>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          The walk-forward evaluation did not return discrete periodic rebalancing records.
        </p>
      </div>
    );
  }

  const toggleExpand = (idx: number) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  // Helper to extract weight details from event
  const getWeightBreakdown = (event: RebalanceEvent) => {
    // If backend provided pre-structured details array
    if (Array.isArray(event.details) && event.details.length > 0) {
      return event.details.map((d) => {
        const prev = Number(d.prev_weight ?? 0);
        const target = Number(d.target_weight ?? 0);
        const delta = Number(d.delta ?? target - prev);
        return {
          ticker: d.ticker,
          prev: Math.abs(prev) <= 1.0 ? prev * 100 : prev,
          target: Math.abs(target) <= 1.0 ? target * 100 : target,
          delta: Math.abs(delta) <= 1.0 ? delta * 100 : delta,
        };
      });
    }

    // If backend provided dictionaries: previous_allocation / target_allocation or prev_weights / new_weights
    const prevAlloc = event.previous_allocation || event.prev_weights || {};
    const targetAlloc = event.target_allocation || event.target_weights || event.new_weights || event.weights || {};

    const allTickers = Array.from(
      new Set([...Object.keys(prevAlloc), ...Object.keys(targetAlloc)])
    );

    return allTickers.map((ticker) => {
      let prev = Number(prevAlloc[ticker] ?? 0);
      let target = Number(targetAlloc[ticker] ?? 0);

      // Normalize if in 0-1 decimal range
      if (Math.abs(prev) <= 1.0) prev = prev * 100;
      if (Math.abs(target) <= 1.0) target = target * 100;

      const delta = target - prev;
      return {
        ticker,
        prev,
        target,
        delta,
      };
    });
  };

  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl space-y-0 ${className}`}>
      {/* Table Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between flex-wrap gap-3 bg-slate-950/50">
        <div>
          <h4 className="text-sm font-bold text-white flex items-center gap-2">
            <span>Periodic Walk-Forward Rebalance Events</span>
            <Badge variant="info" size="sm">
              {events.length} {events.length === 1 ? 'Cycle' : 'Cycles'}
            </Badge>
          </h4>
          <p className="text-xs text-slate-400 mt-0.5">
            Discrete re-optimization dates, turnover volume, and portfolio asset adjustments
          </p>
        </div>
      </div>

      {/* Rebalance Events List */}
      <div className="divide-y divide-slate-800/80">
        {events.map((event, idx) => {
          const dateStr = event.date || event.rebalance_date || `Event #${idx + 1}`;
          const isExpanded = expandedIndex === idx;
          const weights = getWeightBreakdown(event);

          let turnoverVal = Number(event.turnover);
          if (!isNaN(turnoverVal) && Math.abs(turnoverVal) <= 1.0) {
            turnoverVal = turnoverVal * 100;
          }

          const costVal = Number(event.transaction_cost ?? event.cost);

          return (
            <div key={idx} className="transition-colors">
              {/* Row Header Button */}
              <button
                type="button"
                onClick={() => toggleExpand(idx)}
                className="w-full text-left p-4 hover:bg-slate-850/50 transition-colors flex items-center justify-between flex-wrap gap-4 text-xs font-mono"
              >
                <div className="flex items-center gap-3">
                  <div className="text-slate-400">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-cyan-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-md bg-slate-800 text-slate-300 flex items-center justify-center text-[10px] font-bold">
                      {idx + 1}
                    </span>
                    <span className="font-bold text-white text-sm">
                      {formatDate(dateStr)}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  {/* Turnover */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400 font-sans">Turnover:</span>
                    <span className="font-bold text-slate-200">
                      {!isNaN(turnoverVal) ? `${turnoverVal.toFixed(1)}%` : '—'}
                    </span>
                  </div>

                  {/* Transaction Cost */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400 font-sans">Cost:</span>
                    <span className="font-bold text-amber-400">
                      {!isNaN(costVal) ? formatCurrency(costVal, currency) : '—'}
                    </span>
                  </div>

                  {/* Positions altered */}
                  <div className="hidden sm:flex items-center gap-1.5 text-slate-400 font-sans">
                    <span>Assets:</span>
                    <span className="font-mono text-cyan-300 font-bold">{weights.length}</span>
                  </div>

                  <Badge variant={isExpanded ? 'info' : 'default'} size="sm">
                    {isExpanded ? 'Hide Details' : 'View Allocation Shift'}
                  </Badge>
                </div>
              </button>

              {/* Expanded Weight Detail Table */}
              {isExpanded && (
                <div className="bg-slate-950/70 p-4 border-t border-slate-800/80">
                  {weights.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="text-slate-400 border-b border-slate-800 font-mono text-[10px] uppercase">
                            <th className="py-2 px-3">Asset Ticker</th>
                            <th className="py-2 px-3 text-right">Previous Weight</th>
                            <th className="py-2 px-3 text-center">Shift</th>
                            <th className="py-2 px-3 text-right">New Target Weight</th>
                            <th className="py-2 px-3 text-right">Net Delta</th>
                            <th className="py-2 px-3 text-center">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/40 font-mono">
                          {weights.map((w) => {
                            const isNew = w.prev === 0 && w.target > 0;
                            const isExit = w.prev > 0 && w.target === 0;
                            const isUp = w.delta > 0.05;
                            const isDown = w.delta < -0.05;

                            return (
                              <tr key={w.ticker} className="hover:bg-slate-900/50">
                                <td className="py-2.5 px-3 font-bold text-white">
                                  {w.ticker}
                                </td>
                                <td className="py-2.5 px-3 text-right text-slate-400">
                                  {w.prev.toFixed(1)}%
                                </td>
                                <td className="py-2.5 px-3 text-center text-slate-600">
                                  <ArrowRight className="w-3.5 h-3.5 mx-auto" />
                                </td>
                                <td className="py-2.5 px-3 text-right font-bold text-cyan-300">
                                  {w.target.toFixed(1)}%
                                </td>
                                <td
                                  className={`py-2.5 px-3 text-right font-bold ${
                                    w.delta > 0
                                      ? 'text-emerald-400'
                                      : w.delta < 0
                                      ? 'text-rose-400'
                                      : 'text-slate-400'
                                  }`}
                                >
                                  {w.delta > 0 ? '+' : ''}
                                  {w.delta.toFixed(1)}%
                                </td>
                                <td className="py-2.5 px-3 text-center">
                                  {isNew ? (
                                    <span className="text-[10px] px-2 py-0.5 rounded-sm bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 font-sans">
                                      New Entry
                                    </span>
                                  ) : isExit ? (
                                    <span className="text-[10px] px-2 py-0.5 rounded-sm bg-rose-950/60 text-rose-400 border border-rose-800/40 font-sans">
                                      Exit Position
                                    </span>
                                  ) : isUp ? (
                                    <span className="text-[10px] px-2 py-0.5 rounded-sm bg-cyan-950/60 text-cyan-400 border border-cyan-800/40 font-sans">
                                      Increase
                                    </span>
                                  ) : isDown ? (
                                    <span className="text-[10px] px-2 py-0.5 rounded-sm bg-amber-950/60 text-amber-400 border border-amber-800/40 font-sans">
                                      Trim
                                    </span>
                                  ) : (
                                    <span className="text-[10px] px-2 py-0.5 rounded-sm bg-slate-800 text-slate-400 font-sans">
                                      Hold
                                    </span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-center py-4 text-slate-500 text-xs font-sans">
                      No individual asset breakdown details provided for this event.
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
