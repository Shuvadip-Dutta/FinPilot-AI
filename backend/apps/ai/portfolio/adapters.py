"""Adapters connecting portfolio intelligence services to research data tools."""

from collections.abc import Callable
import math
from typing import Any

from apps.ai.portfolio.intelligence import PortfolioMarketDataError


class ResearchMarketDataAdapter:
    """Adapts raw research market-data responses to the PortfolioIntelligenceService contract."""

    def __init__(
        self,
        get_market_data_fn: Callable[..., dict[str, Any]] | None = None,
    ):
        if get_market_data_fn is None:
            from apps.ai.services.research_tools import get_market_data

            get_market_data_fn = get_market_data
        self.get_market_data_fn = get_market_data_fn

    def __call__(self, ticker: str, market: str = "IN") -> dict[str, float]:
        """Callable entry point satisfying MarketDataTool contract."""
        return self.get_market_data(ticker=ticker, market=market)

    def get_market_data(self, ticker: str, market: str = "IN") -> dict[str, float]:
        """Fetch market data from research capability and format as {'last_price': float}."""
        try:
            raw_data = self.get_market_data_fn(ticker=ticker, market=market)
        except (ValueError, TypeError) as exc:
            raise PortfolioMarketDataError(
                f"Unable to retrieve market data for {ticker}: {exc}"
            ) from exc

        if not isinstance(raw_data, dict):
            raise PortfolioMarketDataError(
                f"Invalid market data response for {ticker}: expected dict, got {type(raw_data).__name__}."
            )

        # Allow top-level last_price if already present (e.g. legacy/mock structures)
        if (
            "last_price" in raw_data
            and isinstance(raw_data["last_price"], (int, float))
            and math.isfinite(raw_data["last_price"])
            and raw_data["last_price"] > 0
        ):
            return {"last_price": float(raw_data["last_price"])}

        quotes = raw_data.get("quotes")
        if not isinstance(quotes, list) or not quotes:
            raise PortfolioMarketDataError(
                f"Market data for {ticker} ({market}) contains no quotes."
            )

        # Filter valid quotes with finite positive prices
        valid_quotes = [
            quote
            for quote in quotes
            if isinstance(quote, dict)
            and isinstance(quote.get("price"), (int, float))
            and math.isfinite(quote["price"])
            and quote["price"] > 0
        ]

        if not valid_quotes:
            raise PortfolioMarketDataError(
                f"Market data for {ticker} ({market}) does not contain a valid positive price."
            )

        selected_quote = self._select_quote(valid_quotes, market=market)
        return {"last_price": float(selected_quote["price"])}

    @staticmethod
    def _select_quote(quotes: list[dict[str, Any]], market: str) -> dict[str, Any]:
        """Deterministically select quote based on market exchange priority."""
        market_upper = market.upper() if market else "IN"

        priority_map = {
            "IN": ["NSE", "BSE"],
            "US": ["NASDAQ", "NYSE", "AMEX"],
        }
        preferred_exchanges = priority_map.get(market_upper, [])

        for exchange in preferred_exchanges:
            for quote in quotes:
                if str(quote.get("exchange", "")).upper() == exchange:
                    return quote

        # Default fallback to first valid quote
        return quotes[0]


def create_portfolio_market_data_adapter(
    get_market_data_fn: Callable[..., dict[str, Any]] | None = None
) -> ResearchMarketDataAdapter:
    """Factory creating a ResearchMarketDataAdapter instance."""
    return ResearchMarketDataAdapter(get_market_data_fn=get_market_data_fn)
