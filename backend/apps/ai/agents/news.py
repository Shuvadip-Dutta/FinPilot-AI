"""Deterministic agent for company news intelligence."""

import re
from collections.abc import Callable

from apps.ai.agents.base import BaseAgent
from apps.ai.services import research_tools
from apps.ai.services.schemas import AgentResult


NewsTool = Callable[..., dict[str, object]]


class NewsIntelligenceAgent(BaseAgent):
    """Retrieve and summarize recent company news."""

    def __init__(
        self,
        news_tool: NewsTool | None = None,
        ticker: str | None = None,
        market: str = "IN",
        limit: int = 10,
    ):
        self.news_tool = (
            news_tool or research_tools.get_news
        )
        self.ticker = ticker.upper() if ticker else None
        self.market = market.upper()
        self.limit = limit

    @property
    def name(self) -> str:
        return "news"

    def run(self, message: str) -> AgentResult:
        """Return a deterministic summary of recent company news."""

        ticker = self.ticker or self._extract_ticker(message)

        if ticker is None:
            return AgentResult(
                response=(
                    "Please provide a ticker symbol to analyze company news."
                ),
                tools_used=[],
            )

        try:
            result = self.news_tool(
                ticker=ticker,
                market=self.market,
                limit=self.limit,
            )
        except (ValueError, TypeError) as exc:
            return AgentResult(
                response=(
                    f"Unable to retrieve news analysis for "
                    f"{ticker}: {exc}"
                ),
                tools_used=[],
            )

        return AgentResult(
            response=self._build_summary(
                ticker=ticker,
                news_data=result,
            ),
            tools_used=["get_news"],
        )

    @staticmethod
    def _extract_ticker(message: str) -> str | None:
        """Extract an explicit ticker from the message."""

        excluded_words = {
            "NEWS",
            "LATEST",
            "HEADLINE",
            "HEADLINES",
            "UPDATE",
            "UPDATES",
            "RECENT",
            "SHOW",
            "WHAT",
            "HAPPENING",
            "ABOUT",
            "COMPANY",
        }

        for candidate in re.findall(
            r"\b[A-Z]{2,10}\b",
            message,
        ):
            if candidate not in excluded_words:
                return candidate

        return None

    @staticmethod
    def _build_summary(
        ticker: str,
        news_data: dict[str, object],
    ) -> str:
        articles = news_data.get("articles", [])

        if not isinstance(articles, list):
            return (
                f"News analysis for {ticker}: "
                "no valid news articles were returned."
            )

        article_count = len(articles)

        if article_count == 0:
            return (
                f"News analysis for {ticker}: "
                "no recent news articles found."
            )

        sources: set[str] = set()
        relevance_counts = {
            "DIRECT": 0,
            "RELATED": 0,
            "MARKET_CONTEXT": 0,
        }

        for article in articles:
            if not isinstance(article, dict):
                continue

            source = article.get("source")

            if isinstance(source, str) and source:
                sources.add(source)

            relevance_type = article.get("relevance_type")

            if relevance_type in relevance_counts:
                relevance_counts[relevance_type] += 1

        source_text = (
            ", ".join(sorted(sources))
            if sources
            else "unknown sources"
        )

        return (
            f"News analysis for {ticker}: "
            f"{article_count} recent article(s) from "
            f"{source_text}. "
            f"Relevance: "
            f"{relevance_counts['DIRECT']} direct, "
            f"{relevance_counts['RELATED']} related, "
            f"{relevance_counts['MARKET_CONTEXT']} market context."
        )