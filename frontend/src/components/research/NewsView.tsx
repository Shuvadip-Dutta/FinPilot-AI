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
} from 'lucide-react';
import { formatDate } from '../../utils/formatters';

interface NewsViewProps {
  ticker: string;
  market?: string;
  className?: string;
}

export const NewsView: React.FC<NewsViewProps> = ({
  ticker,
  market = 'NSE',
  className = '',
}) => {
  const [data, setData] = useState<NewsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filterText, setFilterText] = useState('');

  const fetchNews = async () => {
    if (!ticker) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await researchApi.getNews(ticker, market);
      setData(res);
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setError(apiErr.message || `Failed to fetch news & sentiment for ${ticker}.`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNews();
  }, [ticker, market]);

  if (isLoading) {
    return (
      <Card title={`News & Sentiment: ${ticker}`} className={className}>
        <div className="space-y-4">
          <LoadingSkeleton height="h-28" />
          <LoadingSkeleton height="h-20" />
          <LoadingSkeleton height="h-20" />
          <LoadingSkeleton height="h-20" />
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

  const articles: NewsArticle[] =
    data.articles || data.news || (Array.isArray(data) ? (data as any) : []);

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
        sentiment={data.sentiment}
        overallSentiment={data.overall_sentiment}
        sentimentScore={data.sentiment_score}
        sentimentSummary={data.sentiment_summary}
        ticker={ticker}
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
        subtitle="Recent regulatory announcements, earnings reports, and financial press"
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
              News feeds and regulatory wires will appear here once ingested.
            </p>
          </div>
        ) : filteredArticles.length === 0 ? (
          <div className="py-6 text-center text-slate-400 text-xs">
            No news matches &ldquo;{filterText}&rdquo;
          </div>
        ) : (
          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
            {filteredArticles.map((article, idx) => {
              const pubDate = article.published_at || article.published_date || article.datetime;
              const sentimentStr = article.sentiment;
              const isBull =
                sentimentStr?.toLowerCase().includes('bull') || sentimentStr?.toLowerCase().includes('pos');
              const isBear =
                sentimentStr?.toLowerCase().includes('bear') || sentimentStr?.toLowerCase().includes('neg');
              const sentimentVariant = isBull ? 'success' : isBear ? 'danger' : 'neutral';

              return (
                <div
                  key={article.id ?? `news-${idx}`}
                  className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 transition-all space-y-2 text-xs"
                >
                  <div className="flex items-start justify-between gap-3">
                    <h4 className="font-semibold text-slate-100 text-sm leading-snug hover:text-cyan-300 transition-colors">
                      {article.url ? (
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5"
                        >
                          <span>{article.title}</span>
                          <ExternalLink className="w-3 h-3 text-cyan-400 shrink-0 inline" />
                        </a>
                      ) : (
                        article.title
                      )}
                    </h4>

                    {sentimentStr && (
                      <Badge variant={sentimentVariant} size="sm" className="font-mono text-[10px] shrink-0">
                        {isBull ? (
                          <TrendingUp className="w-2.5 h-2.5 mr-1 inline" />
                        ) : isBear ? (
                          <TrendingDown className="w-2.5 h-2.5 mr-1 inline" />
                        ) : (
                          <Minus className="w-2.5 h-2.5 mr-1 inline" />
                        )}
                        {sentimentStr}
                      </Badge>
                    )}
                  </div>

                  {(article.summary || article.description || article.content) && (
                    <p className="text-slate-400 text-xs leading-relaxed line-clamp-3">
                      {article.summary || article.description || article.content}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono pt-2 border-t border-slate-900">
                    <span className="flex items-center gap-1 text-slate-400">
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
