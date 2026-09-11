import React from 'react';
import { OptimizedAssetWeight } from '../../types/portfolio';
import { formatPercent } from '../../utils/formatters';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { BarChart3, Info } from 'lucide-react';

export interface AllocationComparisonChartProps {
  comparisons: OptimizedAssetWeight[];
  className?: string;
}

export const AllocationComparisonChart: React.FC<AllocationComparisonChartProps> = ({
  comparisons,
  className = '',
}) => {
  if (!comparisons || comparisons.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl bg-slate-950/40">
        <BarChart3 className="w-8 h-8 text-slate-600 mb-2" />
        <p className="text-sm font-semibold text-slate-300">No Allocation Data Available</p>
        <p className="text-xs text-slate-500 max-w-sm mt-1">
          Execute the optimizer to generate a side-by-side comparative allocation breakdown.
        </p>
      </div>
    );
  }

  // Format data for Recharts grouped bar chart
  const chartData = comparisons.map((item) => {
    const cur = typeof item.current_weight === 'string' ? parseFloat(item.current_weight) : item.current_weight;
    const tgt = typeof item.target_weight === 'string' ? parseFloat(item.target_weight) : item.target_weight;
    return {
      ticker: item.ticker || item.symbol || 'N/A',
      name: item.name,
      currentWeight: Number((cur ?? 0).toFixed(2)),
      targetWeight: Number((tgt ?? 0).toFixed(2)),
    };
  });

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Allocation Comparison (Current vs Target Optimized)
          </h4>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-cyan-400" />
            <span className="text-slate-300 font-medium">Current Allocation ("What I own")</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-400" />
            <span className="text-slate-300 font-medium">Optimized Target ("Optimizer preference")</span>
          </div>
        </div>
      </div>

      <div className="w-full h-80 min-h-[320px] bg-slate-950/60 border border-slate-800/80 rounded-xl p-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 20, right: 20, left: -10, bottom: 20 }}
            barGap={4}
          >
            <XAxis
              dataKey="ticker"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
              tickFormatter={(val) => `${val}%`}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  const currentVal = payload.find((p) => p.dataKey === 'currentWeight')?.value;
                  const targetVal = payload.find((p) => p.dataKey === 'targetWeight')?.value;
                  const delta =
                    targetVal !== undefined && currentVal !== undefined
                      ? Number(targetVal) - Number(currentVal)
                      : null;

                  return (
                    <div className="bg-slate-900 border border-slate-700 p-3 rounded-xl shadow-xl text-xs space-y-1.5">
                      <div className="font-bold text-slate-100 border-b border-slate-800 pb-1 flex items-center justify-between gap-4">
                        <span>{label}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 text-cyan-300">
                        <span>Current Weight:</span>
                        <span className="font-mono font-bold">
                          {currentVal !== undefined ? `${Number(currentVal).toFixed(2)}%` : '—'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-4 text-emerald-300">
                        <span>Optimized Target:</span>
                        <span className="font-mono font-bold">
                          {targetVal !== undefined ? `${Number(targetVal).toFixed(2)}%` : '—'}
                        </span>
                      </div>
                      {delta !== null && (
                        <div className="flex items-center justify-between gap-4 pt-1 border-t border-slate-800 text-slate-400">
                          <span>Rebalance Delta:</span>
                          <span
                            className={`font-mono font-semibold ${
                              delta > 0
                                ? 'text-emerald-400'
                                : delta < 0
                                ? 'text-rose-400'
                                : 'text-slate-400'
                            }`}
                          >
                            {delta > 0 ? `+${delta.toFixed(2)}%` : `${delta.toFixed(2)}%`}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                }
                return null;
              }}
            />
            <ReferenceLine y={0} stroke="#475569" />
            <Bar
              dataKey="currentWeight"
              name="Current Allocation"
              fill="#06b6d4"
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
            <Bar
              dataKey="targetWeight"
              name="Optimized Target"
              fill="#10b981"
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 pl-1">
        <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span>
          Shows mathematical target allocations produced by the backend optimizer vs your current capital deployment.
        </span>
      </div>
    </div>
  );
};
