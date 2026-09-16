import React from 'react';
import { BrainCircuit, Loader2, Server } from 'lucide-react';

interface ResearchLoadingStateProps {
  query?: string;
  ticker?: string;
  market?: string;
}

export const ResearchLoadingState: React.FC<ResearchLoadingStateProps> = ({
  query,
  ticker,
  market,
}) => {
  return (
    <div className="p-6 rounded-2xl bg-surface border border-accent-primary/30 shadow-card relative overflow-hidden">
      {/* Background ambient sweep */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-accent-primary/5 to-transparent animate-pulse pointer-events-none" />

      <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="w-12 h-12 rounded-xl bg-accent-soft border border-accent-primary/30 flex items-center justify-center text-accent-primary shrink-0">
          <Loader2 className="w-6 h-6 animate-spin text-accent-primary" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
              <BrainCircuit className="w-4 h-4 text-accent-primary" />
              Django AI Research Engine Active
            </span>
            {ticker && (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-accent-soft text-accent-primary border border-accent-primary/30 font-semibold">
                {ticker} {market ? `(${market})` : ''}
              </span>
            )}
          </div>

          <p className="text-xs text-text-secondary mt-1 leading-relaxed">
            Dispatching query to LangGraph multi-agent synthesizer. Synthesizing financial filings, market valuation multiples, and news sentiment...
          </p>

          {query && (
            <div className="mt-2.5 px-3 py-1.5 rounded-lg bg-surface-secondary border border-border-subtle text-xs text-text-muted font-mono truncate">
              <span className="text-accent-primary font-semibold mr-1.5">Prompt:</span>
              &ldquo;{query}&rdquo;
            </div>
          )}

          <div className="mt-3 flex items-center gap-2 text-[11px] font-mono text-text-muted">
            <Server className="w-3.5 h-3.5 text-accent-primary" />
            <span>Server-side LangGraph execution in progress. Authenticated via JWT.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
