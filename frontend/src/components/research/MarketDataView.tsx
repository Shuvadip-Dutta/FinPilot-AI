import React, { useEffect, useState } from 'react';
import { MarketMetrics, HistoricalBar, HistoricalDataResponse } from '../../types/research';
import { researchApi } from '../../api/research';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { LoadingSkeleton } from '../common/LoadingSkeleton';
import { ErrorState } from '../common/ErrorState';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Calendar,
  BarChart2,
  DollarSign,
  RefreshCw,
  Maximize2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts';
import { formatCurrency, formatPercent, formatRatio, formatDate } from '../../utils/formatters';

interface MarketDataViewProps {
  ticker: string;
  market?: string;
  className?: string;
}

export const MarketDataView: React.FC<MarketDataViewProps> = ({
  ticker,
  market = 'NSE',
  className = '',
}) => {
  const [metrics, setMetrics] = useState<MarketMetrics | null>(null);
  const [history, setHistory] = useState<HistoricalBar[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState<'1M' | '3M' | '6M' | '1Y' | 'ALL'>('6M');

  const fetchData = async () => {
    if (!ticker) return;
    setIsLoading(true);
    setError(null);
    try {
      // Fetch both metrics and historical in parallel
      const [metricsRes, histRes] = await Promise.allSettled([
        researchApi.getMetrics(ticker, market),
        researchApi.getHistorical(ticker, market),
      ]);

      if (metricsRes.status === 'fulfilled') {
        setMetrics(metricsRes.value as unknown as MarketMetrics);
      } else {
        console.warn('Metrics fetch error:', metricsRes.reason);
      }

      if (histRes.status === 'fulfilled') {
        const hData = histRes.value as HistoricalDataResponse;
        const bars: HistoricalBar[] =
          hData.data || hData.prices || hData.historical || hData.bars || (Array.isArray(hData) ? (hData as any) : []);
        setHistory(bars);
      } else {
        console.warn('Historical fetch error:', histRes.reason);
      }

      if (metricsRes.status === 'rejected' && histRes.status === 'rejected') {
        throw new Error(`Failed to load market data for ${ticker}.`);
      }
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setError(apiErr.message || `Failed to fetch market data for ${ticker}.`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [ticker, market]);

  if (isLoading) {
    return (
      <Card title={`Market Valuation & Price: ${ticker}`} className={className}>
        <div className="space-y-4">
          <LoadingSkeleton height="h-24" />
          <LoadingSkeleton height="h-64" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LoadingSkeleton height="h-16" />
            <LoadingSkeleton height="h-16" />
            <LoadingSkeleton height="h-16" />
            <LoadingSkeleton height="h-16" />
          </div>
        </div>
      </Card>
    );
  }

  if (error && !metrics && history.length === 0) {
    return (
      <Card title={`Market Valuation & Price: ${ticker}`} className={className}>
        <ErrorState
          title="Unable to load market data"
          message={error || `No market metrics found for ${ticker}.`}
          onRetry={fetchData}
        />
      </Card>
    );
  }

  const currency = metrics?.currency || (market === 'NSE' || market === 'BSE' ? 'INR' : 'USD');
  const price = metrics?.current_price ?? metrics?.price ?? metrics?.close_price ?? history[history.length - 1]?.close;
  const change = metrics?.change ?? 0;
  const changePercent = metrics?.change_percent ?? 0;
  const isPositive = (changePercent ?? 0) >= 0;

  // Filter history by timeframe
  const filteredHistory = history.slice(
    timeframe === '1M'
      ? -22
      : timeframe === '3M'
      ? -66
      : timeframe === '6M'
      ? -132
      : timeframe === '1Y'
      ? -264
      : 0
  );

  return (
    <Card
      title={
        <div className="flex items-center justify-between gap-3 w-full">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span>Market Intelligence & Valuation</span>
            <Badge variant="neutral" size="sm" className="font-mono">
              {ticker}
            </Badge>
          </div>

          <button
            onClick={fetchData}
            className="p-1 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Refresh market data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      }
      subtitle="Authoritative valuation multiples, trading range, and historical prices"
      className={className}
    >
      <div className="space-y-5">
        {/* Real-Time Price Strip Header */}
        <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <span className="text-[11px] text-slate-400 font-mono">
              {ticker} • {market} Price
            </span>
            <div className="flex items-baseline gap-3 mt-0.5">
              <span className="text-2xl font-black text-white font-mono tracking-tight">
                {price !== undefined ? formatCurrency(price, currency) : '—'}
              </span>
              {changePercent !== undefined && (
                <div
                  className={`flex items-center gap-1 font-mono text-xs font-semibold px-2 py-0.5 rounded ${
                    isPositive
                      ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                      : 'bg-rose-950/80 text-rose-400 border border-rose-800/60'
                  }`}
                >
                  {isPositive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                  <span>{formatPercent(changePercent, true)}</span>
                  {change !== 0 && (
                    <span className="text-[10px] text-slate-400 ml-0.5">
                      ({formatCurrency(change, currency)})
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 52W High / Low Range */}
          {(metrics?.high_52w || metrics?.low_52w) && (
            <div className="w-full sm:w-60 space-y-1 text-xs font-mono">
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>52W Low: {formatCurrency(metrics.low_52w, currency)}</span>
                <span>52W High: {formatCurrency(metrics.high_52w, currency)}</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-800 relative">
                {price && metrics.low_52w && metrics.high_52w && (
                  <div
                    className="absolute top-0 bottom-0 w-2.5 h-2.5 -mt-0.5 rounded-full bg-cyan-400 shadow-xs shadow-cyan-500"
                    style={{
                      left: `${Math.min(
                        Math.max(
                          ((price - metrics.low_52w) / (metrics.high_52w - metrics.low_52w)) * 100,
                          0
                        ),
                        100
                      )}%`,
                    }}
                  />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Historical Price Chart */}
        {filteredHistory.length > 0 && (
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-200 font-mono flex items-center gap-1.5">
                <BarChart2 className="w-3.5 h-3.5 text-cyan-400" />
                Historical Price Trend (Close)
              </span>

              {/* Timeframe Buttons */}
              <div className="flex rounded-lg bg-slate-900 p-0.5 border border-slate-800 text-[11px] font-mono">
                {(['1M', '3M', '6M', '1Y', 'ALL'] as const).map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setTimeframe(tf)}
                    className={`px-2 py-0.5 rounded transition-colors ${
                      timeframe === tf
                        ? 'bg-cyan-500/20 text-cyan-300 font-semibold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>

            <div className="h-56 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={filteredHistory} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke="#64748b"
                    fontSize={10}
                    tickFormatter={(val) => formatDate(val, { format: 'short' })}
                  />
                  <YAxis
                    stroke="#64748b"
                    fontSize={10}
                    domain={['auto', 'auto']}
                    tickFormatter={(val) => `${val}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '11px',
                      fontFamily: 'monospace',
                    }}
                    labelFormatter={(label: any) => formatDate(String(label || ''), { includeTime: false })}
                    formatter={(val: any) => [formatCurrency(val, currency), 'Close Price']}
                  />
                  <Area
                    type="monotone"
                    dataKey="close"
                    stroke="#06b6d4"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#priceGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Valuation Multiples Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              P/E Ratio (Trailing)
            </span>
            <p className="font-mono font-bold text-slate-100 text-sm">
              {formatRatio(metrics?.pe_ratio ?? metrics?.trailing_pe)}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              Forward P/E
            </span>
            <p className="font-mono font-bold text-slate-100 text-sm">
              {formatRatio(metrics?.forward_pe)}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              P/B Ratio
            </span>
            <p className="font-mono font-bold text-slate-100 text-sm">
              {formatRatio(metrics?.pb_ratio)}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              EV / EBITDA
            </span>
            <p className="font-mono font-bold text-slate-100 text-sm">
              {formatRatio(metrics?.ev_ebitda)}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              Return on Equity (ROE)
            </span>
            <p className="font-mono font-bold text-emerald-400 text-sm">
              {metrics?.roe !== undefined ? formatPercent(metrics.roe, false) : '—'}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              Dividend Yield
            </span>
            <p className="font-mono font-bold text-cyan-300 text-sm">
              {metrics?.dividend_yield !== undefined ? formatPercent(metrics.dividend_yield, false) : '—'}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              Debt to Equity
            </span>
            <p className="font-mono font-bold text-slate-100 text-sm">
              {formatRatio(metrics?.debt_to_equity)}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              Market Beta
            </span>
            <p className="font-mono font-bold text-slate-100 text-sm">
              {formatRatio(metrics?.beta)}
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
};
