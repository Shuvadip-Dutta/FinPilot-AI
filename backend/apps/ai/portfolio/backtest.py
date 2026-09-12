"""Deterministic walk-forward portfolio backtesting engine."""

import math
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

from apps.ai.portfolio.optimization import OptimizationInput, PortfolioOptimizationEngine


class PortfolioBacktestError(ValueError):
    """Raised when backtesting inputs or calculations fail."""


class RebalanceEvent(BaseModel):
    """Details of a single portfolio rebalancing event."""

    date: str
    portfolio_value_before: float
    portfolio_value_after: float
    target_weights: dict[str, float]
    weights_before: dict[str, float] | None = None
    turnover: float
    transaction_cost: float


from apps.ai.portfolio.schemas import PortfolioRiskMetrics


class RelativeMetrics(BaseModel):
    """Relative performance metrics comparing strategy against benchmark."""

    excess_cagr: float
    total_return_difference: float
    tracking_error: float
    information_ratio: float


class PortfolioBacktestInput(BaseModel):
    """Input configuration and historical data for portfolio backtesting."""

    tickers: list[str]
    historical_prices: dict[str, dict[str, float]]
    initial_capital: float = Field(default=100000.0, gt=0)
    in_sample_window_days: int = Field(default=252, ge=3)
    out_of_sample_step_days: int = Field(default=21, ge=1)
    rebalance_frequency: Literal["monthly", "quarterly", "annually", "periodic"] = "periodic"
    transaction_cost_bps: float = Field(default=10.0, ge=0)
    risk_free_rate: float = 0.0
    min_weight: float = Field(default=0.0, ge=0.0)
    max_weight: float = Field(default=1.0, le=1.0)
    benchmark_ticker: str | None = None
    benchmark_prices: dict[str, float] | None = None
    initial_weights: dict[str, float] | None = None

    @model_validator(mode="after")
    def validate_backtest_input(self) -> "PortfolioBacktestInput":
        if len(self.tickers) < 2:
            raise ValueError("At least two tickers are required for portfolio backtesting.")

        normalized_tickers = [t.strip().upper() for t in self.tickers]
        if len(set(normalized_tickers)) != len(normalized_tickers):
            raise ValueError("Tickers must be unique.")
        self.tickers = normalized_tickers

        if set(self.historical_prices.keys()) != set(self.tickers):
            raise ValueError("Historical prices must be provided for every ticker.")

        for ticker, prices in self.historical_prices.items():
            if not isinstance(prices, dict) or not prices:
                raise ValueError(f"Historical prices for {ticker} must be a non-empty dictionary.")
            for d_str, price in prices.items():
                if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
                    raise ValueError(f"Price for {ticker} on date {d_str} must be positive and finite.")

        if self.benchmark_prices:
            for d_str, price in self.benchmark_prices.items():
                if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
                    raise ValueError(f"Benchmark price on date {d_str} must be positive and finite.")

        if self.min_weight > self.max_weight:
            raise ValueError("min_weight cannot exceed max_weight.")

        return self


class PortfolioBacktestResult(BaseModel):
    """Result structure containing continuous strategy equity curve and rebalance history."""

    success: bool
    message: str
    final_portfolio_value: float | None = None
    total_transaction_costs: float | None = None
    equity_curve: list[dict[str, Any]] | None = None
    drawdown_curve: list[dict[str, Any]] | None = None
    return_series: dict[str, float] | None = None
    rebalance_events: list[RebalanceEvent] | None = None
    strategy_metrics: PortfolioRiskMetrics | None = None
    buy_and_hold_metrics: PortfolioRiskMetrics | None = None
    benchmark_metrics: PortfolioRiskMetrics | None = None
    benchmark_ticker: str | None = None
    relative_metrics: RelativeMetrics | None = None


