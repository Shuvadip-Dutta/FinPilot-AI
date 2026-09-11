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
    <div className="p-6 rounded-2xl bg-slate-900/60 border border-cyan-500/20 shadow-lg relative overflow-hidden">
      {/* Background ambient sweep */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/5 to-transparent animate-pulse pointer-events-none" />

      <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="w-12 h-12 rounded-xl bg-cyan-950/80 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
          <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-white flex items-center gap-1.5">
              <BrainCircuit className="w-4 h-4 text-cyan-400" />
              Django AI Research Engine Active
            </span>
            {ticker && (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/60">
                {ticker} {market ? `(${market})` : ''}
              </span>
            )}
          </div>

          <p className="text-xs text-slate-300 mt-1 leading-relaxed">
            Dispatching query to LangGraph multi-agent synthesizer. Synthesizing financial filings, market valuation multiples, and news sentiment...
          </p>

          {query && (
            <div className="mt-2.5 px-3 py-1.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs text-slate-400 font-mono truncate">
              <span className="text-cyan-400 font-semibold mr-1.5">Prompt:</span>
              &ldquo;{query}&rdquo;
            </div>
          )}

          <div className="mt-3 flex items-center gap-2 text-[11px] font-mono text-slate-400">
            <Server className="w-3.5 h-3.5 text-cyan-400/80" />
            <span>Server-side LangGraph execution in progress. Authenticated via JWT.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
