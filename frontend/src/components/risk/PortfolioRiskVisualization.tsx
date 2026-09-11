import React, { useState } from 'react';
import {
  PortfolioRiskResponse,
  DrawdownSeriesPoint,
  AssetRiskContribution,
  getRiskMaxDrawdown,
} from '../../types/portfolio';
import { formatPercent, formatRatio } from '../../utils/formatters';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import {
  TrendingDown,
  TrendingUp,
  Layers,
  PieChart as PieChartIcon,
  Info,
  Calendar,
  ShieldAlert,
} from 'lucide-react';

export interface PortfolioRiskVisualizationProps {
  riskData: PortfolioRiskResponse | null;
  portfolioName?: string;
  currency?: string;
  className?: string;
}

export const PortfolioRiskVisualization: React.FC<PortfolioRiskVisualizationProps> = ({
  riskData,
  portfolioName,
  currency = 'INR',
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<'cumulative' | 'drawdown' | 'contributions'>('cumulative');

  const seriesData: DrawdownSeriesPoint[] =
    riskData?.drawdown_series ?? riskData?.historical_series ?? [];

  const riskContributions: AssetRiskContribution[] =
    riskData?.risk_contributions ?? [];

  const maxDrawdown = getRiskMaxDrawdown(riskData);

  return (
    <div
      id="portfolio-risk-visualization"
      className={`bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 space-y-6 ${className}`}
    >
      {/* Scope & Conceptual Distinction Banner */}
      <div className="p-4 rounded-xl bg-slate-950/80 border border-cyan-500/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0 mt-0.5">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold tracking-wider uppercase text-cyan-300">
                Authoritative Quantitative Risk Framework
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800/60">
                Django Engine
              </span>
            </div>
            <div className="mt-1 flex flex-col sm:flex-row sm:items-center gap-2 text-xs text-slate-300">
              <span className="font-semibold text-slate-200">
                CURRENT PORTFOLIO:
              </span>
              <span className="text-slate-400">"What I currently own."</span>
              <span className="hidden sm:inline text-slate-600">•</span>
              <span className="font-semibold text-slate-200">
                RISK:
              </span>
              <span className="text-slate-400">"How the current portfolio has behaved historically."</span>
            </div>
          </div>
        </div>

        <div className="text-[11px] text-slate-400 border-l border-slate-800 md:pl-4 max-w-sm leading-relaxed">
          Quantitative risk measures dispersion, downside semi-variance, and peak-to-trough drawdowns based strictly on historical return matrices. Past risk patterns do not guarantee future tail resilience.
        </div>
      </div>

      {/* Visualizer Header with View Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <span>Historical Portfolio Risk & Drawdown Dynamics</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            {portfolioName ? `Evaluated for ${portfolioName}` : 'Portfolio asset trajectory'} • Base Currency: {currency}
          </p>
        </div>

        {/* View Toggle Tabs */}
        <div className="inline-flex rounded-lg bg-slate-950 p-1 border border-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab('cumulative')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === 'cumulative'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-xs'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Cumulative Trajectory</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('drawdown')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === 'drawdown'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30 shadow-xs'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <TrendingDown className="w-3.5 h-3.5" />
            <span>Underwater Drawdown</span>
          </button>
          {riskContributions.length > 0 && (
            <button
              type="button"
              onClick={() => setActiveTab('contributions')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'contributions'
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Risk Contributions</span>
            </button>
          )}
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div className="w-full h-80 min-h-[320px]">
        {activeTab === 'cumulative' && (
          seriesData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={seriesData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="cumReturnGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  stroke="#475569"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#334155' }}
                />
                <YAxis
                  stroke="#475569"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#334155' }}
                  tickFormatter={(val) => `${val}%`}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const returnVal = payload[0]?.value;
                      const benchmarkVal = payload[1]?.value;
                      return (
                        <div className="bg-slate-900 border border-slate-700 p-3 rounded-xl shadow-xl text-xs space-y-1">
                          <div className="font-semibold text-slate-300 border-b border-slate-800 pb-1 flex items-center gap-1.5">
                            <Calendar className="w-3 h-3 text-cyan-400" />
                            <span>{label}</span>
                          </div>
                          <div className="flex items-center justify-between gap-4 pt-1">
                            <span className="text-cyan-400">Portfolio Return:</span>
                            <span className="font-mono font-bold text-slate-100">
                              {returnVal !== undefined ? `${Number(returnVal).toFixed(2)}%` : '—'}
                            </span>
                          </div>
                          {benchmarkVal !== undefined && (
                            <div className="flex items-center justify-between gap-4 text-slate-400">
                              <span>Benchmark:</span>
                              <span className="font-mono font-medium">
                                {Number(benchmarkVal).toFixed(2)}%
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <ReferenceLine y={0} stroke="#64748b" strokeDasharray="3 3" />
                <Area
                  type="monotone"
                  dataKey="cumulative_return"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  fill="url(#cumReturnGrad)"
                  name="Portfolio Return"
                />
                {seriesData[0]?.benchmark_cumulative_return !== undefined && (
                  <Line
                    type="monotone"
                    dataKey="benchmark_cumulative_return"
                    stroke="#94a3b8"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                    name="Benchmark"
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl bg-slate-950/40">
              <TrendingUp className="w-8 h-8 text-slate-600 mb-2" />
              <p className="text-sm font-semibold text-slate-300">Historical Return Trajectory</p>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Time-series daily equity curves are computed by the quantitative backend upon continuous historical observation.
              </p>
            </div>
          )
        )}

        {activeTab === 'drawdown' && (
          seriesData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={seriesData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="drawdownGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.05} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.5} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  stroke="#475569"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#334155' }}
                />
                <YAxis
                  stroke="#475569"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#334155' }}
                  tickFormatter={(val) => `${val}%`}
                  domain={['auto', 0]}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const ddVal = payload[0]?.value;
                      return (
                        <div className="bg-slate-900 border border-slate-700 p-3 rounded-xl shadow-xl text-xs space-y-1">
                          <div className="font-semibold text-slate-300 border-b border-slate-800 pb-1 flex items-center gap-1.5">
                            <Calendar className="w-3 h-3 text-rose-400" />
                            <span>{label}</span>
                          </div>
                          <div className="flex items-center justify-between gap-4 pt-1">
                            <span className="text-rose-400">Peak-to-Trough Drawdown:</span>
                            <span className="font-mono font-bold text-slate-100">
                              {ddVal !== undefined ? `${Number(ddVal).toFixed(2)}%` : '—'}
                            </span>
                          </div>
                          {maxDrawdown !== null && (
                            <div className="text-[10px] text-slate-400 pt-1">
                              Max Drawdown Threshold: <span className="text-rose-300 font-mono font-semibold">{formatPercent(maxDrawdown, false)}</span>
                            </div>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <ReferenceLine y={0} stroke="#94a3b8" />
                {maxDrawdown !== null && (
                  <ReferenceLine
                    y={maxDrawdown}
                    stroke="#f43f5e"
                    strokeDasharray="3 3"
                    label={{
                      value: `Max DD ${formatPercent(maxDrawdown, false)}`,
                      position: 'insideBottomRight',
                      fill: '#f43f5e',
                      fontSize: 10,
                    }}
                  />
                )}
                <Area
                  type="monotone"
                  dataKey="drawdown"
                  stroke="#f43f5e"
                  strokeWidth={2}
                  fill="url(#drawdownGrad)"
                  name="Drawdown"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl bg-slate-950/40">
              <TrendingDown className="w-8 h-8 text-slate-600 mb-2" />
              <p className="text-sm font-semibold text-slate-300">Underwater Drawdown Graph</p>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Visualizes the depth and recovery duration of historical equity drawdowns beneath previous high-water marks.
              </p>
            </div>
          )
        )}

        {activeTab === 'contributions' && (
          riskContributions.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={riskContributions}
                layout="vertical"
                margin={{ top: 10, right: 20, left: 40, bottom: 0 }}
              >
                <XAxis
                  type="number"
                  stroke="#475569"
                  fontSize={11}
                  tickFormatter={(val) => `${val}%`}
                  axisLine={{ stroke: '#334155' }}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="ticker"
                  stroke="#94a3b8"
                  fontSize={11}
                  axisLine={{ stroke: '#334155' }}
                  tickLine={false}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload as AssetRiskContribution;
                      return (
                        <div className="bg-slate-900 border border-slate-700 p-3 rounded-xl shadow-xl text-xs space-y-1">
                          <div className="font-bold text-slate-100 border-b border-slate-800 pb-1">
                            {data.ticker} {data.name ? `— ${data.name}` : ''}
                          </div>
                          <div className="flex items-center justify-between gap-4 pt-1 text-slate-300">
                            <span>Portfolio Weight:</span>
                            <span className="font-mono font-semibold">{formatPercent(data.weight, false)}</span>
                          </div>
                          <div className="flex items-center justify-between gap-4 text-cyan-400">
                            <span>Risk Contribution:</span>
                            <span className="font-mono font-bold">
                              {formatPercent(data.percentage_contribution ?? data.marginal_contribution, false)}
                            </span>
                          </div>
                          {data.volatility !== null && data.volatility !== undefined && (
                            <div className="flex items-center justify-between gap-4 text-slate-400">
                              <span>Asset Volatility:</span>
                              <span className="font-mono">{formatPercent(data.volatility, false)}</span>
                            </div>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="percentage_contribution" radius={[0, 4, 4, 0]}>
                  {riskContributions.map((_, index) => (
                    <Cell
                      key={`cell-contrib-${index}`}
                      fill={index % 2 === 0 ? '#06b6d4' : '#6366f1'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl bg-slate-950/40">
              <Layers className="w-8 h-8 text-slate-600 mb-2" />
              <p className="text-sm font-semibold text-slate-300">Asset Volatility Decomposition</p>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Decomposes total portfolio variance into marginal and percentage risk contributions per asset.
              </p>
            </div>
          )
        )}
      </div>

      {/* Underwater / Drawdown Explanatory Footnote */}
      <div className="flex items-start gap-2 pt-2 text-[11px] text-slate-500">
        <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
        <span>
          Drawdown calculation identifies peak equity levels and tracks subsequent loss percentage until full recovery. Values are computed strictly by backend quantitative pipelines without client-side approximation.
        </span>
      </div>
    </div>
  );
};
