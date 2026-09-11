import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { researchApi } from '../../api/research';
import { ResearchSession } from '../../types/research';
import { PageHeader } from '../../components/layout/PageHeader';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { ErrorState } from '../../components/common/ErrorState';
import {
  History,
  Search,
  PlusCircle,
  Clock,
  MessageSquare,
  ArrowRight,
  RefreshCw,
  Layers,
  Sparkles,
  Calendar,
} from 'lucide-react';
import { formatDate } from '../../utils/formatters';

export const ResearchHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<ResearchSession[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [marketFilter, setMarketFilter] = useState<string>('ALL');

  const fetchSessions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await researchApi.getSessions();
      setSessions(data);
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setError(apiErr.message || 'Failed to fetch research sessions from Django backend.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const filteredSessions = sessions.filter((s) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      !searchTerm.trim() ||
      s.title?.toLowerCase().includes(term) ||
      s.query?.toLowerCase().includes(term) ||
      s.ticker?.toLowerCase().includes(term) ||
      s.summary?.toLowerCase().includes(term);

    const matchesMarket =
      marketFilter === 'ALL' ||
      s.market?.toUpperCase() === marketFilter.toUpperCase();

    return matchesSearch && matchesMarket;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Research History"
        subtitle="All archived multi-agent financial investigations, citations, and analytical threads"
        badge={
          <Badge variant="neutral" size="sm" dot>
            {sessions.length} {sessions.length === 1 ? 'Session' : 'Sessions'}
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              onClick={fetchSessions}
            >
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<PlusCircle className="w-4 h-4" />}
              onClick={() => navigate('/app/research')}
            >
              New Research
            </Button>
          </div>
        }
      />

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search sessions by ticker, title, or topic..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-950/80 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto text-xs font-mono">
          <span className="text-slate-500 text-[11px] shrink-0">Market:</span>
          {['ALL', 'NSE', 'BSE', 'NASDAQ', 'NYSE'].map((m) => (
            <button
              key={m}
              onClick={() => setMarketFilter(m)}
              className={`px-2.5 py-1 rounded-lg transition-colors cursor-pointer ${
                marketFilter === m
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-700 font-semibold'
                  : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <LoadingSkeleton height="h-36" />
          <LoadingSkeleton height="h-36" />
          <LoadingSkeleton height="h-36" />
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <ErrorState
          title="Could not load research sessions"
          message={error}
          onRetry={fetchSessions}
        />
      )}

      {/* Empty State */}
      {!isLoading && !error && filteredSessions.length === 0 && (
        <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800 text-center flex flex-col items-center">
          <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mb-3">
            <History className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-white">
            {searchTerm || marketFilter !== 'ALL'
              ? 'No matching research sessions'
              : 'No research sessions found'}
          </h3>
          <p className="text-xs text-slate-400 mt-1 max-w-sm">
            {searchTerm || marketFilter !== 'ALL'
              ? 'Try changing your search keywords or resetting the market filter.'
              : 'Start your first equity or macro investigation with the LangGraph research engine.'}
          </p>
          <div className="mt-4">
            <Button
              variant="primary"
              size="sm"
              leftIcon={<PlusCircle className="w-4 h-4" />}
              onClick={() => navigate('/app/research')}
            >
              Launch New Research
            </Button>
          </div>
        </div>
      )}

      {/* Sessions Grid */}
      {!isLoading && !error && filteredSessions.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSessions.map((session) => {
            const title = session.title || session.query || `Research Session #${session.id}`;
            const msgCount = session.message_count ?? (session.messages ? session.messages.length : undefined);

            return (
              <div
                key={session.id}
                onClick={() => navigate(`/app/research/${session.id}`)}
                className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/90 hover:border-cyan-500/50 hover:bg-slate-900 transition-all cursor-pointer group flex flex-col justify-between space-y-4 shadow-sm"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      {session.ticker && (
                        <Badge variant="info" size="sm" className="font-mono font-bold">
                          {session.ticker}
                        </Badge>
                      )}
                      {session.market && (
                        <Badge variant="neutral" size="sm" className="font-mono text-[10px]">
                          {session.market}
                        </Badge>
                      )}
                    </div>
                    <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(session.created_at, { format: 'relative' })}
                    </span>
                  </div>

                  <h3 className="font-semibold text-slate-100 text-sm group-hover:text-cyan-300 transition-colors line-clamp-2">
                    {title}
                  </h3>

                  {(session.summary || session.query) && (
                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {session.summary || session.query}
                    </p>
                  )}
                </div>

                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
                  <div className="flex items-center gap-3">
                    {msgCount !== undefined && (
                      <span className="flex items-center gap-1">
                        <MessageSquare className="w-3 h-3 text-cyan-400" />
                        {msgCount} {msgCount === 1 ? 'msg' : 'msgs'}
                      </span>
                    )}
                    <span className="text-slate-500">ID #{session.id}</span>
                  </div>

                  <span className="text-cyan-400 group-hover:translate-x-1 transition-transform flex items-center gap-1 text-[11px]">
                    <span>Open</span>
                    <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
