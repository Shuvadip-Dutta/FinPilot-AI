import { apiClient } from './client';
import {
  Portfolio,
  PortfolioListResponse,
  Holding,
  HoldingsListResponse,
  CreatePortfolioPayload,
  UpdatePortfolioPayload,
  CreateHoldingPayload,
  UpdateHoldingPayload,
  PortfolioRiskResponse,
  OptimizePortfolioPayload,
  PortfolioOptimizationResponse,
  BacktestPayload,
  BacktestResponse,
  PortfolioAiAnalysisResponse,
  Alert,
  MonitoringResponse,
  RunMonitoringPayload,
} from '../types/portfolio';

export const portfolioApi = {
  /**
   * GET /api/v1/portfolio/
   * Retrieves all user portfolios
   */
  async getPortfolios(): Promise<Portfolio[]> {
    const response = await apiClient.get<PortfolioListResponse | Portfolio[]>('portfolio/');

    if (Array.isArray(response)) {
      return response;
    }
    if (response && Array.isArray(response.results)) {
      return response.results;
    }
    return [];
  },

  /**
   * POST /api/v1/portfolio/
   * Creates a new portfolio
   */
  async createPortfolio(payload: CreatePortfolioPayload): Promise<Portfolio> {
    return apiClient.post<Portfolio>('portfolio/', payload);
  },

  /**
   * GET /api/v1/portfolio/<id>/
   * Retrieves details and holdings for a specific portfolio
   */
  async getPortfolio(id: string | number): Promise<Portfolio> {
    return apiClient.get<Portfolio>(`portfolio/${id}/`);
  },

  /**
   * PUT/PATCH /api/v1/portfolio/<id>/
   * Updates portfolio name
   */
  async updatePortfolio(id: string | number, payload: UpdatePortfolioPayload): Promise<Portfolio> {
    return apiClient.patch<Portfolio>(`portfolio/${id}/`, payload);
  },

  /**
   * DELETE /api/v1/portfolio/<id>/
   * Deletes a portfolio
   */
  async deletePortfolio(id: string | number): Promise<void> {
    return apiClient.delete<void>(`portfolio/${id}/`);
  },

  /**
   * GET /api/v1/portfolio/<id>/holdings/
   * Retrieves all asset holdings for a specific portfolio
   */
  async getHoldings(portfolioId: string | number): Promise<Holding[]> {
    const response = await apiClient.get<HoldingsListResponse | Holding[]>(
      `portfolio/${portfolioId}/holdings/`
    );

    if (Array.isArray(response)) {
      return response;
    }
    if (response && Array.isArray(response.results)) {
      return response.results;
    }
    return [];
  },

  /**
   * POST /api/v1/portfolio/<id>/holdings/
   * Adds a new holding to a portfolio
   */
  async addHolding(portfolioId: string | number, payload: CreateHoldingPayload): Promise<Holding> {
    return apiClient.post<Holding>(`portfolio/${portfolioId}/holdings/`, payload);
  },

  /**
   * GET /api/v1/portfolio/<id>/holdings/<holding_id>/
   * Retrieves a single holding
   */
  async getHolding(portfolioId: string | number, holdingId: string | number): Promise<Holding> {
    return apiClient.get<Holding>(`portfolio/${portfolioId}/holdings/${holdingId}/`);
  },

  /**
   * PUT/PATCH /api/v1/portfolio/<id>/holdings/<holding_id>/
   * Updates an existing holding
   */
  async updateHolding(
    portfolioId: string | number,
    holdingId: string | number,
    payload: UpdateHoldingPayload
  ): Promise<Holding> {
    return apiClient.patch<Holding>(`portfolio/${portfolioId}/holdings/${holdingId}/`, payload);
  },

  /**
   * DELETE /api/v1/portfolio/<id>/holdings/<holding_id>/
   * Deletes a holding from a portfolio
   */
  async deleteHolding(portfolioId: string | number, holdingId: string | number): Promise<void> {
    return apiClient.delete<void>(`portfolio/${portfolioId}/holdings/${holdingId}/`);
  },

  /**
   * GET /api/v1/portfolio/<id>/risk/
   * Retrieves deterministic quantitative risk metrics (Sharpe, Sortino, VaR, CVaR, Drawdown, etc.)
   */
  async getPortfolioRisk(
    portfolioId: string | number,
    params?: { period?: string; benchmark?: string; risk_free_rate?: number }
  ): Promise<PortfolioRiskResponse> {
    return apiClient.get<PortfolioRiskResponse>(`portfolio/${portfolioId}/risk/`, { params });
  },

  /**
   * POST /api/v1/portfolio/<id>/optimize/
   * Executes mathematical portfolio optimization (Max Sharpe under bounded simplex)
   */
  async optimizePortfolio(
    portfolioId: string | number,
    payload?: OptimizePortfolioPayload
  ): Promise<PortfolioOptimizationResponse> {
    return apiClient.post<PortfolioOptimizationResponse>(`portfolio/${portfolioId}/optimize/`, payload);
  },

  /**
   * POST /api/v1/portfolio/<id>/backtest/
   * Executes historical walk-forward backtest evaluation vs benchmark
   */
  async runBacktest(
    portfolioId: string | number,
    payload: BacktestPayload
  ): Promise<BacktestResponse> {
    const formattedPayload: Record<string, any> = {
      from_date: payload.from_date || payload.start_date || undefined,
      to_date: payload.to_date || payload.end_date || undefined,
      benchmark_ticker: payload.benchmark_ticker || payload.benchmark || undefined,
      initial_capital: payload.initial_capital,
      rebalance_frequency: payload.rebalance_frequency,
      in_sample_window_days: payload.in_sample_window_days ?? payload.in_sample_window,
      out_of_sample_step_days: payload.out_of_sample_step_days ?? payload.out_of_sample_step,
      transaction_cost_bps:
        payload.transaction_cost_bps !== undefined
          ? payload.transaction_cost_bps
          : payload.transaction_cost !== undefined
          ? (payload.transaction_cost < 1.0 ? payload.transaction_cost * 10000.0 : payload.transaction_cost)
          : undefined,
      risk_free_rate: payload.risk_free_rate,
      min_weight: payload.min_weight,
      max_weight: payload.max_weight,
    };

    return await apiClient.post<BacktestResponse>(
      `portfolio/${portfolioId}/backtest/`,
      formattedPayload,
      { timeoutMs: 60000 }
    );
  },

  /**
   * POST /api/v1/ai/chat/ with portfolio_id
   * Executes multi-agent portfolio intelligence audit and authoritative live valuation
   */
  async analyzePortfolio(
    portfolioId: string | number,
    message?: string
  ): Promise<PortfolioAiAnalysisResponse> {
    return apiClient.post<PortfolioAiAnalysisResponse>(
      'ai/chat/',
      {
        message: message || 'Perform a comprehensive institutional portfolio diagnostic and risk audit.',
        portfolio_id: String(portfolioId),
      },
      { timeoutMs: 360000 }
    );
  },

  /**
   * GET /api/v1/portfolio/<id>/alerts/
   * Retrieves active, acknowledged, and historic monitoring alerts for a specific portfolio
   */
  async getAlerts(portfolioId: string | number): Promise<Alert[]> {
    const response = await apiClient.get<Alert[] | { results: Alert[] }>(
      `portfolio/${portfolioId}/alerts/`
    );
    if (Array.isArray(response)) {
      return response;
    }
    if (response && Array.isArray((response as any).results)) {
      return (response as any).results;
    }
    return [];
  },

  /**
   * POST /api/v1/portfolio/<id>/monitor/
   * Evaluates deterministic portfolio monitoring conditions on demand and creates unsuppressed alerts
   */
  async runMonitoring(
    portfolioId: string | number,
    payload?: RunMonitoringPayload
  ): Promise<MonitoringResponse> {
    return apiClient.post<MonitoringResponse>(
      `portfolio/${portfolioId}/monitor/`,
      payload || {},
      { timeoutMs: 30000 }
    );
  },

  /**
   * POST /api/v1/portfolio/<id>/alerts/<alert_id>/acknowledge/
   * Idempotently acknowledges an active or existing alert
   */
  async acknowledgeAlert(
    portfolioId: string | number,
    alertId: string | number
  ): Promise<Alert> {
    return apiClient.post<Alert>(
      `portfolio/${portfolioId}/alerts/${alertId}/acknowledge/`,
      {}
    );
  },
};
