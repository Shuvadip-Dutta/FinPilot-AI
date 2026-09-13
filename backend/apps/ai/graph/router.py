"""Deterministic routing for FinPilot AI workflows.

This module intentionally contains no model or service dependencies.  A future
router can replace the keyword rules while preserving the ``route`` interface.
"""

from typing import Any, Literal


WorkflowRoute = Literal[
    "financial",
    "market",
    "news",
    "risk",
    "portfolio",
    "general",
]


class WorkflowRouter:
    """Classify messages using predictable, local keyword rules."""

    COMPREHENSIVE_KEYWORDS = (
        "overview",
        "comprehensive",
        "complete research",
        "complete analysis",
        "full analysis",
        "full research",
        "deep dive",
    )
    NEWS_KEYWORDS = (
        "news",
        "headline",
        "headlines",
        "latest update",
        "recent update",
    )
    MARKET_KEYWORDS = (
        "price",
        "stock price",
        "share price",
        "market data",
        "quote",
        "trading at",
    )
    FINANCIAL_KEYWORDS = (
        "financials",
        "revenue",
        "profit",
        "earnings",
        "balance sheet",
        "income statement",
        "cash flow",
        "key metrics",
    )
    RISK_KEYWORDS = (
        "risk",
        "risky",
        "volatility",
        "downside",
        "drawdown",
        "risk assessment",
    )

    BACKTEST_KEYWORDS = (
        "backtest",
        "backtesting",
        "walk forward",
        "walk-forward",
        "historical simulation",
        "historically simulate",
    )

    PORTFOLIO_KEYWORDS = (
        "portfolio",
        "holdings",
        "allocation",
        "portfolio analysis",
        "portfolio optimization",
    ) + BACKTEST_KEYWORDS

    @classmethod
    def is_backtest_intent(cls, message: str) -> bool:
        """Return True if message expresses backtest/historical simulation intent."""
        normalized = message.casefold()
        return cls._contains_keyword(normalized, cls.BACKTEST_KEYWORDS)

    def route(self, message: str) -> WorkflowRoute:
        """Return the workflow route for ``message`` without calling an LLM."""
        normalized_message = message.casefold()

        if self._contains_keyword(normalized_message, self.COMPREHENSIVE_KEYWORDS):
            return "general"

        matching_domains = sum(
            1
            for domain_keywords in (
                self.NEWS_KEYWORDS,
                self.MARKET_KEYWORDS,
                self.FINANCIAL_KEYWORDS,
                self.RISK_KEYWORDS,
                self.PORTFOLIO_KEYWORDS,
            )
            if self._contains_keyword(normalized_message, domain_keywords)
        )

        if matching_domains >= 2:
            return "general"

        if self._contains_keyword(normalized_message, self.NEWS_KEYWORDS):
            return "news"

        if self._contains_keyword(normalized_message, self.MARKET_KEYWORDS):
            return "market"

        if self._contains_keyword(normalized_message, self.FINANCIAL_KEYWORDS):
            return "financial"

        if self._contains_keyword(normalized_message, self.RISK_KEYWORDS):
            return "risk"

        if self._contains_keyword(normalized_message, self.PORTFOLIO_KEYWORDS):
            return "portfolio"

        return "general"

    def classify(self, message: str) -> WorkflowRoute:
        """Alias for callers that prefer classification-oriented naming."""
        return self.route(message)

    def classify_intent(self, message: str) -> dict[str, Any]:
        """Classify route and intent metadata."""
        return {
            "route": self.route(message),
            "is_backtest": self.is_backtest_intent(message),
        }

    @staticmethod
    def _contains_keyword(message: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in message for keyword in keywords)
