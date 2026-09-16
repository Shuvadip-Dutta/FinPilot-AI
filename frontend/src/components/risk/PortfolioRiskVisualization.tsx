import React, { useState } from 'react';
import {
  PortfolioRiskResponse,
  DrawdownSeriesPoint,
  AssetRiskContribution,
  getRiskMaxDrawdown,
} from '../../types/portfolio';
import { formatPercent } from '../../utils/formatters';
import {
  AreaChart,
  Area,
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
  Info,
  Calendar,
  ShieldAlert,
} from 'lucide-react';
import { useChartTheme } from '../../hooks/useChartTheme';

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
  const chartTheme = useChartTheme();
  const [activeTab, setActiveTab] = useState<'cumulative' | 'drawdown' | 'contributions'>('cumulative');

  const seriesData: DrawdownSeriesPoint[] =
    riskData?.drawdown_series ?? riskData?.historical_series ?? [];

  const riskContributions: AssetRiskContribution[] =
    riskData?.risk_contributions ?? [];

  const maxDrawdown = getRiskMaxDrawdown(riskData);

  return (
    <div
      id="portfolio-risk-visualization"
      className={`bg-surface border border-border-theme rounded-2xl p-6 shadow-card space-y-6 ${className}`}
    >
      {/* Scope & Conceptual Distinction Banner */}
      <div className="p-4 rounded-xl bg-surface-secondary/60 border border-border-theme flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-accent-soft border border-accent-primary/30 text-accent-primary shrink-0 mt-0.5">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold tracking-wider uppercase text-accent-primary">
                Authoritative Quantitative Risk Framework
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-accent-soft text-accent-primary border border-accent-primary/30">
                Django Engine
              </span>
            </div>
            <div className="mt-1 flex flex-col sm:flex-row sm:items-center gap-2 text-xs text-text-secondary">
              <span className="font-semibold text-text-primary">
                CURRENT PORTFOLIO:
              </span>
              <span className="text-text-muted">&quot;What I currently own.&quot;</span>
              <span className="hidden sm:inline text-text-muted">•</span>
              <span className="font-semibold text-text-primary">
                RISK:
              </span>
              <span className="text-text-muted">&quot;How the current portfolio has behaved historically.&quot;</span>
            </div>
          </div>
        </div>

        <div className="text-[11px] text-text-muted border-l border-border-subtle md:pl-4 max-w-sm leading-relaxed">
          Quantitative risk measures dispersion, downside semi-variance, and peak-to-trough drawdowns based strictly on historical return matrices. Past risk patterns do not guarantee future tail resilience.
        </div>
      </div>

      {/* Visualizer Header with View Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-4">
        <div>
          <h3 className="text-base font-bold text-text-primary flex items-center gap-2">
            <span>Historical Portfolio Risk & Drawdown Dynamics</span>
          </h3>
          <p className="text-xs text-text-muted mt-0.5">
            {portfolioName ? `Evaluated for ${portfolioName}` : 'Portfolio asset trajectory'} • Base Currency: {currency}
          </p>
        </div>

        {/* View Toggle Tabs */}
        <div className="inline-flex rounded-lg bg-surface-secondary/70 p-1 border border-border-theme">
          <button
            type="button"
            onClick={() => setActiveTab('cumulative')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'cumulative'
                ? 'bg-accent-soft text-accent-primary border border-accent-primary/40 shadow-xs font-semibold'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Cumulative Trajectory</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('drawdown')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'drawdown'
                ? 'bg-status-negative-soft text-status-negative border border-status-negative/40 shadow-xs font-semibold'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <TrendingDown className="w-3.5 h-3.5" />
            <span>Underwater Drawdown</span>
          </button>
          {riskContributions.length > 0 && (
            <button
              type="button"
              onClick={() => setActiveTab('contributions')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'contributions'
                  ? 'bg-status-info-soft text-status-info border border-status-info/40 shadow-xs font-semibold'
                  : 'text-text-muted hover:text-text-primary'
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
                    <stop offset="5%" stopColor={chartTheme.accent} stopOpacity={0.4} />
                    <stop offset="95%" stopColor={chartTheme.accent} stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
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
                      const returnVal = payload[0]?.value;
                      const benchmarkVal = payload[1]?.value;
                      return (
                        <div className="bg-surface-elevated border border-border-theme p-3 rounded-xl shadow-card-hover text-xs space-y-1">
                          <div className="font-semibold text-text-muted border-b border-border-subtle pb-1 flex items-center gap-1.5">
                            <Calendar className="w-3 h-3 text-accent-primary" />
                            <span>{label}</span>
                          </div>
                          <div className="flex items-center justify-between gap-4 pt-1">
                            <span style={{ color: chartTheme.accent }}>Portfolio Return:</span>
                            <span className="font-mono font-bold text-text-primary">
                              {returnVal !== undefined ? `${Number(returnVal).toFixed(2)}%` : '—'}
                            </span>
                          </div>
                          {benchmarkVal !== undefined && (
                            <div className="flex items-center justify-between gap-4 text-text-muted">
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
                <ReferenceLine y={0} stroke={chartTheme.border} strokeDasharray="3 3" />
                <Area
                  type="monotone"
                  dataKey="cumulative_return"
                  stroke={chartTheme.accent}
                  strokeWidth={2}
                  fill="url(#cumReturnGrad)"
                  name="Portfolio Return"
                />
                {seriesData[0]?.benchmark_cumulative_return !== undefined && (
                  <Line
                    type="monotone"
                    dataKey="benchmark_cumulative_return"
                    stroke={chartTheme.muted}
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                    name="Benchmark"
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-border-theme rounded-xl bg-surface-secondary/40">
              <TrendingUp className="w-8 h-8 text-text-muted mb-2" />
              <p className="text-sm font-semibold text-text-primary">Historical Return Trajectory</p>
              <p className="text-xs text-text-muted max-w-sm mt-1">
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
                    <stop offset="5%" stopColor={chartTheme.negative} stopOpacity={0.05} />
                    <stop offset="95%" stopColor={chartTheme.negative} stopOpacity={0.5} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
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
                  domain={['auto', 0]}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const ddVal = payload[0]?.value;
                      return (
                        <div className="bg-surface-elevated border border-border-theme p-3 rounded-xl shadow-card-hover text-xs space-y-1">
                          <div className="font-semibold text-text-muted border-b border-border-subtle pb-1 flex items-center gap-1.5">
                            <Calendar className="w-3 h-3 text-status-negative" />
                            <span>{label}</span>
                          </div>
                          <div className="flex items-center justify-between gap-4 pt-1">
                            <span className="text-status-negative">Peak-to-Trough Drawdown:</span>
                            <span className="font-mono font-bold text-text-primary">
                              {ddVal !== undefined ? `${Number(ddVal).toFixed(2)}%` : '—'}
                            </span>
                          </div>
                          {maxDrawdown !== null && (
                            <div className="text-[10px] text-text-muted pt-1">
                              Max Drawdown Threshold: <span className="text-status-negative font-mono font-semibold">{formatPercent(maxDrawdown, false)}</span>
                            </div>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <ReferenceLine y={0} stroke={chartTheme.border} />
                {maxDrawdown !== null && (
                  <ReferenceLine
                    y={maxDrawdown}
                    stroke={chartTheme.negative}
                    strokeDasharray="3 3"
                    label={{
                      value: `Max DD ${formatPercent(maxDrawdown, false)}`,
                      position: 'insideBottomRight',
                      fill: chartTheme.negative,
                      fontSize: 10,
                    }}
                  />
                )}
                <Area
                  type="monotone"
                  dataKey="drawdown"
                  stroke={chartTheme.negative}
                  strokeWidth={2}
                  fill="url(#drawdownGrad)"
                  name="Drawdown"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-border-theme rounded-xl bg-surface-secondary/40">
              <TrendingDown className="w-8 h-8 text-text-muted mb-2" />
              <p className="text-sm font-semibold text-text-primary">Underwater Drawdown Graph</p>
              <p className="text-xs text-text-muted max-w-sm mt-1">
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
                  stroke={chartTheme.axis}
                  fontSize={11}
                  tickFormatter={(val) => `${val}%`}
                  axisLine={{ stroke: chartTheme.border }}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="ticker"
                  stroke={chartTheme.axis}
                  fontSize={11}
                  axisLine={{ stroke: chartTheme.border }}
                  tickLine={false}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload as AssetRiskContribution;
                      return (
                        <div className="bg-surface-elevated border border-border-theme p-3 rounded-xl shadow-card-hover text-xs space-y-1">
                          <div className="font-bold text-text-primary border-b border-border-subtle pb-1">
                            {data.ticker} {data.name ? `— ${data.name}` : ''}
                          </div>
                          <div className="flex items-center justify-between gap-4 pt-1 text-text-secondary">
                            <span>Portfolio Weight:</span>
                            <span className="font-mono font-semibold">{formatPercent(data.weight, false)}</span>
                          </div>
                          <div className="flex items-center justify-between gap-4" style={{ color: chartTheme.accent }}>
                            <span>Risk Contribution:</span>
                            <span className="font-mono font-bold">
                              {formatPercent(data.percentage_contribution ?? data.marginal_contribution, false)}
                            </span>
                          </div>
                          {data.volatility !== null && data.volatility !== undefined && (
                            <div className="flex items-center justify-between gap-4 text-text-muted">
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
                      fill={index % 2 === 0 ? chartTheme.accent : chartTheme.info}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-border-theme rounded-xl bg-surface-secondary/40">
              <Layers className="w-8 h-8 text-text-muted mb-2" />
              <p className="text-sm font-semibold text-text-primary">Asset Volatility Decomposition</p>
              <p className="text-xs text-text-muted max-w-sm mt-1">
                Decomposes total portfolio variance into marginal and percentage risk contributions per asset.
              </p>
            </div>
          )
        )}
      </div>

      {/* Underwater / Drawdown Explanatory Footnote */}
      <div className="flex items-start gap-2 pt-2 text-[11px] text-text-muted">
        <Info className="w-3.5 h-3.5 text-text-muted shrink-0 mt-0.5" />
        <span>
          Drawdown calculation identifies peak equity levels and tracks subsequent loss percentage until full recovery. Values are computed strictly by backend quantitative pipelines without client-side approximation.
        </span>
      </div>
    </div>
  );
};
