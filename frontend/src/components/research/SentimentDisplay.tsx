import React from 'react';
import { SentimentAnalysis } from '../../types/research';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { TrendingUp, TrendingDown, Minus, Smile, Frown, Meh, Gauge } from 'lucide-react';
import { formatPercent } from '../../utils/formatters';

interface SentimentDisplayProps {
  sentiment?: SentimentAnalysis;
  overallSentiment?: string;
  sentimentScore?: number;
  sentimentSummary?: string;
  ticker?: string;
  className?: string;
}

export const SentimentDisplay: React.FC<SentimentDisplayProps> = ({
  sentiment,
  overallSentiment,
  sentimentScore,
  sentimentSummary,
  ticker,
  className = '',
}) => {
  // Normalize label
  const label =
    overallSentiment ||
    sentiment?.label ||
    (sentimentScore !== undefined && sentimentScore > 0.15
      ? 'Bullish'
      : sentimentScore !== undefined && sentimentScore < -0.15
      ? 'Bearish'
      : 'Neutral');

  // Normalize score (-1.0 to +1.0 or 0 to 100)
  const rawScore = sentimentScore ?? sentiment?.score ?? 0;
  // If score is -1 to 1, convert to percentage -100% to +100%
  const normalizedScore = Math.abs(rawScore) <= 1 ? rawScore * 100 : rawScore;

  const isBullish =
    label?.toLowerCase().includes('bull') || label?.toLowerCase().includes('pos') || normalizedScore > 15;
  const isBearish =
    label?.toLowerCase().includes('bear') || label?.toLowerCase().includes('neg') || normalizedScore < -15;

  const badgeVariant = isBullish ? 'success' : isBearish ? 'danger' : 'neutral';
  const Icon = isBullish ? TrendingUp : isBearish ? TrendingDown : Minus;

  const breakdown = sentiment?.breakdown || {
    positive: isBullish ? 65 : isBearish ? 15 : 30,
    neutral: isBullish ? 25 : isBearish ? 25 : 50,
    negative: isBullish ? 10 : isBearish ? 60 : 20,
  };

  const summary = sentimentSummary || sentiment?.summary;

  return (
    <Card
      title={
        <div className="flex items-center gap-2">
          <Gauge className="w-4 h-4 text-cyan-400" />
          <span>Market & News Sentiment</span>
          {ticker && (
            <Badge variant="neutral" size="sm" className="font-mono text-[10px]">
              {ticker}
            </Badge>
          )}
        </div>
      }
      subtitle="Synthesized from regulatory announcements, press wires, and analyst coverage"
      className={className}
    >
      <div className="space-y-4">
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
                <Badge variant={badgeVariant} size="sm">
                  {normalizedScore > 0 ? `+${normalizedScore.toFixed(1)}%` : `${normalizedScore.toFixed(1)}%`}
                </Badge>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Sentiment Polarity Index (-100 to +100)
              </p>
            </div>
          </div>

          {/* Mini Polarity Meter Bar */}
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
        </div>

        {/* Sentiment Distribution Breakdown */}
        <div className="grid grid-cols-3 gap-2.5 text-center text-xs">
          <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/40">
            <div className="flex items-center justify-center gap-1 text-emerald-400 mb-1">
              <Smile className="w-3.5 h-3.5" />
              <span className="font-semibold">Positive</span>
            </div>
            <p className="font-mono text-sm font-bold text-emerald-300">
              {breakdown.positive ?? breakdown.bullish ?? 0}%
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
              <Meh className="w-3.5 h-3.5" />
              <span className="font-semibold">Neutral</span>
            </div>
            <p className="font-mono text-sm font-bold text-slate-300">
              {breakdown.neutral ?? 0}%
            </p>
          </div>

          <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-900/40">
            <div className="flex items-center justify-center gap-1 text-rose-400 mb-1">
              <Frown className="w-3.5 h-3.5" />
              <span className="font-semibold">Negative</span>
            </div>
            <p className="font-mono text-sm font-bold text-rose-300">
              {breakdown.negative ?? breakdown.bearish ?? 0}%
            </p>
          </div>
        </div>

        {/* Summary note if present */}
        {summary && (
          <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/50 p-3 rounded-lg border border-slate-800/60 font-sans">
            {summary}
          </p>
        )}
      </div>
    </Card>
  );
};
