from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.agents.news import NewsIntelligenceAgent
from apps.ai.exceptions import LLMError
from apps.ai.services.schemas import AgentResult


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
        mock_llm_service.assert_called_once_with(model="fast")

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
