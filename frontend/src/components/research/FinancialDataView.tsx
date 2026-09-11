import React, { useEffect, useState } from 'react';
import {
  FinancialsResponse,
  FinancialStatementItem,
  KeyMetricsResponse,
  KeyMetricItem,
} from '../../types/research';
import { ApiError } from '../../types/api';
import { researchApi } from '../../api/research';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { LoadingSkeleton } from '../common/LoadingSkeleton';
import { ErrorState } from '../common/ErrorState';
import {
  FileSpreadsheet,
  Layers,
  RefreshCw,
  AlertCircle,
  Activity,
  DollarSign,
  TrendingUp,
} from 'lucide-react';
import { formatCurrency, formatNumber } from '../../utils/formatters';

interface FinancialDataViewProps {
  ticker: string;
  market?: string;
  className?: string;
}

export const FinancialDataView: React.FC<FinancialDataViewProps> = ({
  ticker,
  market = 'IN',
  className = '',
}) => {
  const [financials, setFinancials] = useState<FinancialsResponse | null>(null);
  const [metrics, setMetrics] = useState<KeyMetricsResponse | null>(null);
  const [isLoadingFinancials, setIsLoadingFinancials] = useState<boolean>(true);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState<boolean>(true);
  const [financialsError, setFinancialsError] = useState<string | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [isMarketRestricted, setIsMarketRestricted] = useState<boolean>(false);

  // Sub-tabs: 'statements' | 'metrics'
  const [activeTab, setActiveTab] = useState<'statements' | 'metrics'>('statements');

  // Filter for statement types (e.g. 'ALL', 'INC', 'BAL', 'CAS')
  const [selectedStatementType, setSelectedStatementType] = useState<string>('ALL');

  const fetchData = async () => {
    if (!ticker || !ticker.trim()) return;

    // Stale data protection: immediately clear previous records
    setFinancials(null);
    setMetrics(null);
    setFinancialsError(null);
    setMetricsError(null);
    setIsMarketRestricted(false);
    setIsLoadingFinancials(true);
    setIsLoadingMetrics(true);

    const isUS = market.trim().toUpperCase() === 'US' || market.trim().toUpperCase() === 'USA';

    // 1. Fetch Financial Statements
    try {
      const finData = await researchApi.getFinancials(ticker, market);
      setFinancials(finData);
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      if (apiErr.status === 400 && (isUS || JSON.stringify(apiErr).includes('valid choice'))) {
        setIsMarketRestricted(true);
        setFinancialsError(
          `Financial Statements are currently supported exclusively for the Indian market (IN / NSE / BSE). Upstream providers for market "${market}" are not yet available.`
        );
      } else if (apiErr.isNetworkError) {
        setFinancialsError('Unable to connect to the FinPilot server. Please ensure the Django backend is running.');
      } else if (apiErr.status === 404) {
        setFinancialsError(apiErr.detail || apiErr.message || `No financial statements found for ${ticker}.`);
      } else if (apiErr.status === 429) {
        setFinancialsError('Rate limit exceeded. Please wait a moment before retrying.');
      } else if (apiErr.status === 502) {
        setFinancialsError('External market data provider is currently unavailable.');
      } else {
        setFinancialsError(apiErr.detail || apiErr.message || `Failed to fetch financial statements for ${ticker}.`);
      }
    } finally {
      setIsLoadingFinancials(false);
    }

    // 2. Fetch Key Metrics
    try {
      const metData = await researchApi.getMetrics(ticker, market);
      setMetrics(metData);
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      if (apiErr.status === 400 && (isUS || JSON.stringify(apiErr).includes('valid choice'))) {
        setIsMarketRestricted(true);
        setMetricsError(
          `Financial Metrics are currently supported exclusively for the Indian market (IN / NSE / BSE). Upstream providers for market "${market}" are not yet available.`
        );
      } else if (apiErr.isNetworkError) {
        setMetricsError('Unable to connect to the FinPilot server.');
      } else if (apiErr.status === 404) {
        setMetricsError(apiErr.detail || apiErr.message || `No key metrics found for ${ticker}.`);
      } else if (apiErr.status === 429) {
        setMetricsError('Rate limit exceeded. Please wait a moment before retrying.');
      } else if (apiErr.status === 502) {
        setMetricsError('External market data provider is currently unavailable.');
      } else {
        setMetricsError(apiErr.detail || apiErr.message || `Failed to fetch key metrics for ${ticker}.`);
      }
    } finally {
      setIsLoadingMetrics(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [ticker, market]);

  const isLoading = isLoadingFinancials || isLoadingMetrics;
  const currency = market.toUpperCase() === 'IN' || market.toUpperCase() === 'NSE' || market.toUpperCase() === 'BSE' ? 'INR' : 'USD';

  // Render loading skeleton
  if (isLoading && !financials && !metrics) {
    return (
      <Card title={`Financial Data: ${ticker.toUpperCase()}`} className={className}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LoadingSkeleton height="h-16" />
            <LoadingSkeleton height="h-16" />
            <LoadingSkeleton height="h-16" />
            <LoadingSkeleton height="h-16" />
          </div>
          <LoadingSkeleton height="h-64" />
        </div>
      </Card>
    );
  }

  // Market constraint state (e.g. US market requested on India-only endpoints)
  if (isMarketRestricted) {
    return (
      <Card
        title={
          <div className="flex items-center justify-between gap-3 w-full">
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-amber-400" />
              <span>Financial Data: {ticker.toUpperCase()}</span>
              <Badge variant="warning" size="sm" className="font-mono">
                {market.toUpperCase()}
              </Badge>
            </div>
            <button
              onClick={fetchData}
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
              Market Constraint: Indian Equities Only
            </h3>
            <p className="text-xs text-amber-300/80 mt-1 max-w-md leading-relaxed">
              Financial statements and valuation metrics are currently integrated exclusively for the Indian market (<span className="font-mono text-amber-200">IN</span> / NSE / BSE).
            </p>
            <p className="text-[11px] text-slate-400 mt-2">
              To inspect financial statements, search for Indian equities such as <span className="font-mono text-cyan-300">RELIANCE</span> or <span className="font-mono text-cyan-300">TCS</span> on the <span className="font-mono text-cyan-300">IN</span> market.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  // Raw statements array from backend
  const statementList: FinancialStatementItem[] = financials?.financials || [];
  const metricsList: KeyMetricItem[] = metrics?.metrics || [];

  // Derive distinct statement types present in response (e.g. ['INC', 'BAL', 'CAS'])
  const availableStatementTypes = Array.from(
    new Set(statementList.map((s) => s.statement_type).filter(Boolean))
  );

  // Filter statements according to selectedStatementType tab
  const filteredStatements = selectedStatementType === 'ALL'
    ? statementList
    : statementList.filter((s) => s.statement_type === selectedStatementType);

  // Derive distinct periods/fiscal years dynamically across filtered statements
  const dynamicPeriods = Array.from(
    new Set(
      filteredStatements
        .map((s) => s.fiscal_year || s.end_date)
        .filter(Boolean)
    )
  ).sort((a, b) => {
    // Sort descending so latest period is first
    const numA = parseInt(a, 10);
    const numB = parseInt(b, 10);
    if (!isNaN(numA) && !isNaN(numB)) return numB - numA;
    return b.localeCompare(a);
  });

  // Group statement types present in filtered set for section headers
  const statementTypeGroups = selectedStatementType === 'ALL'
    ? availableStatementTypes
    : [selectedStatementType];

  // Derive distinct metric categories from backend key metrics
  const metricCategories = Array.from(
    new Set(metricsList.map((m) => m.category || 'general').filter(Boolean))
  );

  const getStatementTypeLabel = (type: string) => {
    switch (type.toUpperCase()) {
      case 'INC':
        return 'Income Statement';
      case 'BAL':
        return 'Balance Sheet';
      case 'CAS':
        return 'Cash Flow Statement';
      default:
        return type;
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category.toLowerCase()) {
      case 'valuation':
        return 'Valuation Multiples';
      case 'profitability':
        return 'Profitability & Returns';
      case 'liquidity':
        return 'Liquidity & Solvency';
      case 'mgmteffectiveness':
        return 'Management Effectiveness';
      case 'growth':
        return 'Growth Metrics';
      default:
        return category.charAt(0).toUpperCase() + category.slice(1);
    }
  };

  return (
    <Card
      title={
        <div className="flex items-center justify-between gap-3 w-full flex-wrap">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-emerald-950/80 border border-emerald-800/60 flex items-center justify-center text-emerald-400">
              <FileSpreadsheet className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-base">Financial Research</span>
                <Badge variant="info" size="sm" className="font-mono">
                  {ticker.toUpperCase()}
                </Badge>
                <Badge variant="neutral" size="sm" className="font-mono">
                  {market.toUpperCase()}
                </Badge>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* View Switcher: Statements vs Metrics */}
            <div className="flex rounded-lg bg-slate-950 p-0.5 border border-slate-800 text-xs font-mono">
              <button
                onClick={() => setActiveTab('statements')}
                className={`px-3 py-1 rounded transition-colors cursor-pointer ${
                  activeTab === 'statements'
                    ? 'bg-slate-800 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Statements {statementList.length > 0 ? `(${statementList.length})` : ''}
              </button>
              <button
                onClick={() => setActiveTab('metrics')}
                className={`px-3 py-1 rounded transition-colors cursor-pointer ${
                  activeTab === 'metrics'
                    ? 'bg-slate-800 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Key Metrics {metricsList.length > 0 ? `(${metricsList.length})` : ''}
              </button>
            </div>

            <button
              onClick={fetchData}
              className="p-1.5 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
              title="Refresh financial data"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      }
      subtitle="Audited financial statements and authoritative valuation ratios from Django"
      className={className}
    >
      <div className="space-y-5">
        {/* Top Key Metrics Overview Bar (if metrics are available) */}
        {metricsList.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
            {metricsList.map((m, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1"
              >
                <span className="text-[10px] text-slate-400 font-mono block truncate" title={m.name}>
                  {m.name}
                </span>
                <p className="text-xs font-bold text-slate-100 font-mono">
                  {m.raw_value || (m.value !== null ? formatNumber(m.value) : '—')}
                </p>
                <span className="text-[9px] text-slate-400 font-mono block uppercase">
                  {m.category}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* TAB 1: FINANCIAL STATEMENTS */}
        {activeTab === 'statements' && (
          <div className="space-y-4">
            {financialsError ? (
              <ErrorState
                title="Unable to load financial statements"
                message={financialsError}
                onRetry={fetchData}
              />
            ) : statementList.length === 0 ? (
              <div className="p-8 rounded-xl bg-slate-950/40 border border-slate-800/80 text-center text-xs text-slate-400">
                <p className="font-semibold text-slate-300">No financial statement records returned</p>
                <p className="mt-1 text-[11px] text-slate-400">
                  The upstream provider did not return audited statements for {ticker} on {market}.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Statement Type Filter Pills */}
                {availableStatementTypes.length > 1 && (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-[11px] text-slate-400 font-mono mr-1">Statement:</span>
                    <button
                      onClick={() => setSelectedStatementType('ALL')}
                      className={`px-2.5 py-1 rounded-md text-xs font-mono transition-colors cursor-pointer ${
                        selectedStatementType === 'ALL'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold'
                          : 'bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800'
                      }`}
                    >
                      All ({statementList.length})
                    </button>
                    {availableStatementTypes.map((type) => (
                      <button
                        key={type}
                        onClick={() => setSelectedStatementType(type)}
                        className={`px-2.5 py-1 rounded-md text-xs font-mono transition-colors cursor-pointer ${
                          selectedStatementType === type
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold'
                            : 'bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800'
                        }`}
                      >
                        {getStatementTypeLabel(type)} ({statementList.filter((s) => s.statement_type === type).length})
                      </button>
                    ))}
                  </div>
                )}

                {/* Dynamic Statements Table for each statement type group */}
                {statementTypeGroups.map((stType) => {
                  const typeStatements = filteredStatements.filter((s) => s.statement_type === stType);
                  if (typeStatements.length === 0) return null;

                  // Derive unique periods for this statement type
                  const typePeriods = Array.from(
                    new Set(typeStatements.map((s) => s.fiscal_year || s.end_date).filter(Boolean))
                  ).sort((a, b) => {
                    const numA = parseInt(a, 10);
                    const numB = parseInt(b, 10);
                    if (!isNaN(numA) && !isNaN(numB)) return numB - numA;
                    return b.localeCompare(a);
                  });

                  // Derive unique metrics dynamically across these statements
                  const metricKeysMap = new Map<string, string>();
                  typeStatements.forEach((stmt) => {
                    stmt.metrics.forEach((m) => {
                      if (m.key && !metricKeysMap.has(m.key)) {
                        metricKeysMap.set(m.key, m.name || m.key);
                      }
                    });
                  });

                  const uniqueMetricKeys = Array.from(metricKeysMap.keys());

                  return (
                    <div
                      key={stType}
                      className="rounded-xl border border-slate-800 bg-slate-950/70 overflow-hidden space-y-0"
                    >
                      {/* Statement Header */}
                      <div className="px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between">
                        <span className="font-semibold text-xs text-slate-200 flex items-center gap-1.5">
                          <Layers className="w-3.5 h-3.5 text-emerald-400" />
                          {getStatementTypeLabel(stType)}
                        </span>
                        <Badge variant="neutral" size="sm" className="font-mono">
                          {typeStatements[0]?.period_type || 'Annual'}
                        </Badge>
                      </div>

                      {/* Period Columns Table */}
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left border-collapse">
                          <thead className="bg-slate-950/80 text-slate-400 font-mono uppercase text-[10.5px] border-b border-slate-800/80">
                            <tr>
                              <th className="px-4 py-2.5 font-semibold text-slate-300">Metric</th>
                              {typePeriods.map((period) => (
                                <th key={period} className="px-4 py-2.5 font-semibold text-right text-slate-300 whitespace-nowrap">
                                  {period.startsWith('20') ? `FY ${period}` : period}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                            {uniqueMetricKeys.map((key) => {
                              const metricName = metricKeysMap.get(key) || key;
                              return (
                                <tr key={key} className="hover:bg-slate-900/40 transition-colors">
                                  <td className="px-4 py-2 font-medium text-slate-200 font-sans">
                                    {metricName}
                                  </td>
                                  {typePeriods.map((period) => {
                                    const matchingStmt = typeStatements.find(
                                      (s) => (s.fiscal_year || s.end_date) === period
                                    );
                                    const metric = matchingStmt?.metrics.find((m) => m.key === key);
                                    const val = metric?.value;

                                    return (
                                      <td
                                        key={period}
                                        className={`px-4 py-2 text-right font-mono ${
                                          val !== null && val !== undefined && val < 0
                                            ? 'text-rose-400'
                                            : 'text-slate-300'
                                        }`}
                                      >
                                        {val !== null && val !== undefined
                                          ? formatCurrency(val, currency, { compact: true })
                                          : '—'}
                                      </td>
                                    );
                                  })}
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: FINANCIAL METRICS */}
        {activeTab === 'metrics' && (
          <div className="space-y-4">
            {metricsError ? (
              <ErrorState
                title="Unable to load financial metrics"
                message={metricsError}
                onRetry={fetchData}
              />
            ) : metricsList.length === 0 ? (
              <div className="p-8 rounded-xl bg-slate-950/40 border border-slate-800/80 text-center text-xs text-slate-400">
                <p className="font-semibold text-slate-300">No key metrics returned</p>
                <p className="mt-1 text-[11px] text-slate-400">
                  The upstream provider did not return valuation or ratio metrics for {ticker} on {market}.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {metricCategories.map((category) => {
                  const categoryMetrics = metricsList.filter(
                    (m) => (m.category || 'general') === category
                  );

                  return (
                    <div
                      key={category}
                      className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-3"
                    >
                      <span className="text-xs font-bold text-slate-200 font-mono uppercase tracking-wider flex items-center gap-1.5">
                        <Activity className="w-3.5 h-3.5 text-cyan-400" />
                        {getCategoryLabel(category)}
                      </span>

                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {categoryMetrics.map((m, idx) => {
                          const displayValue = m.raw_value || (m.value !== null ? formatNumber(m.value) : '—');
                          const isNegative = m.value !== null && m.value < 0;

                          return (
                            <div
                              key={idx}
                              className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/60 flex items-center justify-between"
                            >
                              <div className="space-y-0.5">
                                <p className="text-xs text-slate-300 font-medium">{m.name}</p>
                                <p className="text-[10px] text-slate-400 font-mono">{m.key}</p>
                              </div>
                              <span
                                className={`text-sm font-bold font-mono ${
                                  isNegative ? 'text-rose-400' : 'text-slate-100'
                                }`}
                              >
                                {displayValue}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Provenance Footer */}
        <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-400 font-mono">
          <div className="flex items-center gap-2">
            <span>Market: <strong className="text-slate-300">{market.toUpperCase()}</strong></span>
            <span>•</span>
            <span>Currency: <strong className="text-slate-300">{currency}</strong></span>
          </div>
          <div>
            Source: <span className="text-slate-400 font-mono">Django REST Research Service</span>
          </div>
        </div>
      </div>
    </Card>
  );
};
