import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { researchApi } from '../../api/research';
import {
  ChatMessage,
  ChatResponse,
  EvidenceItem,
  ProvenanceData,
  ResearchSession,
} from '../../types/research';
import { PageHeader } from '../../components/layout/PageHeader';
import { ResearchComposer } from '../../components/research/ResearchComposer';
import { AiResponseView } from '../../components/research/AiResponseView';
import { ResearchLoadingState } from '../../components/research/ResearchLoadingState';
import { CompanyResearchView } from '../../components/research/CompanyResearchView';
import { FinancialDataView } from '../../components/research/FinancialDataView';
import { MarketDataView } from '../../components/research/MarketDataView';
import { NewsView } from '../../components/research/NewsView';
import { EvidencePanel } from '../../components/research/EvidencePanel';
import { ProvenancePanel } from '../../components/research/ProvenancePanel';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import {
  BrainCircuit,
  Building2,
  FileSpreadsheet,
  TrendingUp,
  Newspaper,
  History,
  BookOpen,
  GitCommit,
  PlusCircle,
  AlertCircle,
  RefreshCw,
  Search,
  ExternalLink,
} from 'lucide-react';
import { formatDate } from '../../utils/formatters';

type ResearchTab = 'synthesis' | 'company' | 'financials' | 'market' | 'news' | 'evidence' | 'provenance';

