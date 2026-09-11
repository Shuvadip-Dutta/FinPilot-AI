import React, { useEffect, useState } from 'react';
import { FinancialsData, FinancialPeriod } from '../../types/research';
import { researchApi } from '../../api/research';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { LoadingSkeleton } from '../common/LoadingSkeleton';
import { ErrorState } from '../common/ErrorState';
import {
  FileSpreadsheet,
  TrendingUp,
  DollarSign,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
} from 'lucide-react';
import { formatCurrency, formatPercent, formatRatio } from '../../utils/formatters';

interface FinancialDataViewProps {
  ticker: string;
  market?: string;
  className?: string;
}

export const FinancialDataView: React.FC<FinancialDataViewProps> = ({
  ticker,
  market = 'NSE',
  className = '',
}) => {
  const [financials, setFinancials] = useState<FinancialsData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'periods'>('overview');

  const fetchFinancials = async () => {
    if (!ticker) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await researchApi.getFinancials(ticker, market);
      setFinancials(data);
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setError(apiErr.message || `Failed to fetch financials for ${ticker}.`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFinancials();
  }, [ticker, market]);

  if (isLoading) {
    return (
      <Card title={`Financial Statements: ${ticker}`} className={className}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LoadingSkeleton height="h-16" />
            <LoadingSkeleton height="h-16" />
            <LoadingSkeleton height="h-16" />
            <LoadingSkeleton height="h-16" />
          </div>
          <LoadingSkeleton height="h-44" />
        </div>
      </Card>
    );
  }

  if (error || !financials) {
    return (
      <Card title={`Financial Statements: ${ticker}`} className={className}>
        <ErrorState
          title="Unable to load financial statements"
          message={error || `No financial statement records available for ${ticker}.`}
          onRetry={fetchFinancials}
        />
      </Card>
    );
  }

  const currency = financials.currency || (market === 'NSE' || market === 'BSE' ? 'INR' : 'USD');
  const periods: FinancialPeriod[] =
    financials.periods || financials.annual || financials.quarterly || [];

  // Summary figures either from top level or from most recent period
  const latestPeriod = periods.length > 0 ? periods[0] : null;
  const revenue = financials.revenue ?? latestPeriod?.total_revenue ?? latestPeriod?.revenue;
  const netIncome = financials.net_income ?? latestPeriod?.net_income;
  const operatingIncome = financials.operating_income ?? latestPeriod?.operating_income;
  const grossProfit = financials.gross_profit ?? latestPeriod?.gross_profit;
  const fcf = financials.free_cash_flow ?? latestPeriod?.free_cash_flow;
  const eps = financials.eps ?? latestPeriod?.diluted_eps ?? latestPeriod?.eps;

  // Derived margins
  const netMargin =
    revenue && netIncome ? (netIncome / revenue) * 100 : financials.profit_margin;
  const opMargin =
    revenue && operatingIncome
      ? (operatingIncome / revenue) * 100
      : financials.operating_margin;

  return (
    <Card
      title={
        <div className="flex items-center justify-between gap-3 w-full">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
            <span>Financial Statements</span>
            <Badge variant="neutral" size="sm" className="font-mono">
              {ticker}
            </Badge>
            <Badge variant="info" size="sm" className="font-mono">
              {currency}
            </Badge>
          </div>

          <div className="flex items-center gap-2">
            {periods.length > 0 && (
              <div className="flex rounded-lg bg-slate-950 p-0.5 border border-slate-800 text-[11px] font-mono">
                <button
                  onClick={() => setActiveTab('overview')}
                  className={`px-2 py-0.5 rounded ${
                    activeTab === 'overview'
                      ? 'bg-slate-800 text-white font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Summary
                </button>
                <button
                  onClick={() => setActiveTab('periods')}
                  className={`px-2 py-0.5 rounded ${
                    activeTab === 'periods'
                      ? 'bg-slate-800 text-white font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Period History ({periods.length})
                </button>
              </div>
            )}

            <button
              onClick={fetchFinancials}
              className="p-1 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
              title="Refresh financials"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      }
      subtitle="Income statement, cash generation, and balance sheet capitalization"
      className={className}
    >
      <div className="space-y-4">
        {/* Core KPI Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              Total Revenue
            </span>
            <p className="font-mono font-bold text-slate-100 text-xs sm:text-sm truncate">
              {formatCurrency(revenue, currency, { compact: true })}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              Operating Income
            </span>
            <p className="font-mono font-bold text-slate-100 text-xs sm:text-sm truncate">
              {formatCurrency(operatingIncome, currency, { compact: true })}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              Net Income
            </span>
            <p
              className={`font-mono font-bold text-xs sm:text-sm truncate ${
                netIncome && netIncome >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {formatCurrency(netIncome, currency, { compact: true })}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              Net Margin
            </span>
            <p className="font-mono font-bold text-cyan-300 text-xs sm:text-sm truncate">
              {netMargin !== undefined ? formatPercent(netMargin, false) : '—'}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              Free Cash Flow
            </span>
            <p className="font-mono font-bold text-slate-100 text-xs sm:text-sm truncate">
              {formatCurrency(fcf, currency, { compact: true })}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <span className="text-[10.5px] text-slate-400 font-mono block mb-1">
              EPS (Diluted)
            </span>
            <p className="font-mono font-bold text-slate-100 text-xs sm:text-sm truncate">
              {eps !== undefined ? formatCurrency(eps, currency) : '—'}
            </p>
          </div>
        </div>

        {/* Periods Table View */}
        {activeTab === 'periods' && periods.length > 0 ? (
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-slate-900/90 text-slate-400 font-mono uppercase text-[11px] border-b border-slate-800">
                <tr>
                  <th className="px-3.5 py-2.5 font-semibold text-slate-300">Period</th>
                  <th className="px-3.5 py-2.5 font-semibold text-right">Revenue</th>
                  <th className="px-3.5 py-2.5 font-semibold text-right">Gross Profit</th>
                  <th className="px-3.5 py-2.5 font-semibold text-right">Op. Income</th>
                  <th className="px-3.5 py-2.5 font-semibold text-right">Net Income</th>
                  <th className="px-3.5 py-2.5 font-semibold text-right">EPS</th>
                  <th className="px-3.5 py-2.5 font-semibold text-right">FCF</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[12px]">
                {periods.map((p, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                    <td className="px-3.5 py-2 font-semibold text-slate-200">
                      {p.period || p.year || p.date || `P${idx + 1}`}
                    </td>
                    <td className="px-3.5 py-2 text-right text-slate-300">
                      {formatCurrency(p.total_revenue ?? p.revenue, currency, { compact: true })}
                    </td>
                    <td className="px-3.5 py-2 text-right text-slate-300">
                      {formatCurrency(p.gross_profit, currency, { compact: true })}
                    </td>
                    <td className="px-3.5 py-2 text-right text-slate-300">
                      {formatCurrency(p.operating_income, currency, { compact: true })}
                    </td>
                    <td
                      className={`px-3.5 py-2 text-right font-semibold ${
                        (p.net_income ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {formatCurrency(p.net_income, currency, { compact: true })}
                    </td>
                    <td className="px-3.5 py-2 text-right text-slate-300">
                      {p.eps !== undefined || p.diluted_eps !== undefined
                        ? formatCurrency(p.diluted_eps ?? p.eps, currency)
                        : '—'}
                    </td>
                    <td className="px-3.5 py-2 text-right text-slate-300">
                      {formatCurrency(p.free_cash_flow, currency, { compact: true })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          /* Balance Sheet & Cash Flow Structure Breakdown */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-2">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Activity className="w-3 h-3 text-cyan-400" />
                Capitalization & Balance Sheet
              </span>
              <div className="space-y-1.5 font-mono">
                <div className="flex justify-between py-1 border-b border-slate-900">
                  <span className="text-slate-400">Total Assets:</span>
                  <span className="text-slate-200 font-semibold">
                    {formatCurrency(financials.total_assets ?? latestPeriod?.total_assets, currency, { compact: true })}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-900">
                  <span className="text-slate-400">Total Liabilities:</span>
                  <span className="text-slate-200 font-semibold">
                    {formatCurrency(financials.total_liabilities ?? latestPeriod?.total_liabilities, currency, { compact: true })}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-900">
                  <span className="text-slate-400">Total Debt:</span>
                  <span className="text-slate-200 font-semibold">
                    {formatCurrency(financials.total_debt ?? latestPeriod?.total_debt, currency, { compact: true })}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Cash & Equivalents:</span>
                  <span className="text-emerald-400 font-semibold">
                    {formatCurrency(latestPeriod?.cash_and_equivalents, currency, { compact: true })}
                  </span>
                </div>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-2">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <TrendingUp className="w-3 h-3 text-emerald-400" />
                Profitability & Cash Generation
              </span>
              <div className="space-y-1.5 font-mono">
                <div className="flex justify-between py-1 border-b border-slate-900">
                  <span className="text-slate-400">Gross Margin:</span>
                  <span className="text-slate-200 font-semibold">
                    {revenue && grossProfit ? formatPercent((grossProfit / revenue) * 100, false) : '—'}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-900">
                  <span className="text-slate-400">Operating Margin:</span>
                  <span className="text-slate-200 font-semibold">
                    {opMargin !== undefined ? formatPercent(opMargin, false) : '—'}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-900">
                  <span className="text-slate-400">Operating Cash Flow:</span>
                  <span className="text-slate-200 font-semibold">
                    {formatCurrency(latestPeriod?.operating_cash_flow, currency, { compact: true })}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Capital Expenditure:</span>
                  <span className="text-rose-300 font-semibold">
                    {formatCurrency(latestPeriod?.capital_expenditure, currency, { compact: true })}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
