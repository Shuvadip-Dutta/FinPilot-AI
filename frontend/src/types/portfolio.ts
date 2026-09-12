/**
 * Portfolio and Holding TypeScript Definitions for FinPilot AI (Phase C)
 * Matches Django REST Framework portfolio API contracts.
 */

export interface Portfolio {
  id: string;
  name: string;
  holdings?: Holding[];
  created_at?: string;
  updated_at?: string;

  // Optional presentation / compatibility fields
  currency?: string | null;
  holdings_count?: number | null;
}

export interface Holding {
  id: string;
  portfolio: string;
  ticker: string;
  market: 'IN' | 'US';
  quantity: string | number; // DRF returns decimal as string e.g. "10.0000"
  average_price: string | number; // DRF returns decimal as string e.g. "2850.0000"
  created_at?: string;
  updated_at?: string;

  // Optional presentation/AI evaluation fields
  invested_value?: number | null;
  current_price?: number | null;
  current_value?: number | null;
  pnl?: number | null;
  pnl_percentage?: number | null;
  weight?: number | null;

  // Optional presentation / compatibility fields
  symbol?: string;
  name?: string;
  company_name?: string;
  allocation?: number | string | null;
  allocation_percentage?: number | string | null;
}

export interface CreatePortfolioPayload {
  name: string;
}

export interface UpdatePortfolioPayload {
  name: string;
}

export interface CreateHoldingPayload {
  ticker: string;
  market: 'IN' | 'US';
  quantity: number | string;
  average_price: number | string;
}

export interface UpdateHoldingPayload {
  ticker?: string;
  market?: 'IN' | 'US';
  quantity?: number | string;
  average_price?: number | string;
}

export interface PortfolioStructuredValuation {
  invested_value: number;
  current_value: number;
  profit_loss: number;
  profit_loss_percentage: number;
  holdings_count: number;
  currency?: string | null;
  currency_context?: string | null;
  market_currency_context?: Record<string, { market: string; currency: string; currency_symbol: string }> | null;
}

export interface PortfolioAiAnalysisResponse {
  response: string;
  tools_used: string[];
  session_id: string | null;
  thread_id: string;
  route: string;
  structured_data?: {
    portfolio?: PortfolioStructuredValuation;
    portfolio_risk?: {
      current_risk?: PortfolioRiskMetrics | Record<string, any>;
      optimized_risk?: PortfolioRiskMetrics | Record<string, any> | null;
      [key: string]: any;
    };
    [key: string]: any;
  };
}

/**
 * ============================================================================
 * Phase D: Portfolio Quantitative Risk & Optimization Types
 * Strictly authoritative from the Django backend.
 * ============================================================================
 */

export interface PortfolioRiskMetrics {
  // Authoritative 12 exact backend fields
  total_period_return?: number | string | null;
  annualized_return?: number | string | null;
  cagr?: number | string | null;
  volatility?: number | string | null;
  downside_volatility?: number | string | null;
  sharpe_ratio?: number | string | null;
  sortino_ratio?: number | string | null;
  calmar_ratio?: number | string | null;
  max_drawdown?: number | string | null;
  max_drawdown_duration_days?: number | string | null;
  var_95_historical?: number | string | null;
  cvar_95_historical?: number | string | null;

  // Compatibility aliases
  annualized_volatility?: number | string | null;
  downside_deviation?: number | string | null;
  maximum_drawdown?: number | string | null;
  drawdown_duration?: number | string | null;
  drawdown_duration_days?: number | string | null;
  var_95?: number | string | null;
  var_95_percent?: number | string | null;
  cvar_95?: number | string | null;
  cvar_95_percent?: number | string | null;
  beta?: number | string | null;
  alpha?: number | string | null;
  r_squared?: number | string | null;
  information_ratio?: number | string | null;
  tracking_error?: number | string | null;
  risk_free_rate?: number | string | null;
  benchmark_ticker?: string | null;
  benchmark_name?: string | null;
  calculation_period?: string | null;
  data_points?: number | null;
}

export interface DrawdownSeriesPoint {
  date: string;
  portfolio_return?: number | null;
  cumulative_return?: number | null;
  drawdown?: number | null;
  drawdown_percent?: number | null;
  high_water_mark?: number | null;
  benchmark_cumulative_return?: number | null;
}

