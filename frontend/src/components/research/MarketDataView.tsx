import React, { useEffect, useState, useMemo } from 'react';
import {
  HistoricalCandle,
  HistoricalResponse,
  KeyMetricsResponse,
  KeyMetricItem,
  MarketMetrics,
} from '../../types/research';
import { ApiError } from '../../types/api';
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
  RefreshCw,
  AlertCircle,
  Clock,
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
import { formatCurrency, formatPercent, formatRatio, formatDate, formatNumber } from '../../utils/formatters';

interface MarketDataViewProps {
  ticker: string;
  market?: string;
  className?: string;
}

type TimeframeOption = '1M' | '3M' | '6M' | '1Y' | 'CUSTOM';

export const MarketDataView: React.FC<MarketDataViewProps> = ({
  ticker,
  market = 'IN',
  className = '',
}) => {
  const [candles, setCandles] = useState<HistoricalCandle[]>([]);
  const [metrics, setMetrics] = useState<KeyMetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isMarketRestricted, setIsMarketRestricted] = useState<boolean>(false);

  // Timeframe and custom date controls
  const [timeframe, setTimeframe] = useState<TimeframeOption>('1M');
  const [customFrom, setCustomFrom] = useState<string>('');
  const [customTo, setCustomTo] = useState<string>('');
  const [dateValidationError, setDateValidationError] = useState<string | null>(null);

  // Helper to compute ISO YYYY-MM-DD from offset days
  const getDateRangeForTimeframe = (tf: TimeframeOption): { fromDate: string; toDate: string } => {
    const today = new Date();
    const toDate = today.toISOString().split('T')[0];

    const from = new Date();
    switch (tf) {
      case '1M':
        from.setDate(today.getDate() - 30);
        break;
      case '3M':
        from.setDate(today.getDate() - 90);
        break;
      case '6M':
        from.setDate(today.getDate() - 180);
        break;
      case '1Y':
        from.setDate(today.getDate() - 365);
        break;
      case 'CUSTOM':
        return {
          fromDate: customFrom || new Date(today.setDate(today.getDate() - 30)).toISOString().split('T')[0],
          toDate: customTo || toDate,
        };
    }
    return { fromDate: from.toISOString().split('T')[0], toDate };
  };

  const fetchData = async (overrideTf?: TimeframeOption, overrideFrom?: string, overrideTo?: string) => {
    if (!ticker || !ticker.trim()) return;

    // Stale data protection: immediately clear prior state
    setCandles([]);
    setMetrics(null);
    setError(null);
    setDateValidationError(null);
    setIsMarketRestricted(false);
    setIsLoading(true);

    const activeTf = overrideTf || timeframe;
    const isUS = market.trim().toUpperCase() === 'US' || market.trim().toUpperCase() === 'USA' || market.trim().toUpperCase() === 'NASDAQ' || market.trim().toUpperCase() === 'NYSE';

    let rangeFrom: string;
    let rangeTo: string;

    if (activeTf === 'CUSTOM') {
      rangeFrom = overrideFrom !== undefined ? overrideFrom : customFrom;
      rangeTo = overrideTo !== undefined ? overrideTo : customTo;

      const todayStr = new Date().toISOString().split('T')[0];

      // Client-side date range validation
      if (!rangeTo) {
        rangeTo = todayStr;
      }
      if (rangeTo > todayStr) {
        setDateValidationError('End date cannot be in the future.');
        setIsLoading(false);
        return;
      }
      if (rangeFrom && rangeFrom > todayStr) {
        setDateValidationError('Start date cannot be in the future.');
        setIsLoading(false);
        return;
      }
      if (rangeFrom && rangeFrom > rangeTo) {
        setDateValidationError('Start date must be before or equal to end date.');
        setIsLoading(false);
        return;
      }
    } else {
      const computed = getDateRangeForTimeframe(activeTf);
      rangeFrom = computed.fromDate;
      rangeTo = computed.toDate;
    }

    try {
      // Parallel fetch of historical candles and key metrics
      const [histRes, metRes] = await Promise.allSettled([
        researchApi.getHistorical(ticker, market, rangeFrom, rangeTo),
        researchApi.getMetrics(ticker, market),
      ]);

      // Process Key Metrics
      if (metRes.status === 'fulfilled') {
        setMetrics(metRes.value);
      }

      // Process Historical Candles
      if (histRes.status === 'fulfilled') {
        const rawCandles = histRes.value.candles || [];
        // Django returns candles in reverse-chronological order (newest first).
        // Sort chronologically (oldest first) so charts render naturally left-to-right.
        const sorted = [...rawCandles].sort((a, b) => {
          return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
        });
        setCandles(sorted);
      } else {
        const apiErr = histRes.reason as ApiError;
        const errObj = apiErr as unknown as Record<string, unknown>;
        const fromDateErr = errObj?.from_date || apiErr?.errors?.from_date;
        const toDateErr = errObj?.to_date || apiErr?.errors?.to_date;

        if (apiErr?.status === 400 && (isUS || JSON.stringify(apiErr).includes('valid choice'))) {
          setIsMarketRestricted(true);
        } else if (apiErr?.status === 400 && fromDateErr) {
          setDateValidationError(Array.isArray(fromDateErr) ? String(fromDateErr[0]) : String(fromDateErr));
        } else if (apiErr?.status === 400 && toDateErr) {
          setDateValidationError(Array.isArray(toDateErr) ? String(toDateErr[0]) : String(toDateErr));
        } else if (apiErr?.status === 404) {
          setError(apiErr.detail || apiErr.message || `No historical market data found for ticker ${ticker}.`);
        } else if (apiErr?.status === 429) {
          setError('Rate limit exceeded. Please wait a moment before retrying.');
        } else if (apiErr?.status === 502) {
          setError('External market data provider is currently unavailable.');
        } else if (apiErr?.isNetworkError) {
          setError('Unable to connect to the FinPilot server. Please check backend connection.');
        } else {
          setError(apiErr?.detail || apiErr?.message || `Failed to fetch historical market data for ${ticker}.`);
        }
      }
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setError(apiErr.detail || apiErr.message || `Failed to fetch market data for ${ticker}.`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Initialize default custom range dates
    const today = new Date().toISOString().split('T')[0];
    const past = new Date();
    past.setDate(past.getDate() - 30);
    setCustomFrom(past.toISOString().split('T')[0]);
    setCustomTo(today);

    fetchData(timeframe);
  }, [ticker, market]);

  const handleTimeframeChange = (tf: TimeframeOption) => {
    setTimeframe(tf);
    if (tf !== 'CUSTOM') {
      fetchData(tf);
    }
  };

  const handleCustomRangeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData('CUSTOM', customFrom, customTo);
  };

  const isIndia = market.trim().toUpperCase() === 'IN' || market.trim().toUpperCase() === 'NSE' || market.trim().toUpperCase() === 'BSE';
  const currency = isIndia ? 'INR' : 'USD';

  // Latest price and price change derived from authoritative candles
  const latestCandle = candles.length > 0 ? candles[candles.length - 1] : null;
  const previousCandle = candles.length > 1 ? candles[candles.length - 2] : null;
  const currentPrice = latestCandle?.close ?? null;
  const priceChange = latestCandle && previousCandle ? latestCandle.close - previousCandle.close : null;
  const priceChangePercent = latestCandle && previousCandle && previousCandle.close !== 0
    ? ((latestCandle.close - previousCandle.close) / previousCandle.close) * 100
    : null;

  // Render loading skeleton
  if (isLoading && candles.length === 0 && !isMarketRestricted && !error) {
    return (
      <Card title={`Market Intelligence: ${ticker.toUpperCase()}`} className={className}>
        <div className="space-y-4">
          <LoadingSkeleton height="h-20" />
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

  // Market constraint state: US market requested on India-only historical endpoint
  if (isMarketRestricted) {
    return (
      <Card
        title={
          <div className="flex items-center justify-between gap-3 w-full">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-amber-400" />
              <span>Historical Market Data: {ticker.toUpperCase()}</span>
              <Badge variant="warning" size="sm" className="font-mono">
                {market.toUpperCase()}
              </Badge>
            </div>
            <button
              onClick={() => fetchData(timeframe)}
              className="p-1.5 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
              title="Retry"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        }
        className={className}
      >
        <div className="p-6 rounded-xl bg-amber-950/20 border border-amber-800/40 text-center flex flex-col items-center space-y-3">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-amber-200">
              Historical Data Constraint: Indian Equities Only
            </h3>
            <p className="text-xs text-amber-300/80 mt-1 max-w-md leading-relaxed">
              Historical OHLCV candle charts are currently integrated exclusively for the Indian market (<span className="font-mono text-amber-200">IN</span> / NSE / BSE). Upstream providers for US market history are not yet supported by the Django backend.
            </p>
            <p className="text-[11px] text-slate-400 mt-2">
              To inspect historical charts, select Indian assets such as <span className="font-mono text-cyan-300">RELIANCE</span>, <span className="font-mono text-cyan-300">TCS</span>, or <span className="font-mono text-cyan-300">HDFCBANK</span> on the <span className="font-mono text-cyan-300">IN</span> market.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  // Error state
  if (error && candles.length === 0) {
    return (
      <Card title={`Market Intelligence: ${ticker.toUpperCase()}`} className={className}>
        <ErrorState
          title="Unable to load historical market data"
          message={error}
          onRetry={() => fetchData(timeframe)}
        />
      </Card>
    );
  }

  // Flatten key metrics list if present
  const metricsList: KeyMetricItem[] = metrics?.metrics || [];

  return (
    <Card
      title={
        <div className="flex items-center justify-between gap-3 w-full flex-wrap">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-base">Market Valuation & Historical Trend</span>
                <Badge variant="info" size="sm" className="font-mono">
                  {ticker.toUpperCase()}
                </Badge>
                <Badge variant="neutral" size="sm" className="font-mono">
                  {market.toUpperCase()}
                </Badge>
              </div>
            </div>
          </div>

          <button
            onClick={() => fetchData(timeframe)}
            className="p-1.5 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Refresh market data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      }
      subtitle="Authoritative historical OHLCV price series and valuation multiples from Django"
      className={className}
    >
      <div className="space-y-5">
        {/* Latest Price & Summary Banner */}
        {currentPrice !== null && (
          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <span className="text-[11px] text-slate-400 font-mono">
                {ticker.toUpperCase()} Latest Close
              </span>
              <div className="flex items-baseline gap-3 mt-0.5 flex-wrap">
                <span className="text-2xl font-black text-white font-mono tracking-tight">
                  {formatCurrency(currentPrice, currency)}
                </span>
                {priceChangePercent !== null && (
                  <div
                    className={`flex items-center gap-1 font-mono text-xs font-semibold px-2 py-0.5 rounded ${
                      priceChangePercent >= 0
                        ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                        : 'bg-rose-950/80 text-rose-400 border border-rose-800/60'
                    }`}
                  >
                    {priceChangePercent >= 0 ? (
                      <TrendingUp className="w-3.5 h-3.5" />
                    ) : (
                      <TrendingDown className="w-3.5 h-3.5" />
                    )}
                    <span>{formatPercent(priceChangePercent, true)}</span>
                    {priceChange !== null && (
                      <span className="text-[10px] text-slate-400 ml-0.5">
                        ({priceChange >= 0 ? `+${priceChange.toFixed(2)}` : priceChange.toFixed(2)})
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* OHLC Mini Summary for Latest Session */}
            {latestCandle && (
              <div className="flex items-center gap-4 text-xs font-mono text-slate-400 flex-wrap">
                <div>
                  <span className="text-[10px] text-slate-400 block">Open:</span>
                  <span className="text-slate-200 font-semibold">{formatCurrency(latestCandle.open, currency)}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">High:</span>
                  <span className="text-emerald-400 font-semibold">{formatCurrency(latestCandle.high, currency)}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Low:</span>
                  <span className="text-rose-400 font-semibold">{formatCurrency(latestCandle.low, currency)}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Volume:</span>
                  <span className="text-slate-200 font-semibold">{formatNumber(latestCandle.volume, 0)}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Historical Price Chart Card */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-200 font-mono">
                Historical Price Trend ({candles.length} trading sessions)
              </span>
            </div>

            {/* Timeframe Selection Pills */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <div className="flex rounded-lg bg-slate-900 p-0.5 border border-slate-800 text-[11px] font-mono">
                {(['1M', '3M', '6M', '1Y', 'CUSTOM'] as const).map((tf) => (
                  <button
                    key={tf}
                    onClick={() => handleTimeframeChange(tf)}
                    className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                      timeframe === tf
                        ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/30'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {tf === 'CUSTOM' ? 'Custom Range' : tf}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Custom Date Range Picker Strip */}
          {timeframe === 'CUSTOM' && (
            <form
              onSubmit={handleCustomRangeSubmit}
              className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-wrap items-center gap-3 text-xs font-mono"
            >
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400">From:</span>
                <input
                  type="date"
                  value={customFrom}
                  onChange={(e) => setCustomFrom(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                  className="px-2 py-1 rounded bg-slate-950 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-slate-400">To:</span>
                <input
                  type="date"
                  value={customTo}
                  onChange={(e) => setCustomTo(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                  className="px-2 py-1 rounded bg-slate-950 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
                />
              </div>

              <button
                type="submit"
                className="px-3 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold transition-colors cursor-pointer text-xs"
              >
                Apply Range
              </button>

              {dateValidationError && (
                <span className="text-rose-400 text-xs flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {dateValidationError}
                </span>
              )}
            </form>
          )}

          {/* Chart View */}
          {candles.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400 font-mono">
              No price candles available for the requested range.
            </div>
          ) : (
            <div className="h-64 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={candles} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                  <defs>
                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="timestamp"
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
                    formatter={(val: any, name: any, item: any) => {
                      const c = item.payload as HistoricalCandle;
                      return [
                        <div key="details" className="space-y-1">
                          <p className="text-cyan-300 font-bold">Close: {formatCurrency(c.close, currency)}</p>
                          <p className="text-slate-300">Open: {formatCurrency(c.open, currency)}</p>
                          <p className="text-emerald-400">High: {formatCurrency(c.high, currency)}</p>
                          <p className="text-rose-400">Low: {formatCurrency(c.low, currency)}</p>
                          <p className="text-slate-400">Vol: {formatNumber(c.volume, 0)}</p>
                        </div>,
                        '',
                      ];
                    }}
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
          )}

          {/* Non-trading days note */}
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1">
            <span>* Missing weekend & holiday trading sessions are omitted naturally without interpolation.</span>
            <span>Provider: Upstox / Django Research API</span>
          </div>
        </div>

        {/* Valuation Multiples Strip from Key Metrics if available */}
        {metricsList.length > 0 && (
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-300 font-mono flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              Authoritative Valuation & Financial Multiples
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
              {metricsList.map((m, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1"
                >
                  <span className="text-[10px] text-slate-400 font-mono block truncate" title={m.name}>
                    {m.name}
                  </span>
                  <p className="font-mono font-bold text-slate-100 text-xs sm:text-sm">
                    {m.raw_value || (m.value !== null ? formatNumber(m.value) : '—')}
                  </p>
                  <span className="text-[9px] text-slate-400 font-mono block uppercase">
                    {m.category}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
