"""Deterministic agent for current and historical market analysis."""

import json
import re
from collections.abc import Callable

from apps.ai.agents.base import BaseAgent
from apps.ai.exceptions import LLMError
from apps.ai.services import research_tools
from apps.ai.services.llm_service import LLMService
from apps.ai.services.schemas import AgentResult
from apps.ai.services.token_budget import (
    DegradationTier,
    get_default_token_budget_manager,
)


ResearchTool = Callable[..., dict[str, object]]
LLMCallable = Callable[[list[dict[str, str]]], str]


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
        llm_service: LLMCallable | None = None,
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
        self.llm_service = llm_service or LLMService(model="market")

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

        tier = self._get_degradation_tier()

        evidence = {
            "ticker": ticker,
            "market": self.market,
        }
        if self._has_usable_quotes(market_data):
            evidence["market_data"] = market_data
        if historical_data is not None:
            evidence["historical_data"] = historical_data

        if tier == DegradationTier.EXHAUSTED:
            summary = self._build_summary(ticker, market_data, historical_data)
            return AgentResult(
                response=summary,
                tools_used=tools_used,
                data=evidence,
            )

        effective_historical_data = self._apply_historical_degradation(
            historical_data, tier
        )

        messages = self._build_analysis_messages(
            message=message,
            ticker=ticker,
            market_data=market_data,
            historical_data=effective_historical_data,
        )

        max_completion_tokens = self._get_max_completion_tokens_for_tier(tier)

        try:
            response = self._call_llm(
                messages, max_completion_tokens=max_completion_tokens
            )
        except LLMError:
            raise

        if not isinstance(response, str) or not response.strip():
            return AgentResult(
                response=(
                    f"Unable to analyze market data for {ticker}: "
                    "the fast model returned an empty response."
                ),
                tools_used=tools_used,
            )

        return AgentResult(
            response=response.strip(),
            tools_used=tools_used,
            data=evidence,
        )

    def _get_degradation_tier(self) -> DegradationTier:
        manager = getattr(self.llm_service, "token_budget_manager", None)
        if manager is None and hasattr(self.llm_service, "__self__"):
            manager = getattr(
                self.llm_service.__self__, "token_budget_manager", None
            )

        if manager is not None and hasattr(manager, "get_degradation_tier"):
            return manager.get_degradation_tier()

        return get_default_token_budget_manager().get_degradation_tier()

    @staticmethod
    def _apply_historical_degradation(
        historical_data: dict[str, object] | None,
        tier: DegradationTier,
    ) -> dict[str, object] | None:
        if not isinstance(historical_data, dict) or not historical_data:
            return historical_data

        candles = historical_data.get("candles")
        if not isinstance(candles, list) or not candles:
            return historical_data

        if tier == DegradationTier.CONSTRAINED:
            limit = 15
        elif tier == DegradationTier.CRITICAL:
            limit = 5
        else:
            return historical_data

        if len(candles) <= limit:
            return historical_data

        return {
            **historical_data,
            "candles": candles[-limit:],
        }

    @staticmethod
    def _get_max_completion_tokens_for_tier(tier: DegradationTier) -> int | None:
        if tier == DegradationTier.CONSTRAINED:
            return 512
        if tier == DegradationTier.CRITICAL:
            return 256
        return None

    def _call_llm(
        self,
        messages: list[dict[str, str]],
        max_completion_tokens: int | None = None,
    ) -> str:
        if isinstance(self.llm_service, LLMService):
            return self.llm_service.generate(
                messages, max_completion_tokens=max_completion_tokens
            )

        if max_completion_tokens is not None:
            try:
                return self.llm_service(
                    messages, max_completion_tokens=max_completion_tokens
                )
            except TypeError:
                pass

        return self.llm_service(messages)

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
    def _build_analysis_messages(
        message: str,
        ticker: str,
        market_data: dict[str, object],
        historical_data: dict[str, object] | None,
    ) -> list[dict[str, str]]:
        system_prompt = (
            "You are the market analysis specialist for FinPilot AI. "
            "Use only the current and historical market information supplied in this prompt. "
            "Summarize the supplied current market information without inventing values. "
            "Multiple exchange quotes may exist for the same ticker. Preserve exchange identity, "
            "report exchange-specific prices when they differ, and do not merge them into one "
            "universal price or average them unless explicitly requested and mathematically appropriate. "
            "Describe observable historical movement when historical data exists. "
            "Identify simple trends or direction only when supported by the data. "
            "Call out meaningful price ranges or volatility observations when supported. "
            "Compare relevant supplied values only when they are in the provided data. "
            "Distinguish factual observations from interpretation. Explicitly state when "
            "historical or current data is unavailable. Never invent prices, dates, candles, "
            "volume, or other market values. Never make unsupported predictions or guarantee returns. "
            "Never provide a buy/sell recommendation merely from the supplied data."
        )

        context = {
            "user_question": message,
            "ticker": ticker,
            "current_market_data": (
                market_data
                if MarketAnalysisAgent._has_usable_quotes(market_data)
                else "Current market data is unavailable."
            ),
            "historical_market_data": (
                historical_data
                if isinstance(historical_data, dict)
                and historical_data
                and (
                    not isinstance(historical_data.get("candles"), list)
                    or bool(historical_data.get("candles"))
                )
                else "Historical data unavailable."
            ),
        }

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    context,
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ]

    @staticmethod
    def _has_usable_quotes(market_data: object) -> bool:
        if not isinstance(market_data, dict):
            return False

        quotes = market_data.get("quotes")
        return isinstance(quotes, list) and any(
            isinstance(quote, dict)
            and quote.get("exchange")
            and quote.get("price") is not None
            for quote in quotes
        )

    @staticmethod
    def _build_summary(
        ticker: str,
        market_data: dict[str, object],
        historical_data: dict[str, object] | None,
    ) -> str:
        quotes = market_data.get("quotes", [])
        exchange_prices = [
            f"{quote.get('exchange')}: {quote.get('price')}"
            for quote in quotes
            if isinstance(quote, dict)
        ]
        response = (
            f"Market analysis for {ticker}: exchange prices "
            f"{', '.join(exchange_prices) or 'unavailable'}."
        )

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
