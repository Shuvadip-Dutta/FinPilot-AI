import React, { useEffect, useState } from 'react';
import {
  CompanyResearchResponse,
  UsMarketQuote,
  IndiaExchangeQuote,
} from '../../types/research';
import { ApiError } from '../../types/api';
import { researchApi } from '../../api/research';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { LoadingSkeleton } from '../common/LoadingSkeleton';
import { ErrorState } from '../common/ErrorState';
import {
  Building2,
  Briefcase,
  Layers,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Globe,
  Hash,
  DollarSign,
} from 'lucide-react';
import { formatCurrency } from '../../utils/formatters';

interface CompanyResearchViewProps {
  ticker: string;
  market?: string;
  className?: string;
}

export const CompanyResearchView: React.FC<CompanyResearchViewProps> = ({
  ticker,
  market = 'IN',
  className = '',
}) => {
  const [data, setData] = useState<CompanyResearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCompany = async () => {
    if (!ticker || !ticker.trim()) return;
    setIsLoading(true);
    setError(null);
    setData(null); // Clear previous data so stale results are never shown on failure

    try {
      const res = await researchApi.getCompany(ticker, market);
      setData(res);
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      if (apiErr.isNetworkError) {
        setError(
          'Unable to connect to the FinPilot server. Please ensure the Django backend is running at http://127.0.0.1:8000.'
        );
      } else if (apiErr.status === 404) {
        setError(apiErr.detail || apiErr.message || `Company not found for ticker: ${ticker}`);
      } else if (apiErr.status === 429) {
        setError(apiErr.detail || apiErr.message || 'Rate limit exceeded. Please wait shortly before retrying.');
      } else if (apiErr.status === 502) {
        setError(apiErr.detail || apiErr.message || 'External market data provider is currently unavailable.');
      } else if (apiErr.status === 400) {
        setError(apiErr.detail || apiErr.message || `Invalid request for ${ticker} on market ${market}.`);
      } else {
        setError(apiErr.detail || apiErr.message || `Failed to fetch company profile for ${ticker}.`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCompany();
  }, [ticker, market]);

  if (isLoading) {
    return (
      <Card title={`Company Profile: ${ticker.toUpperCase()}`} className={className}>
        <div className="space-y-4">
          <LoadingSkeleton height="h-8" width="w-2/3" />
          <LoadingSkeleton height="h-20" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LoadingSkeleton height="h-14" />
            <LoadingSkeleton height="h-14" />
            <LoadingSkeleton height="h-14" />
            <LoadingSkeleton height="h-14" />
          </div>
        </div>
      </Card>
    );
  }

  if (error || !data || !data.company) {
    return (
      <Card title={`Company Profile: ${ticker.toUpperCase()}`} className={className}>
        <ErrorState
          title="Unable to load company profile"
          message={error || `No company fundamentals found for ${ticker} on ${market}.`}
          onRetry={fetchCompany}
        />
      </Card>
    );
  }

  const { company, market_data, market: resMarket } = data;
  const isIndia = resMarket === 'IN' || market === 'IN';
  const currency = isIndia ? 'INR' : 'USD';

  // Safely extract market quotes whether object (US) or array (India)
  const isArrayQuotes = Array.isArray(market_data);
  const indiaQuotes: IndiaExchangeQuote[] = isArrayQuotes ? (market_data as IndiaExchangeQuote[]) : [];
  const usQuote: UsMarketQuote | null = !isArrayQuotes && market_data ? (market_data as UsMarketQuote) : null;

  // Primary price and percentage change
  const primaryPrice = isArrayQuotes
    ? indiaQuotes[0]?.price ?? null
    : usQuote?.price ?? null;

  const percentChange = isArrayQuotes
    ? indiaQuotes[0]?.percent_change ?? null
    : usQuote?.percent_change ?? null;

  const companyName = company.name || company.ticker || ticker;
  const description = company.description || 'No business overview summary provided by provider.';

  return (
    <Card
      title={
        <div className="flex items-center justify-between gap-3 w-full">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 font-bold font-mono">
              <Building2 className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-bold text-white text-base">{companyName}</span>
                <Badge variant="info" size="sm" className="font-mono">
                  {company.ticker || ticker}
                </Badge>
                {company.exchange && (
                  <Badge variant="neutral" size="sm" className="font-mono">
                    {company.exchange}
                  </Badge>
                )}
                {company.country && (
                  <Badge variant="neutral" size="sm" className="font-mono">
                    {company.country}
                  </Badge>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={fetchCompany}
            className="p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            title="Refresh company data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      }
      subtitle={`${company.sector || 'Equities'} • ${company.industry || (isIndia ? 'Indian Market' : 'US Market')}`}
      className={className}
    >
      <div className="space-y-4 text-xs">
        {/* Key Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {/* Real-time Market Price */}
          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1 mb-1">
              <DollarSign className="w-3 h-3 text-cyan-400" />
              Latest Price
            </span>
            <div className="flex items-baseline gap-1.5 flex-wrap">
              <p className="text-sm font-bold text-slate-100 font-mono">
                {primaryPrice !== null ? formatCurrency(primaryPrice, currency) : '—'}
              </p>
              {percentChange !== null && (
                <span
                  className={`text-[11px] font-mono flex items-center ${
                    percentChange >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {percentChange >= 0 ? (
                    <TrendingUp className="w-2.5 h-2.5 inline mr-0.5" />
                  ) : (
                    <TrendingDown className="w-2.5 h-2.5 inline mr-0.5" />
                  )}
                  {percentChange >= 0 ? `+${percentChange.toFixed(2)}%` : `${percentChange.toFixed(2)}%`}
                </span>
              )}
            </div>
          </div>

          {/* Sector */}
          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1 mb-1">
              <Layers className="w-3 h-3 text-indigo-400" />
              Sector
            </span>
            <p className="text-xs font-semibold text-slate-200 truncate" title={company.sector || '—'}>
              {company.sector || '—'}
            </p>
          </div>

          {/* Industry */}
          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1 mb-1">
              <Briefcase className="w-3 h-3 text-emerald-400" />
              Industry
            </span>
            <p className="text-xs font-semibold text-slate-200 truncate" title={company.industry || '—'}>
              {company.industry || '—'}
            </p>
          </div>

          {/* Range / Day Trading Span */}
          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1 mb-1">
              <Globe className="w-3 h-3 text-amber-400" />
              {isArrayQuotes ? '52-Week Range' : 'Day Range'}
            </span>
            <p className="text-xs font-semibold text-slate-200 font-mono truncate">
              {isArrayQuotes && indiaQuotes[0]
                ? `${indiaQuotes[0].year_low !== null ? formatCurrency(indiaQuotes[0].year_low, currency, { compact: true }) : '—'} - ${indiaQuotes[0].year_high !== null ? formatCurrency(indiaQuotes[0].year_high, currency, { compact: true }) : '—'}`
                : usQuote
                ? `${usQuote.low !== null ? formatCurrency(usQuote.low, currency) : '—'} - ${usQuote.high !== null ? formatCurrency(usQuote.high, currency) : '—'}`
                : '—'}
            </p>
          </div>
        </div>

        {/* Multi-Exchange Indian Quotes Strip if applicable */}
        {isArrayQuotes && indiaQuotes.length > 1 && (
          <div className="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800/60 flex items-center gap-4 flex-wrap text-xs">
            <span className="text-[11px] text-slate-400 font-mono">Exchange Quotes:</span>
            {indiaQuotes.map((q, idx) => (
              <div key={idx} className="flex items-center gap-1.5 font-mono text-[11px]">
                <Badge variant="neutral" size="sm">
                  {q.exchange || 'EXCH'}
                </Badge>
                <span className="text-slate-200 font-bold">
                  {q.price !== null ? formatCurrency(q.price, currency) : '—'}
                </span>
                {q.percent_change !== null && (
                  <span className={q.percent_change >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                    ({q.percent_change >= 0 ? `+${q.percent_change}%` : `${q.percent_change}%`})
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* US Market Day Detail Strip if applicable */}
        {usQuote && (usQuote.open !== null || usQuote.previous_close !== null) && (
          <div className="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800/60 flex items-center gap-4 flex-wrap text-xs font-mono">
            {usQuote.open !== null && (
              <span className="text-slate-400 text-[11px]">
                Open: <span className="text-slate-200 font-semibold">{formatCurrency(usQuote.open, currency)}</span>
              </span>
            )}
            {usQuote.previous_close !== null && (
              <span className="text-slate-400 text-[11px]">
                Prev Close: <span className="text-slate-200 font-semibold">{formatCurrency(usQuote.previous_close, currency)}</span>
              </span>
            )}
            {usQuote.change !== null && (
              <span className="text-slate-400 text-[11px]">
                Day Change: <span className={`font-semibold ${usQuote.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{usQuote.change >= 0 ? `+${usQuote.change}` : usQuote.change}</span>
              </span>
            )}
          </div>
        )}

        {/* Business Description */}
        <div>
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono block mb-1.5">
            Business Overview
          </span>
          <p className="text-slate-300 leading-relaxed bg-slate-950/50 p-3.5 rounded-xl border border-slate-800/60 font-sans text-xs sm:text-[13px]">
            {description}
          </p>
        </div>

        {/* Identifiers & Provenance Footer */}
        <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-400 font-mono">
          <div className="flex items-center gap-4 flex-wrap">
            {company.isin && (
              <span className="flex items-center gap-1">
                <Hash className="w-3 h-3 text-cyan-400/80" />
                ISIN: <span className="text-slate-200">{company.isin}</span>
              </span>
            )}
            {company.nse_symbol && (
              <span className="flex items-center gap-1">
                NSE: <span className="text-slate-200">{company.nse_symbol}</span>
              </span>
            )}
            {company.bse_code && (
              <span className="flex items-center gap-1">
                BSE: <span className="text-slate-200">{company.bse_code}</span>
              </span>
            )}
            {company.exchange && !company.nse_symbol && !company.bse_code && (
              <span className="flex items-center gap-1">
                Exchange: <span className="text-slate-200">{company.exchange}</span>
              </span>
            )}
          </div>

          <div className="text-[10px] text-slate-400">
            Source: <span className="text-slate-400 font-mono">Django REST Research API</span>
          </div>
        </div>
      </div>
    </Card>
  );
};
