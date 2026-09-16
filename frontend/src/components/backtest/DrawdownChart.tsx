import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import {
  BacktestResponse,
  getBacktestDrawdownCurve,
  getBacktestMaxDrawdown,
  getBacktestStrategyMetrics,
} from '../../types/portfolio';
import { Badge } from '../common/Badge';
import { ShieldAlert } from 'lucide-react';
import { formatDate } from '../../utils/formatters';
import { useChartTheme } from '../../hooks/useChartTheme';

export interface DrawdownChartProps {
  response: BacktestResponse | null;
  className?: string;
}

export const DrawdownChart: React.FC<DrawdownChartProps> = ({
  response,
  className = '',
}) => {
  const chartTheme = useChartTheme();
  const rawDrawdowns = useMemo(() => getBacktestDrawdownCurve(response), [response]);
  const stratMetrics = getBacktestStrategyMetrics(response);
  const maxDd = getBacktestMaxDrawdown(stratMetrics);

  // Normalize drawdowns to negative percentage (-5%, -15%)
  const chartData = useMemo(() => {
    if (!rawDrawdowns || rawDrawdowns.length === 0) return [];

    return rawDrawdowns.map((pt) => {
      let stratDd = pt.strategy_drawdown;
      let bmDd = pt.benchmark_drawdown;

      // Ensure negative percentage e.g. -12.4%
      if (stratDd !== null && stratDd !== undefined) {
        stratDd = Number(stratDd);
        if (stratDd > 0) stratDd = -stratDd; // if backend gave positive drawdown, flip to negative for underwater view
        if (Math.abs(stratDd) <= 1.0) stratDd = stratDd * 100;
      }

      if (bmDd !== null && bmDd !== undefined) {
        bmDd = Number(bmDd);
        if (bmDd > 0) bmDd = -bmDd;
        if (Math.abs(bmDd) <= 1.0) bmDd = bmDd * 100;
      }

      return {
        date: pt.date,
        formattedDate: formatDate(pt.date),
        strategy_drawdown: stratDd,
        benchmark_drawdown: bmDd,
      };
    });
  }, [rawDrawdowns]);

  if (!response || chartData.length === 0) {
    return (
      <div className={`bg-surface border border-border-theme rounded-2xl p-8 text-center ${className}`}>
        <div className="w-12 h-12 rounded-xl bg-surface-secondary flex items-center justify-center mx-auto mb-3 text-text-muted">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-semibold text-text-primary mb-1">No Drawdown Series Returned</h4>
        <p className="text-xs text-text-muted max-w-sm mx-auto">
          The backend did not provide a discrete time-series drawdown curve for this backtest.
          {maxDd !== null && (
            <span className="block mt-1 font-mono text-status-negative">
              Reported Peak Max Drawdown: {(maxDd * (Math.abs(maxDd) <= 1 ? 100 : 1)).toFixed(2)}%
            </span>
          )}
        </p>
      </div>
    );
  }

  // Custom Dual Theme Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <div className="bg-surface-elevated border border-border-theme rounded-xl p-3 shadow-card-hover text-xs font-mono space-y-1.5 min-w-[180px]">
        <div className="text-[11px] text-text-muted font-sans font-semibold pb-1 border-b border-border-subtle">
          {label}
        </div>
        {payload.map((entry: any) => {
          const isStrat = entry.dataKey === 'strategy_drawdown';
          const name = isStrat ? 'Strategy Drawdown' : `Benchmark (${response.benchmark || '^NSEI'})`;
          const val = entry.value;

          return (
            <div key={entry.dataKey} className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-1.5 text-text-secondary">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="font-sans text-[11px]">{name}:</span>
              </span>
              <span className="font-bold font-mono text-status-negative">
                {val !== null && val !== undefined ? `${val.toFixed(2)}%` : 'N/A'}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className={`bg-surface border border-border-theme rounded-2xl p-6 shadow-card space-y-4 ${className}`}>
      <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-border-subtle">
        <div>
          <h4 className="text-sm font-bold text-text-primary flex items-center gap-2">
            <span>Historical Underwater Drawdown Profile</span>
            <Badge variant="danger" size="sm">Tail Risk</Badge>
          </h4>
          <p className="text-xs text-text-muted mt-0.5">
            Realized peak-to-trough equity drops beneath rolling high-water marks
          </p>
        </div>

        {maxDd !== null && (
          <div className="flex items-center gap-2 bg-surface-secondary/70 px-3 py-1.5 rounded-lg border border-border-theme text-xs">
            <span className="text-text-muted">Peak Strategy Drawdown:</span>
            <span className="font-mono font-bold text-status-negative">
              {(maxDd * (Math.abs(maxDd) <= 1 ? 100 : 1)).toFixed(2)}%
            </span>
          </div>
        )}
      </div>

      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 20, left: 10, bottom: 5 }}
          >
            <defs>
              <linearGradient id="stratDdGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={chartTheme.negative} stopOpacity={0.4} />
                <stop offset="95%" stopColor={chartTheme.negative} stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="bmDdGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={chartTheme.info} stopOpacity={0.25} />
                <stop offset="95%" stopColor={chartTheme.info} stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis
              dataKey="formattedDate"
              stroke={chartTheme.axis}
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: chartTheme.border }}
              minTickGap={30}
            />
            <YAxis
              stroke={chartTheme.axis}
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: chartTheme.border }}
              tickFormatter={(val) => `${val.toFixed(0)}%`}
              domain={['dataMin', 0]}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0} stroke={chartTheme.border} strokeWidth={1} />
            <Legend
              verticalAlign="bottom"
              height={32}
              iconType="circle"
              wrapperStyle={{ fontSize: '11px', color: chartTheme.muted }}
              formatter={(value) => {
                if (value === 'strategy_drawdown') return 'Strategy Drawdown (Under HWM)';
                if (value === 'benchmark_drawdown') return `Benchmark (${response.benchmark || '^NSEI'})`;
                return value;
              }}
            />

            {/* Benchmark Drawdown Area */}
            <Area
              type="monotone"
              dataKey="benchmark_drawdown"
              name="benchmark_drawdown"
              stroke={chartTheme.info}
              strokeWidth={1.5}
              fillOpacity={1}
              fill="url(#bmDdGrad)"
            />

            {/* Strategy Drawdown Area */}
            <Area
              type="monotone"
              dataKey="strategy_drawdown"
              name="strategy_drawdown"
              stroke={chartTheme.negative}
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#stratDdGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="text-[11px] text-text-muted pt-2 border-t border-border-subtle flex items-center justify-between">
        <span>A value of 0% indicates trading at an all-time peak portfolio high-water mark.</span>
        <span>Deeper drops represent larger historical capital drawdown exposure.</span>
      </div>
    </div>
  );
};