export const ResearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Active target asset
  const [ticker, setTicker] = useState<string>(searchParams.get('ticker') || 'RELIANCE');
  const [market, setMarket] = useState<string>(searchParams.get('market') || 'IN');

  // Active view tab
  const [activeTab, setActiveTab] = useState<ResearchTab>(
    (searchParams.get('tab') as ResearchTab) || 'synthesis'
  );

  // Chat conversation state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | number | undefined>(undefined);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [currentPrompt, setCurrentPrompt] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  // Quick research history sidebar/list
  const [recentSessions, setRecentSessions] = useState<ResearchSession[]>([]);
  const [loadingSessions, setLoadingSessions] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync state to URL params cleanly
  useEffect(() => {
    const params = new URLSearchParams();
    if (ticker) params.set('ticker', ticker);
    if (market) params.set('market', market);
    if (activeTab !== 'synthesis') params.set('tab', activeTab);
    setSearchParams(params, { replace: true });
  }, [ticker, market, activeTab, setSearchParams]);

  // Load recent research sessions for quick access
  const fetchRecentSessions = async () => {
    setLoadingSessions(true);
    try {
      const sessions = await researchApi.getSessions({ limit: 5 });
      setRecentSessions(sessions.slice(0, 5));
    } catch (err) {
      console.warn('Unable to load recent sessions:', err);
    } finally {
      setLoadingSessions(false);
    }
  };

  useEffect(() => {
    fetchRecentSessions();
  }, []);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (messages.length > 0 && activeTab === 'synthesis') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading, activeTab]);

  // Submit research query to POST /api/v1/ai/chat/
  const handleQuerySubmit = async (prompt: string, queryTicker: string, queryMarket: string) => {
    setError(null);
    setIsLoading(true);
    setCurrentPrompt(prompt);

    if (queryTicker !== ticker) setTicker(queryTicker);
    if (queryMarket !== market) setMarket(queryMarket);

    // Append user query to conversation
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
      ticker: queryTicker,
      market: queryMarket,
    };

    setMessages((prev) => [...prev, userMsg]);

    try {
      const response: ChatResponse = await researchApi.chat({
        message: prompt,
        session_id: sessionId,
        ticker: queryTicker,
        market: queryMarket,
      });

      // Update active session ID if returned
      if (response.session_id) {
        setSessionId(response.session_id);
      }

      // Format AI assistant message
      const aiContent =
        response.message ||
        response.content ||
        response.response ||
        'Research synthesis completed.';

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
        ticker: response.ticker || queryTicker,
        market: response.market || queryMarket,
        evidence,
        provenance,
        sentiment: response.sentiment,
      };

      setMessages((prev) => [...prev, aiMsg]);
      // Refresh session list in background
      fetchRecentSessions();
    } catch (err: unknown) {
      const apiErr = err as { message?: string; detail?: string; status?: number };
      const errorMessage =
        apiErr.message ||
        apiErr.detail ||
        'Failed to connect to Django AI Research engine. Please verify the backend is running.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
      setCurrentPrompt('');
    }
  };

  const handleStartNewSession = () => {
    setMessages([]);
    setSessionId(undefined);
    setError(null);
    setActiveTab('synthesis');
  };

  // Collect all accumulated evidence across current session
  const accumulatedEvidence: EvidenceItem[] = messages.flatMap((m) => m.evidence || []);
  const latestProvenance: ProvenanceData | undefined = [...messages]
    .reverse()
    .find((m) => m.provenance)?.provenance;

  return (
    <div className="space-y-6">
      {/* Top Page Header */}
      <PageHeader
        title="AI Financial Research Engine"
        subtitle="LangGraph multi-agent financial synthesis, SEC filings, fundamental valuation & news"
        badge={
          <Badge variant="info" size="sm" dot>
            Phase B Active
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              leftIcon={<History className="w-4 h-4" />}
              onClick={() => navigate('/app/research/history')}
            >
              Session History
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<PlusCircle className="w-4 h-4" />}
              onClick={handleStartNewSession}
            >
              New Research
            </Button>
          </div>
        }
      />

      {/* Target Asset Ribbon & Tab Navigation */}
      <div className="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 flex flex-wrap items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-white px-2.5 py-1 rounded bg-cyan-950 border border-cyan-800/80">
            {ticker}
          </span>
          <span className="text-xs font-mono text-slate-400">
            Market: <span className="text-cyan-400">{market}</span>
          </span>
          {sessionId && (
            <span className="text-[11px] font-mono text-slate-500 hidden sm:inline">
              Session #{sessionId}
            </span>
          )}
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-none text-xs font-mono">
          <button
            onClick={() => setActiveTab('synthesis')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'synthesis'
                ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40 shadow-xs'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <BrainCircuit className="w-3.5 h-3.5 text-cyan-400" />
            <span>AI Synthesis</span>
            {messages.length > 0 && (
              <span className="w-4 h-4 rounded-full bg-cyan-900 text-cyan-300 text-[10px] flex items-center justify-center">
                {messages.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('company')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'company'
                ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40 shadow-xs'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Building2 className="w-3.5 h-3.5 text-indigo-400" />
            <span>Company</span>
          </button>

          <button
            onClick={() => setActiveTab('financials')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'financials'
                ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40 shadow-xs'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            <span>Financials</span>
          </button>

          <button
            onClick={() => setActiveTab('market')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'market'
                ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40 shadow-xs'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
            <span>Valuation & Prices</span>
          </button>

          <button
            onClick={() => setActiveTab('news')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'news'
                ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40 shadow-xs'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Newspaper className="w-3.5 h-3.5 text-amber-400" />
            <span>News & Sentiment</span>
          </button>

          {accumulatedEvidence.length > 0 && (
            <button
              onClick={() => setActiveTab('evidence')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap ${
                activeTab === 'evidence'
                  ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40 shadow-xs'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
              <span>Evidence ({accumulatedEvidence.length})</span>
            </button>
          )}

          {latestProvenance && (
            <button
              onClick={() => setActiveTab('provenance')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap ${
                activeTab === 'provenance'
                  ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40 shadow-xs'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <GitCommit className="w-3.5 h-3.5 text-indigo-400" />
              <span>Provenance</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Tab Content */}
      {activeTab === 'synthesis' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Chat Stream & Composer Column */}
          <div className="lg:col-span-3 space-y-6">
            {/* Research Input Composer */}
            <ResearchComposer
              onSubmit={handleQuerySubmit}
              isLoading={isLoading}
              initialTicker={ticker}
              initialMarket={market}
            />

            {/* Error State Banner */}
            {error && (
              <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 flex items-start gap-3 text-xs text-rose-300 animate-in fade-in">
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div className="flex-1 space-y-1">
                  <p className="font-semibold text-rose-200">Research Query Error</p>
                  <p className="text-rose-300/90 leading-relaxed">{error}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => currentPrompt && handleQuerySubmit(currentPrompt, ticker, market)}
                  className="border-rose-700 text-rose-300 hover:bg-rose-900/30"
                >
                  Retry
                </Button>
              </div>
            )}

            {/* Loading State (No Fake Progress) */}
            {isLoading && (
              <ResearchLoadingState query={currentPrompt} ticker={ticker} market={market} />
            )}

            {/* Conversation Messages */}
            {messages.length === 0 && !isLoading && (
              <div className="p-8 sm:p-12 rounded-2xl bg-slate-900/40 border border-slate-800/80 text-center flex flex-col items-center">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-indigo-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-4 shadow-lg shadow-cyan-500/5">
                  <BrainCircuit className="w-7 h-7 stroke-[2]" />
                </div>
                <h3 className="text-base font-bold text-white">
                  Ready for Multi-Agent Financial Research
                </h3>
                <p className="text-xs text-slate-400 mt-1.5 max-w-lg leading-relaxed">
                  Compose a query above or choose a preset to dispatch tasks to LangGraph financial analysts, SEC filing inspectors, market valuation agents, and sentiment monitors.
                </p>

                {/* Quick Prompts Grid */}
                <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl text-left">
                  <button
                    onClick={() =>
                      handleQuerySubmit(
                        `Perform a comprehensive valuation and earnings moat analysis for ${ticker} (${market}).`,
                        ticker,
                        market
                      )
                    }
                    className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 hover:border-cyan-500/40 transition-colors text-xs cursor-pointer group"
                  >
                    <p className="font-semibold text-slate-200 group-hover:text-cyan-300 transition-colors">
                      Valuation & Moat Assessment
                    </p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      P/E, EV/EBITDA multiples, competitive position, and sector margins.
                    </p>
                  </button>

                  <button
                    onClick={() =>
                      handleQuerySubmit(
                        `Synthesize the latest news, regulatory updates, and sentiment drivers for ${ticker} (${market}).`,
                        ticker,
                        market
                      )
                    }
                    className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 hover:border-cyan-500/40 transition-colors text-xs cursor-pointer group"
                  >
                    <p className="font-semibold text-slate-200 group-hover:text-cyan-300 transition-colors">
                      News & Catalyst Breakdown
                    </p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Sentiment score, recent corporate announcements, and regulatory filings.
                    </p>
                  </button>
                </div>
              </div>
            )}

            {/* Conversation Timeline */}
            <div className="space-y-4">
              {messages.map((msg) => (
                <AiResponseView key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Right Sidebar: Quick Navigation & Recent Sessions */}
          <div className="space-y-6">
            {/* Quick Context Card */}
            <Card
              title="Active Research Context"
              subtitle="Target symbol & data parameters"
            >
              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-800/80 font-mono">
                  <span className="text-slate-400">Ticker Symbol:</span>
                  <span className="text-white font-bold">{ticker}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800/80 font-mono">
                  <span className="text-slate-400">Exchange Market:</span>
                  <span className="text-cyan-400 font-bold">{market}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800/80 font-mono">
                  <span className="text-slate-400">Session Status:</span>
                  <span className="text-emerald-400 font-medium">
                    {sessionId ? `Active (#${sessionId})` : 'New Query'}
                  </span>
                </div>

                <div className="pt-2 flex flex-col gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-xs justify-start"
                    leftIcon={<Building2 className="w-3.5 h-3.5 text-indigo-400" />}
                    onClick={() => setActiveTab('company')}
                  >
                    View Company Profile
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-xs justify-start"
                    leftIcon={<FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />}
                    onClick={() => setActiveTab('financials')}
                  >
                    View Financial Statements
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-xs justify-start"
                    leftIcon={<TrendingUp className="w-3.5 h-3.5 text-cyan-400" />}
                    onClick={() => setActiveTab('market')}
                  >
                    View Valuation & Chart
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-xs justify-start"
                    leftIcon={<Newspaper className="w-3.5 h-3.5 text-amber-400" />}
                    onClick={() => setActiveTab('news')}
                  >
                    View News & Sentiment
                  </Button>
                </div>
              </div>
            </Card>

            {/* Recent Sessions List */}
            <Card
              title={
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-1.5 text-slate-100">
                    <History className="w-4 h-4 text-cyan-400" />
                    <span>Recent Sessions</span>
                  </div>
                  <button
                    onClick={fetchRecentSessions}
                    className="p-1 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                    title="Refresh session list"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </button>
                </div>
              }
              subtitle="Persisted research sessions on Django"
            >
              {loadingSessions ? (
                <div className="space-y-2 py-2">
                  <div className="h-8 rounded bg-slate-800/40 animate-pulse" />
                  <div className="h-8 rounded bg-slate-800/40 animate-pulse" />
                </div>
              ) : recentSessions.length === 0 ? (
                <div className="py-4 text-center text-xs text-slate-400">
                  <p>No prior sessions found.</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Sessions will persist to <code className="font-mono text-cyan-400">GET /api/v1/research/sessions/</code>
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {recentSessions.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => navigate(`/app/research/${s.id}`)}
                      className="w-full p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 hover:border-cyan-500/40 text-left transition-colors cursor-pointer group space-y-1 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-cyan-400 text-[11px] font-semibold">
                          #{s.id} {s.ticker ? `• ${s.ticker}` : ''}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {formatDate(s.created_at, { format: 'relative' })}
                        </span>
                      </div>
                      <p className="text-slate-200 group-hover:text-cyan-300 font-medium truncate">
                        {s.title || s.query || 'Research Session'}
                      </p>
                    </button>
                  ))}

                  <div className="pt-2 text-center">
                    <button
                      onClick={() => navigate('/app/research/history')}
                      className="text-xs text-cyan-400 hover:text-cyan-300 font-mono transition-colors cursor-pointer"
                    >
                      View All History →
                    </button>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* Tab: Company Profile */}
      {activeTab === 'company' && <CompanyResearchView ticker={ticker} market={market} />}

      {/* Tab: Financial Statements */}
      {activeTab === 'financials' && <FinancialDataView ticker={ticker} market={market} />}

      {/* Tab: Market Data & Historical Chart */}
      {activeTab === 'market' && <MarketDataView ticker={ticker} market={market} />}

      {/* Tab: News & Sentiment */}
      {activeTab === 'news' && <NewsView ticker={ticker} market={market} />}

      {/* Tab: Evidence Citations */}
      {activeTab === 'evidence' && <EvidencePanel evidence={accumulatedEvidence} />}

      {/* Tab: Provenance Trace */}
      {activeTab === 'provenance' && <ProvenancePanel provenance={latestProvenance} />}
    </div>
  );
};
