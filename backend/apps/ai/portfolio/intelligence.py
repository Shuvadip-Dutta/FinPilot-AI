"""Deterministic portfolio valuation using injected market data."""

from collections.abc import Callable

from apps.ai.portfolio.schemas import Portfolio, PortfolioIntelligence


MarketDataTool = Callable[..., dict[str, object]]


class PortfolioMarketDataError(ValueError):
    """Raised when a holding cannot be valued from market data."""


class PortfolioIntelligenceService:
    """Calculate portfolio intelligence without provider or LLM dependencies."""

    def __init__(self, market_data_tool: MarketDataTool):
        self.market_data_tool = market_data_tool

    def analyze(self, portfolio: Portfolio) -> PortfolioIntelligence:
        """Value every holding and return aggregate portfolio performance."""
        invested_value = 0.0
        current_value = 0.0

        for holding in portfolio.holdings:
            invested_value += holding.quantity * holding.average_price
            last_price = self._get_last_price(
                ticker=holding.ticker,
                market=holding.market,
            )
            current_value += holding.quantity * last_price

        profit_loss = current_value - invested_value
        profit_loss_percentage = (
            (profit_loss / invested_value) * 100
            if invested_value
            else 0.0
        )

        return PortfolioIntelligence(
            invested_value=invested_value,
            current_value=current_value,
            profit_loss=profit_loss,
            profit_loss_percentage=profit_loss_percentage,
            holdings_count=len(portfolio.holdings),
        )

    def get_last_prices(self, portfolio: Portfolio) -> dict[str, float]:
        """Fetch current last prices for all holdings in a portfolio."""
        prices: dict[str, float] = {}
        for holding in portfolio.holdings:
            ticker = holding.ticker.strip().upper()
            if ticker not in prices:
                prices[ticker] = self._get_last_price(holding.ticker, holding.market)
        return prices

    def _get_last_price(self, ticker: str, market: str) -> float:
        try:
            market_data = self.market_data_tool(
                ticker=ticker,
                market=market,
            )
        except (ValueError, TypeError) as exc:
            raise PortfolioMarketDataError(
                f"Unable to retrieve market data for {ticker}: {exc}"
            ) from exc

        last_price = market_data.get("last_price")

        if not isinstance(last_price, (int, float)):
            raise PortfolioMarketDataError(
                f"Market data for {ticker} does not include a valid last_price."
            )

        return float(last_price)
