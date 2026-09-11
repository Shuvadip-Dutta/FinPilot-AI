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
} from '../types/portfolio';

export const portfolioApi = {
  /**
   * GET /api/v1/portfolio/
   * Retrieves all user portfolios
   */
  async getPortfolios(params?: { search?: string; page?: number }): Promise<Portfolio[]> {
    const response = await apiClient.get<PortfolioListResponse | Portfolio[]>('portfolio/', {
      params,
    });

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
   * Retrieves details and current valuation metrics for a specific portfolio
   */
  async getPortfolio(id: string | number): Promise<Portfolio> {
    return apiClient.get<Portfolio>(`portfolio/${id}/`);
  },

  /**
   * PUT/PATCH /api/v1/portfolio/<id>/
   * Updates portfolio details (name, description, currency, cash balance)
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
    try {
      return await apiClient.get<PortfolioRiskResponse>(`portfolio/${portfolioId}/risk/`, { params });
    } catch (err: any) {
      // Fallback endpoint if Django registers it as metrics or analytics
      try {
        return await apiClient.get<PortfolioRiskResponse>(`portfolio/${portfolioId}/metrics/`, { params });
      } catch {
        throw err;
      }
    }
  },

  /**
   * POST /api/v1/portfolio/<id>/optimize/
   * Executes mathematical portfolio optimization (Max Sharpe, Min Volatility, etc.)
   */
  async optimizePortfolio(
    portfolioId: string | number,
    payload?: OptimizePortfolioPayload
  ): Promise<PortfolioOptimizationResponse> {
    try {
      return await apiClient.post<PortfolioOptimizationResponse>(`portfolio/${portfolioId}/optimize/`, payload);
    } catch (err: any) {
      try {
        return await apiClient.post<PortfolioOptimizationResponse>(`portfolio/${portfolioId}/optimization/`, payload);
      } catch {
        throw err;
      }
    }
  },

  /**
   * POST /api/v1/portfolio/<id>/backtest/
   * Executes historical walk-forward backtest evaluation vs benchmark
   */
  async runBacktest(
    portfolioId: string | number,
    payload: BacktestPayload
  ): Promise<BacktestResponse> {
    // Harmonize date field aliases for robust backend deserialization
    const formattedPayload: Record<string, any> = {
      ...payload,
      start_date: payload.start_date || payload.from_date,
      end_date: payload.end_date || payload.to_date,
      from_date: payload.from_date || payload.start_date,
      to_date: payload.to_date || payload.end_date,
    };

    return await apiClient.post<BacktestResponse>(
      `portfolio/${portfolioId}/backtest/`,
      formattedPayload
    );
  },
};