export interface AssetRiskContribution {
  ticker: string;
  symbol?: string;
  name?: string;
  weight: number | string;
  volatility?: number | string | null;
  marginal_contribution?: number | string | null;
  percentage_contribution?: number | string | null;
  beta?: number | string | null;
}

export interface PortfolioRiskResponse {
  portfolio_id?: string | number;
  portfolio_name?: string;
  as_of_date?: string;
  market?: string;
  data_points?: number;
  period?: string;
  benchmark?: string;
  risk_metrics?: PortfolioRiskMetrics;
  metrics?: PortfolioRiskMetrics;
  drawdown_series?: DrawdownSeriesPoint[];
  historical_series?: DrawdownSeriesPoint[];
  risk_contributions?: AssetRiskContribution[];

  // Authoritative 12 exact backend fields (flat top-level)
  total_period_return?: number | string | null;
  annualized_return?: number | string | null;
  cagr?: number | string | null;
  volatility?: number | string | null;
  downside_volatility?: number | string | null;
  sharpe_ratio?: number | string | null;
  sortino_ratio?: number | string | null;
  calmar_ratio?: number | string | null;
  max_drawdown?: number | string | null;
  max_drawdown_duration_days?: number | string | null;
  var_95_historical?: number | string | null;
  cvar_95_historical?: number | string | null;

  // Compatibility aliases
  drawdown_duration?: number | string | null;
  var_95?: number | string | null;
  cvar_95?: number | string | null;
  beta?: number | string | null;
}

export interface OptimizePortfolioPayload {
  /**
   * The backend deterministic engine currently exclusively implements Sharpe ratio maximization
   * subject to bounded simplex constraints. Other objectives are not supported.
   */
  objective?: 'max_sharpe';
  risk_free_rate?: number;
  max_weight?: number;
  min_weight?: number;
  allow_short?: boolean;
  benchmark?: string;
  from_date?: string | null;
  to_date?: string | null;
}

export interface OptimizedAssetWeight {
  ticker: string;
  symbol?: string;
  name?: string;
  current_weight: number | string;
  target_weight: number | string;
  optimized_weight?: number | string;
  weight_difference: number | string;
  delta?: number | string;
  current_value?: number | string | null;
  target_value?: number | string | null;
  direction?: 'increase' | 'decrease' | 'hold' | 'exit' | 'enter';
}

export interface OptimizationMetrics {
  current_expected_return?: number | string | null;
  optimized_expected_return?: number | string | null;
  current_volatility?: number | string | null;
  optimized_volatility?: number | string | null;
  current_sharpe?: number | string | null;
  optimized_sharpe?: number | string | null;
  expected_return?: number | string | null;
  volatility?: number | string | null;
  sharpe_ratio?: number | string | null;
  turnover?: number | string | null;
  diversification_ratio?: number | string | null;
}

export interface PortfolioOptimizationResponse {
  portfolio_id?: string | number;
  portfolio_name?: string;
  timestamp?: string;
  objective?: 'max_sharpe' | 'min_volatility' | 'target_return' | 'risk_parity' | string;
  status?: string;
  weights?: Record<string, number>;
  optimized_weights?: Record<string, number>;
  target_weights?: Record<string, number>;
  current_weights?: Record<string, number>;
  weight_comparisons?: OptimizedAssetWeight[];
  comparisons?: OptimizedAssetWeight[];
  metrics?: OptimizationMetrics;
  optimization_metrics?: OptimizationMetrics;
  current_metrics?: {
    expected_return?: number | string | null;
    volatility?: number | string | null;
    sharpe_ratio?: number | string | null;
  };
  optimized_metrics?: {
    expected_return?: number | string | null;
    volatility?: number | string | null;
    sharpe_ratio?: number | string | null;
  };
  methodology?: {
    optimizer_type?: string;
    covariance_estimator?: string;
    historical_window?: string;
    constraints?: Record<string, unknown>;
  };
}

export interface AllocationItem {
  name: string;
  ticker?: string;
  percentage?: number | string | null;
  weight?: number | string | null;
  value?: number | string | null;
  color?: string;
}

