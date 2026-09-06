"""Contracts for portfolio-oriented LangGraph workflows."""

from pydantic import BaseModel, Field

from apps.ai.portfolio.optimization import OptimizationInput
from apps.ai.portfolio.schemas import Portfolio


class PortfolioWorkflowInput(BaseModel):
    """Validated inputs supplied to a portfolio LangGraph workflow."""

    portfolio: Portfolio
    optimization_input: OptimizationInput | None = None
    historical_prices: dict[str, list[float]] | None = None

    django_portfolio_id: str | None = None
    """Primary key of the Django Portfolio ORM object that owns this workflow.
    Required by the backtest node to resolve the persisted portfolio via
    Django ORM (Portfolio.objects.get).  Not used by any other node."""

    # ---------------------------------------------------------------------------
    # Optional backtest configuration
    # ---------------------------------------------------------------------------
    include_backtest: bool = False
    """When True the portfolio_backtest node runs the deterministic backtest pipeline."""

    backtest_from_date: str | None = None
    """ISO-8601 start date for the backtest window, e.g. '2024-01-01'."""

    backtest_to_date: str | None = None
    """ISO-8601 end date for the backtest window, e.g. '2025-06-01'."""

    backtest_benchmark_ticker: str | None = None
    """Optional benchmark index ticker, e.g. 'NIFTY 50'."""

    backtest_initial_capital: float = Field(default=100_000.0, gt=0)
    """Starting capital in base currency units."""

    backtest_rebalance_frequency: str = "monthly"
    """Rebalance cadence: 'monthly' | 'quarterly' | 'annually' | 'periodic'."""

    backtest_in_sample_window_days: int = Field(default=252, ge=3)
    """Number of trading days in the rolling in-sample optimisation window."""

    backtest_out_of_sample_step_days: int = Field(default=21, ge=1)
    """Number of out-of-sample days between consecutive rebalance events."""

    backtest_transaction_cost_bps: float = Field(default=10.0, ge=0)
    """Round-trip transaction cost in basis points applied at each rebalance."""

    backtest_risk_free_rate: float = 0.0
    """Annual risk-free rate used for Sharpe / Sortino calculation."""

    backtest_min_weight: float = Field(default=0.0, ge=0.0)
    """Minimum portfolio weight per asset."""

    backtest_max_weight: float = Field(default=1.0, le=1.0)
    """Maximum portfolio weight per asset."""