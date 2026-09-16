import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { PageHeader } from '../../components/layout/PageHeader';
import { MarketDataView } from '../../components/research/MarketDataView';
import { CompanyResearchView } from '../../components/research/CompanyResearchView';
import { FinancialDataView } from '../../components/research/FinancialDataView';
import { NewsView } from '../../components/research/NewsView';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import {
  TrendingUp,
  Building2,
  FileSpreadsheet,
  Newspaper,
  Search,
  Sparkles,
  ArrowRight,
} from 'lucide-react';

type MarketTab = 'valuation' | 'company' | 'financials' | 'news';

const QUICK_TICKERS = [
  { ticker: 'RELIANCE', market: 'NSE' },
  { ticker: 'TCS', market: 'NSE' },
  { ticker: 'HDFCBANK', market: 'NSE' },
  { ticker: 'INFY', market: 'NSE' },
  { ticker: 'ICICIBANK', market: 'NSE' },
  { ticker: 'AAPL', market: 'NASDAQ' },
  { ticker: 'NVDA', market: 'NASDAQ' },
  { ticker: 'MSFT', market: 'NASDAQ' },
];

export const MarketsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [inputTicker, setInputTicker] = useState(searchParams.get('ticker') || 'RELIANCE');
  const [activeTicker, setActiveTicker] = useState(searchParams.get('ticker') || 'RELIANCE');
  const [market, setMarket] = useState(searchParams.get('market') || 'NSE');
  const [activeTab, setActiveTab] = useState<MarketTab>('valuation');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputTicker.trim()) return;
    const clean = inputTicker.trim().toUpperCase();
    setActiveTicker(clean);
    setSearchParams({ ticker: clean, market });
  };

  const selectQuickTicker = (t: string, m: string) => {
    setInputTicker(t);
    setActiveTicker(t);
    setMarket(m);
    setSearchParams({ ticker: t, market: m });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Market Intelligence & Fundamentals"
        subtitle="Real-time valuation multiples, historical OHLCV charts, financial filings & news sentiment"
        badge={
          <Badge variant="info" size="sm" dot>
            Live Market Data
          </Badge>
        }
        actions={
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Sparkles className="w-4 h-4" />}
            onClick={() => navigate(`/app/research?ticker=${activeTicker}&market=${market}`)}
          >
            Synthesize with AI
          </Button>
        }
      />

      {/* Asset Search & Quick Select Bar */}
      <div className="p-4 rounded-2xl bg-surface border border-border-theme space-y-3">
        <form onSubmit={handleSearch} className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[240px] relative">
            <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputTicker}
              onChange={(e) => setInputTicker(e.target.value.toUpperCase())}
              placeholder="Search ticker (e.g. RELIANCE, TCS, AAPL)..."
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-surface-secondary border border-border-theme text-xs font-mono font-bold uppercase text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30"
            />
          </div>

          <select
            value={market}
            onChange={(e) => setMarket(e.target.value)}
            className="px-3 py-2 text-xs font-mono rounded-xl bg-surface-secondary border border-border-theme text-text-primary focus:outline-none focus:border-accent-primary cursor-pointer"
          >
            <option value="NSE">NSE (India)</option>
            <option value="BSE">BSE (India)</option>
            <option value="NASDAQ">NASDAQ (US)</option>
            <option value="NYSE">NYSE (US)</option>
          </select>

          <Button type="submit" variant="primary" size="sm">
            Load Asset
          </Button>
        </form>

        {/* Quick Tickers */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] font-mono text-text-muted pt-1">
          <span className="shrink-0">Popular:</span>
          {QUICK_TICKERS.map((item) => (
            <button
              key={item.ticker}
              type="button"
              onClick={() => selectQuickTicker(item.ticker, item.market)}
              className={`px-2 py-0.5 rounded transition-colors cursor-pointer shrink-0 ${
                activeTicker === item.ticker && market === item.market
                  ? 'bg-accent-soft text-accent-primary border border-accent-primary/30 font-semibold'
                  : 'bg-surface-secondary text-text-muted hover:text-text-primary border border-border-subtle'
              }`}
            >
              {item.ticker} ({item.market})
            </button>
          ))}
        </div>
      </div>

      {/* Sub-view Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-border-subtle pb-2 overflow-x-auto text-xs font-mono">
        <button
          onClick={() => setActiveTab('valuation')}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
            activeTab === 'valuation'
              ? 'bg-accent-soft text-accent-primary border border-accent-primary/30 font-semibold'
              : 'text-text-muted hover:text-text-primary hover:bg-surface-secondary/60'
          }`}
        >
          <TrendingUp className="w-3.5 h-3.5" />
          <span>Valuation & Historical Chart</span>
        </button>

        <button
          onClick={() => setActiveTab('company')}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
            activeTab === 'company'
              ? 'bg-accent-soft text-accent-primary border border-accent-primary/30 font-semibold'
              : 'text-text-muted hover:text-text-primary hover:bg-surface-secondary/60'
          }`}
        >
          <Building2 className="w-3.5 h-3.5" />
          <span>Company Overview</span>
        </button>

        <button
          onClick={() => setActiveTab('financials')}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
            activeTab === 'financials'
              ? 'bg-accent-soft text-accent-primary border border-accent-primary/30 font-semibold'
              : 'text-text-muted hover:text-text-primary hover:bg-surface-secondary/60'
          }`}
        >
          <FileSpreadsheet className="w-3.5 h-3.5" />
          <span>Financial Statements</span>
        </button>

        <button
          onClick={() => setActiveTab('news')}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
            activeTab === 'news'
              ? 'bg-accent-soft text-accent-primary border border-accent-primary/30 font-semibold'
              : 'text-text-muted hover:text-text-primary hover:bg-surface-secondary/60'
          }`}
        >
          <Newspaper className="w-3.5 h-3.5" />
          <span>News & Sentiment</span>
        </button>
      </div>

      {/* Render Active View */}
      {activeTab === 'valuation' && (
        <MarketDataView ticker={activeTicker} market={market} />
      )}

      {activeTab === 'company' && (
        <CompanyResearchView ticker={activeTicker} market={market} />
      )}

      {activeTab === 'financials' && (
        <FinancialDataView ticker={activeTicker} market={market} />
      )}

      {activeTab === 'news' && (
        <NewsView ticker={activeTicker} market={market} />
      )}
    </div>
  );
};
