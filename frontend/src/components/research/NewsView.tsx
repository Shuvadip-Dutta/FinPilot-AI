import React, { useEffect, useState } from 'react';
import { NewsResponse, NewsArticle } from '../../types/research';
import { researchApi } from '../../api/research';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { LoadingSkeleton } from '../common/LoadingSkeleton';
import { ErrorState } from '../common/ErrorState';
import { SentimentDisplay } from './SentimentDisplay';
import {
  Newspaper,
  ExternalLink,
  Calendar,
  Layers,
  Search,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  Tag,
} from 'lucide-react';
import { formatDate } from '../../utils/formatters';

interface NewsViewProps {
  ticker: string;
  market?: string;
  className?: string;
}

export const NewsView: React.FC<NewsViewProps> = ({
  ticker,
  market = 'IN',
  className = '',
}) => {
  const normalizedMarket = (market || 'IN').trim().toUpperCase() === 'US' ? 'US' : 'IN';

  const [data, setData] = useState<NewsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filterText, setFilterText] = useState('');

  const fetchNews = async () => {
    if (!ticker) return;
    if (normalizedMarket === 'US') {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const res = await researchApi.getNews(ticker, normalizedMarket);
      setData(res);
    } catch (err: unknown) {
      const apiErr = err as {
        response?: {
          status?: number;
          data?: { error?: string; market?: string[] };
        };
        message?: string;
      };
      const status = apiErr.response?.status;
      const errorMsg =
        apiErr.response?.data?.error ||
        (Array.isArray(apiErr.response?.data?.market)
          ? apiErr.response?.data?.market.join(' ')
          : null) ||
        apiErr.message ||
        `Failed to fetch news & sentiment for ${ticker}.`;

      if (status === 400 && errorMsg.includes('choice')) {
        setError('MARKET_CONSTRAINT');
      } else if (status === 429) {
        setError('Request rate limit reached. Please wait a few seconds before refreshing.');
      } else if (status === 502) {
        setError('Upstream news providers are temporarily unavailable. Please try again.');
      } else {
        setError(errorMsg);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let isSubscribed = true;

    // Immediately clear stale state when ticker or market changes
    setData(null);
    setError(null);
    setFilterText('');

    if (!ticker) {
      setIsLoading(false);
      return;
    }

    if (normalizedMarket === 'US') {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);

    const loadData = async () => {
      try {
        const res = await researchApi.getNews(ticker, normalizedMarket);
        if (isSubscribed) {
          setData(res);
        }
      } catch (err: unknown) {
        if (isSubscribed) {
          const apiErr = err as {
            response?: {
              status?: number;
              data?: { error?: string; market?: string[] };
            };
            message?: string;
          };
          const status = apiErr.response?.status;
          const errorMsg =
            apiErr.response?.data?.error ||
            (Array.isArray(apiErr.response?.data?.market)
              ? apiErr.response?.data?.market.join(' ')
              : null) ||
            apiErr.message ||
            `Failed to fetch news & sentiment for ${ticker}.`;

          if (status === 400 && errorMsg.includes('choice')) {
            setError('MARKET_CONSTRAINT');
          } else if (status === 429) {
            setError('Request rate limit reached. Please wait a few seconds before refreshing.');
          } else if (status === 502) {
            setError('Upstream news providers are temporarily unavailable. Please try again.');
          } else {
            setError(errorMsg);
          }
        }
      } finally {
        if (isSubscribed) {
          setIsLoading(false);
        }
      }
    };

    loadData();

    return () => {
      isSubscribed = false;
    };
  }, [ticker, normalizedMarket]);

  // Market constraint banner for US equities
  if (normalizedMarket === 'US') {
    return (
      <Card title={`News & Sentiment: ${ticker} (US)`} className={className}>
        <div className="p-5 rounded-xl bg-amber-950/20 border border-amber-800/40 text-amber-200 text-xs flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-semibold text-amber-300 text-sm">Market Constraint: India Only</h4>
            <p className="text-amber-200/80 leading-relaxed">
              Django news aggregation and entity sentiment analysis are currently supported for Indian equities (<code className="font-mono text-amber-300">market="IN"</code>). Aggregation for US equities will be enabled in a future release.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card title={`News & Sentiment: ${ticker}`} className={className}>
        <div className="space-y-4">
          <LoadingSkeleton height="h-28" />
          <LoadingSkeleton height="h-24" />
          <LoadingSkeleton height="h-24" />
          <LoadingSkeleton height="h-24" />
        </div>
      </Card>
    );
  }

  if (error === 'MARKET_CONSTRAINT') {
    return (
      <Card title={`News & Sentiment: ${ticker}`} className={className}>
        <div className="p-5 rounded-xl bg-amber-950/20 border border-amber-800/40 text-amber-200 text-xs flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-semibold text-amber-300 text-sm">Market Constraint</h4>
            <p className="text-amber-200/80 leading-relaxed">
              News and sentiment are currently supported for Indian equities (<code className="font-mono text-amber-300">market="IN"</code>).
            </p>
          </div>
        </div>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card title={`News & Sentiment: ${ticker}`} className={className}>
        <ErrorState
          title="Unable to load news feed"
          message={error || `No news articles available for ${ticker}.`}
          onRetry={fetchNews}
        />
      </Card>
    );
  }

  const rawArticles: NewsArticle[] =
    data.articles || data.news || (Array.isArray(data) ? (data as unknown as NewsArticle[]) : []);

  // Derive target entity sentiment across articles
  const tickerUpper = ticker.toUpperCase();
  let totalScore = 0;
  let scoredCount = 0;
  let positiveCount = 0;
  let neutralCount = 0;
  let negativeCount = 0;

  const articles = rawArticles.map((art) => {
    // Find matching entity for the target ticker
    const matchedEntity = art.entities?.find(
      (e) =>
        e.symbol?.toUpperCase() === tickerUpper ||
        e.symbol?.toUpperCase() === `${tickerUpper}.NS` ||
        e.symbol?.toUpperCase() === `${tickerUpper}.BO` ||
        (e.name && e.name.toLowerCase().includes(tickerUpper.toLowerCase()))
    );

    // Fall back to first entity with a sentiment score if no exact symbol match
    const entityWithScore =
      matchedEntity?.sentiment_score != null
        ? matchedEntity
        : art.entities?.find((e) => e.sentiment_score != null);

    const entityScore = entityWithScore?.sentiment_score ?? null;

    if (entityScore !== null) {
      scoredCount++;
      totalScore += entityScore;
      if (entityScore > 0.15) positiveCount++;
      else if (entityScore < -0.15) negativeCount++;
      else neutralCount++;
    }

    return {
      ...art,
      targetEntityScore: entityScore,
    };
  });

  const averageScore = scoredCount > 0 ? totalScore / scoredCount : null;
  const sentimentCounts =
    scoredCount > 0
      ? {
          positive: positiveCount,
          neutral: neutralCount,
          negative: negativeCount,
          total: scoredCount,
        }
      : null;

  const filteredArticles = articles.filter((art) => {
    if (!filterText.trim()) return true;
    const q = filterText.toLowerCase();
    return (
      art.title?.toLowerCase().includes(q) ||
      art.summary?.toLowerCase().includes(q) ||
      art.source?.toLowerCase().includes(q)
    );
  });

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Sentiment Overview Gauge Panel */}
      <SentimentDisplay
        ticker={ticker}
        averageScore={averageScore}
        counts={sentimentCounts}
        totalArticles={articles.length}
        scoredArticlesCount={scoredCount}
        overallSentiment={data.overall_sentiment}
        sentimentSummary={data.sentiment_summary}
      />

      {/* Verified News Articles Card */}
      <Card
        title={
          <div className="flex items-center justify-between gap-3 w-full">
            <div className="flex items-center gap-2">
              <Newspaper className="w-4 h-4 text-cyan-400" />
              <span>Verified Market News & Catalysts</span>
              <Badge variant="neutral" size="sm" className="font-mono">
                {articles.length} {articles.length === 1 ? 'article' : 'articles'}
              </Badge>
            </div>

            <button
              onClick={fetchNews}
              className="p-1 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
              title="Refresh news feed"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        }
        subtitle="Recent regulatory announcements, earnings reports, and financial press aggregated from multiple wires"
      >
        {/* Search filter if multiple articles */}
        {articles.length > 2 && (
          <div className="mb-4 relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search news by headline or keyword..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
            />
          </div>
        )}

        {articles.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs flex flex-col items-center">
            <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mb-2">
              <Newspaper className="w-5 h-5" />
            </div>
            <p className="font-medium text-slate-300">No news articles found</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              News feeds and regulatory wires will appear here once ingested for {ticker}.
            </p>
          </div>
        ) : filteredArticles.length === 0 ? (
          <div className="py-6 text-center text-slate-400 text-xs">
            No news matches &ldquo;{filterText}&rdquo;
          </div>
        ) : (
          <div className="space-y-3 max-h-[650px] overflow-y-auto pr-1">
            {filteredArticles.map((article, idx) => {
              const pubDate = article.published_at || article.published_date || article.datetime;
              const entityScore = article.targetEntityScore;
              const hasScore = entityScore !== null;
              const isBull = hasScore && entityScore > 0.15;
              const isBear = hasScore && entityScore < -0.15;
              const sentimentVariant = isBull ? 'success' : isBear ? 'danger' : 'neutral';
              const sentimentLabel = isBull ? 'Bullish' : isBear ? 'Bearish' : 'Neutral';

              return (
                <div
                  key={article.id ?? `news-${idx}`}
                  className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 transition-all space-y-2 text-xs"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        {article.relevance_type && (
                          <Badge variant="neutral" size="sm" className="font-mono text-[9px] uppercase tracking-wider text-slate-400 border-slate-800">
                            <Tag className="w-2.5 h-2.5 mr-1 text-cyan-400" />
                            {article.relevance_type}
                          </Badge>
                        )}
                        {article.target_match_score !== null && article.target_match_score !== undefined && (
                          <span className="text-[10px] text-slate-500 font-mono">
                            Match: {article.target_match_score.toFixed(0)}%
                          </span>
                        )}
                      </div>

                      <h4 className="font-semibold text-slate-100 text-sm leading-snug hover:text-cyan-300 transition-colors">
                        {article.url ? (
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5"
                          >
                            <span>{article.title}</span>
                            <ExternalLink className="w-3 h-3 text-cyan-400 shrink-0 inline" />
                          </a>
                        ) : (
                          article.title
                        )}
                      </h4>
                    </div>

                    {hasScore && (
                      <Badge variant={sentimentVariant} size="sm" className="font-mono text-[10px] shrink-0">
                        {isBull ? (
                          <TrendingUp className="w-2.5 h-2.5 mr-1 inline" />
                        ) : isBear ? (
                          <TrendingDown className="w-2.5 h-2.5 mr-1 inline" />
                        ) : (
                          <Minus className="w-2.5 h-2.5 mr-1 inline" />
                        )}
                        {entityScore > 0 ? `+${entityScore.toFixed(2)}` : entityScore.toFixed(2)} {sentimentLabel}
                      </Badge>
                    )}
                  </div>

                  {(article.summary || article.description || article.content) && (
                    <p className="text-slate-400 text-xs leading-relaxed line-clamp-3">
                      {article.summary || article.description || article.content}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono pt-2 border-t border-slate-900">
                    <span className="flex items-center gap-1.5 text-slate-400">
                      <Layers className="w-3 h-3 text-cyan-400/80" />
                      {article.source || 'Financial Wire'}
                    </span>

                    {pubDate && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(pubDate, { includeTime: true })}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
};
