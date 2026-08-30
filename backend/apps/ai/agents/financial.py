"""Deterministic agent for company financial analysis."""

import re
from collections.abc import Callable

from apps.ai.agents.base import BaseAgent
from apps.ai.services import research_tools
from apps.ai.services.schemas import AgentResult


ResearchTool = Callable[[str, str], dict[str, object]]


class FinancialAnalysisAgent(BaseAgent):
    """Retrieve and summarize financial statements and key metrics.

    Research callables are injectable so callers and tests can run the agent
    without creating external service clients.
    """

    def __init__(
        self,
        financials_tool: ResearchTool | None = None,
        key_metrics_tool: ResearchTool | None = None,
        ticker: str | None = None,
        market: str = "IN",
    ):
        self.financials_tool = (
            financials_tool or research_tools.get_financials
        )
        self.key_metrics_tool = (
            key_metrics_tool or research_tools.get_key_metrics
        )
        self.ticker = ticker.upper() if ticker else None
        self.market = market.upper()

    @property
    def name(self) -> str:
        return "financial"

    def run(self, message: str) -> AgentResult:
        """Return a local, deterministic summary of financial research data."""
        ticker = self.ticker or self._extract_ticker(message)

        if ticker is None:
            return AgentResult(
                response=(
                    "Please provide a ticker symbol to analyze financials."
                ),
                tools_used=[],
            )

        tools_used: list[str] = []

        try:
            financials = self.financials_tool(
                ticker=ticker,
                market=self.market,
            )
            tools_used.append("get_financials")

            key_metrics = self.key_metrics_tool(
                ticker=ticker,
                market=self.market,
            )
            tools_used.append("get_key_metrics")
        except Exception as exc:
            return AgentResult(
                response=(
                    f"Unable to retrieve financial analysis for {ticker}: {exc}"
                ),
                tools_used=tools_used,
            )

        return AgentResult(
            response=self._build_summary(
                ticker=ticker,
                financials=financials,
                key_metrics=key_metrics,
            ),
            tools_used=tools_used,
        )

    @staticmethod
    def _extract_ticker(message: str) -> str | None:
        """Extract an explicit all-caps ticker without using an LLM."""
        excluded_words = {
            "ANALYZE",
            "FINANCIAL",
            "FINANCIALS",
            "METRICS",
            "REVENUE",
            "PROFIT",
            "EARNINGS",
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
        financials: dict[str, object],
        key_metrics: dict[str, object],
    ) -> str:
        statements = financials.get("financials", [])
        metrics = key_metrics.get("metrics", [])

        statement_count = (
            len(statements) if isinstance(statements, list) else 0
        )
        metric_count = len(metrics) if isinstance(metrics, list) else 0

        return (
            f"Financial analysis for {ticker}: retrieved "
            f"{statement_count} financial statement(s) and "
            f"{metric_count} key metric(s)."
        )