export interface PortfolioListResponse {
  count?: number;
  next?: string | null;
  previous?: string | null;
  results?: Portfolio[];
}

export interface HoldingsListResponse {
  count?: number;
  next?: string | null;
  previous?: string | null;
  results?: Holding[];
}

/**
 * Accessor helpers to safely read backend-computed metrics without recalculating
 */
export function getPortfolioInvestedValue(p: Portfolio | null | undefined): number | null {
  if (!p || !p.holdings || p.holdings.length === 0) return null;
  let total = 0;
  for (const h of p.holdings) {
    const inv = getHoldingInvestedValue(h);
    if (inv !== null) {
      total += inv;
    }
  }
  return total;
}

export function getPortfolioCurrentValue(p: Portfolio | null | undefined): number | null {
  // Current value is authoritatively returned by AI analysis or per-holding quote; return null if not computed
  if (!p) return null;
  return null;
}

export function getPortfolioPnL(p: Portfolio | null | undefined): number | null {
  if (!p) return null;
  return null;
}

export function getPortfolioPnLPercent(p: Portfolio | null | undefined): number | null {
  if (!p) return null;
  return null;
}

export function getPortfolioCashBalance(p: Portfolio | null | undefined): number | null {
  if (!p) return null;
  return null;
}

export function getHoldingInvestedValue(h: Holding | null | undefined): number | null {
  if (!h) return null;
  if (h.invested_value !== undefined && h.invested_value !== null) {
    const n = typeof h.invested_value === 'string' ? parseFloat(h.invested_value) : h.invested_value;
    return isNaN(n) ? null : n;
  }
  const qty = typeof h.quantity === 'string' ? parseFloat(h.quantity) : h.quantity;
  const price = typeof h.average_price === 'string' ? parseFloat(h.average_price) : h.average_price;
  if (qty !== undefined && qty !== null && !isNaN(qty) && price !== undefined && price !== null && !isNaN(price)) {
    return qty * price;
  }
  return null;
}

export function getHoldingCurrentValue(h: Holding | null | undefined): number | null {
  if (!h || h.current_value === undefined || h.current_value === null) return null;
  const n = typeof h.current_value === 'string' ? parseFloat(h.current_value) : h.current_value;
  return isNaN(n) ? null : n;
}

export function getHoldingCurrentPrice(h: Holding | null | undefined): number | null {
  if (!h || h.current_price === undefined || h.current_price === null) return null;
  const n = typeof h.current_price === 'string' ? parseFloat(h.current_price) : h.current_price;
  return isNaN(n) ? null : n;
}

export function getHoldingPnL(h: Holding | null | undefined): number | null {
  if (!h || h.pnl === undefined || h.pnl === null) return null;
  const n = typeof h.pnl === 'string' ? parseFloat(h.pnl) : h.pnl;
  return isNaN(n) ? null : n;
}

export function getHoldingPnLPercent(h: Holding | null | undefined): number | null {
  if (!h || h.pnl_percentage === undefined || h.pnl_percentage === null) return null;
  const n = typeof h.pnl_percentage === 'string' ? parseFloat(h.pnl_percentage) : h.pnl_percentage;
  return isNaN(n) ? null : n;
}

export function getHoldingAllocation(h: Holding | null | undefined): number | null {
  if (!h || h.weight === undefined || h.weight === null) return null;
  const n = typeof h.weight === 'string' ? parseFloat(h.weight) : h.weight;
  return isNaN(n) ? null : n;
}

/**
 * ============================================================================
 * Safe Accessors for Quantitative Risk Metrics (strictly authoritative from backend)
 * ============================================================================
 */

function parseNum(val: unknown): number | null {
  if (val === null || val === undefined || val === '') return null;
  const n = typeof val === 'string' ? parseFloat(val) : typeof val === 'number' ? val : null;
  return n !== null && !isNaN(n) ? n : null;
}

export function getRiskMetrics(
  response: PortfolioRiskResponse | null | undefined
): PortfolioRiskMetrics | null {
  if (!response) return null;
  return response.risk_metrics ?? response.metrics ?? response;
}

export function getRiskTotalPeriodReturn(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.total_period_return);
}

