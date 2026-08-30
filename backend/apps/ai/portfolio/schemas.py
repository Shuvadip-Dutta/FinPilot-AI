"""Typed data contracts for portfolio intelligence."""

from typing import Literal

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


class PortfolioIntelligence(BaseModel):
    """Aggregate valuation and performance for a portfolio."""

    invested_value: float
    current_value: float
    profit_loss: float
    profit_loss_percentage: float
    holdings_count: int
