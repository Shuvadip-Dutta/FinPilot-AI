import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { researchApi } from '../../api/research';
import {
  ResearchSessionDetail,
  ChatMessage,
  ChatResponse,
  EvidenceItem,
  ProvenanceData,
} from '../../types/research';
import { AiResponseView } from '../../components/research/AiResponseView';
import { ResearchComposer } from '../../components/research/ResearchComposer';
import { ResearchLoadingState } from '../../components/research/ResearchLoadingState';
import { EvidencePanel } from '../../components/research/EvidencePanel';
import { ProvenancePanel } from '../../components/research/ProvenancePanel';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { ErrorState } from '../../components/common/ErrorState';
import {
  ArrowLeft,
  BookOpen,
  GitCommit,
  Clock,
  MessageSquare,
  PlusCircle,
  RefreshCw,
  Activity,
  Cpu,
  Wrench,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { formatDate } from '../../utils/formatters';

export const ResearchSessionDetailPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<ResearchSessionDetail | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [currentPrompt, setCurrentPrompt] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'conversation' | 'evidence' | 'provenance'>('conversation');
  const [expandedAgentData, setExpandedAgentData] = useState<Record<number, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Stale-data & race-condition protected fetch
  const fetchSessionDetail = () => {
    if (!sessionId) return;
    let isCurrent = true;
    setSession(null);
    setMessages([]);
    setIsLoading(true);
    setError(null);

    researchApi
      .getSession(sessionId)
      .then((data) => {
        if (isCurrent) {
          setSession(data);
          setMessages(data.messages || []);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isCurrent) {
          const apiErr = err as { message?: string };
          setError(
            apiErr.message ||
              `Session #${sessionId} was not found or you do not have permission to view it.`
          );
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  };

  useEffect(() => {
    const cancel = fetchSessionDetail();
    return () => {
      if (cancel) cancel();
    };
  }, [sessionId]);

  useEffect(() => {
    if (messages.length > 0 && activeView === 'conversation') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isSubmitting, activeView]);

  const handleFollowupSubmit = async (prompt: string, ticker: string, market: string) => {
    if (!sessionId) return;
    setIsSubmitting(true);
    setCurrentPrompt(prompt);

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
      ticker,
      market,
    };

    setMessages((prev) => [...prev, userMsg]);

    try {
      setSubmitError(null);
      const response: ChatResponse = await researchApi.chat({
        message: prompt,
        session_id: sessionId,
        ticker,
        market,
      });

      const aiContent =
        response.message || response.content || response.response || 'Synthesis updated.';
      const evidence: EvidenceItem[] = response.evidence || response.sources || [];
      const provenance: ProvenanceData | undefined =
        response.provenance ||
        (Array.isArray(response.agent_trace)
          ? { steps: response.agent_trace as any }
          : (response.agent_trace as ProvenanceData));

      const aiMsg: ChatMessage = {
        id: response.id || `assistant-${Date.now()}`,
        role: 'assistant',
        content: aiContent,
        timestamp: response.created_at || response.timestamp || new Date().toISOString(),
        ticker: response.ticker || ticker,
        market: response.market || market,
        evidence,
        provenance,
        sentiment: response.sentiment,
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setSubmitError(apiErr.message || 'Failed to submit follow-up query.');
    } finally {
      setIsSubmitting(false);
      setCurrentPrompt('');
    }
  };

  const toggleExpandAgent = (id: number) => {
    setExpandedAgentData((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton height="h-20" />
        <div className="space-y-4">
          <LoadingSkeleton height="h-32" />
          <LoadingSkeleton height="h-44" />
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="space-y-6">
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft className="w-4 h-4" />}
          onClick={() => navigate('/app/research/history')}
        >
          Back to Sessions
        </Button>
        <ErrorState
          title="Unable to load research session"
          message={error || `Session #${sessionId} was not found or is inaccessible.`}
          onRetry={fetchSessionDetail}
        />
      </div>
    );
  }

  const ticker = session.ticker || '';
  const market = session.market || '';
  const shortId = session.id.length > 8 ? session.id.slice(0, 8) : session.id;
  const allEvidence: EvidenceItem[] = [
    ...(session.evidence || []),
    ...messages.flatMap((m) => m.evidence || []),
  ];
  const allProvenance =
    session.provenance ||
    [...messages].reverse().find((m) => m.provenance)?.provenance;

  const getStatusBadge = (status?: string) => {
    const s = (status || 'COMPLETED').toUpperCase();
    if (s === 'COMPLETED') {
      return (
        <Badge variant="success" size="sm" className="font-mono text-[10px]">
          COMPLETED
        </Badge>
      );
    }
    if (s === 'FAILED') {
      return (
        <Badge variant="danger" size="sm" className="font-mono text-[10px]">
          FAILED
        </Badge>
      );
    }
    return (
      <Badge variant="info" size="sm" className="font-mono text-[10px]">
        {s}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}
              onClick={() => navigate('/app/research/history')}
              className="text-slate-400 hover:text-white px-2 py-1 h-auto"
            >
              History
            </Button>
            <span className="text-slate-600">/</span>
            <span className="font-mono text-cyan-400 text-xs font-semibold">
              Session #{shortId}
            </span>
            {ticker && (
              <Badge variant="info" size="sm" className="font-mono">
                {ticker} {market ? `(${market})` : ''}
              </Badge>
            )}
            {getStatusBadge(session.status)}
            {session.route && (
              <span className="text-[10px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                Route: {session.route}
              </span>
            )}
          </div>

          <h1 className="text-xl font-bold text-white tracking-tight">
            {session.user_message || session.title || 'Research Session Detail'}
          </h1>

          <div className="flex items-center gap-4 text-xs text-slate-400 font-mono flex-wrap">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              Created {formatDate(session.created_at, { includeTime: true })}
            </span>
            {session.latency_ms && (
              <span className="flex items-center gap-1 text-slate-400">
                <Activity className="w-3.5 h-3.5 text-cyan-400" />
                Latency: {session.latency_ms > 1000 ? `${(session.latency_ms / 1000).toFixed(2)}s` : `${Math.round(session.latency_ms)}ms`}
              </span>
            )}
            {session.evidence_items && (
              <span className="flex items-center gap-1 text-slate-400">
                <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                {session.evidence_items.length} specialist {session.evidence_items.length === 1 ? 'agent' : 'agents'}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            onClick={fetchSessionDetail}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            leftIcon={<PlusCircle className="w-4 h-4" />}
            onClick={() => navigate('/app/research')}
          >
            New Session
          </Button>
        </div>
      </div>

      {/* View Switcher Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 text-xs font-mono">
        <button
          onClick={() => setActiveView('conversation')}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
            activeView === 'conversation'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-700 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>Investigation & Synthesis ({messages.length})</span>
        </button>

        <button
          onClick={() => setActiveView('evidence')}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
            activeView === 'evidence'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-700 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Specialist Evidence ({session.evidence_items?.length || allEvidence.length})</span>
        </button>

        <button
          onClick={() => setActiveView('provenance')}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
            activeView === 'provenance'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-700 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <GitCommit className="w-3.5 h-3.5" />
          <span>Execution Provenance</span>
        </button>
      </div>

      {/* Main Content Area */}
      {activeView === 'conversation' && (
        <div className="space-y-6">
          {/* Message Stream */}
          <div className="space-y-4">
            {messages.map((msg) => (
              <AiResponseView key={msg.id} message={msg} />
            ))}
          </div>

          {/* Follow-up Loading state */}
          {isSubmitting && (
            <ResearchLoadingState query={currentPrompt} ticker={ticker} market={market} />
          )}

          <div ref={messagesEndRef} />

          {submitError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg flex items-center justify-between">
              <span>{submitError}</span>
              <button
                onClick={() => setSubmitError(null)}
                className="text-rose-400 hover:text-rose-300 font-semibold ml-3"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Follow-up Composer */}
          <div className="pt-2">
            <ResearchComposer
              onSubmit={handleFollowupSubmit}
              isLoading={isSubmitting}
              initialTicker={ticker}
              initialMarket={market}
              placeholder="Ask a follow-up question in this research thread..."
            />
          </div>
        </div>
      )}

      {/* Evidence View */}
      {activeView === 'evidence' && (
        <div className="space-y-6">
          {session.evidence_items && session.evidence_items.length > 0 ? (
            <Card
              title={
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-cyan-400" />
                  <span>Specialist Agent Evidence ({session.evidence_items.length})</span>
                </div>
              }
              subtitle="Detailed analytical outputs and tools used by each specialist agent in this session"
            >
              <div className="space-y-4">
                {session.evidence_items.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 text-xs space-y-3"
                  >
                    <div className="flex items-center justify-between gap-2 flex-wrap pb-2 border-b border-slate-800/80">
                      <div className="flex items-center gap-2">
                        <Badge variant="info" size="sm" className="font-mono uppercase">
                          {item.agent_name}
                        </Badge>
                        {item.tools_used && item.tools_used.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap">
                            <span className="text-slate-500 text-[11px]">Tools:</span>
                            {item.tools_used.map((t) => (
                              <span
                                key={t}
                                className="font-mono text-[10px] bg-slate-900 border border-slate-800 text-cyan-400 px-1.5 py-0.5 rounded"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <span className="text-[10px] font-mono text-slate-500">
                        {formatDate(item.created_at, { includeTime: true })}
                      </span>
                    </div>

                    {item.response && (
                      <div className="text-slate-300 leading-relaxed whitespace-pre-line font-sans text-xs">
                        {item.response}
                      </div>
                    )}

                    {item.structured_data && Object.keys(item.structured_data).length > 0 && (
                      <div className="pt-2">
                        <button
                          onClick={() => toggleExpandAgent(item.id)}
                          className="flex items-center gap-1.5 text-[11px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer"
                        >
                          <Wrench className="w-3 h-3" />
                          <span>
                            {expandedAgentData[item.id] ? 'Hide Structured Data' : 'View Structured Data JSON'}
                          </span>
                          {expandedAgentData[item.id] ? (
                            <ChevronUp className="w-3 h-3" />
                          ) : (
                            <ChevronDown className="w-3 h-3" />
                          )}
                        </button>

                        {expandedAgentData[item.id] && (
                          <pre className="mt-2 p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-72">
                            {JSON.stringify(item.structured_data, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            <EvidencePanel
              evidence={allEvidence}
              title={`All Citations in Session #${shortId}`}
            />
          )}
        </div>
      )}

      {/* Provenance View */}
      {activeView === 'provenance' && (
        <div className="space-y-4">
          <ProvenancePanel provenance={allProvenance} />
          <Card
            title={
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-indigo-400" />
                <span>Session Thread Metadata</span>
              </div>
            }
            subtitle="Underlying database persistence identifiers"
          >
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block text-[10px] uppercase">Session ID</span>
                <span className="text-slate-200 break-all">{session.id}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block text-[10px] uppercase">Thread ID</span>
                <span className="text-cyan-400 break-all">{session.thread_id || '—'}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block text-[10px] uppercase">Route</span>
                <span className="text-indigo-400">{session.route || 'general'}</span>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
