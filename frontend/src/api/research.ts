import { apiClient } from './client';
import { researchDataCache } from './researchCache';
export { researchDataCache };
import {
  ChatRequest,
  ChatResponse,
  ChatMessage,
  ResearchSession,
  ResearchSessionDetail,
  ResearchSessionListResponse,
  CompanyProfile,
  CompanyResearchResponse,
  FinancialsData,
  FinancialsResponse,
  MarketMetrics,
  KeyMetricsResponse,
  NewsResponse,
  HistoricalDataResponse,
  HistoricalResponse,
} from '../types/research';

export const researchApi = {
  /**
   * POST /api/v1/ai/chat/
   * Dispatches analyst research query to the LangGraph multi-agent financial synthesizer
   */
  async chat(payload: ChatRequest): Promise<ChatResponse> {
    return apiClient.post<ChatResponse>('ai/chat/', payload, {
      timeoutMs: 360000, // LangGraph multi-agent synthesis budget (360s / 6min)
    });
  },

  /**
   * GET /api/v1/research/sessions/
   * Retrieves previous research sessions for the authenticated user from Django.
   * Note: Django sessions endpoint is not paginated; it returns the full array.
   */
  async getSessions(): Promise<ResearchSession[]> {
    const response = await apiClient.get<ResearchSessionListResponse | ResearchSession[]>('research/sessions/');

    // Normalize if backend returns direct array [...] or wrapped object
    if (Array.isArray(response)) {
      return response;
    }
    const anyResp = response as unknown as { results?: ResearchSession[] };
    if (anyResp && Array.isArray(anyResp.results)) {
      return anyResp.results;
    }
    return [];
  },

  /**
   * GET /api/v1/research/sessions/<id>/
   * Retrieves full details, evidence items, and execution metadata for a session
   */
  async getSession(id: string): Promise<ResearchSessionDetail> {
    const raw = await apiClient.get<ResearchSessionDetail | Record<string, unknown>>(`research/sessions/${id}/`);
    return normalizeSessionDetail(raw, id);
  },

  /**
   * GET /api/v1/research/company/?ticker=&market=
   * Retrieves fundamental company profile, sector, description, and market quotes from Django.
   * Cached for 60 seconds with in-flight request deduplication.
   */
  async getCompany(ticker: string, market: string = 'IN'): Promise<CompanyResearchResponse> {
    const rawMarket = (market || 'IN').trim().toUpperCase();
    const normalizedMarket =
      rawMarket === 'US' || rawMarket === 'USA' || rawMarket === 'NASDAQ' || rawMarket === 'NYSE'
        ? 'US'
        : 'IN';
    const normalizedTicker = ticker.trim().toUpperCase();
    const cacheKey = researchDataCache.createKey('company', normalizedTicker, normalizedMarket);

    return researchDataCache.getOrFetch(cacheKey, () =>
      apiClient.get<CompanyResearchResponse>('research/company/', {
        params: { ticker: normalizedTicker, market: normalizedMarket },
      })
    );
  },

  /**
   * GET /api/v1/research/financials/?ticker=&market=
   * Retrieves income statement (INC), balance sheet (BAL), and cash flow (CAS) statements.
   * Cached for 60 seconds with in-flight request deduplication.
   */
  async getFinancials(ticker: string, market: string = 'IN'): Promise<FinancialsResponse> {
    const rawMarket = (market || 'IN').trim().toUpperCase();
    const normalizedMarket =
      rawMarket === 'US' || rawMarket === 'USA' || rawMarket === 'NASDAQ' || rawMarket === 'NYSE'
        ? 'US'
        : 'IN';
    const normalizedTicker = ticker.trim().toUpperCase();
    const cacheKey = researchDataCache.createKey('financials', normalizedTicker, normalizedMarket);

    return researchDataCache.getOrFetch(cacheKey, () =>
      apiClient.get<FinancialsResponse>('research/financials/', {
        params: { ticker: normalizedTicker, market: normalizedMarket },
      })
    );
  },

  /**
   * GET /api/v1/research/metrics/?ticker=&market=
   * Retrieves key valuation, profitability, and liquidity metrics from Django.
   * Cached for 60 seconds with in-flight request deduplication.
   */
  async getMetrics(ticker: string, market: string = 'IN'): Promise<KeyMetricsResponse> {
    const rawMarket = (market || 'IN').trim().toUpperCase();
    const normalizedMarket =
      rawMarket === 'US' || rawMarket === 'USA' || rawMarket === 'NASDAQ' || rawMarket === 'NYSE'
        ? 'US'
        : 'IN';
    const normalizedTicker = ticker.trim().toUpperCase();
    const cacheKey = researchDataCache.createKey('metrics', normalizedTicker, normalizedMarket);

    return researchDataCache.getOrFetch(cacheKey, () =>
      apiClient.get<KeyMetricsResponse>('research/metrics/', {
        params: { ticker: normalizedTicker, market: normalizedMarket },
      })
    );
  },

  /**
   * GET /api/v1/research/news/?ticker=&market=
   * Retrieves verified market news and entity sentiment from Django.
   * Cached for 60 seconds with in-flight request deduplication.
   */
  async getNews(ticker: string, market: string = 'IN'): Promise<NewsResponse> {
    const rawMarket = (market || 'IN').trim().toUpperCase();
    const normalizedMarket =
      rawMarket === 'US' || rawMarket === 'USA' || rawMarket === 'NASDAQ' || rawMarket === 'NYSE'
        ? 'US'
        : 'IN';
    const normalizedTicker = ticker.trim().toUpperCase();
    const cacheKey = researchDataCache.createKey('news', normalizedTicker, normalizedMarket);

    return researchDataCache.getOrFetch(cacheKey, () =>
      apiClient.get<NewsResponse>('research/news/', {
        params: { ticker: normalizedTicker, market: normalizedMarket },
      })
    );
  },

  /**
   * GET /api/v1/research/historical/?ticker=&market=&from_date=&to_date=
   * Retrieves historical OHLCV price bars for the requested symbol.
   * Cached for 60 seconds with in-flight request deduplication.
   */
  async getHistorical(
    ticker: string,
    market: string = 'IN',
    fromDate?: string,
    toDate?: string
  ): Promise<HistoricalResponse> {
    const rawMarket = (market || 'IN').trim().toUpperCase();
    const normalizedMarket =
      rawMarket === 'US' || rawMarket === 'USA' || rawMarket === 'NASDAQ' || rawMarket === 'NYSE'
        ? 'US'
        : 'IN';
    const normalizedTicker = ticker.trim().toUpperCase();
    const resolvedToDate = toDate || new Date().toISOString().split('T')[0];
    const cacheExtra = `${fromDate || ''}:${resolvedToDate}`;
    const cacheKey = researchDataCache.createKey('historical', normalizedTicker, normalizedMarket, cacheExtra);

    const params: Record<string, string> = {
      ticker: normalizedTicker,
      market: normalizedMarket,
      to_date: resolvedToDate,
    };
    if (fromDate) {
      params.from_date = fromDate;
    }

    return researchDataCache.getOrFetch(cacheKey, () =>
      apiClient.get<HistoricalResponse>('research/historical/', {
        params,
      })
    );
  },
};