export function getRiskAnnualizedReturn(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.annualized_return);
}

export function getRiskVolatility(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.volatility ?? (metrics as any)?.annualized_volatility);
}

export function getRiskDownsideVolatility(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.downside_volatility ?? (metrics as any)?.downside_deviation);
}

export function getRiskSharpeRatio(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.sharpe_ratio);
}

export function getRiskSortinoRatio(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.sortino_ratio);
}

export function getRiskCalmarRatio(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.calmar_ratio);
}

export function getRiskMaxDrawdown(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.max_drawdown ?? (metrics as any)?.maximum_drawdown);
}

export function getRiskDrawdownDuration(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.max_drawdown_duration_days ?? metrics?.drawdown_duration ?? (metrics as any)?.drawdown_duration_days);
}

export function getRiskVaR95(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.var_95_historical ?? metrics?.var_95 ?? (metrics as any)?.var_95_percent);
}

export function getRiskCVaR95(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.cvar_95_historical ?? metrics?.cvar_95 ?? (metrics as any)?.cvar_95_percent);
}

export function getRiskCAGR(
  response: PortfolioRiskResponse | PortfolioRiskMetrics | null | undefined
): number | null {
  if (!response) return null;
  const metrics = 'risk_metrics' in response ? response.risk_metrics ?? response.metrics ?? response : response;
  return parseNum(metrics?.cagr);
}

/**
 * ============================================================================
 * Safe Accessors for Optimization Metrics (strictly authoritative from backend)
 * ============================================================================
 */

export function getOptMetrics(
  response: PortfolioOptimizationResponse | null | undefined
): OptimizationMetrics | null {
  if (!response) return null;
  return response.optimization_metrics ?? response.metrics ?? null;
}

export function getOptExpectedReturn(
  response: PortfolioOptimizationResponse | null | undefined
): number | null {
  if (!response) return null;
  const m = response.optimization_metrics ?? response.metrics;
  return parseNum(
    m?.optimized_expected_return ??
    response.optimized_metrics?.expected_return ??
    m?.expected_return
  );
}

export function getOptVolatility(
  response: PortfolioOptimizationResponse | null | undefined
): number | null {
  if (!response) return null;
  const m = response.optimization_metrics ?? response.metrics;
  return parseNum(
    m?.optimized_volatility ??
    response.optimized_metrics?.volatility ??
    m?.volatility
  );
}

export function getOptSharpe(
  response: PortfolioOptimizationResponse | null | undefined
): number | null {
  if (!response) return null;
  const m = response.optimization_metrics ?? response.metrics;
  return parseNum(
    m?.optimized_sharpe ??
    response.optimized_metrics?.sharpe_ratio ??
    m?.sharpe_ratio
  );
}

export function getOptCurrentExpectedReturn(
  response: PortfolioOptimizationResponse | null | undefined
): number | null {
  if (!response) return null;
  const m = response.optimization_metrics ?? response.metrics;
  return parseNum(
    m?.current_expected_return ??
    response.current_metrics?.expected_return
  );
}

export function getOptCurrentVolatility(
  response: PortfolioOptimizationResponse | null | undefined
): number | null {
  if (!response) return null;
  const m = response.optimization_metrics ?? response.metrics;
  return parseNum(
    m?.current_volatility ??
    response.current_metrics?.volatility
  );
}

export function getOptCurrentSharpe(
  response: PortfolioOptimizationResponse | null | undefined
): number | null {
  if (!response) return null;
  const m = response.optimization_metrics ?? response.metrics;
  return parseNum(
    m?.current_sharpe ??
    response.current_metrics?.sharpe_ratio
  );
}

// ============================================================================
// PHASE E — WALK-FORWARD BACKTEST INTERFACES & SAFE ACCESSORS
// ============================================================================

export type RebalanceFrequency =
  | 'monthly'
  | 'quarterly'
  | 'semi-annually'
  | 'annually'
  | 'weekly'
  | 'M'
  | 'Q'
  | 'Y';

