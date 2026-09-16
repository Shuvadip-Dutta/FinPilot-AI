import React from 'react';
import { OptimizedAssetWeight } from '../../types/portfolio';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { BarChart3, Info } from 'lucide-react';
import { useChartTheme } from '../../hooks/useChartTheme';

export interface AllocationComparisonChartProps {
  comparisons: OptimizedAssetWeight[];
  className?: string;
}

export const AllocationComparisonChart: React.FC<AllocationComparisonChartProps> = ({
  comparisons,
  className = '',
}) => {
  const chartTheme = useChartTheme();

  if (!comparisons || comparisons.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-center p-6 border border-dashed border-border-theme rounded-xl bg-surface-secondary/40">
        <BarChart3 className="w-8 h-8 text-text-muted mb-2" />
        <p className="text-sm font-semibold text-text-primary">No Allocation Data Available</p>
        <p className="text-xs text-text-muted max-w-sm mt-1">
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
          <BarChart3 className="w-4 h-4 text-accent-primary" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary">
            Allocation Comparison (Current vs Target Optimized)
          </h4>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: chartTheme.info }} />
            <span className="text-text-secondary font-medium">Current Allocation (&quot;What I own&quot;)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: chartTheme.accent }} />
            <span className="text-text-secondary font-medium">Optimized Target (&quot;Optimizer preference&quot;)</span>
          </div>
        </div>
      </div>

      <div className="w-full h-80 min-h-[320px] bg-surface border border-border-theme rounded-xl p-4 shadow-card">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 20, right: 20, left: -10, bottom: 20 }}
            barGap={4}
          >
            <XAxis
              dataKey="ticker"
              stroke={chartTheme.axis}
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: chartTheme.border }}
            />
            <YAxis
              stroke={chartTheme.axis}
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: chartTheme.border }}
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
                    <div className="bg-surface-elevated border border-border-theme p-3 rounded-xl shadow-card-hover text-xs space-y-1.5">
                      <div className="font-bold text-text-primary border-b border-border-subtle pb-1 flex items-center justify-between gap-4">
                        <span>{label}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4" style={{ color: chartTheme.info }}>
                        <span>Current Weight:</span>
                        <span className="font-mono font-bold">
                          {currentVal !== undefined ? `${Number(currentVal).toFixed(2)}%` : '—'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-4" style={{ color: chartTheme.accent }}>
                        <span>Optimized Target:</span>
                        <span className="font-mono font-bold">
                          {targetVal !== undefined ? `${Number(targetVal).toFixed(2)}%` : '—'}
                        </span>
                      </div>
                      {delta !== null && (
                        <div className="flex items-center justify-between gap-4 pt-1 border-t border-border-subtle text-text-muted">
                          <span>Rebalance Delta:</span>
                          <span
                            className={`font-mono font-semibold ${
                              delta > 0
                                ? 'text-status-positive'
                                : delta < 0
                                ? 'text-status-negative'
                                : 'text-text-muted'
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
            <ReferenceLine y={0} stroke={chartTheme.border} />
            <Bar
              dataKey="currentWeight"
              name="Current Allocation"
              fill={chartTheme.info}
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
            <Bar
              dataKey="targetWeight"
              name="Optimized Target"
              fill={chartTheme.accent}
              radius={[4, 4, 0, 0]}
              maxBarSize={40}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-1.5 text-[11px] text-text-muted pl-1">
        <Info className="w-3.5 h-3.5 text-text-muted shrink-0" />
        <span>
          Shows mathematical target allocations produced by the backend optimizer vs your current capital deployment.
        </span>
      </div>
    </div>
  );
};
