/**
 * TypeScript definitions for Phase B — AI Research Engine and Market Data APIs
 * Designed to mirror Django REST Framework serialization formats.
 */

export type MarketCode = 'NSE' | 'BSE' | 'NASDAQ' | 'NYSE' | string;

export interface ChatRequest {
  message: string;
  session_id?: string | number;
  ticker?: string;
  market?: string;
  stream?: boolean;
}

export interface EvidenceItem {
  id?: string | number;
  title?: string;
  source?: string;
  url?: string;
  snippet?: string;
  content?: string;
  published_date?: string;
  published_at?: string;
  date?: string;
  score?: number;
  confidence?: number;
  relevance?: number;
  source_type?: 'sec_filing' | 'annual_report' | 'news' | 'market_feed' | 'rag_doc' | string;
  metadata?: Record<string, unknown>;
}

export interface AgentExecutionStep {
  agent?: string;
  name?: string;
  status?: 'started' | 'completed' | 'failed' | string;
  timestamp?: string;
  duration_ms?: number;
  latency_ms?: number;
  tools_called?: string[] | Array<{ tool: string; args?: Record<string, unknown> }>;
  reasoning?: string;
  summary?: string;
  tokens?: {
    prompt?: number;
    completion?: number;
    total?: number;
  };
}

export interface ProvenanceData {
  workflow?: string;
  agents?: string[] | AgentExecutionStep[];
  steps?: AgentExecutionStep[];
  model?: string;
  execution_time_ms?: number;
  rag_documents_retrieved?: number;
  timestamp?: string;
  confidence_score?: number;
  [key: string]: unknown;
}

export interface SentimentAnalysis {
  label?: 'Bullish' | 'Bearish' | 'Neutral' | 'Positive' | 'Negative' | string;
  score?: number; // e.g. -1.0 to 1.0 or 0 to 100
  polarity?: number;
  subjectivity?: number;
  breakdown?: {
    positive?: number;
    negative?: number;
    neutral?: number;
    bullish?: number;
    bearish?: number;
  };
  summary?: string;
}

export interface ChatMessage {
  id: string | number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  ticker?: string;
  market?: string;
  evidence?: EvidenceItem[];
  provenance?: ProvenanceData;
  sentiment?: SentimentAnalysis | string;
}

export interface ChatResponse {
  session_id?: string | number;
  id?: string | number;
  message?: string;
  content?: string;
  response?: string;
  role?: string;
  ticker?: string;
  market?: string;
  created_at?: string;
  timestamp?: string;
  evidence?: EvidenceItem[];
  sources?: EvidenceItem[];
  provenance?: ProvenanceData;
  agent_trace?: ProvenanceData | AgentExecutionStep[];
  sentiment?: SentimentAnalysis | string;
  [key: string]: unknown;
}

export interface ResearchEvidenceItem {
  id: number;
  agent_name: string;
  response: string;
  tools_used: string[];
  structured_data?: Record<string, unknown> | null;
  created_at: string;
}

export interface ResearchSession {
  id: string; // UUID
  thread_id: string;
  user_message: string;
  ticker: string | null;
  market: string | null;
  route: string;
  status: 'COMPLETED' | 'FAILED' | 'RUNNING' | string;
  final_synthesis: string | null;
  latency_ms: number | null;
  created_at: string;
  // Optional client-side presentation helper fields
  title?: string;
  query?: string;
  summary?: string;
  message_count?: number;
  messages_count?: number;
  messages?: ChatMessage[];
  last_message?: string;
}

export interface ResearchSessionDetail extends ResearchSession {
  evidence_items: ResearchEvidenceItem[];
  messages: ChatMessage[];
  evidence?: EvidenceItem[];
  provenance?: ProvenanceData;
}

export type ResearchSessionListResponse = ResearchSession[];

export interface CompanyInfo {
  ticker: string;
  name: string;
  exchange?: string | null;
  country?: string | null;
  sector?: string | null;
  industry?: string | null;
  description?: string | null;
  isin?: string | null;
  nse_symbol?: string | null;
  bse_code?: string | null;
  [key: string]: unknown;
}

export interface UsMarketQuote {
  ticker?: string | null;
  price?: number | null;
  change?: number | null;
  percent_change?: number | null;
  high?: number | null;
  low?: number | null;
  open?: number | null;
  previous_close?: number | null;
  [key: string]: unknown;
}

export interface IndiaExchangeQuote {
  exchange?: string | null;
  price?: number | null;
  percent_change?: number | null;
  year_high?: number | null;
  year_low?: number | null;
  [key: string]: unknown;
}

export type CompanyMarketData = UsMarketQuote | IndiaExchangeQuote[] | null | undefined;

export interface CompanyResearchResponse {
  ticker: string;
  market: string;
  company: CompanyInfo;
  market_data?: CompanyMarketData;
  error?: string;
  [key: string]: unknown;
}

