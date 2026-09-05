import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.agents.news import NewsIntelligenceAgent
from apps.ai.exceptions import LLMError
from apps.ai.services.schemas import AgentResult
from apps.ai.services.token_budget import (
    DegradationTier,
    LLMUsage,
    TokenBudgetManager,
)


class NewsIntelligenceAgentTestCase(SimpleTestCase):

    def test_agent_name(self):
        agent = NewsIntelligenceAgent()
        self.assertEqual(agent.name, "news")

    def test_successful_news_analysis(self):
        news_tool = MagicMock(
            return_value={
                "ticker": "RELIANCE",
                "articles": [
                    {
                        "title": "Reliance update",
                        "summary": "Expansion continues at a strong pace.",
                        "source": "upstox.com",
                        "relevance_type": "DIRECT",
                    },
                    {
                        "title": "Market update",
                        "summary": "Broader market sentiment is mixed.",
                        "source": "livemint.com",
                        "relevance_type": "RELATED",
                    },
                ],
            }
        )
        sentiment_classifier = MagicMock(
            side_effect=[
                {"label": "positive", "confidence": 0.82},
                {"label": "neutral", "confidence": 0.61},
            ]
        )
        llm_service = MagicMock(
            return_value="The direct update is constructive while the broader context remains mixed."
        )

        agent = NewsIntelligenceAgent(
            news_tool=news_tool,
            ticker="RELIANCE",
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        result = agent.run("Show me the latest news about Reliance.")

        self.assertIsInstance(result, AgentResult)
        self.assertIn(
            "The direct update is constructive while the broader context remains mixed.",
            result.response,
        )
        self.assertEqual(result.tools_used, ["get_news"])
        self.assertEqual(news_tool.call_count, 1)
        self.assertEqual(sentiment_classifier.call_count, 2)
        llm_service.assert_called_once()

        messages = llm_service.call_args[0][0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("RELIANCE", messages[1]["content"])
        self.assertIn("article_titles", messages[1]["content"])
        self.assertIn("aggregated_sentiment", messages[1]["content"])
        self.assertIn("do not recalculate them", messages[0]["content"])
        self.assertIn("positive=1", result.response)
        self.assertIn("neutral=1", result.response)
        self.assertIn("negative=0", result.response)
        self.assertEqual(len(result.data["articles"]), 2)
        self.assertEqual(result.data["articles"][0]["sentiment"]["label"], "positive")
        self.assertEqual(
            result.data["aggregated_sentiment"],
            {
                "positive": 1,
                "neutral": 1,
                "negative": 0,
                "unavailable": 0,
                "average_confidence": 0.715,
            },
        )

    @patch("apps.ai.agents.news.LLMService")
    def test_uses_fast_model_by_default(self, mock_llm_service):
        NewsIntelligenceAgent(
            news_tool=lambda **kwargs: {"articles": [{"title": "News", "summary": "Updated."}]},
            ticker="RELIANCE",
            sentiment_classifier=lambda text: {"label": "positive", "confidence": 0.8},
        )
        mock_llm_service.assert_called_once_with(model="news")

    def test_no_news_returns_clear_message(self):
        agent = NewsIntelligenceAgent(
            news_tool=lambda **kwargs: {"ticker": "RELIANCE", "articles": []},
            ticker="RELIANCE",
            sentiment_classifier=lambda text: {"label": "positive", "confidence": 0.9},
        )

        result = agent.run("Show me the latest news.")

        self.assertEqual(
            result.response,
            "News analysis for RELIANCE: no recent news articles found.",
        )
        self.assertEqual(result.tools_used, ["get_news"])

    def test_missing_ticker_returns_request_for_ticker(self):
        sentiment_classifier = MagicMock()
        llm_service = MagicMock()
        agent = NewsIntelligenceAgent(
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        result = agent.run("Show me the latest company news.")

        self.assertIn("Please provide a ticker symbol", result.response)
        self.assertEqual(result.tools_used, [])
        sentiment_classifier.assert_not_called()
        llm_service.assert_not_called()

    def test_tool_failure_returns_agent_result(self):
        def failing_news_tool(**kwargs):
            raise ValueError("News provider unavailable")

        sentiment_classifier = MagicMock()
        llm_service = MagicMock()
        agent = NewsIntelligenceAgent(
            news_tool=failing_news_tool,
            ticker="RELIANCE",
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        result = agent.run("Show Reliance news.")

        self.assertIn("News provider unavailable", result.response)
        self.assertEqual(result.tools_used, [])
        sentiment_classifier.assert_not_called()
        llm_service.assert_not_called()

    def test_run_returns_agent_result(self):
        agent = NewsIntelligenceAgent(
            news_tool=lambda **kwargs: {"articles": []},
            ticker="TCS",
            sentiment_classifier=lambda text: {"label": "positive", "confidence": 0.9},
            llm_service=lambda messages: "Analysis complete.",
        )

        result = agent.run("Show TCS news.")
        self.assertIsInstance(result, AgentResult)

    def test_injected_tool_prevents_real_api_call(self):
        calls = []

        def news_tool(**kwargs):
            calls.append(kwargs)
            return {"ticker": "TCS", "articles": []}

        agent = NewsIntelligenceAgent(
            news_tool=news_tool,
            ticker="TCS",
            limit=5,
            sentiment_classifier=lambda text: {"label": "positive", "confidence": 0.9},
        )

        agent.run("Show TCS news.")

        self.assertEqual(calls, [{"ticker": "TCS", "market": "IN", "limit": 5}])

    def test_empty_article_text_is_not_sentiment_classified(self):
        news_tool = MagicMock(
            return_value={
                "articles": [
                    {"title": "", "summary": "", "source": "x", "relevance_type": "DIRECT"},
                    {"title": "Company update", "summary": "Results are strong.", "source": "y", "relevance_type": "RELATED"},
                ]
            }
        )
        sentiment_classifier = MagicMock(return_value={"label": "positive", "confidence": 0.9})
        llm_service = MagicMock(return_value="The sample is mostly positive.")

        agent = NewsIntelligenceAgent(
            news_tool=news_tool,
            ticker="RELIANCE",
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        agent.run("Show Reliance news.")
        self.assertEqual(sentiment_classifier.call_count, 1)
        self.assertEqual(sentiment_classifier.call_args[0][0], "Company update Results are strong.")

    def test_llm_failure_is_not_silently_swallowed(self):
        llm_service = MagicMock(side_effect=LLMError("Groq unavailable"))
        agent = NewsIntelligenceAgent(
            news_tool=lambda **kwargs: {"articles": [{"title": "Reliance update", "summary": "Strong results.", "source": "moneycontrol", "relevance_type": "DIRECT"}]},
            ticker="RELIANCE",
            sentiment_classifier=lambda text: {"label": "positive", "confidence": 0.9},
            llm_service=llm_service,
        )

        with self.assertRaises(LLMError):
            agent.run("Show Reliance news.")

    def test_sentiment_aggregation_is_deterministic(self):
        sentiment_classifier = MagicMock(
            side_effect=[
                {"label": "positive", "confidence": 0.84},
                {"label": "negative", "confidence": 0.71},
                {"label": "neutral", "confidence": 0.53},
            ]
        )
        llm_service = MagicMock(return_value="The mix is balanced but slightly positive.")
        agent = NewsIntelligenceAgent(
            news_tool=lambda **kwargs: {
                "articles": [
                    {"title": "A", "summary": "A", "source": "s1", "relevance_type": "DIRECT"},
                    {"title": "B", "summary": "B", "source": "s2", "relevance_type": "RELATED"},
                    {"title": "C", "summary": "C", "source": "s3", "relevance_type": "MARKET_CONTEXT"},
                ]
            },
            ticker="RELIANCE",
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        result = agent.run("Analyze RELIANCE news.")
        self.assertIn("The mix is balanced but slightly positive.", result.response)
        prompt_content = llm_service.call_args[0][0][1]["content"]
        self.assertIn("positive", prompt_content.lower())
        self.assertIn("negative", prompt_content.lower())
        self.assertIn("neutral", prompt_content.lower())

    def test_seven_articles_have_conserved_deterministic_sentiment_counts(self):
        analyzed_articles = [
            {"sentiment": {"label": label, "confidence": 0.8}}
            for label in [
                "positive", "positive", "positive", "neutral",
                "neutral", "negative", "unavailable",
            ]
        ]

        aggregate = NewsIntelligenceAgent._aggregate_sentiment(analyzed_articles)

        self.assertEqual(aggregate["positive"], 3)
        self.assertEqual(aggregate["neutral"], 2)
        self.assertEqual(aggregate["negative"], 1)
        self.assertEqual(aggregate["unavailable"], 1)
        self.assertEqual(
            sum(aggregate[label] for label in ("positive", "neutral", "negative", "unavailable")),
            7,
        )

    def test_unavailable_sentiment_is_counted_separately(self):
        aggregate = NewsIntelligenceAgent._aggregate_sentiment([
            {"sentiment": {"label": "positive", "confidence": 0.8}},
            {"sentiment": {"label": "unavailable", "confidence": 0.0}},
        ])

        self.assertEqual(aggregate["positive"], 1)
        self.assertEqual(aggregate["unavailable"], 1)
        self.assertEqual(aggregate["neutral"], 0)

    def test_llm_cannot_change_authoritative_aggregate_in_result(self):
        agent = NewsIntelligenceAgent(
            news_tool=lambda **kwargs: {"articles": [
                {"title": "A", "summary": "A", "source": "s"},
                {"title": "B", "summary": "B", "source": "s"},
            ]},
            ticker="RELIANCE",
            sentiment_classifier=lambda text: {"label": "positive", "confidence": 0.9},
            llm_service=lambda messages: "Positive: 99, Neutral: 99, Negative: 99",
        )

        result = agent.run("Summarize RELIANCE news sentiment.")

        self.assertIn("Positive: 99", result.response)
        self.assertIn("positive=2", result.response)
        self.assertIn("neutral=0", result.response)
        self.assertIn("negative=0", result.response)

    def test_constrained_tier_reduces_article_context_and_caps_output(self):
        manager = TokenBudgetManager(
            max_request_tokens=100000,
            safety_reserve_tokens=0,
            tpm_limit=10000,
        )
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=3750,
                completion_tokens=3750,
                total_tokens=7500,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.CONSTRAINED)

        articles = [
            {
                "title": f"Article {i}",
                "summary": f"Summary {i}",
                "source": "news.com",
                "relevance_type": "DIRECT",
            }
            for i in range(10)
        ]
        news_tool = MagicMock(return_value={"ticker": "RELIANCE", "articles": articles})
        sentiment_classifier = MagicMock(return_value={"label": "positive", "confidence": 0.8})
        llm_service = MagicMock(return_value="Constrained news analysis.")
        llm_service.token_budget_manager = manager

        agent = NewsIntelligenceAgent(
            news_tool=news_tool,
            ticker="RELIANCE",
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        result = agent.run("Show Reliance news.")

        self.assertIsInstance(result, AgentResult)
        self.assertIn("Constrained news analysis.", result.response)
        self.assertIn("Authoritative sentiment: positive=10", result.response)
        self.assertEqual(result.tools_used, ["get_news"])
        self.assertEqual(sentiment_classifier.call_count, 10)
        llm_service.assert_called_once()

        _, kwargs = llm_service.call_args
        self.assertEqual(kwargs.get("max_completion_tokens"), 512)

        messages = llm_service.call_args[0][0]
        prompt_json = json.loads(messages[1]["content"])
        self.assertEqual(len(prompt_json["article_titles"]), 5)
        self.assertEqual(len(prompt_json["article_level_sentiment"]), 5)
        self.assertEqual(prompt_json["aggregated_sentiment"]["positive"], 10)
        self.assertEqual(len(result.data["articles"]), 10)

    def test_critical_tier_reduces_article_context_further_and_caps_output(self):
        manager = TokenBudgetManager(
            max_request_tokens=100000,
            safety_reserve_tokens=0,
            tpm_limit=10000,
        )
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=4750,
                completion_tokens=4750,
                total_tokens=9500,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.CRITICAL)

        articles = [
            {
                "title": f"Article {i}",
                "summary": f"Summary {i}",
                "source": "news.com",
                "relevance_type": "DIRECT",
            }
            for i in range(10)
        ]
        news_tool = MagicMock(return_value={"ticker": "RELIANCE", "articles": articles})
        sentiment_classifier = MagicMock(return_value={"label": "positive", "confidence": 0.8})
        llm_service = MagicMock(return_value="Critical news analysis.")
        llm_service.token_budget_manager = manager

        agent = NewsIntelligenceAgent(
            news_tool=news_tool,
            ticker="RELIANCE",
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        result = agent.run("Show Reliance news.")

        self.assertIsInstance(result, AgentResult)
        self.assertIn("Critical news analysis.", result.response)
        self.assertIn("Authoritative sentiment: positive=10", result.response)
        llm_service.assert_called_once()

        _, kwargs = llm_service.call_args
        self.assertEqual(kwargs.get("max_completion_tokens"), 256)

        messages = llm_service.call_args[0][0]
        prompt_json = json.loads(messages[1]["content"])
        self.assertEqual(len(prompt_json["article_titles"]), 3)
        self.assertEqual(len(prompt_json["article_level_sentiment"]), 3)
        self.assertEqual(prompt_json["aggregated_sentiment"]["positive"], 10)
        self.assertEqual(len(result.data["articles"]), 10)

    def test_exhausted_tier_bypasses_llm_and_returns_deterministic_summary(self):
        manager = TokenBudgetManager(
            max_request_tokens=100000,
            safety_reserve_tokens=0,
            tpm_limit=10000,
        )
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=5000,
                completion_tokens=5000,
                total_tokens=10000,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.EXHAUSTED)

        articles = [
            {
                "title": f"Article {i}",
                "summary": f"Summary {i}",
                "source": "news.com",
                "relevance_type": "DIRECT",
            }
            for i in range(5)
        ]
        news_tool = MagicMock(return_value={"ticker": "RELIANCE", "articles": articles})
        sentiment_classifier = MagicMock(return_value={"label": "positive", "confidence": 0.8})
        llm_service = MagicMock(return_value="Should not be called.")
        llm_service.token_budget_manager = manager

        agent = NewsIntelligenceAgent(
            news_tool=news_tool,
            ticker="RELIANCE",
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        result = agent.run("Show Reliance news.")

        self.assertIsInstance(result, AgentResult)
        self.assertIn("News analysis for RELIANCE: 5 recent article(s)", result.response)
        self.assertIn("Authoritative sentiment: positive=5", result.response)
        self.assertEqual(result.tools_used, ["get_news"])
        self.assertEqual(result.data["aggregated_sentiment"]["positive"], 5)
        self.assertEqual(len(result.data["articles"]), 5)
        llm_service.assert_not_called()

    def test_run_accepts_agent_state_with_ticker_and_market(self):
        from apps.ai.graph.state import AgentState

        news_tool = MagicMock(return_value={"ticker": "LT", "articles": []})
        agent = NewsIntelligenceAgent(news_tool=news_tool)

        state = AgentState(
            user_message="Conduct research on Larsen & Toubro",
            ticker="LT",
            market="IN",
        )

        result = agent.run(state)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(
            result.response,
            "News analysis for LT: no recent news articles found.",
        )
        news_tool.assert_called_once_with(ticker="LT", market="IN", limit=10)

    def test_news_agent_consumes_canonical_research_context(self):
        from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
        from apps.research.services.schemas import NewsArticle, NewsResearch

        articles = [
            NewsArticle(
                title="L&T Order Win",
                summary="Larsen & Toubro receives mega order.",
                url="https://example.com/lt-win",
                source="Reuters",
                published_at="2026-09-01T10:00:00Z",
                relevance_type="DIRECT",
            ),
        ]
        news_research = NewsResearch(ticker="LT", articles=articles)
        prov = {
            "news": ProviderProvenance(
                primary_provider="news_aggregator",
                source="marketaux",
                fallback_used=False,
                data_status="complete",
            )
        }
        ctx = ResearchContext(
            ticker="LT",
            market="IN",
            news=news_research,
            provenance=prov,
        )

        sentiment_classifier = MagicMock(return_value={"label": "positive", "confidence": 0.95})
        llm_service = MagicMock(return_value="L&T news sentiment is positive.")
        agent = NewsIntelligenceAgent(
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        result = agent.run(ctx)

        self.assertIsInstance(result, AgentResult)
        self.assertIn("L&T news sentiment is positive.", result.response)
        self.assertEqual(result.data["ticker"], "LT")
        self.assertIn("provenance", result.data)
        self.assertEqual(result.data["provenance"]["news"]["source"], "marketaux")

    def test_news_article_source_remains_news_publisher_not_confused_with_provider_provenance(self):
        from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
        from apps.research.services.schemas import NewsArticle, NewsResearch

        articles = [
            NewsArticle(
                title="Q1 Earnings Update",
                summary="Strong growth reported by company.",
                url="https://example.com/q1-earnings",
                source="Bloomberg",
                published_at="2026-09-01T10:00:00Z",
            ),
        ]
        news_research = NewsResearch(ticker="RELIANCE", articles=articles)
        prov = {
            "news": ProviderProvenance(
                primary_provider="upstox",
                source="upstox_news_api",
                fallback_used=False,
                data_status="complete",
            )
        }
        ctx = ResearchContext(
            ticker="RELIANCE",
            market="IN",
            news=news_research,
            provenance=prov,
        )

        sentiment_classifier = MagicMock(return_value={"label": "positive", "confidence": 0.88})
        llm_service = MagicMock(return_value="Positive earnings coverage.")
        agent = NewsIntelligenceAgent(
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        result = agent.run(ctx)

        self.assertEqual(result.data["articles"][0]["source"], "Bloomberg")
        self.assertEqual(result.data["provenance"]["news"]["source"], "upstox_news_api")
        self.assertNotEqual(result.data["articles"][0]["source"], result.data["provenance"]["news"]["source"])

    def test_provenance_survives_from_news_tool_dict_into_agent_context(self):
        news_dict = {
            "ticker": "LT",
            "market": "IN",
            "primary_provider": "news_aggregator",
            "source": "indian_api",
            "fallback_used": True,
            "data_status": "complete",
            "provenance": {
                "primary_provider": "news_aggregator",
                "source": "indian_api",
                "fallback_used": True,
                "data_status": "complete",
            },
            "articles": [
                {"title": "LT update", "summary": "Order win.", "source": "Financial Express"},
            ],
        }

        sentiment_classifier = MagicMock(return_value={"label": "positive", "confidence": 0.9})
        llm_service = MagicMock(return_value="News analysis complete.")
        agent = NewsIntelligenceAgent(
            news_tool=lambda **kwargs: news_dict,
            ticker="LT",
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        result = agent.run("Show LT news.")

        self.assertIn("provenance", result.data)
        self.assertTrue(result.data["provenance"]["news"]["fallback_used"])
        self.assertEqual(result.data["provenance"]["news"]["source"], "indian_api")

    def test_missing_optional_news_sections_do_not_break_agent(self):
        from apps.ai.graph.contracts import ResearchContext

        ctx = ResearchContext(
            ticker="INFY",
            market="IN",
            news=None,
        )

        agent = NewsIntelligenceAgent()
        result = agent.run(ctx)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "News analysis for INFY: no recent news articles found.")
        self.assertEqual(result.data["articles"], [])

    def test_context_payload_is_bounded_and_removes_unnecessary_raw_fields(self):
        news_dict = {
            "ticker": "LT",
            "articles": [
                {
                    "title": "Article Title",
                    "summary": "Summary text.",
                    "source": "Reuters",
                    "raw_html": "<html><body>" + "x" * 2000 + "</body></html>",
                    "provider_entity_tokens": ["token1", "token2"],
                }
            ],
        }

        sentiment_classifier = MagicMock(return_value={"label": "neutral", "confidence": 0.7})
        llm_service = MagicMock(return_value="Clean summary.")
        agent = NewsIntelligenceAgent(
            news_tool=lambda **kwargs: news_dict,
            ticker="LT",
            sentiment_classifier=sentiment_classifier,
            llm_service=llm_service,
        )

        agent.run("Show LT news.")

        prompt_content = llm_service.call_args[0][0][1]["content"]
        self.assertNotIn("raw_html", prompt_content)
        self.assertNotIn("provider_entity_tokens", prompt_content)


