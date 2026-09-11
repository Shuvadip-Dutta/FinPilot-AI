import React from 'react';
import { SentimentAnalysis } from '../../types/research';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { TrendingUp, TrendingDown, Minus, Smile, Frown, Meh, Gauge, Info } from 'lucide-react';

export interface SentimentCounts {
  positive: number;
  neutral: number;
  negative: number;
  total: number;
}

interface SentimentDisplayProps {
  sentiment?: SentimentAnalysis;
  overallSentiment?: string;
  sentimentScore?: number;
  sentimentSummary?: string;
  ticker?: string;
  averageScore?: number | null;
  counts?: SentimentCounts | null;
  totalArticles?: number;
  scoredArticlesCount?: number;
  className?: string;
}

export const SentimentDisplay: React.FC<SentimentDisplayProps> = ({
  ticker,
  averageScore,
  counts,
  totalArticles = 0,
  scoredArticlesCount = 0,
  sentiment,
  overallSentiment,
  sentimentScore,
  sentimentSummary,
  className = '',
}) => {
  // Resolve numeric score (-1.0 to +1.0)
  const resolvedScore =
    averageScore !== undefined
      ? averageScore
      : sentimentScore !== undefined
      ? sentimentScore
      : sentiment?.score ?? null;

  // Normalized score (-100 to +100)
  const normalizedScore =
    resolvedScore !== null
      ? Math.abs(resolvedScore) <= 1
        ? resolvedScore * 100
        : resolvedScore
      : null;

  // Determine sentiment label
  const label =
    overallSentiment ||
    sentiment?.label ||
    (resolvedScore !== null
      ? resolvedScore > 0.15
        ? 'Bullish'
        : resolvedScore < -0.15
        ? 'Bearish'
        : 'Neutral'
      : null);

  const isBullish = label?.toLowerCase().includes('bull') || label?.toLowerCase().includes('pos') || (normalizedScore !== null && normalizedScore > 15);
  const isBearish = label?.toLowerCase().includes('bear') || label?.toLowerCase().includes('neg') || (normalizedScore !== null && normalizedScore < -15);

  const badgeVariant = isBullish ? 'success' : isBearish ? 'danger' : 'neutral';
  const Icon = isBullish ? TrendingUp : isBearish ? TrendingDown : Minus;

  const hasScoredData = (scoredArticlesCount > 0 && resolvedScore !== null) || (counts && counts.total > 0);

  return (
    <Card
      title={
        <div className="flex items-center gap-2">
          <Gauge className="w-4 h-4 text-cyan-400" />
          <span>Entity & Provider Sentiment</span>
          {ticker && (
            <Badge variant="neutral" size="sm" className="font-mono text-[10px]">
              {ticker}
            </Badge>
          )}
        </div>
      }
      subtitle="Derived from entity-level financial NLP scores across verified market news"
      className={className}
    >
      <div className="space-y-4">
        {hasScoredData ? (
          <>
            {/* Main Sentiment Card */}
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 border ${
                    isBullish
                      ? 'bg-emerald-950/60 border-emerald-800/60 text-emerald-400'
                      : isBearish
                      ? 'bg-rose-950/60 border-rose-800/60 text-rose-400'
                      : 'bg-slate-900 border-slate-700 text-slate-300'
                  }`}
                >
                  <Icon className="w-6 h-6 stroke-[2.5]" />
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-white tracking-tight">
                      {label}
                    </span>
                    {normalizedScore !== null && (
                      <Badge variant={badgeVariant} size="sm">
                        {normalizedScore > 0
                          ? `+${normalizedScore.toFixed(1)}%`
                          : `${normalizedScore.toFixed(1)}%`}
                      </Badge>
                    )}
                    <span className="text-[10px] text-slate-500 font-mono">
                      (Entity Average)
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Polarity Index (-100 to +100) based on {scoredArticlesCount} scored {scoredArticlesCount === 1 ? 'article' : 'articles'}
                  </p>
                </div>
              </div>

              {/* Mini Polarity Meter Bar */}
              {normalizedScore !== null && (
                <div className="w-full sm:w-48 space-y-1.5">
                  <div className="flex justify-between text-[11px] font-mono text-slate-400">
                    <span className="text-rose-400">Bearish</span>
                    <span className="text-slate-500">Neutral</span>
                    <span className="text-emerald-400">Bullish</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden relative">
                    <div
                      className={`h-full transition-all duration-500 ${
                        isBullish
                          ? 'bg-gradient-to-r from-emerald-500 to-cyan-400'
                          : isBearish
                          ? 'bg-gradient-to-r from-rose-600 to-amber-500'
                          : 'bg-slate-500'
                      }`}
                      style={{
                        width: `${Math.min(Math.max((normalizedScore + 100) / 2, 5), 100)}%`,
                      }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Sentiment Distribution Breakdown */}
            {counts && counts.total > 0 && (
              <div className="grid grid-cols-3 gap-2.5 text-center text-xs">
                <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/40">
                  <div className="flex items-center justify-center gap-1 text-emerald-400 mb-1">
                    <Smile className="w-3.5 h-3.5" />
                    <span className="font-semibold">Positive</span>
                  </div>
                  <p className="font-mono text-sm font-bold text-emerald-300">
                    {counts.positive}{' '}
                    <span className="text-[11px] font-normal text-emerald-500">
                      ({Math.round((counts.positive / counts.total) * 100)}%)
                    </span>
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                  <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
                    <Meh className="w-3.5 h-3.5" />
                    <span className="font-semibold">Neutral</span>
                  </div>
                  <p className="font-mono text-sm font-bold text-slate-300">
                    {counts.neutral}{' '}
                    <span className="text-[11px] font-normal text-slate-500">
                      ({Math.round((counts.neutral / counts.total) * 100)}%)
                    </span>
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-900/40">
                  <div className="flex items-center justify-center gap-1 text-rose-400 mb-1">
                    <Frown className="w-3.5 h-3.5" />
                    <span className="font-semibold">Negative</span>
                  </div>
                  <p className="font-mono text-sm font-bold text-rose-300">
                    {counts.negative}{' '}
                    <span className="text-[11px] font-normal text-rose-500">
                      ({Math.round((counts.negative / counts.total) * 100)}%)
                    </span>
                  </p>
                </div>
              </div>
            )}

            {/* Provenance note */}
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-slate-950/40 border border-slate-900 text-[11px] text-slate-400">
              <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
              <span>
                Frontend summary aggregated from {scoredArticlesCount} of {totalArticles} articles with entity-level NLP sentiment from Marketaux. Wire articles without entity scores (Upstox, Livemint) are excluded from the score index.
              </span>
            </div>
          </>
        ) : (
          <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/60 flex items-center gap-3 text-slate-400 text-xs">
            <Info className="w-4 h-4 text-slate-500 shrink-0" />
            <span>
              Entity sentiment scores are not available for current wire articles. Upstox and Livemint feeds do not provide entity NLP sentiment scores.
            </span>
          </div>
        )}

        {/* Summary note if present */}
        {sentimentSummary && (
          <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/50 p-3 rounded-lg border border-slate-800/60 font-sans">
            {sentimentSummary}
          </p>
        )}
      </div>
    </Card>
  );
};
