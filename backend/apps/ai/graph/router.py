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

    VALUATION_KEYWORDS = (
        "premium to historical averages",
        "premium to historical average",
        "discount to historical averages",
        "discount to historical average",
        "trading at a premium",
        "trading at a discount",
        "historical valuations",
        "historical valuation",
        "enterprise value / ebitda",
        "enterprise value/ebitda",
        "valuation multiples",
        "valuation multiple",
        "price-to-earnings",
        "price to earnings",
        "price-to-book",
        "price to book",
        "trailing p/e",
        "forward p/e",
        "price book",
        "pe ratio",
        "p/e ratio",
        "pb ratio",
        "p/b ratio",
        "ev/ebitda",
        "valuations",
        "valuation",
        "p/e",
        "p/b",
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

        has_valuation = self._contains_keyword(normalized_message, self.VALUATION_KEYWORDS)
        has_financial = self._contains_keyword(normalized_message, self.FINANCIAL_KEYWORDS) or has_valuation

        # Avoid market keyword false positives for valuation phrases such as "price-to-book" or "trading at a discount"
        market_eval_message = normalized_message
        for kw in self.VALUATION_KEYWORDS:
            if kw in market_eval_message:
                market_eval_message = market_eval_message.replace(kw, " ")

        has_market = self._contains_keyword(market_eval_message, self.MARKET_KEYWORDS)
        has_news = self._contains_keyword(normalized_message, self.NEWS_KEYWORDS)
        has_risk = self._contains_keyword(normalized_message, self.RISK_KEYWORDS)
        has_portfolio = self._contains_keyword(normalized_message, self.PORTFOLIO_KEYWORDS)

        matching_domains = sum(
            1
            for domain_active in (
                has_news,
                has_market,
                has_financial,
                has_risk,
                has_portfolio,
            )
            if domain_active
        )

        if matching_domains >= 2:
            return "general"

        if has_valuation:
            return "financial"

        if has_news:
            return "news"

        if has_market:
            return "market"

        if has_financial:
            return "financial"

        if has_risk:
            return "risk"

        if has_portfolio:
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
