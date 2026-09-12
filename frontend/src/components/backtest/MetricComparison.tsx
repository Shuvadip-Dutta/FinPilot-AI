import React from 'react';
import {
  BacktestResponse,
  BacktestMetricsGroup,
  BacktestRelativeMetrics,
  getBacktestStrategyMetrics,
  getBacktestBuyAndHoldMetrics,
  getBacktestBenchmarkMetrics,
  getBacktestRelativeMetrics,
} from '../../types/portfolio';
import { Badge } from '../common/Badge';
import { Award, TrendingUp, ShieldAlert, Activity, ArrowRightLeft } from 'lucide-react';

export interface MetricComparisonProps {
  response: BacktestResponse | null;
  currency?: string;
  className?: string;
}

export const MetricComparison: React.FC<MetricComparisonProps> = ({
  response,
  currency = 'INR',
  className = '',
}) => {
  if (!response) return null;

  const strat = getBacktestStrategyMetrics(response);
  const bnh = getBacktestBuyAndHoldMetrics(response);
  const bm = getBacktestBenchmarkMetrics(response);
  const rel = getBacktestRelativeMetrics(response);

  // Helper formatting numbers
  const fmtPct = (val: number | string | null | undefined, forceSign = false): string => {
    if (val === null || val === undefined) return '—';
    const num = Number(val);
    if (isNaN(num)) return '—';
    const normalized = Math.abs(num) > 1.5 ? num : num * 100;
    const sign = forceSign && normalized > 0 ? '+' : '';
    return `${sign}${normalized.toFixed(2)}%`;
  };

  const fmtRatio = (val: number | string | null | undefined): string => {
    if (val === null || val === undefined) return '—';
    const num = Number(val);
    if (isNaN(num)) return '—';
    return num.toFixed(2);
  };

  const fmtCurrency = (val: number | string | null | undefined): string => {
    if (val === null || val === undefined) return '—';
    const num = Number(val);
    if (isNaN(num)) return '—';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency,
      maximumFractionDigits: 0,
    }).format(num);
  };

  // Structured table rows for core metrics
  const metricRows = [
    {
      label: 'Total Return',
      description: 'Cumulative compounded growth over backtest span',
      strat: fmtPct(strat?.total_period_return ?? strat?.total_return, true),
      bnh: fmtPct(bnh?.total_period_return ?? bnh?.total_return, true),
      bm: fmtPct(bm?.total_period_return ?? bm?.total_return, true),
      higherIsBetter: true,
      rawStrat: Number(strat?.total_period_return ?? strat?.total_return),
      rawBm: Number(bm?.total_period_return ?? bm?.total_return),
    },
    {
      label: 'CAGR (Annualized)',
      description: 'Compound Annual Growth Rate',
      strat: fmtPct(strat?.cagr ?? strat?.annualized_return, true),
      bnh: fmtPct(bnh?.cagr ?? bnh?.annualized_return, true),
      bm: fmtPct(bm?.cagr ?? bm?.annualized_return, true),
      higherIsBetter: true,
      rawStrat: Number(strat?.cagr ?? strat?.annualized_return),
      rawBm: Number(bm?.cagr ?? bm?.annualized_return),
    },
    {
      label: 'Sharpe Ratio',
      description: 'Excess return over risk-free rate per unit total volatility',
      strat: fmtRatio(strat?.sharpe_ratio),
      bnh: fmtRatio(bnh?.sharpe_ratio),
      bm: fmtRatio(bm?.sharpe_ratio),
      higherIsBetter: true,
      rawStrat: Number(strat?.sharpe_ratio),
      rawBm: Number(bm?.sharpe_ratio),
    },
    {
      label: 'Sortino Ratio',
      description: 'Excess return penalized strictly by downside semi-deviation',
      strat: fmtRatio(strat?.sortino_ratio),
      bnh: fmtRatio(bnh?.sortino_ratio),
      bm: fmtRatio(bm?.sortino_ratio),
      higherIsBetter: true,
      rawStrat: Number(strat?.sortino_ratio),
      rawBm: Number(bm?.sortino_ratio),
    },
    {
      label: 'Maximum Drawdown',
      description: 'Deepest historical peak-to-trough equity drop',
      strat: fmtPct(strat?.max_drawdown),
      bnh: fmtPct(bnh?.max_drawdown),
      bm: fmtPct(bm?.max_drawdown),
      higherIsBetter: false,
      rawStrat: Number(strat?.max_drawdown),
      rawBm: Number(bm?.max_drawdown),
    },
    {
      label: 'Annualized Volatility',
      description: 'Standard deviation of periodic asset returns',
      strat: fmtPct(strat?.volatility ?? strat?.annualized_volatility),
      bnh: fmtPct(bnh?.volatility ?? bnh?.annualized_volatility),
      bm: fmtPct(bm?.volatility ?? bm?.annualized_volatility),
      higherIsBetter: false,
      rawStrat: Number(strat?.volatility ?? strat?.annualized_volatility),
      rawBm: Number(bm?.volatility ?? bm?.annualized_volatility),
    },
    {
      label: 'Calmar Ratio',
      description: 'Annualized return divided by absolute maximum drawdown',
      strat: fmtRatio(strat?.calmar_ratio),
      bnh: fmtRatio(bnh?.calmar_ratio),
      bm: fmtRatio(bm?.calmar_ratio),
      higherIsBetter: true,
      rawStrat: Number(strat?.calmar_ratio),
      rawBm: Number(bm?.calmar_ratio),
    },
    {
      label: 'Final Capital Valuation',
      description: 'Terminal equity at backtest completion',
      strat: fmtCurrency(strat?.final_value ?? strat?.final_portfolio_value ?? response.final_value),
      bnh: fmtCurrency(bnh?.final_value),
      bm: fmtCurrency(bm?.final_value),
      higherIsBetter: true,
      rawStrat: Number(strat?.final_value ?? response.final_value),
      rawBm: Number(bm?.final_value),
    },
  ];

  // Check if relative metrics exist
  const hasRelativeMetrics =
    rel &&
    (rel.information_ratio !== undefined ||
      rel.tracking_error !== undefined ||
      rel.alpha !== undefined ||
      rel.beta !== undefined ||
      rel.excess_return !== undefined);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 1. Comparison Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between flex-wrap gap-3 bg-slate-950/50">
          <div>
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Authoritative Performance & Risk Comparison</span>
              <Badge variant="info" size="sm">Strategy vs Benchmarks</Badge>
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Deterministic metrics evaluated over the walk-forward out-of-sample periods
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
              <span className="text-cyan-300 font-semibold">Strategy</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
              <span className="text-amber-300 font-semibold">Buy & Hold</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
              <span className="text-purple-300 font-semibold">Benchmark</span>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/70 text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                <th className="py-3 px-5 font-semibold">Metric</th>
                <th className="py-3 px-4 font-semibold text-cyan-400 text-right">
                  Strategy (Rolling WF)
                </th>
                <th className="py-3 px-4 font-semibold text-amber-400 text-right">
                  Buy & Hold
                </th>
                <th className="py-3 px-4 font-semibold text-purple-400 text-right">
                  Benchmark ({response.benchmark || '^NSEI'})
                </th>
                <th className="py-3 px-4 font-semibold text-slate-400 text-right">
                  Strategy vs BM
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {metricRows.map((row, idx) => {
                // Determine if strategy beat benchmark
                const hasBoth = !isNaN(row.rawStrat) && !isNaN(row.rawBm);
                let diffBadge = null;
                if (hasBoth) {
                  const outperforming = row.higherIsBetter
                    ? row.rawStrat > row.rawBm
                    : row.rawStrat < row.rawBm;
                  diffBadge = (
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-sm border ${
                        outperforming
                          ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/40'
                          : 'bg-rose-950/60 text-rose-400 border-rose-800/40'
                      }`}
                    >
                      {outperforming ? 'Outperforming' : 'Underperforming'}
                    </span>
                  );
                }

                return (
                  <tr
                    key={row.label}
                    className={`hover:bg-slate-850/50 transition-colors ${
                      idx % 2 === 0 ? 'bg-slate-900/30' : 'bg-transparent'
                    }`}
                  >
                    <td className="py-3.5 px-5 font-sans">
                      <div className="font-semibold text-slate-200">{row.label}</div>
                      <div className="text-[10px] text-slate-500 font-normal">{row.description}</div>
                    </td>
                    <td className="py-3.5 px-4 text-right font-bold text-cyan-300 text-sm">
                      {row.strat}
                    </td>
                    <td className="py-3.5 px-4 text-right text-slate-300">
                      {row.bnh}
                    </td>
                    <td className="py-3.5 px-4 text-right text-slate-300">
                      {row.bm}
                    </td>
                    <td className="py-3.5 px-4 text-right font-sans">
                      {diffBadge || <span className="text-slate-600">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. Relative Benchmark Metrics & Execution Friction Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Relative Metrics Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h5 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Relative Risk & Benchmark Sensitivity</span>
            </h5>
            <Badge variant="neutral" size="sm">Hurdle Relative</Badge>
          </div>

          {hasRelativeMetrics ? (
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-[10px] text-slate-400 uppercase font-mono block mb-1">
                  Information Ratio
                </span>
                <span className="text-lg font-bold font-mono text-cyan-300">
                  {fmtRatio(rel.information_ratio)}
                </span>
                <span className="text-[10px] text-slate-500 block mt-0.5">
                  Excess return per unit tracking error
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-[10px] text-slate-400 uppercase font-mono block mb-1">
                  Tracking Error
                </span>
                <span className="text-lg font-bold font-mono text-slate-200">
                  {fmtPct(rel.tracking_error)}
                </span>
                <span className="text-[10px] text-slate-500 block mt-0.5">
                  Standard dev of excess returns
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-[10px] text-slate-400 uppercase font-mono block mb-1">
                  Jensen's Alpha
                </span>
                <span
                  className={`text-lg font-bold font-mono ${
                    Number(rel.alpha) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {fmtPct(rel.alpha, true)}
                </span>
                <span className="text-[10px] text-slate-500 block mt-0.5">
                  Uncorrelated excess return
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                <span className="text-[10px] text-slate-400 uppercase font-mono block mb-1">
                  Beta to Benchmark
                </span>
                <span className="text-lg font-bold font-mono text-slate-200">
                  {fmtRatio(rel.beta)}
                </span>
                <span className="text-[10px] text-slate-500 block mt-0.5">
                  Systematic market covariance
                </span>
              </div>
            </div>
          ) : (
            <div className="p-6 rounded-xl bg-slate-950/50 border border-slate-800/80 text-center text-xs text-slate-500">
              Relative metrics (Information Ratio, Tracking Error, Alpha, Beta) not included in this backend response.
            </div>
          )}
        </div>

        {/* Execution Friction & Operational Realism Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h5 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <ArrowRightLeft className="w-4 h-4 text-amber-400" />
              <span>Turnover & Friction Realism</span>
            </h5>
            <Badge variant="warning" size="sm">Friction Model</Badge>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800/80">
              <div>
                <span className="font-semibold text-slate-200 block">Total Transaction Costs</span>
                <span className="text-[10px] text-slate-500">Cumulative friction deducted from equity</span>
              </div>
              <span className="text-base font-bold font-mono text-amber-400">
                {fmtCurrency(response.total_transaction_costs ?? strat?.total_transaction_costs)}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800/80">
              <div>
                <span className="font-semibold text-slate-200 block">Cumulative Turnover</span>
                <span className="text-[10px] text-slate-500">Total rebalance volume scaled by portfolio value</span>
              </div>
              <span className="text-base font-bold font-mono text-slate-200">
                {response.total_turnover !== undefined
                  ? `${(Number(response.total_turnover) * (Number(response.total_turnover) < 2 ? 100 : 1)).toFixed(1)}%`
                  : '—'}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-[11px] text-slate-400 leading-relaxed">
              <strong className="text-slate-200 block mb-1">Institutional Realism Guard:</strong>
              Unlike naive backtests that assume cost-free rebalancing, this engine explicitly deducts transaction fees
              and slippage at each walk-forward step, ensuring that high-turnover noise does not artificially inflate reported returns.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
