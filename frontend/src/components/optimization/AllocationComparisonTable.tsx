import React from 'react';
import { OptimizedAssetWeight } from '../../types/portfolio';
import { formatPercent, formatCurrency } from '../../utils/formatters';
import {
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from 'lucide-react';

export interface AllocationComparisonTableProps {
  comparisons: OptimizedAssetWeight[];
  portfolioValue?: number | null;
  currency?: string;
  className?: string;
}

export const AllocationComparisonTable: React.FC<AllocationComparisonTableProps> = ({
  comparisons,
  portfolioValue,
  currency = 'INR',
  className = '',
}) => {
  if (!comparisons || comparisons.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-500 text-xs">
        No comparative allocation records available. Run the optimization algorithm to generate weights.
      </div>
    );
  }

  const renderDirectionBadge = (item: OptimizedAssetWeight, delta: number) => {
    const isZero = Math.abs(delta) < 0.25; // negligible threshold
    if (isZero) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
          <Minus className="w-2.5 h-2.5" /> Hold
        </span>
      );
    }

    if (delta > 0) {
      const cur = typeof item.current_weight === 'string' ? parseFloat(item.current_weight) : item.current_weight;
      const isNew = !cur || cur <= 0.01;
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <ArrowUpRight className="w-2.5 h-2.5" />
          {isNew ? 'New Entry' : `Overweight (+${delta.toFixed(1)}%)`}
        </span>
      );
    }

    const tgt = typeof item.target_weight === 'string' ? parseFloat(item.target_weight) : item.target_weight;
    const isExit = !tgt || tgt <= 0.01;
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <ArrowDownRight className="w-2.5 h-2.5" />
        {isExit ? 'Full Exit' : `Underweight (${delta.toFixed(1)}%)`}
      </span>
    );
  };

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Target Weight Rebalance Schedule
          </h4>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Theoretical target weight adjustments derived mathematically under optimizer bounds
          </p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              <th className="py-3 px-4">Asset / Ticker</th>
              <th className="py-3 px-4 text-right">
                Current Weight
                <span className="block text-[9px] font-normal text-cyan-400">"What I own"</span>
              </th>
              <th className="py-3 px-4 text-right">
                Target Weight
                <span className="block text-[9px] font-normal text-emerald-400">"Optimizer"</span>
              </th>
              <th className="py-3 px-4 text-right">Weight Delta</th>
              {portfolioValue ? (
                <th className="py-3 px-4 text-right">Target Value</th>
              ) : null}
              <th className="py-3 px-4 text-center">Mathematical Direction</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {comparisons.map((item, idx) => {
              const curWeight =
                typeof item.current_weight === 'string'
                  ? parseFloat(item.current_weight)
                  : item.current_weight;
              const tgtWeight =
                typeof item.target_weight === 'string'
                  ? parseFloat(item.target_weight)
                  : item.target_weight;
              const delta =
                item.weight_difference !== undefined && item.weight_difference !== null
                  ? typeof item.weight_difference === 'string'
                    ? parseFloat(item.weight_difference)
                    : item.weight_difference
                  : tgtWeight - curWeight;

              const targetCapValue =
                portfolioValue && tgtWeight !== null
                  ? (portfolioValue * (tgtWeight / 100))
                  : null;

              return (
                <tr
                  key={`asset-comp-${item.ticker || idx}`}
                  className="hover:bg-slate-800/40 transition-colors"
                >
                  <td className="py-3 px-4 font-mono font-bold text-slate-100">
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-400">{item.ticker || item.symbol}</span>
                      {item.name && (
                        <span className="text-[11px] font-sans font-normal text-slate-400 truncate max-w-[140px]">
                          {item.name}
                        </span>
                      )}
                    </div>
                  </td>

                  <td className="py-3 px-4 text-right font-mono font-semibold text-slate-200">
                    {formatPercent(curWeight, false)}
                  </td>

                  <td className="py-3 px-4 text-right font-mono font-bold text-emerald-400">
                    {formatPercent(tgtWeight, false)}
                  </td>

                  <td className="py-3 px-4 text-right font-mono font-bold">
                    <span
                      className={
                        delta > 0
                          ? 'text-emerald-400'
                          : delta < 0
                          ? 'text-rose-400'
                          : 'text-slate-400'
                      }
                    >
                      {delta > 0 ? `+${delta.toFixed(2)}%` : `${delta.toFixed(2)}%`}
                    </span>
                  </td>

                  {portfolioValue ? (
                    <td className="py-3 px-4 text-right font-mono text-slate-300">
                      {targetCapValue !== null ? formatCurrency(targetCapValue, currency) : '—'}
                    </td>
                  ) : null}

                  <td className="py-3 px-4 text-center">
                    {renderDirectionBadge(item, delta)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
