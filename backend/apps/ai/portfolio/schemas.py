"""Typed data contracts for portfolio intelligence."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Holding(BaseModel):
    """A single equity position in a portfolio."""

    ticker: str
    market: Literal["IN", "US"]
    quantity: float = Field(gt=0)
    average_price: float = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def ticker_must_not_be_empty(cls, ticker: str) -> str:
        normalized_ticker = ticker.strip().upper()

        if not normalized_ticker:
            raise ValueError("Ticker must not be empty.")

        return normalized_ticker


class Portfolio(BaseModel):
    """A collection of holdings to evaluate together."""

    holdings: list[Holding]


class CurrencySubtotal(BaseModel):
    """Subtotal metrics for a single currency in a portfolio."""

    invested_value: float
    current_value: float
    profit_loss: float
    profit_loss_percentage: float
    currency: str
    currency_symbol: str
    holdings_count: int


class PortfolioIntelligence(BaseModel):
    """Aggregate valuation and performance for a portfolio."""

    invested_value: float | None = None
    current_value: float | None = None
    profit_loss: float | None = None
    profit_loss_percentage: float | None = None
    holdings_count: int
    currency: str | None = None
    currency_context: str | None = None
    market_currency_context: dict[str, dict[str, str]] | None = None
    currency_totals: dict[str, CurrencySubtotal] | None = None
    is_mixed_currency: bool = False


class PortfolioRiskMetrics(BaseModel):
    """Deterministic quantitative risk analytics for a portfolio."""

    volatility: float
    downside_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float | None = None
    max_drawdown: float
    max_drawdown_duration_days: int
    var_95_historical: float
    cvar_95_historical: float
    annualized_return: float
    cagr: float
    total_period_return: float
    drawdown_series: list[dict[str, Any]] | None = None

