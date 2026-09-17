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

  // Authoritative URL navigation state
  const urlTicker = (searchParams.get('ticker') || 'RELIANCE').trim().toUpperCase();
  const urlMarket = (searchParams.get('market') || 'IN').trim().toUpperCase();
  const urlTab = (searchParams.get('tab') as ResearchTab) || 'synthesis';
  const urlQuery = searchParams.get('q') || '';
  const shouldFocus = searchParams.get('focus') === 'composer';

  // Active target asset
  const [ticker, setTicker] = useState<string>(urlTicker);
  const [market, setMarket] = useState<string>(urlMarket);

  // Active view tab
  const [activeTab, setActiveTab] = useState<ResearchTab>(urlTab);

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

  // Synchronize state when URL search parameters change (browser back/forward, direct URL navigation)
  useEffect(() => {
    if (urlTicker && urlTicker !== ticker) {
      setTicker(urlTicker);
    }
    if (urlMarket && urlMarket !== market) {
      setMarket(urlMarket);
    }
    if (urlTab && urlTab !== activeTab) {
      setActiveTab(urlTab);
    }
  }, [urlTicker, urlMarket, urlTab]);

  // Ensure default ticker and market are present in URL on initial visit without adding extra history
  useEffect(() => {
    const hasTicker = searchParams.has('ticker');
    const hasMarket = searchParams.has('market');
    if (!hasTicker || !hasMarket) {
      const params = new URLSearchParams(searchParams);
      if (!hasTicker) params.set('ticker', ticker);
      if (!hasMarket) params.set('market', market);
      setSearchParams(params, { replace: true });
    }
  }, []);

  // Update target asset and synchronize to URL search params
  const updateTargetAsset = (newTicker: string, newMarket?: string, replaceHistory = false) => {
    const normTicker = (newTicker.trim() || 'RELIANCE').toUpperCase();
    const normMarket = (newMarket ? newMarket.trim() : market).toUpperCase();

    if (normTicker === ticker && normMarket === market) {
      return;
    }

    setTicker(normTicker);
    setMarket(normMarket);

    const params = new URLSearchParams(searchParams);
    params.set('ticker', normTicker);
    params.set('market', normMarket);
    setSearchParams(params, { replace: replaceHistory });
  };

  // Switch research view tab and synchronize to URL search params
  const handleTabChange = (newTab: ResearchTab) => {
    setActiveTab(newTab);
    const params = new URLSearchParams(searchParams);
    if (newTab === 'synthesis') {
      params.delete('tab');
    } else {
      params.set('tab', newTab);
    }
    setSearchParams(params, { replace: true });
  };

  // Load recent research sessions for quick access
  const fetchRecentSessions = async () => {
    setLoadingSessions(true);
    try {
      const sessions = await researchApi.getSessions();
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

    const normTicker = (queryTicker || ticker).trim().toUpperCase();
    const normMarket = (queryMarket || market).trim().toUpperCase();

    if (normTicker !== ticker || normMarket !== market) {
      updateTargetAsset(normTicker, normMarket, false);
    }

    // Append user query to conversation
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
      ticker: normTicker,
      market: normMarket,
    };

    setMessages((prev) => [...prev, userMsg]);

    try {
      const response: ChatResponse = await researchApi.chat({
        message: prompt,
        session_id: sessionId,
        ticker: normTicker,
        market: normMarket,
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
    handleTabChange('synthesis');
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
      <div className="p-3.5 rounded-2xl bg-surface border border-border-theme flex flex-wrap items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-accent-soft text-accent-primary border border-accent-primary/30">
            {ticker}
          </span>
          <span className="text-xs font-mono text-text-muted">
            Market: <span className="text-accent-primary font-semibold">{market}</span>
          </span>
          {sessionId && (
            <span className="text-[11px] font-mono text-text-muted hidden sm:inline">
              Session #{sessionId}
            </span>
          )}
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none text-xs font-mono">
          <button
            onClick={() => handleTabChange('synthesis')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
              activeTab === 'synthesis'
                ? 'bg-accent-soft text-accent-primary font-semibold border border-accent-primary shadow-xs ring-1 ring-accent-primary/20'
                : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
            }`}
          >
            <BrainCircuit className="w-3.5 h-3.5 text-accent-primary" />
            <span>AI Synthesis</span>
            {messages.length > 0 && (
              <span className="w-4 h-4 rounded-full bg-accent-primary text-white text-[10px] font-bold flex items-center justify-center">
                {messages.length}
              </span>
            )}
          </button>

          <button
            onClick={() => handleTabChange('company')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
              activeTab === 'company'
                ? 'bg-accent-soft text-accent-primary font-semibold border border-accent-primary shadow-xs ring-1 ring-accent-primary/20'
                : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
            }`}
          >
            <Building2 className="w-3.5 h-3.5 text-status-info" />
            <span>Company</span>
          </button>

          <button
            onClick={() => handleTabChange('financials')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
              activeTab === 'financials'
                ? 'bg-accent-soft text-accent-primary font-semibold border border-accent-primary shadow-xs ring-1 ring-accent-primary/20'
                : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-accent-primary" />
            <span>Financials</span>
          </button>

          <button
            onClick={() => handleTabChange('market')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
              activeTab === 'market'
                ? 'bg-accent-soft text-accent-primary font-semibold border border-accent-primary shadow-xs ring-1 ring-accent-primary/20'
                : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5 text-accent-primary" />
            <span>Valuation & Prices</span>
          </button>

          <button
            onClick={() => handleTabChange('news')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
              activeTab === 'news'
                ? 'bg-accent-soft text-accent-primary font-semibold border border-accent-primary shadow-xs ring-1 ring-accent-primary/20'
                : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
            }`}
          >
            <Newspaper className="w-3.5 h-3.5 text-status-warning" />
            <span>News & Sentiment</span>
          </button>

          {accumulatedEvidence.length > 0 && (
            <button
              onClick={() => handleTabChange('evidence')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
                activeTab === 'evidence'
                  ? 'bg-accent-soft text-accent-primary font-semibold border border-accent-primary shadow-xs ring-1 ring-accent-primary/20'
                  : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5 text-accent-primary" />
              <span>Evidence ({accumulatedEvidence.length})</span>
            </button>
          )}

          {latestProvenance && (
            <button
              onClick={() => handleTabChange('provenance')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
                activeTab === 'provenance'
                  ? 'bg-accent-soft text-accent-primary font-semibold border border-accent-primary shadow-xs ring-1 ring-accent-primary/20'
                  : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
              }`}
            >
              <GitCommit className="w-3.5 h-3.5 text-status-info" />
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
              onTickerChange={(newTicker, newMarket) => updateTargetAsset(newTicker, newMarket, false)}
              isLoading={isLoading}
              initialTicker={ticker}
              initialMarket={market}
              initialQuery={urlQuery}
              autoFocus={shouldFocus}
            />

            {/* Error State Banner */}
            {error && (
              <div className="p-4 rounded-xl bg-status-danger-soft border border-status-danger/30 flex items-start gap-3 text-xs text-status-danger animate-in fade-in">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <div className="flex-1 space-y-1">
                  <p className="font-semibold">Research Query Error</p>
                  <p className="opacity-90 leading-relaxed">{error}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => currentPrompt && handleQuerySubmit(currentPrompt, ticker, market)}
                  className="border-status-danger/50 text-status-danger hover:bg-status-danger-soft"
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
              <div className="p-8 sm:p-12 rounded-2xl bg-surface border border-border-theme text-center flex flex-col items-center">
                <div className="w-14 h-14 rounded-2xl bg-accent-soft border border-accent-primary/20 flex items-center justify-center text-accent-primary mb-4 shadow-lg shadow-accent-primary/5">
                  <BrainCircuit className="w-7 h-7 stroke-[2]" />
                </div>
                <h3 className="text-base font-bold text-text-primary">
                  Ready for Multi-Agent Financial Research
                </h3>
                <p className="text-xs text-text-muted mt-1.5 max-w-lg leading-relaxed">
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
                    className="p-3 rounded-xl bg-surface-secondary/50 border border-border-subtle hover:border-accent-primary/40 transition-colors text-xs cursor-pointer group"
                  >
                    <p className="font-semibold text-text-primary group-hover:text-accent-primary transition-colors">
                      Valuation & Moat Assessment
                    </p>
                    <p className="text-[11px] text-text-muted mt-0.5">
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
                    className="p-3 rounded-xl bg-surface-secondary/50 border border-border-subtle hover:border-accent-primary/40 transition-colors text-xs cursor-pointer group"
                  >
                    <p className="font-semibold text-text-primary group-hover:text-accent-primary transition-colors">
                      News & Catalyst Breakdown
                    </p>
                    <p className="text-[11px] text-text-muted mt-0.5">
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
                <div className="flex justify-between py-1 border-b border-border-subtle font-mono">
                  <span className="text-text-muted">Ticker Symbol:</span>
                  <span className="text-text-primary font-bold">{ticker}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border-subtle font-mono">
                  <span className="text-text-muted">Exchange Market:</span>
                  <span className="text-accent-primary font-bold">{market}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border-subtle font-mono">
                  <span className="text-text-muted">Session Status:</span>
                  <span className="text-status-success font-medium">
                    {sessionId ? `Active (#${sessionId})` : 'New Query'}
                  </span>
                </div>

                <div className="pt-2 flex flex-col gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-xs justify-start"
                    leftIcon={<Building2 className="w-3.5 h-3.5 text-status-info" />}
                    onClick={() => handleTabChange('company')}
                  >
                    View Company Profile
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-xs justify-start"
                    leftIcon={<FileSpreadsheet className="w-3.5 h-3.5 text-accent-primary" />}
                    onClick={() => handleTabChange('financials')}
                  >
                    View Financial Statements
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-xs justify-start"
                    leftIcon={<TrendingUp className="w-3.5 h-3.5 text-accent-primary" />}
                    onClick={() => handleTabChange('market')}
                  >
                    View Valuation & Chart
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-xs justify-start"
                    leftIcon={<Newspaper className="w-3.5 h-3.5 text-status-warning" />}
                    onClick={() => handleTabChange('news')}
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
                  <div className="flex items-center gap-1.5 text-text-primary">
                    <History className="w-4 h-4 text-accent-primary" />
                    <span>Recent Sessions</span>
                  </div>
                  <button
                    onClick={fetchRecentSessions}
                    className="p-1 rounded text-text-muted hover:text-text-primary transition-colors cursor-pointer"
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
                  <div className="h-8 rounded bg-surface-secondary animate-pulse" />
                  <div className="h-8 rounded bg-surface-secondary animate-pulse" />
                </div>
              ) : recentSessions.length === 0 ? (
                <div className="py-4 text-center text-xs text-text-muted">
                  <p>No prior sessions found.</p>
                  <p className="text-[11px] text-text-muted mt-0.5">
                    Sessions will persist to <code className="font-mono text-accent-primary">GET /api/v1/research/sessions/</code>
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {recentSessions.map((s) => {
                    const shortId = s.id.length > 8 ? s.id.slice(0, 8) : s.id;
                    const sessionLabel = s.user_message || s.title || s.query || 'Research Session';
                    return (
                      <button
                        key={s.id}
                        onClick={() => navigate(`/app/research/${s.id}`)}
                        className="w-full p-2.5 rounded-lg bg-surface-secondary/50 border border-border-subtle hover:border-accent-primary/40 text-left transition-colors cursor-pointer group space-y-1 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-accent-primary text-[11px] font-semibold">
                            #{shortId} {s.ticker ? `• ${s.ticker}` : ''}
                          </span>
                          <span className="text-[10px] text-text-muted font-mono">
                            {formatDate(s.created_at, { format: 'relative' })}
                          </span>
                        </div>
                        <p className="text-text-primary group-hover:text-accent-primary font-medium truncate">
                          {sessionLabel}
                        </p>
                      </button>
                    );
                  })}

                  <div className="pt-2 text-center">
                    <button
                      onClick={() => navigate('/app/research/history')}
                      className="text-xs text-accent-primary hover:text-accent-hover font-medium transition-colors cursor-pointer"
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