export interface BacktestPayload {
  start_date?: string;
  end_date?: string;
  from_date?: string;
  to_date?: string;
  benchmark?: string;
  initial_capital?: number;
  rebalance_frequency?: RebalanceFrequency | string;
  in_sample_window?: number; // trading days or periods
  out_of_sample_step?: number; // trading days or periods
  transaction_cost?: number; // decimal e.g. 0.001 for 10bps
  risk_free_rate?: number; // decimal e.g. 0.065
  min_weight?: number; // 0.0
  max_weight?: number; // 0.35
}

export interface BacktestMetricsGroup {
  cagr?: number | string | null;
  annualized_return?: number | string | null;
  total_return?: number | string | null;
  sharpe_ratio?: number | string | null;
  sortino_ratio?: number | string | null;
  calmar_ratio?: number | string | null;
  max_drawdown?: number | string | null;
  drawdown_duration?: number | string | null;
  volatility?: number | string | null;
  annualized_volatility?: number | string | null;
  final_value?: number | string | null;
  final_portfolio_value?: number | string | null;
  total_transaction_costs?: number | string | null;
  total_turnover?: number | string | null;
  win_rate?: number | string | null;
  rebalance_count?: number | string | null;
  trades_count?: number | string | null;
}

export interface BacktestRelativeMetrics {
  information_ratio?: number | string | null;
  tracking_error?: number | string | null;
  alpha?: number | string | null;
  beta?: number | string | null;
  excess_return?: number | string | null;
  up_capture?: number | string | null;
  down_capture?: number | string | null;
}

export interface EquityCurvePoint {
  date: string;
  strategy?: number | string | null;
  strategy_value?: number | string | null;
  buy_and_hold?: number | string | null;
  buy_and_hold_value?: number | string | null;
  benchmark?: number | string | null;
  benchmark_value?: number | string | null;
  strategy_drawdown?: number | string | null;
  benchmark_drawdown?: number | string | null;
  buy_and_hold_drawdown?: number | string | null;
}

export interface RebalanceEventDetail {
  ticker: string;
  prev_weight?: number | string | null;
  target_weight?: number | string | null;
  delta?: number | string | null;
}

export interface RebalanceEvent {
  date?: string;
  rebalance_date?: string;
  turnover?: number | string | null;
  transaction_cost?: number | string | null;
  cost?: number | string | null;
  previous_allocation?: Record<string, number | string>;
  prev_weights?: Record<string, number | string>;
  target_allocation?: Record<string, number | string>;
  target_weights?: Record<string, number | string>;
  new_weights?: Record<string, number | string>;
  weights?: Record<string, number | string>;
  details?: RebalanceEventDetail[];
}

export interface BacktestResponse {
  portfolio_id?: string | number;
  initial_capital?: number | string;
  final_value?: number | string;
  final_portfolio_value?: number | string;
  total_transaction_costs?: number | string;
  total_turnover?: number | string;
  start_date?: string;
  end_date?: string;
  benchmark?: string;
  execution_mode?: 'deterministic' | 'langgraph' | string;

  strategy_metrics?: BacktestMetricsGroup;
  buy_and_hold_metrics?: BacktestMetricsGroup;
  benchmark_metrics?: BacktestMetricsGroup;
  relative_metrics?: BacktestRelativeMetrics;

  equity_curve?: EquityCurvePoint[];
  drawdown_curve?: Array<{
    date: string;
    strategy_drawdown: number | string;
    benchmark_drawdown?: number | string;
    buy_and_hold_drawdown?: number | string;
  }>;
  return_series?: Array<{
    date: string;
    strategy_return?: number | string;
    benchmark_return?: number | string;
    buy_and_hold_return?: number | string;
  }>;
  rebalance_events?: RebalanceEvent[];
  status?: string;
  message?: string;
}

// ----------------------------------------------------------------------------
// SAFE ACCESSORS FOR BACKTEST
// ----------------------------------------------------------------------------

export function getBacktestStrategyMetrics(
  response: BacktestResponse | null | undefined
): BacktestMetricsGroup | null {
  if (!response) return null;
  return response.strategy_metrics || null;
}

export function getBacktestBuyAndHoldMetrics(
  response: BacktestResponse | null | undefined
): BacktestMetricsGroup | null {
  if (!response) return null;
  return response.buy_and_hold_metrics || null;
}

