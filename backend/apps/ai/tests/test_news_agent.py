from django.test import SimpleTestCase

from apps.ai.agents.news import NewsIntelligenceAgent
from apps.ai.services.schemas import AgentResult


class NewsIntelligenceAgentTestCase(SimpleTestCase):

    def test_agent_name(self):
        agent = NewsIntelligenceAgent()

        self.assertEqual(
            agent.name,
            "news",
        )

    def test_successful_news_analysis(self):
        def news_tool(**kwargs):
            return {
                "ticker": "RELIANCE",
                "articles": [
                    {
                        "title": "Reliance update",
                        "source": "upstox.com",
                        "relevance_type": "DIRECT",
                    },
                    {
                        "title": "Market update",
                        "source": "livemint.com",
                        "relevance_type": "RELATED",
                    },
                ],
            }

        agent = NewsIntelligenceAgent(
            news_tool=news_tool,
            ticker="RELIANCE",
        )

        result = agent.run(
            "Show me the latest news about Reliance."
        )

        self.assertIn(
            "News analysis for RELIANCE",
            result.response,
        )

        self.assertIn(
            "2 recent article(s)",
            result.response,
        )

        self.assertIn(
            "1 direct",
            result.response,
        )

        self.assertEqual(
            result.tools_used,
            ["get_news"],
        )

    def test_no_news_returns_clear_message(self):
        agent = NewsIntelligenceAgent(
            news_tool=lambda **kwargs: {
                "ticker": "RELIANCE",
                "articles": [],
            },
            ticker="RELIANCE",
        )

        result = agent.run(
            "Show me the latest news."
        )

        self.assertEqual(
            result.response,
            "News analysis for RELIANCE: "
            "no recent news articles found.",
        )

        self.assertEqual(
            result.tools_used,
            ["get_news"],
        )

    def test_missing_ticker_returns_request_for_ticker(self):
        agent = NewsIntelligenceAgent()

        result = agent.run(
            "Show me the latest company news."
        )

        self.assertIn(
            "Please provide a ticker symbol",
            result.response,
        )

        self.assertEqual(
            result.tools_used,
            [],
        )

    def test_tool_failure_returns_agent_result(self):
        def failing_news_tool(**kwargs):
            raise ValueError("News provider unavailable")

        agent = NewsIntelligenceAgent(
            news_tool=failing_news_tool,
            ticker="RELIANCE",
        )

        result = agent.run(
            "Show Reliance news."
        )

        self.assertIn(
            "News provider unavailable",
            result.response,
        )

        self.assertEqual(
            result.tools_used,
            [],
        )

    def test_run_returns_agent_result(self):
        agent = NewsIntelligenceAgent(
            news_tool=lambda **kwargs: {
                "articles": [],
            },
            ticker="TCS",
        )

        result = agent.run(
            "Show TCS news."
        )

        self.assertIsInstance(
            result,
            AgentResult,
        )

    def test_injected_tool_prevents_real_api_call(self):
        calls = []

        def news_tool(**kwargs):
            calls.append(kwargs)

            return {
                "ticker": "TCS",
                "articles": [],
            }

        agent = NewsIntelligenceAgent(
            news_tool=news_tool,
            ticker="TCS",
            limit=5,
        )

        agent.run("Show TCS news.")

        self.assertEqual(
            calls,
            [
                {
                    "ticker": "TCS",
                    "market": "IN",
                    "limit": 5,
                }
            ],
        )