"""Deterministic routing for FinPilot AI workflows.

This module intentionally contains no model or service dependencies.  A future
router can replace the keyword rules while preserving the ``route`` interface.
"""

from typing import Literal


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

    PORTFOLIO_KEYWORDS = (
        "portfolio",
        "holdings",
        "allocation",
        "portfolio analysis",
        "portfolio optimization",
    )

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

    @staticmethod
    def _contains_keyword(message: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in message for keyword in keywords)
