import { apiClient } from './client';
import {
  ChatRequest,
  ChatResponse,
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
} from '../types/research';

export const researchApi = {
  /**
   * POST /api/v1/ai/chat/
   * Dispatches analyst research query to the LangGraph multi-agent financial synthesizer
   */
  async chat(payload: ChatRequest): Promise<ChatResponse> {
    return apiClient.post<ChatResponse>('ai/chat/', payload, {
      timeoutMs: 60000, // LangGraph agent synthesis might take a few seconds
    });
  },

  /**
   * GET /api/v1/research/sessions/
   * Retrieves previous research sessions
   */
  async getSessions(params?: { page?: number; limit?: number; search?: string }): Promise<ResearchSession[]> {
    const response = await apiClient.get<ResearchSessionListResponse | ResearchSession[]>('research/sessions/', {
      params,
    });

    // Normalize if backend returns paginated object { results: [...] } or direct array [...]
    if (Array.isArray(response)) {
      return response;
    }
    if (response && Array.isArray(response.results)) {
      return response.results;
    }
    return [];
  },

  /**
   * GET /api/v1/research/sessions/<id>/
   * Retrieves full details, chat messages, evidence, and provenance for a session
   */
  async getSession(id: string | number): Promise<ResearchSessionDetail> {
    const raw = await apiClient.get<ResearchSessionDetail | Record<string, unknown>>(`research/sessions/${id}/`);
    return normalizeSessionDetail(raw, id);
  },

  /**
   * GET /api/v1/research/company/?ticker=&market=
   * Retrieves fundamental company profile, sector, description, and market quotes from Django
   */
  async getCompany(ticker: string, market: string = 'IN'): Promise<CompanyResearchResponse> {
    const rawMarket = (market || 'IN').trim().toUpperCase();
    const normalizedMarket =
      rawMarket === 'US' || rawMarket === 'USA' || rawMarket === 'NASDAQ' || rawMarket === 'NYSE'
        ? 'US'
        : 'IN';

    return apiClient.get<CompanyResearchResponse>('research/company/', {
      params: { ticker: ticker.trim().toUpperCase(), market: normalizedMarket },
    });
  },

  /**
   * GET /api/v1/research/financials/?ticker=&market=
   * Retrieves income statement (INC), balance sheet (BAL), and cash flow (CAS) statements
   */
  async getFinancials(ticker: string, market: string = 'IN'): Promise<FinancialsResponse> {
    const rawMarket = (market || 'IN').trim().toUpperCase();
    const normalizedMarket =
      rawMarket === 'US' || rawMarket === 'USA' || rawMarket === 'NASDAQ' || rawMarket === 'NYSE'
        ? 'US'
        : 'IN';

    return apiClient.get<FinancialsResponse>('research/financials/', {
      params: { ticker: ticker.trim().toUpperCase(), market: normalizedMarket },
    });
  },

  /**
   * GET /api/v1/research/metrics/?ticker=&market=
   * Retrieves key valuation, profitability, and liquidity metrics from Django
   */
  async getMetrics(ticker: string, market: string = 'IN'): Promise<KeyMetricsResponse> {
    const rawMarket = (market || 'IN').trim().toUpperCase();
    const normalizedMarket =
      rawMarket === 'US' || rawMarket === 'USA' || rawMarket === 'NASDAQ' || rawMarket === 'NYSE'
        ? 'US'
        : 'IN';

    return apiClient.get<KeyMetricsResponse>('research/metrics/', {
      params: { ticker: ticker.trim().toUpperCase(), market: normalizedMarket },
    });
  },

  /**
   * GET /api/v1/research/news/?ticker=&market=
   * Retrieves verified market news and sentiment classification
   */
  async getNews(ticker: string, market: string = 'NSE'): Promise<NewsResponse> {
    return apiClient.get<NewsResponse>('research/news/', {
      params: { ticker: ticker.toUpperCase(), market: market.toUpperCase() },
    });
  },

  /**
   * GET /api/v1/research/historical/?ticker=&market=&from_date=&to_date=
   * Retrieves historical OHLCV price bars for the requested symbol
   */
  async getHistorical(
    ticker: string,
    market: string = 'NSE',
    fromDate?: string,
    toDate?: string
  ): Promise<HistoricalDataResponse> {
    return apiClient.get<HistoricalDataResponse>('research/historical/', {
      params: {
        ticker: ticker.toUpperCase(),
        market: market.toUpperCase(),
        from_date: fromDate,
        to_date: toDate,
      },
    });
  },
};

/**
 * Normalizes raw session detail to prevent runtime UI errors across different DRF serializers
 */
function normalizeSessionDetail(raw: unknown, fallbackId: string | number): ResearchSessionDetail {
  if (!raw || typeof raw !== 'object') {
    return {
      id: fallbackId,
      created_at: new Date().toISOString(),
      messages: [],
    };
  }

  const obj = raw as Record<string, unknown>;
  const rawMessages = (obj.messages || obj.history || obj.chat || []) as Array<Record<string, unknown>>;

  const messages = rawMessages.map((msg, idx) => ({
    id: (msg.id as string | number) || `msg-${idx}`,
    role: (msg.role as 'user' | 'assistant' | 'system') || (msg.is_user ? 'user' : 'assistant'),
    content: (msg.content as string) || (msg.message as string) || (msg.text as string) || '',
    timestamp: (msg.timestamp as string) || (msg.created_at as string) || new Date().toISOString(),
    ticker: (msg.ticker as string) || (obj.ticker as string),
    market: (msg.market as string) || (obj.market as string),
    evidence: (msg.evidence || msg.sources || obj.evidence) as any,
    provenance: (msg.provenance || msg.agent_trace || obj.provenance) as any,
    sentiment: (msg.sentiment || obj.sentiment) as any,
  }));

  return {
    id: (obj.id as string | number) || fallbackId,
    title: (obj.title as string) || (obj.query as string) || (obj.topic as string) || 'Research Session',
    ticker: obj.ticker as string | undefined,
    market: obj.market as string | undefined,
    created_at: (obj.created_at as string) || new Date().toISOString(),
    updated_at: obj.updated_at as string | undefined,
    summary: (obj.summary as string) || (obj.description as string),
    messages,
    evidence: (obj.evidence || obj.sources) as any,
    provenance: (obj.provenance || obj.agent_trace) as any,
  };
}
