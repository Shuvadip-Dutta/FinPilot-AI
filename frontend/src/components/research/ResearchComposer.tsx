import React, { useState, useRef, useEffect } from 'react';
import { Button } from '../common/Button';
import {
  Send,
  Sparkles,
  Search,
  Command,
  CornerDownLeft,
  X,
  TrendingUp,
  FileSpreadsheet,
  Newspaper,
  ShieldCheck,
} from 'lucide-react';

interface ResearchComposerProps {
  onSubmit: (prompt: string, ticker: string, market: string) => void;
  isLoading: boolean;
  initialTicker?: string;
  initialMarket?: string;
  placeholder?: string;
}

const PRESET_PROMPTS = [
  {
    icon: Sparkles,
    label: 'Comprehensive Financial Analysis',
    template: (t: string, m: string) =>
      `Provide a comprehensive equity research breakdown for ${t} (${m}). Analyze revenue growth, operating margin durability, return on invested capital, and competitive moat vs peers.`,
  },
  {
    icon: FileSpreadsheet,
    label: 'Financials & Balance Sheet Health',
    template: (t: string, m: string) =>
      `Evaluate the balance sheet health, debt-to-equity ratio, free cash flow generation, and working capital cycle for ${t} (${m}). Are there any red flags?`,
  },
  {
    icon: TrendingUp,
    label: 'Valuation & Multiples vs Sector',
    template: (t: string, m: string) =>
      `Assess the current valuation of ${t} (${m}) based on trailing and forward P/E, EV/EBITDA, and price-to-book ratios. Is it trading at a discount or premium to historical averages?`,
  },
  {
    icon: Newspaper,
    label: 'Recent News & Sentiment Impact',
    template: (t: string, m: string) =>
      `Synthesize the latest news, regulatory filings, and market sentiment for ${t} (${m}). Highlight key near-term catalysts and downside risks.`,
  },
];

const POPULAR_TICKERS = [
  { ticker: 'RELIANCE', market: 'IN' },
  { ticker: 'TCS', market: 'IN' },
  { ticker: 'HDFCBANK', market: 'IN' },
  { ticker: 'INFY', market: 'IN' },
  { ticker: 'AAPL', market: 'US' },
  { ticker: 'NVDA', market: 'US' },
  { ticker: 'MSFT', market: 'US' },
];

export const ResearchComposer: React.FC<ResearchComposerProps> = ({
  onSubmit,
  isLoading,
  initialTicker = 'RELIANCE',
  initialMarket = 'IN',
  placeholder = 'Ask FinPilot AI any financial question or synthesis request...',
}) => {
  const [prompt, setPrompt] = useState('');
  const [ticker, setTicker] = useState(initialTicker);
  const [market, setMarket] = useState(initialMarket);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (initialTicker) setTicker(initialTicker);
  }, [initialTicker]);

  useEffect(() => {
    if (initialMarket) setMarket(initialMarket);
  }, [initialMarket]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!prompt.trim() || isLoading) return;
    onSubmit(prompt.trim(), ticker.trim().toUpperCase(), market.trim().toUpperCase());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  const applyPreset = (presetFn: (t: string, m: string) => string) => {
    const activeTicker = ticker.trim() || 'RELIANCE';
    const activeMarket = market.trim() || 'IN';
    const text = presetFn(activeTicker, activeMarket);
    setPrompt(text);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800/90 rounded-2xl p-4 sm:p-5 shadow-xl backdrop-blur-md">
      {/* Ticker & Market Configuration Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3 pb-3 border-b border-slate-800/60">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5 font-mono">
            <Search className="w-3.5 h-3.5 text-cyan-400" />
            TARGET ASSET:
          </span>

          {/* Ticker Input */}
          <div className="relative">
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="e.g. RELIANCE"
              className="w-32 px-2.5 py-1 text-xs font-mono font-bold uppercase rounded-lg bg-slate-950 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Market Selector */}
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value)}
            className="px-2.5 py-1 text-xs font-mono rounded-lg bg-slate-950 border border-slate-700 text-cyan-300 focus:outline-none focus:border-cyan-500 cursor-pointer"
          >
            <option value="IN">India (NSE/BSE)</option>
            <option value="US">United States (US)</option>
          </select>

          {/* Quick Ticker Chips */}
          <div className="hidden md:flex items-center gap-1.5 ml-2 text-[11px] text-slate-500 font-mono">
            <span>Quick:</span>
            {POPULAR_TICKERS.map((t) => (
              <button
                key={t.ticker}
                type="button"
                onClick={() => {
                  setTicker(t.ticker);
                  setMarket(t.market);
                }}
                className={`px-1.5 py-0.5 rounded text-[10px] transition-colors cursor-pointer ${
                  ticker === t.ticker
                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-700'
                    : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {t.ticker}
              </button>
            ))}
          </div>
        </div>

        {prompt && (
          <button
            type="button"
            onClick={() => setPrompt('')}
            className="text-slate-500 hover:text-slate-300 text-xs flex items-center gap-1 cursor-pointer transition-colors"
          >
            <X className="w-3 h-3" />
            <span>Clear</span>
          </button>
        )}
      </div>

      {/* Composer Input Form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative">
          <textarea
            ref={textareaRef}
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder={placeholder}
            className="w-full px-3.5 py-3 rounded-xl bg-slate-950/80 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40 resize-none leading-relaxed transition-all disabled:opacity-50"
          />
        </div>

        {/* Preset Prompt Recommendations */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
          <span className="text-[11px] font-mono text-slate-500 shrink-0 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-cyan-400" />
            Presets:
          </span>
          {PRESET_PROMPTS.map((preset, index) => {
            const Icon = preset.icon;
            return (
              <button
                key={index}
                type="button"
                onClick={() => applyPreset(preset.template)}
                disabled={isLoading}
                className="shrink-0 px-2.5 py-1 rounded-lg bg-slate-950/80 hover:bg-slate-800/80 border border-slate-800 text-[11px] text-slate-300 hover:text-cyan-300 transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-40"
              >
                <Icon className="w-3 h-3 text-cyan-400" />
                <span>{preset.label}</span>
              </button>
            );
          })}
        </div>

        {/* Footer with Action & Shortcut Hint */}
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
            <span className="hidden sm:inline-flex items-center gap-1">
              <Command className="w-3 h-3" />
              <span>or Ctrl +</span>
              <CornerDownLeft className="w-3 h-3" />
              <span>to send</span>
            </span>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="md"
            isLoading={isLoading}
            disabled={!prompt.trim() || isLoading}
            rightIcon={<Send className="w-4 h-4" />}
            className="font-semibold shadow-md shadow-cyan-500/20"
          >
            Ask FinPilot AI
          </Button>
        </div>
      </form>
    </div>
  );
};
