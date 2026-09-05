"""Agent for company news intelligence with sentiment and synthesis."""

import json
import re
from collections.abc import Callable

from apps.ai.agents.base import BaseAgent
from apps.ai.exceptions import LLMError
from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
from apps.ai.graph.state import AgentState
from apps.ai.services import research_tools
from apps.ai.services.llm_service import LLMService
from apps.ai.services.schemas import AgentResult, AggregatedSentiment, SentimentResult
from apps.ai.services.token_budget import (
    DegradationTier,
    get_default_token_budget_manager,
)
from apps.research.services.schemas import NewsArticle, NewsResearch


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
        self.llm_service = llm_service or LLMService(model="news")

    @property
    def name(self) -> str:
        return "news"

    def run(self, message: str | AgentState | ResearchContext) -> AgentResult:
        """Return a synthesized summary of recent company news."""
        research_context: ResearchContext | None = None

        if isinstance(message, ResearchContext):
            research_context = message
            user_message = f"Analyze news for {research_context.ticker}"
            ticker = research_context.ticker
            market = research_context.market
        elif isinstance(message, AgentState):
            user_message = message.user_message
            ticker = (
                self.ticker
                or (message.ticker.upper() if message.ticker else None)
                or self._extract_ticker(user_message)
            )
            market = (
                (message.market.upper() if message.market else None)
                or self.market
            )
        else:
            user_message = message
            ticker = self.ticker or self._extract_ticker(message)
            market = self.market

        if ticker is None:
            return AgentResult(
                response=(
                    "Please provide a ticker symbol to analyze company news."
                ),
                tools_used=[],
            )

        tools_used: list[str] = []
        news_data: dict[str, object] | None = None
        articles: list[dict | NewsArticle] = []

        if research_context is not None:
            articles = research_context.news.articles if research_context.news else []
        else:
            try:
                news_data = self.news_tool(
                    ticker=ticker,
                    market=market,
                    limit=self.limit,
                )
                tools_used.append("get_news")
            except (ValueError, TypeError) as exc:
                return AgentResult(
                    response=(
                        f"Unable to retrieve news analysis for {ticker}: {exc}"
                    ),
                    tools_used=tools_used,
                )

            if isinstance(news_data, dict):
                raw_articles = news_data.get("articles", [])
                if isinstance(raw_articles, list):
                    articles = raw_articles

            research_context = self.build_canonical_context(
                ticker=ticker,
                market=market,
                news_data_raw=news_data,
            )

        if not articles:
            return AgentResult(
                response=(
                    f"News analysis for {ticker}: "
                    "no recent news articles found."
                ),
                tools_used=[] if isinstance(message, ResearchContext) else (tools_used or ["get_news"]),
                data={"ticker": ticker, "market": market, "articles": []},
            )

        analyzed_articles = self._analyze_articles(articles)
        aggregated_sentiment = self._aggregate_sentiment(analyzed_articles)

        tier = self._get_degradation_tier()

        data_payload: dict[str, object] = {
            "ticker": ticker,
            "market": market,
            "articles": analyzed_articles,
            "aggregated_sentiment": aggregated_sentiment,
        }

        if research_context and research_context.provenance:
            data_payload["provenance"] = {
                section: prov.model_dump()
                for section, prov in research_context.provenance.items()
            }

        if tier == DegradationTier.EXHAUSTED:
            summary = self._build_summary(ticker, news_data or {"articles": articles})
            return AgentResult(
                response=(
                    f"{summary}\n\n"
                    f"Authoritative sentiment: "
                    f"positive={aggregated_sentiment['positive']}, "
                    f"neutral={aggregated_sentiment['neutral']}, "
                    f"negative={aggregated_sentiment['negative']}, "
                    f"unavailable={aggregated_sentiment['unavailable']}, "
                    f"average_confidence={aggregated_sentiment['average_confidence']}."
                ),
                tools_used=tools_used or ["get_news"],
                data=data_payload,
            )

        article_limit = self._get_article_limit_for_tier(tier)
        articles_for_prompt = (
            articles[:article_limit] if article_limit is not None else articles
        )
        analyzed_for_prompt = (
            analyzed_articles[:article_limit]
            if article_limit is not None
            else analyzed_articles
        )

        messages = self._build_analysis_messages(
            message=user_message,
            ticker=ticker,
            articles=articles_for_prompt,
            analyzed_articles=analyzed_for_prompt,
            aggregated_sentiment=aggregated_sentiment,
        )

        max_tokens = self._get_max_completion_tokens_for_tier(tier)

        try:
            response = self._call_llm(messages, max_completion_tokens=max_tokens)
        except LLMError:
            raise

        if not isinstance(response, str) or not response.strip():
            return AgentResult(
                response=(
                    f"Unable to analyze news for {ticker}: "
                    "the fast model returned an empty response."
                ),
                tools_used=tools_used or ["get_news"],
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
            tools_used=tools_used or ["get_news"],
            data=data_payload,
        )

    def build_canonical_context(
        self,
        ticker: str,
        market: str = "IN",
        news_data_raw: object = None,
    ) -> ResearchContext:
        """Construct a canonical ResearchContext from raw news data outputs."""
        provenance_dict: dict[str, ProviderProvenance] = {}
        parsed_news: NewsResearch | None = None

        if isinstance(news_data_raw, dict):
            prov = self._extract_provider_provenance(news_data_raw)
            if prov:
                provenance_dict["news"] = prov

            raw_articles = news_data_raw.get("articles") or []
            article_objects: list[NewsArticle] = []
            if isinstance(raw_articles, list):
                for a in raw_articles:
                    if isinstance(a, NewsArticle):
                        article_objects.append(a)
                    elif isinstance(a, dict):
                        article_objects.append(
                            NewsArticle(
                                title=str(a.get("title") or ""),
                                summary=a.get("summary"),
                                url=str(a.get("url") or ""),
                                source=str(a.get("source") or "Publisher"), # Publisher name
                                published_at=a.get("published_at"),
                                image_url=a.get("image_url"),
                                relevance_score=a.get("relevance_score"),
                                target_match_score=a.get("target_match_score"),
                                relevance_type=a.get("relevance_type"),
                            )
                        )
            parsed_news = NewsResearch(ticker=ticker, articles=article_objects)

        return ResearchContext(
            ticker=ticker,
            market=market,
            news=parsed_news,
            provenance=provenance_dict,
        )

    def _extract_provider_provenance(self, raw_dict: dict) -> ProviderProvenance | None:
        if not isinstance(raw_dict, dict):
            return None
        prov_dict = raw_dict.get("provenance") if isinstance(raw_dict.get("provenance"), dict) else raw_dict
        if not isinstance(prov_dict, dict):
            return None
        if "source" in prov_dict or "primary_provider" in prov_dict or "fallback_used" in prov_dict:
            status_val = str(prov_dict.get("data_status") or "complete")
            if hasattr(status_val, "value"):
                status_val = status_val.value
            return ProviderProvenance(
                primary_provider=str(prov_dict.get("primary_provider") or "news_aggregator"),
                source=str(prov_dict.get("source") or prov_dict.get("provider_used") or "news_aggregator"),
                fallback_used=bool(prov_dict.get("fallback_used", False)),
                data_status=status_val if status_val in ("complete", "partial", "empty", "failed") else "complete",
                fallback_reason=str(prov_dict.get("fallback_reason")) if prov_dict.get("fallback_reason") else None,
            )
        return None


    def _get_degradation_tier(self) -> DegradationTier:
        manager = getattr(self.llm_service, "token_budget_manager", None)
        if manager is None and hasattr(self.llm_service, "__self__"):
            manager = getattr(
                self.llm_service.__self__, "token_budget_manager", None
            )

        if manager is not None and hasattr(manager, "get_degradation_tier"):
            res = manager.get_degradation_tier()
            if isinstance(res, DegradationTier):
                return res

        return get_default_token_budget_manager().get_degradation_tier()

    @staticmethod
    def _get_article_limit_for_tier(tier: DegradationTier) -> int | None:
        if tier == DegradationTier.CONSTRAINED:
            return 5
        if tier == DegradationTier.CRITICAL:
            return 3
        return None

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

    @staticmethod
    def _get_article_field(article: object, field_name: str, default: object = None) -> object:
        if isinstance(article, dict):
            return article.get(field_name, default)
        return getattr(article, field_name, default)

    def _analyze_articles(
        self,
        articles: list[object],
    ) -> list[dict[str, object]]:
        if self.sentiment_classifier is None:
            from apps.ai.services.sentiment import FinancialSentimentClassifier

            self.sentiment_classifier = FinancialSentimentClassifier()

        analyzed: list[dict[str, object]] = []
        for article in articles:
            title = self._get_article_field(article, "title")
            summary = self._get_article_field(article, "summary")
            source = self._get_article_field(article, "source")
            relevance_type = self._get_article_field(article, "relevance_type")

            combined_text = self._coalesce_article_text(title, summary)
            if not combined_text:
                analyzed.append(
                    {
                        "title": title,
                        "summary": summary,
                        "source": source,
                        "relevance_type": relevance_type,
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
                    "source": source,
                    "relevance_type": relevance_type,
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
        articles: list[object],
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
                    "title": NewsIntelligenceAgent._get_article_field(article, "title"),
                    "summary": NewsIntelligenceAgent._get_article_field(article, "summary"),
                    "source": NewsIntelligenceAgent._get_article_field(article, "source"),
                    "relevance_type": NewsIntelligenceAgent._get_article_field(article, "relevance_type"),
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
            source = NewsIntelligenceAgent._get_article_field(article, "source")
            if isinstance(source, str) and source:
                sources.add(source)
            relevance_type = NewsIntelligenceAgent._get_article_field(article, "relevance_type")
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