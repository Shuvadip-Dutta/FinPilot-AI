"""Agent for company news intelligence with sentiment and synthesis."""

import json
import re
from collections.abc import Callable

from apps.ai.agents.base import BaseAgent
from apps.ai.exceptions import LLMError
from apps.ai.services import research_tools
from apps.ai.services.llm_service import LLMService
from apps.ai.services.schemas import AgentResult, AggregatedSentiment, SentimentResult


NewsTool = Callable[..., dict[str, object]]
SentimentClassifier = Callable[[str], dict[str, object] | SentimentResult]


class NewsIntelligenceAgent(BaseAgent):
    """Retrieve news, score sentiment, and synthesize with the fast model."""

    def __init__(
        self,
        news_tool: NewsTool | None = None,
        ticker: str | None = None,
        market: str = "IN",
        limit: int = 10,
        sentiment_classifier: SentimentClassifier | None = None,
        llm_service: Callable[[list[dict[str, str]]], str] | None = None,
    ):
        self.news_tool = news_tool or research_tools.get_news
        self.ticker = ticker.upper() if ticker else None
        self.market = market.upper()
        self.limit = limit
        self.sentiment_classifier = sentiment_classifier
        self.llm_service = llm_service or LLMService(model="fast")

    @property
    def name(self) -> str:
        return "news"

    def run(self, message: str) -> AgentResult:
        """Return a synthesized summary of recent company news."""
        ticker = self.ticker or self._extract_ticker(message)

        if ticker is None:
            return AgentResult(
                response=(
                    "Please provide a ticker symbol to analyze company news."
                ),
                tools_used=[],
            )

        try:
            news_data = self.news_tool(
                ticker=ticker,
                market=self.market,
                limit=self.limit,
            )
        except (ValueError, TypeError) as exc:
            return AgentResult(
                response=(
                    f"Unable to retrieve news analysis for {ticker}: {exc}"
                ),
                tools_used=[],
            )

        articles = news_data.get("articles", [])
        if not isinstance(articles, list):
            articles = []

        if not articles:
            return AgentResult(
                response=(
                    f"News analysis for {ticker}: "
                    "no recent news articles found."
                ),
                tools_used=["get_news"],
            )

        analyzed_articles = self._analyze_articles(articles)
        aggregated_sentiment = self._aggregate_sentiment(analyzed_articles)
        messages = self._build_analysis_messages(
            message=message,
            ticker=ticker,
            articles=articles,
            analyzed_articles=analyzed_articles,
            aggregated_sentiment=aggregated_sentiment,
        )

        try:
            response = self.llm_service(messages)
        except LLMError:
            raise

        if not isinstance(response, str) or not response.strip():
            return AgentResult(
                response=(
                    f"Unable to analyze news for {ticker}: "
                    "the fast model returned an empty response."
                ),
                tools_used=["get_news"],
            )

        return AgentResult(
            response=(
                f"{response.strip()}\n\n"
                f"Authoritative sentiment: "
                f"positive={aggregated_sentiment['positive']}, "
                f"neutral={aggregated_sentiment['neutral']}, "
                f"negative={aggregated_sentiment['negative']}, "
                f"unavailable={aggregated_sentiment['unavailable']}, "
                f"average_confidence={aggregated_sentiment['average_confidence']}."
            ),
            tools_used=["get_news"],
            data={
                "ticker": ticker,
                "market": self.market,
                "articles": analyzed_articles,
                "aggregated_sentiment": aggregated_sentiment,
            },
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

        for candidate in re.findall(r"\b[A-Z]{2,10}\b", message):
            if candidate not in excluded_words:
                return candidate

        return None

    def _analyze_articles(
        self,
        articles: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        if self.sentiment_classifier is None:
            from apps.ai.services.sentiment import FinancialSentimentClassifier

            self.sentiment_classifier = FinancialSentimentClassifier()

        analyzed: list[dict[str, object]] = []
        for article in articles:
            if not isinstance(article, dict):
                continue

            title = article.get("title")
            summary = article.get("summary")
            combined_text = self._coalesce_article_text(title, summary)
            if not combined_text:
                analyzed.append(
                    {
                        "title": title,
                        "summary": summary,
                        "source": article.get("source"),
                        "relevance_type": article.get("relevance_type"),
                        "sentiment": {"label": "unavailable", "confidence": 0.0},
                    }
                )
                continue

            sentiment = self.sentiment_classifier(classified_text := combined_text)
            normalized = self._normalize_sentiment_result(sentiment)
            analyzed.append(
                {
                    "title": title,
                    "summary": summary,
                    "source": article.get("source"),
                    "relevance_type": article.get("relevance_type"),
                    "sentiment": normalized,
                }
            )

        return analyzed

    @staticmethod
    def _coalesce_article_text(title: object, summary: object) -> str:
        pieces = []
        for value in (title, summary):
            if isinstance(value, str) and value.strip():
                pieces.append(value.strip())
        return " ".join(pieces)

    @staticmethod
    def _normalize_sentiment_result(
        sentiment: dict[str, object] | SentimentResult,
    ) -> dict[str, object]:
        if isinstance(sentiment, SentimentResult):
            return {
                "label": sentiment.label,
                "confidence": float(sentiment.confidence),
            }

        if isinstance(sentiment, dict):
            return {
                "label": str(sentiment.get("label", "neutral")).lower(),
                "confidence": float(sentiment.get("confidence", 0.0)),
            }

        raise ValueError("Sentiment classifier returned an unsupported value.")

    @staticmethod
    def _aggregate_sentiment(
        analyzed_articles: list[dict[str, object]],
    ) -> dict[str, object]:
        counts = {"positive": 0, "neutral": 0, "negative": 0, "unavailable": 0}
        confidence_scores: list[float] = []

        for article in analyzed_articles:
            sentiment = article.get("sentiment")
            if not isinstance(sentiment, dict):
                continue

            label = str(sentiment.get("label", "neutral")).lower()
            if label not in counts:
                label = "neutral"
            counts[label] = counts.get(label, 0) + 1

            confidence = float(sentiment.get("confidence", 0.0))
            confidence_scores.append(confidence)

        average_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.0
        )

        return {
            "positive": counts["positive"],
            "neutral": counts["neutral"],
            "negative": counts["negative"],
            "unavailable": counts["unavailable"],
            "average_confidence": round(average_confidence, 4),
        }

    @staticmethod
    def _build_analysis_messages(
        message: str,
        ticker: str,
        articles: list[dict[str, object]],
        analyzed_articles: list[dict[str, object]],
        aggregated_sentiment: dict[str, object] | None = None,
    ) -> list[dict[str, str]]:
        system_prompt = (
            "You are the financial news synthesis specialist for FinPilot AI. "
            "Use only the supplied news and sentiment evidence. Summarize the major themes, "
            "highlight positive or negative developments supported by the provided article data, "
            "and distinguish direct company news from related or broader market-context coverage. "
            "Incorporate the specialist sentiment signals and point out mixed or conflicting signals when present. "
            "The AGGREGATED SENTIMENT counts are authoritative: do not recalculate them, change their labels, "
            "or invent additional articles. Use the supplied aggregate exactly. "
            "Do not over-weight a single article. State when the sample is limited. "
            "Distinguish facts from interpretation. Never invent headlines, events, sentiment labels, prices, dates, or companies. "
            "Never claim the news predicts future returns or guarantees market performance. Do not provide an automatic buy/sell recommendation."
        )

        aggregated = aggregated_sentiment or NewsIntelligenceAgent._aggregate_sentiment(
            analyzed_articles
        )

        context = {
            "user_question": message,
            "ticker": ticker,
            "article_titles": [
                {
                    "title": article.get("title"),
                    "summary": article.get("summary"),
                    "source": article.get("source"),
                    "relevance_type": article.get("relevance_type"),
                }
                for article in articles
            ],
            "article_level_sentiment": analyzed_articles,
            "aggregated_sentiment": aggregated,
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

        source_text = ", ".join(sorted(sources)) if sources else "unknown sources"

        return (
            f"News analysis for {ticker}: "
            f"{article_count} recent article(s) from "
            f"{source_text}. "
            f"Relevance: "
            f"{relevance_counts['DIRECT']} direct, "
            f"{relevance_counts['RELATED']} related, "
            f"{relevance_counts['MARKET_CONTEXT']} market context."
        )