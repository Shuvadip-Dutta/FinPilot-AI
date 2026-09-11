import React, { useEffect, useState } from 'react';
import { CompanyProfile } from '../../types/research';
import { researchApi } from '../../api/research';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { LoadingSkeleton } from '../common/LoadingSkeleton';
import { ErrorState } from '../common/ErrorState';
import {
  Building2,
  Globe,
  MapPin,
  Calendar,
  Users,
  Briefcase,
  ExternalLink,
  DollarSign,
  Layers,
  RefreshCw,
} from 'lucide-react';
import { formatCurrency } from '../../utils/formatters';

interface CompanyResearchViewProps {
  ticker: string;
  market?: string;
  className?: string;
}

export const CompanyResearchView: React.FC<CompanyResearchViewProps> = ({
  ticker,
  market = 'NSE',
  className = '',
}) => {
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCompany = async () => {
    if (!ticker) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await researchApi.getCompany(ticker, market);
      setCompany(data);
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setError(apiErr.message || `Failed to fetch company profile for ${ticker}.`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCompany();
  }, [ticker, market]);

  if (isLoading) {
    return (
      <Card title={`Company Profile: ${ticker}`} className={className}>
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

  if (error || !company) {
    return (
      <Card title={`Company Profile: ${ticker}`} className={className}>
        <ErrorState
          title="Unable to load company profile"
          message={error || `No company fundamentals found for ${ticker} on ${market}.`}
          onRetry={fetchCompany}
        />
      </Card>
    );
  }

  const name = company.name || company.company_name || ticker;
  const description = company.description || company.summary || 'No overview summary provided.';
  const marketCap = company.market_cap ?? company.market_capitalization;
  const currency = company.currency || (market === 'NSE' || market === 'BSE' ? 'INR' : 'USD');

  return (
    <Card
      title={
        <div className="flex items-center justify-between gap-3 w-full">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 font-bold font-mono">
              <Building2 className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-base">{name}</span>
                <Badge variant="info" size="sm" className="font-mono">
                  {ticker}
                </Badge>
                <Badge variant="neutral" size="sm" className="font-mono">
                  {company.exchange || market}
                </Badge>
              </div>
            </div>
          </div>

          <button
            onClick={fetchCompany}
            className="p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            title="Refresh company profile"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      }
      subtitle={`${company.sector || 'Equities'} • ${company.industry || 'Market Capitalization'}`}
      className={className}
    >
      <div className="space-y-4 text-xs">
        {/* Key Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1 mb-1">
              <DollarSign className="w-3 h-3 text-cyan-400" />
              Market Cap
            </span>
            <p className="text-sm font-bold text-slate-100 font-mono">
              {marketCap ? formatCurrency(marketCap, currency, { compact: true }) : '—'}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1 mb-1">
              <Layers className="w-3 h-3 text-indigo-400" />
              Sector
            </span>
            <p className="text-xs font-semibold text-slate-200 truncate">
              {company.sector || '—'}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1 mb-1">
              <Briefcase className="w-3 h-3 text-emerald-400" />
              Industry
            </span>
            <p className="text-xs font-semibold text-slate-200 truncate">
              {company.industry || '—'}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1 mb-1">
              <Users className="w-3 h-3 text-amber-400" />
              Leadership
            </span>
            <p className="text-xs font-semibold text-slate-200 truncate">
              {company.ceo || '—'}
            </p>
          </div>
        </div>

        {/* Business Description */}
        <div>
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono block mb-1.5">
            Business Overview
          </span>
          <p className="text-slate-300 leading-relaxed bg-slate-950/50 p-3.5 rounded-xl border border-slate-800/60 font-sans text-xs sm:text-[13px]">
            {description}
          </p>
        </div>

        {/* Metadata Footer: Headquarters, Founded, Employees, Website */}
        <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-400 font-mono">
          <div className="flex items-center gap-4 flex-wrap">
            {company.headquarters && (
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3 text-cyan-400/80" />
                {company.headquarters}
              </span>
            )}
            {company.founded && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3 text-slate-500" />
                Founded {company.founded}
              </span>
            )}
            {company.employees && (
              <span className="flex items-center gap-1">
                <Users className="w-3 h-3 text-slate-500" />
                {company.employees.toLocaleString()} employees
              </span>
            )}
          </div>

          {company.website && (
            <a
              href={company.website.startsWith('http') ? company.website : `https://${company.website}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
            >
              <Globe className="w-3 h-3" />
              <span>Official Website</span>
              <ExternalLink className="w-2.5 h-2.5" />
            </a>
          )}
        </div>
      </div>
    </Card>
  );
};
