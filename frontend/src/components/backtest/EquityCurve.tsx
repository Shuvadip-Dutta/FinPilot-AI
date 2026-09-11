import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import {
  BacktestResponse,
  getBacktestEquityCurve,
} from '../../types/portfolio';
import { Badge } from '../common/Badge';
import { TrendingUp, Eye, EyeOff } from 'lucide-react';
import { formatCurrency, formatDate } from '../../utils/formatters';

export interface EquityCurveProps {
  response: BacktestResponse | null;
  currency?: string;
  initialCapital?: number;
  className?: string;
}

export const EquityCurve: React.FC<EquityCurveProps> = ({
  response,
  currency = 'INR',
  initialCapital = 100000,
  className = '',
}) => {
  const [showStrategy, setShowStrategy] = useState(true);
  const [showBuyAndHold, setShowBuyAndHold] = useState(true);
  const [showBenchmark, setShowBenchmark] = useState(true);
  const [scaleMode, setScaleMode] = useState<'currency' | 'percent'>('currency');

  const rawCurve = useMemo(() => getBacktestEquityCurve(response), [response]);

  // Compute normalized or currency series
  const chartData = useMemo(() => {
    if (!rawCurve || rawCurve.length === 0) return [];

    const baseStrat = rawCurve.find((p) => p.strategy !== null)?.strategy || initialCapital;
    const baseBnh = rawCurve.find((p) => p.buy_and_hold !== null)?.buy_and_hold || initialCapital;
    const baseBm = rawCurve.find((p) => p.benchmark !== null)?.benchmark || initialCapital;

    return rawCurve.map((point) => {
      let stratVal = point.strategy;
      let bnhVal = point.buy_and_hold;
      let bmVal = point.benchmark;

      if (scaleMode === 'percent') {
        stratVal = stratVal !== null ? ((stratVal - baseStrat) / baseStrat) * 100 : null;
        bnhVal = bnhVal !== null ? ((bnhVal - baseBnh) / baseBnh) * 100 : null;
        bmVal = bmVal !== null ? ((bmVal - baseBm) / baseBm) * 100 : null;
      }

      return {
        date: point.date,
        formattedDate: formatDate(point.date),
        strategy: stratVal,
        buy_and_hold: bnhVal,
        benchmark: bmVal,
        rawStrat: point.strategy,
        rawBnh: point.buy_and_hold,
        rawBm: point.benchmark,
      };
    });
  }, [rawCurve, scaleMode, initialCapital]);

  if (!response || chartData.length === 0) {
    return (
      <div className={`bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center ${className}`}>
        <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center mx-auto mb-3 text-slate-500">
          <TrendingUp className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-semibold text-slate-200 mb-1">No Equity Curve Data Available</h4>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          The backend did not return discrete periodic equity curve points for this backtest run.
        </p>
      </div>
    );
  }

  // Custom Dark Theme Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <div className="bg-slate-950/95 border border-slate-700/80 rounded-xl p-3.5 shadow-2xl backdrop-blur-md text-xs font-mono space-y-2 min-w-[200px]">
        <div className="text-[11px] text-slate-400 font-sans font-semibold pb-1.5 border-b border-slate-800">
          {label}
        </div>
        {payload.map((entry: any) => {
          const isStrat = entry.dataKey === 'strategy';
          const isBnh = entry.dataKey === 'buy_and_hold';
          const name = isStrat
            ? 'Strategy (Rolling WF)'
            : isBnh
            ? 'Buy & Hold'
            : `Benchmark (${response.benchmark || '^NSEI'})`;

          const val = entry.value;
          const formatted =
            val !== null && val !== undefined
              ? scaleMode === 'percent'
                ? `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`
                : formatCurrency(val, currency)
              : 'N/A';

          return (
            <div key={entry.dataKey} className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="font-sans text-[11px]">{name}:</span>
              </span>
              <span className="font-bold font-mono" style={{ color: entry.color }}>
                {formatted}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4 ${className}`}>
      {/* Chart Controls Header */}
      <div className="flex items-center justify-between flex-wrap gap-4 pb-3 border-b border-slate-800">
        <div>
          <h4 className="text-sm font-bold text-white flex items-center gap-2">
            <span>Cumulative Out-of-Sample Equity Growth Trajectory</span>
            <Badge variant="info" size="sm">Multi-Asset</Badge>
          </h4>
          <p className="text-xs text-slate-400 mt-0.5">
            Realized trajectory evaluated strictly across forward out-of-sample segments with friction
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Scale Mode Switch */}
          <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              type="button"
              onClick={() => setScaleMode('currency')}
              className={`px-2.5 py-1 rounded transition-colors ${
                scaleMode === 'currency'
                  ? 'bg-cyan-500/20 text-cyan-300 font-semibold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Absolute ({currency})
            </button>
            <button
              type="button"
              onClick={() => setScaleMode('percent')}
              className={`px-2.5 py-1 rounded transition-colors ${
                scaleMode === 'percent'
                  ? 'bg-cyan-500/20 text-cyan-300 font-semibold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Normalized (%)
            </button>
          </div>

          {/* Series Toggles */}
          <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              type="button"
              onClick={() => setShowStrategy(!showStrategy)}
              className={`px-2 py-1 rounded flex items-center gap-1.5 text-[11px] font-mono transition-colors ${
                showStrategy
                  ? 'bg-cyan-950 text-cyan-400 border border-cyan-800/60'
                  : 'text-slate-500 line-through'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              Strategy
            </button>
            <button
              type="button"
              onClick={() => setShowBuyAndHold(!showBuyAndHold)}
              className={`px-2 py-1 rounded flex items-center gap-1.5 text-[11px] font-mono transition-colors ${
                showBuyAndHold
                  ? 'bg-amber-950 text-amber-400 border border-amber-800/60'
                  : 'text-slate-500 line-through'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              Buy & Hold
            </button>
            <button
              type="button"
              onClick={() => setShowBenchmark(!showBenchmark)}
              className={`px-2 py-1 rounded flex items-center gap-1.5 text-[11px] font-mono transition-colors ${
                showBenchmark
                  ? 'bg-purple-950 text-purple-400 border border-purple-800/60'
                  : 'text-slate-500 line-through'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-purple-400" />
              Benchmark
            </button>
          </div>
        </div>
      </div>

      {/* Recharts Interactive Line Chart */}
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 15, right: 20, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
            <XAxis
              dataKey="formattedDate"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
              minTickGap={30}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
              tickFormatter={(val) =>
                scaleMode === 'percent'
                  ? `${val >= 0 ? '+' : ''}${val.toFixed(0)}%`
                  : val >= 1000000
                  ? `${(val / 1000000).toFixed(1)}M`
                  : val >= 1000
                  ? `${(val / 1000).toFixed(0)}k`
                  : `${val}`
              }
              domain={['auto', 'auto']}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }}
              formatter={(value) => {
                if (value === 'strategy') return 'Strategy (Rolling WF)';
                if (value === 'buy_and_hold') return 'Buy & Hold Baseline';
                if (value === 'benchmark') return `Benchmark (${response.benchmark || '^NSEI'})`;
                return value;
              }}
            />

            {/* Benchmark Series */}
            {showBenchmark && (
              <Line
                type="monotone"
                dataKey="benchmark"
                name="benchmark"
                stroke="#a855f7"
                strokeWidth={1.75}
                strokeDasharray="4 4"
                dot={false}
                activeDot={{ r: 4, fill: '#a855f7' }}
              />
            )}

            {/* Buy & Hold Series */}
            {showBuyAndHold && (
              <Line
                type="monotone"
                dataKey="buy_and_hold"
                name="buy_and_hold"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#f59e0b' }}
              />
            )}

            {/* Strategy Series (Hero) */}
            {showStrategy && (
              <Line
                type="monotone"
                dataKey="strategy"
                name="strategy"
                stroke="#06b6d4"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5, fill: '#06b6d4', stroke: '#fff', strokeWidth: 1.5 }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-800/80">
        <span>
          Data Points: <strong className="text-slate-300 font-mono">{chartData.length}</strong> intervals
        </span>
        <span>All returns account for calibrated transaction friction and rebalance drift.</span>
      </div>
    </div>
  );
};