export interface CompanyProfile {
  ticker: string;
  market?: string;
  name?: string;
  company_name?: string;
  sector?: string;
  industry?: string;
  description?: string;
  summary?: string;
  exchange?: string;
  country?: string;
  currency?: string;
  ceo?: string;
  founded?: string | number;
  employees?: number;
  headquarters?: string;
  website?: string;
  market_cap?: number;
  market_capitalization?: number;
  logo_url?: string;
  [key: string]: unknown;
}

export interface FinancialMetricItem {
  name: string;
  key: string;
  value: number | null;
}

export interface FinancialStatementItem {
  statement_type: 'INC' | 'BAL' | 'CAS' | string;
  fiscal_year: string;
  end_date: string;
  period_type: string;
  period_length?: number;
  metrics: FinancialMetricItem[];
}

export interface FinancialsResponse {
  ticker: string;
  market: string;
  financials: FinancialStatementItem[];
  [key: string]: unknown;
}

export interface KeyMetricItem {
  category: string;
  name: string;
  key: string;
  value: number | null;
  raw_value: string | null;
}

export interface KeyMetricsResponse {
  ticker: string;
  market: string;
  metrics: KeyMetricItem[];
  [key: string]: unknown;
}

export interface FinancialPeriod {
  period?: string;
  year?: string | number;
  date?: string;
  revenue?: number;
  total_revenue?: number;
  gross_profit?: number;
  operating_income?: number;
  operating_expense?: number;
  net_income?: number;
  ebitda?: number;
  eps?: number;
  diluted_eps?: number;
  total_assets?: number;
  total_liabilities?: number;
  total_debt?: number;
  total_equity?: number;
  cash_and_equivalents?: number;
  operating_cash_flow?: number;
  capital_expenditure?: number;
  free_cash_flow?: number;
  [key: string]: unknown;
}

export interface FinancialsData {
  ticker: string;
  market?: string;
  currency?: string;
  financials?: FinancialStatementItem[];
  periods?: FinancialPeriod[];
  annual?: FinancialPeriod[];
  quarterly?: FinancialPeriod[];
  // Direct summary fields
  revenue?: number;
  net_income?: number;
  gross_profit?: number;
  operating_income?: number;
  eps?: number;
  profit_margin?: number;
  operating_margin?: number;
  free_cash_flow?: number;
  total_assets?: number;
  total_liabilities?: number;
  total_debt?: number;
  [key: string]: unknown;
}

export interface MarketMetrics {
  ticker: string;
  market?: string;
  metrics?: KeyMetricItem[];
  price?: number;
  current_price?: number;
  close_price?: number;
  change?: number;
  change_percent?: number;
  volume?: number;
  avg_volume?: number;
  market_cap?: number;
  pe_ratio?: number;
  trailing_pe?: number;
  forward_pe?: number;
  pb_ratio?: number;
  ps_ratio?: number;
  ev_ebitda?: number;
  roe?: number;
  roa?: number;
  roce?: number;
  dividend_yield?: number;
  debt_to_equity?: number;
  current_ratio?: number;
  beta?: number;
  high_52w?: number;
  low_52w?: number;
  day_high?: number;
  day_low?: number;
  currency?: string;
  last_updated?: string;
  [key: string]: unknown;
}

export interface NewsEntity {
  symbol: string;
  name: string;
  country?: string | null;
  entity_type?: string | null;
  match_score?: number | null;
  sentiment_score?: number | null;
}

export interface NewsArticle {
  id?: string | number;
  title: string;
  summary?: string | null;
  description?: string | null;
  content?: string | null;
  source: string;
  url: string;
  published_at?: string | null;
  published_date?: string | null;
  datetime?: string | null;
  image_url?: string | null;
  relevance_score?: number | null;
  target_match_score?: number | null;
  relevance_type?: 'DIRECT' | 'RELATED' | 'MARKET_CONTEXT' | string | null;
  entities?: NewsEntity[] | null;
  sentiment?: 'positive' | 'negative' | 'neutral' | 'bullish' | 'bearish' | string;
  sentiment_score?: number | null;
  thumbnail?: string | null;
}

export interface NewsResponse {
  ticker: string;
  market?: string;
  articles: NewsArticle[];
  news?: NewsArticle[];
  sentiment?: SentimentAnalysis;
  overall_sentiment?: string;
  sentiment_score?: number;
  sentiment_summary?: string;
  count?: number;
  [key: string]: unknown;
}

export interface HistoricalCandle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  open_interest?: number | null;
}

export interface HistoricalResponse {
  ticker: string;
  market: string;
  candles: HistoricalCandle[];
  [key: string]: unknown;
}

export interface HistoricalBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adj_close?: number;
}

export interface HistoricalDataResponse {
  ticker?: string;
  market?: string;
  from_date?: string;
  to_date?: string;
  candles?: HistoricalCandle[];
  data?: HistoricalBar[];
  prices?: HistoricalBar[];
  historical?: HistoricalBar[];
  bars?: HistoricalBar[];
  [key: string]: unknown;
}
