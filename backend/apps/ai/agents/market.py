"""Deterministic agent for current and historical market analysis."""

import re
from collections.abc import Callable

from apps.ai.agents.base import BaseAgent
from apps.ai.services import research_tools
from apps.ai.services.schemas import AgentResult


ResearchTool = Callable[..., dict[str, object]]


class MarketAnalysisAgent(BaseAgent):
    """Retrieve current prices and optional historical candle data."""

    def __init__(
        self,
        market_data_tool: ResearchTool | None = None,
        historical_data_tool: ResearchTool | None = None,
        ticker: str | None = None,
        market: str = "IN",
        to_date: str | None = None,
        from_date: str | None = None,
    ):
        self.market_data_tool = (
            market_data_tool or research_tools.get_market_data
        )
        self.historical_data_tool = (
            historical_data_tool or research_tools.get_historical_data
        )
        self.ticker = ticker.upper() if ticker else None
        self.market = market.upper()
        self.to_date = to_date
        self.from_date = from_date

    @property
    def name(self) -> str:
        return "market"

    def run(self, message: str) -> AgentResult:
        """Return a deterministic summary based on market research payloads."""
        ticker = self.ticker or self._extract_ticker(message)

        if ticker is None:
            return AgentResult(
                response="Please provide a ticker symbol to analyze market data.",
                tools_used=[],
            )

        tools_used: list[str] = []

        try:
            market_data = self.market_data_tool(
                ticker=ticker,
                market=self.market,
            )
            tools_used.append("get_market_data")

            to_date, from_date = self._resolve_date_range(message)
            historical_data: dict[str, object] | None = None

            if to_date:
                historical_data = self.historical_data_tool(
                    ticker=ticker,
                    to_date=to_date,
                    from_date=from_date,
                    market=self.market,
                )
                tools_used.append("get_historical_data")
        except (ValueError, TypeError) as exc:
            return AgentResult(
                response=(
                    f"Unable to retrieve market analysis for {ticker}: {exc}"
                ),
                tools_used=tools_used,
            )

        return AgentResult(
            response=self._build_summary(
                ticker=ticker,
                market_data=market_data,
                historical_data=historical_data,
            ),
            tools_used=tools_used,
        )

    def _resolve_date_range(self, message: str) -> tuple[str | None, str | None]:
        if self.to_date:
            return self.to_date, self.from_date

        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", message)

        if len(dates) >= 2:
            return dates[1], dates[0]

        if len(dates) == 1:
            return dates[0], None

        return None, None

    @staticmethod
    def _extract_ticker(message: str) -> str | None:
        excluded_words = {
            "ANALYZE",
            "MARKET",
            "PRICE",
            "CURRENT",
            "HISTORICAL",
            "SHOW",
            "WHAT",
        }

        for candidate in re.findall(r"\b[A-Z]{2,10}\b", message):
            if candidate not in excluded_words:
                return candidate

        return None

    @staticmethod
    def _build_summary(
        ticker: str,
        market_data: dict[str, object],
        historical_data: dict[str, object] | None,
    ) -> str:
        current_price = market_data.get("last_price")
        response = f"Market analysis for {ticker}: current price {current_price}."

        if historical_data is None:
            return response

        candles = historical_data.get("candles", [])
        candle_count = len(candles) if isinstance(candles, list) else 0
        latest_close = None

        if candles and isinstance(candles[-1], dict):
            latest_close = candles[-1].get("close")

        return (
            f"{response} Historical data: {candle_count} candle(s), "
            f"latest close {latest_close}."
        )
