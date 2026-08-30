"""Deterministic routing for FinPilot AI workflows.

This module intentionally contains no model or service dependencies.  A future
router can replace the keyword rules while preserving the ``route`` interface.
"""

from typing import Literal


WorkflowRoute = Literal[
    "financial",
    "market",
    "news",
    "general",
]


class WorkflowRouter:
    """Classify messages using predictable, local keyword rules."""

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

    def route(self, message: str) -> WorkflowRoute:
        """Return the workflow route for ``message`` without calling an LLM."""
        normalized_message = message.casefold()

        if self._contains_keyword(normalized_message, self.NEWS_KEYWORDS):
            return "news"

        if self._contains_keyword(normalized_message, self.MARKET_KEYWORDS):
            return "market"

        if self._contains_keyword(normalized_message, self.FINANCIAL_KEYWORDS):
            return "financial"

        return "general"

    def classify(self, message: str) -> WorkflowRoute:
        """Alias for callers that prefer classification-oriented naming."""
        return self.route(message)

    @staticmethod
    def _contains_keyword(message: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in message for keyword in keywords)