export function getBacktestBenchmarkMetrics(
  response: BacktestResponse | null | undefined
): BacktestMetricsGroup | null {
  if (!response) return null;
  return response.benchmark_metrics || null;
}

export function getBacktestRelativeMetrics(
  response: BacktestResponse | null | undefined
): BacktestRelativeMetrics | null {
  if (!response) return null;
  return response.relative_metrics || null;
}

export function getBacktestFinalValue(
  response: BacktestResponse | null | undefined
): number | null {
  if (!response) return null;
  return parseNum(
    response.final_value ??
    response.final_portfolio_value ??
    response.strategy_metrics?.final_value ??
    response.strategy_metrics?.final_portfolio_value
  );
}

export function getBacktestTotalCosts(
  response: BacktestResponse | null | undefined
): number | null {
  if (!response) return null;
  return parseNum(
    response.total_transaction_costs ??
    response.strategy_metrics?.total_transaction_costs
  );
}

export function getBacktestTotalTurnover(
  response: BacktestResponse | null | undefined
): number | null {
  if (!response) return null;
  return parseNum(
    response.total_turnover ??
    response.strategy_metrics?.total_turnover
  );
}

export function getBacktestCAGR(
  metrics: BacktestMetricsGroup | null | undefined
): number | null {
  if (!metrics) return null;
  return parseNum(metrics.cagr ?? metrics.annualized_return);
}

export function getBacktestSharpe(
  metrics: BacktestMetricsGroup | null | undefined
): number | null {
  if (!metrics) return null;
  return parseNum(metrics.sharpe_ratio);
}

export function getBacktestMaxDrawdown(
  metrics: BacktestMetricsGroup | null | undefined
): number | null {
  if (!metrics) return null;
  return parseNum(metrics.max_drawdown);
}

export function getBacktestTotalReturn(
  metrics: BacktestMetricsGroup | null | undefined
): number | null {
  if (!metrics) return null;
  return parseNum(metrics.total_return);
}

export function getBacktestVolatility(
  metrics: BacktestMetricsGroup | null | undefined
): number | null {
  if (!metrics) return null;
  return parseNum(metrics.volatility ?? metrics.annualized_volatility);
}

export function getBacktestEquityCurve(
  response: BacktestResponse | null | undefined
): Array<{
  date: string;
  strategy: number | null;
  buy_and_hold: number | null;
  benchmark: number | null;
}> {
  if (!response || !Array.isArray(response.equity_curve)) return [];
  return response.equity_curve.map((pt) => ({
    date: pt.date,
    strategy: parseNum(pt.strategy ?? pt.strategy_value),
    buy_and_hold: parseNum(pt.buy_and_hold ?? pt.buy_and_hold_value),
    benchmark: parseNum(pt.benchmark ?? pt.benchmark_value),
  }));
}

export function getBacktestDrawdownCurve(
  response: BacktestResponse | null | undefined
): Array<{
  date: string;
  strategy_drawdown: number | null;
  benchmark_drawdown: number | null;
}> {
  if (!response) return [];
  if (Array.isArray(response.drawdown_curve) && response.drawdown_curve.length > 0) {
    return response.drawdown_curve.map((pt) => ({
      date: pt.date,
      strategy_drawdown: parseNum(pt.strategy_drawdown),
      benchmark_drawdown: parseNum(pt.benchmark_drawdown),
    }));
  }
  // Check if equity_curve includes drawdown fields
  if (Array.isArray(response.equity_curve) && response.equity_curve.length > 0) {
    const hasDrawdown = response.equity_curve.some(
      (p) => p.strategy_drawdown !== undefined || p.benchmark_drawdown !== undefined
    );
    if (hasDrawdown) {
      return response.equity_curve.map((pt) => ({
        date: pt.date,
        strategy_drawdown: parseNum(pt.strategy_drawdown),
        benchmark_drawdown: parseNum(pt.benchmark_drawdown),
      }));
    }
  }
  return [];
}

export function getBacktestRebalanceEvents(
  response: BacktestResponse | null | undefined
): RebalanceEvent[] {
  if (!response || !Array.isArray(response.rebalance_events)) return [];
  return response.rebalance_events;
}


