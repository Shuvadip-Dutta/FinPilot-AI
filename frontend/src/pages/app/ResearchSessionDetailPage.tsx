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
import { PageHeader } from '../../components/layout/PageHeader';
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
  Sparkles,
  ExternalLink,
  PlusCircle,
  RefreshCw,
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

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchSessionDetail = async () => {
    if (!sessionId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await researchApi.getSession(sessionId);
      setSession(data);
      setMessages(data.messages || []);
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setError(apiErr.message || `Failed to load session #${sessionId}.`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessionDetail();
  }, [sessionId]);

  useEffect(() => {
    if (messages.length > 0 && activeView === 'conversation') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isSubmitting, activeView]);

  // Submit follow-up message in this session
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
          message={error || `Session #${sessionId} was not found.`}
          onRetry={fetchSessionDetail}
        />
      </div>
    );
  }

  const ticker = session.ticker || 'RELIANCE';
  const market = session.market || 'NSE';
  const allEvidence: EvidenceItem[] = [
    ...(session.evidence || []),
    ...messages.flatMap((m) => m.evidence || []),
  ];
  const allProvenance =
    session.provenance ||
    [...messages].reverse().find((m) => m.provenance)?.provenance;

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
              Session #{session.id}
            </span>
            {session.ticker && (
              <Badge variant="info" size="sm" className="font-mono">
                {session.ticker} {session.market ? `(${session.market})` : ''}
              </Badge>
            )}
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            {session.title || 'Research Session Detail'}
          </h1>
          <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              Created {formatDate(session.created_at, { includeTime: true })}
            </span>
            <span className="flex items-center gap-1">
              <MessageSquare className="w-3.5 h-3.5 text-cyan-400" />
              {messages.length} messages
            </span>
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
          <span>Conversation Stream ({messages.length})</span>
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
          <span>Evidence Sources ({allEvidence.length})</span>
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
        <EvidencePanel
          evidence={allEvidence}
          title={`All Citations in Session #${session.id}`}
        />
      )}

      {/* Provenance View */}
      {activeView === 'provenance' && (
        <ProvenancePanel provenance={allProvenance} />
      )}
    </div>
  );
};