class PortfolioBacktestEngine:
    """Deterministic walk-forward portfolio backtesting engine."""

    def __init__(self, optimizer_engine: PortfolioOptimizationEngine | None = None):
        self.optimizer_engine = optimizer_engine or PortfolioOptimizationEngine()

    def run(self, input_data: PortfolioBacktestInput) -> PortfolioBacktestResult:
        """Run a deterministic walk-forward backtest across aligned historical price series."""
        tickers = sorted(input_data.tickers)

        # Determine common aligned dates chronologically
        date_sets = [set(input_data.historical_prices[t].keys()) for t in tickers]
        common_dates = set.intersection(*date_sets) if date_sets else set()
        sorted_dates = sorted(list(common_dates))

        w_in = input_data.in_sample_window_days
        k_out = input_data.out_of_sample_step_days

        if len(sorted_dates) < w_in + 1:
            return PortfolioBacktestResult(
                success=False,
                message=f"Insufficient historical observations ({len(sorted_dates)}) for in-sample window ({w_in}) plus test data.",
            )

        rebalance_events: list[RebalanceEvent] = []
        equity_curve: list[dict[str, Any]] = []

        current_value = input_data.initial_capital
        current_shares: dict[str, float] = {}

        rebalance_indices = list(range(w_in - 1, len(sorted_dates), k_out))

        for idx, rebal_idx in enumerate(rebalance_indices):
            rebal_date = sorted_dates[rebal_idx]

            # In-sample window: strictly dates <= rebal_date (length = w_in)
            in_sample_dates = sorted_dates[rebal_idx - w_in + 1 : rebal_idx + 1]

            in_sample_prices = {
                ticker: [input_data.historical_prices[ticker][d] for d in in_sample_dates]
                for ticker in tickers
            }

            # Run optimizer ONLY on in-sample prices
            try:
                opt_input = OptimizationInput(
                    tickers=tickers,
                    historical_prices=in_sample_prices,
                    risk_free_rate=input_data.risk_free_rate,
                    min_weight=input_data.min_weight,
                    max_weight=input_data.max_weight,
                )
                opt_result = self.optimizer_engine.optimize(opt_input)
            except Exception as exc:
                return PortfolioBacktestResult(
                    success=False,
                    message=f"Optimization failed on date {rebal_date}: {exc}",
                )

            if not opt_result.success or not opt_result.optimized_weights:
                return PortfolioBacktestResult(
                    success=False,
                    message=f"Optimizer returned failure on date {rebal_date}: {opt_result.message}",
                )

            target_weights = opt_result.optimized_weights

            # Calculate portfolio value before rebalance
            if idx == 0:
                portfolio_value_before = input_data.initial_capital
                weights_before = None
                turnover = sum(target_weights.values())
            else:
                portfolio_value_before = sum(
                    current_shares[t] * input_data.historical_prices[t][rebal_date]
                    for t in tickers
                )
                weights_before = {
                    t: (current_shares[t] * input_data.historical_prices[t][rebal_date]) / portfolio_value_before
                    for t in tickers
                }
                turnover = sum(abs(target_weights[t] - weights_before[t]) for t in tickers)

            # Deduct transaction costs
            cost_rate = input_data.transaction_cost_bps / 10000.0
            transaction_cost = portfolio_value_before * turnover * cost_rate
            portfolio_value_after = portfolio_value_before - transaction_cost

            # Update share quantities for out-of-sample period
            current_shares = {
                t: (portfolio_value_after * target_weights[t]) / input_data.historical_prices[t][rebal_date]
                for t in tickers
            }

            event = RebalanceEvent(
                date=rebal_date,
                portfolio_value_before=portfolio_value_before,
                portfolio_value_after=portfolio_value_after,
                target_weights=target_weights,
                weights_before=weights_before,
                turnover=turnover,
                transaction_cost=transaction_cost,
            )
            rebalance_events.append(event)

            # Determine out-of-sample date range for equity curve accumulation
            next_rebal_idx = rebalance_indices[idx + 1] if idx + 1 < len(rebalance_indices) else len(sorted_dates)
            oos_dates = sorted_dates[rebal_idx:next_rebal_idx]

            for oos_date in oos_dates:
                if equity_curve and equity_curve[-1]["date"] == oos_date:
                    equity_curve[-1]["portfolio_value"] = portfolio_value_after
                    continue

                daily_val = sum(
                    current_shares[t] * input_data.historical_prices[t][oos_date]
                    for t in tickers
                )
                prev_val = equity_curve[-1]["portfolio_value"] if equity_curve else portfolio_value_after
                daily_return = (daily_val / prev_val) - 1.0 if prev_val > 0 else 0.0

                equity_curve.append({
                    "date": oos_date,
                    "portfolio_value": daily_val,
                    "daily_return": daily_return,
                })

        total_costs = sum(e.transaction_cost for e in rebalance_events)
        final_val = equity_curve[-1]["portfolio_value"] if equity_curve else current_value
        return_series = {item["date"]: item["daily_return"] for item in equity_curve}

        return PortfolioBacktestResult(
            success=True,
            message="Backtest completed successfully.",
            final_portfolio_value=final_val,
            total_transaction_costs=total_costs,
            equity_curve=equity_curve,
            return_series=return_series,
            rebalance_events=rebalance_events,
        )