/**
 * Normalizes raw session detail to match Django's ResearchSessionDetailSerializer
 */
function normalizeSessionDetail(raw: unknown, fallbackId: string): ResearchSessionDetail {
  if (!raw || typeof raw !== 'object') {
    return {
      id: fallbackId,
      thread_id: '',
      user_message: '',
      ticker: null,
      market: null,
      route: 'general',
      status: 'COMPLETED',
      final_synthesis: null,
      latency_ms: null,
      created_at: new Date().toISOString(),
      evidence_items: [],
      messages: [],
    };
  }

  const obj = raw as Record<string, unknown>;
  const id = String(obj.id || fallbackId);
  const threadId = String(obj.thread_id || '');
  const userMessage = String(obj.user_message || obj.query || obj.prompt || '');
  const ticker = (obj.ticker as string) || null;
  const market = (obj.market as string) || null;
  const route = String(obj.route || 'general');
  const status = String(obj.status || 'COMPLETED');
  const finalSynthesis = (obj.final_synthesis as string) || null;
  const latencyMs = typeof obj.latency_ms === 'number' ? obj.latency_ms : null;
  const createdAt = (obj.created_at as string) || new Date().toISOString();

  // Extract raw evidence items from Django ResearchEvidence model
  const rawEvidenceItems = Array.isArray(obj.evidence_items) ? (obj.evidence_items as Record<string, unknown>[]) : [];
  const evidenceItems = rawEvidenceItems.map((item, idx) => ({
    id: typeof item.id === 'number' ? item.id : idx + 1,
    agent_name: String(item.agent_name || 'agent'),
    response: String(item.response || ''),
    tools_used: Array.isArray(item.tools_used) ? (item.tools_used as string[]) : [],
    structured_data: (item.structured_data as Record<string, unknown>) || null,
    created_at: String(item.created_at || createdAt),
  }));

  // Map to UI EvidenceItem format for EvidencePanel
  const mappedEvidence = evidenceItems.map((item) => ({
    id: item.id,
    title: `Specialist Agent: ${item.agent_name.toUpperCase()}`,
    source: item.agent_name,
    source_type: item.agent_name,
    snippet: item.response ? (item.response.length > 250 ? item.response.slice(0, 250) + '...' : item.response) : (item.tools_used.length > 0 ? `Tools used: ${item.tools_used.join(', ')}` : ''),
    content: item.response,
    published_at: item.created_at,
    metadata: item.structured_data || undefined,
  }));

  // Map to UI Provenance format for ProvenancePanel
  const mappedProvenance = {
    workflow: `Workflow: ${route.toUpperCase()}`,
    model: 'LangGraph Multi-Agent Synthesizer',
    execution_time_ms: latencyMs ? Math.round(latencyMs) : undefined,
    agents: evidenceItems.map((item) => ({
      agent: item.agent_name,
      name: item.agent_name.toUpperCase(),
      status: 'completed',
      tools_called: item.tools_used,
      timestamp: item.created_at,
    })),
    timestamp: createdAt,
  };

  // Construct conversation stream messages
  let messages: ChatMessage[] = [];
  if (Array.isArray(obj.messages) && obj.messages.length > 0) {
    messages = obj.messages as ChatMessage[];
  } else {
    // Message 1: User research prompt
    if (userMessage) {
      messages.push({
        id: `${id}-user`,
        role: 'user',
        content: userMessage,
        timestamp: createdAt,
        ticker: ticker || undefined,
        market: market || undefined,
      });
    }

    // Message 2: FinPilot AI synthesized answer
    if (finalSynthesis) {
      messages.push({
        id: `${id}-assistant`,
        role: 'assistant',
        content: finalSynthesis,
        timestamp: createdAt,
        ticker: ticker || undefined,
        market: market || undefined,
        evidence: mappedEvidence,
        provenance: mappedProvenance,
      });
    } else if (status === 'FAILED') {
      messages.push({
        id: `${id}-failed`,
        role: 'assistant',
        content: 'Workflow execution encountered an error during processing.',
        timestamp: createdAt,
        ticker: ticker || undefined,
        market: market || undefined,
      });
    }
  }

  return {
    id,
    thread_id: threadId,
    user_message: userMessage,
    ticker,
    market,
    route,
    status,
    final_synthesis: finalSynthesis,
    latency_ms: latencyMs,
    created_at: createdAt,
    title: userMessage || `Session #${id.slice(0, 8)}`,
    query: userMessage,
    summary: finalSynthesis ? (finalSynthesis.slice(0, 160) + '...') : undefined,
    evidence_items: evidenceItems,
    messages,
    evidence: mappedEvidence,
    provenance: mappedProvenance,
  };
}
