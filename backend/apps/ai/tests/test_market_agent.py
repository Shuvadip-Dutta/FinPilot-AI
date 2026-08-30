from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.ai.agents.market import MarketAnalysisAgent
from apps.ai.services.schemas import AgentResult


class MarketAnalysisAgentTestCase(SimpleTestCase):

    def test_agent_name(self):
        agent = MarketAnalysisAgent()

        self.assertEqual(agent.name, "market")

    def test_successful_current_market_analysis(self):
        agent = MarketAnalysisAgent(
            market_data_tool=lambda **kwargs: {"last_price": 1287.0},
            historical_data_tool=lambda **kwargs: {"candles": []},
            ticker="RELIANCE",
        )

        result = agent.run("What is the current price?")

        self.assertEqual(
            result.response,
            "Market analysis for RELIANCE: current price 1287.0.",
        )
        self.assertEqual(result.tools_used, ["get_market_data"])

    def test_historical_data_path(self):
        calls = []

        def historical_data_tool(**kwargs):
            calls.append(kwargs)
            return {
                "candles": [
                    {"close": 1250.0},
                    {"close": 1287.0},
                ]
            }

        agent = MarketAnalysisAgent(
            market_data_tool=lambda **kwargs: {"last_price": 1287.0},
            historical_data_tool=historical_data_tool,
            ticker="RELIANCE",
            from_date="2026-08-01",
            to_date="2026-08-28",
        )

        result = agent.run("Show historical market data.")

        self.assertIn("2 candle(s), latest close 1287.0", result.response)
        self.assertEqual(
            result.tools_used,
            ["get_market_data", "get_historical_data"],
        )
        self.assertEqual(
            calls,
            [
                {
                    "ticker": "RELIANCE",
                    "to_date": "2026-08-28",
                    "from_date": "2026-08-01",
                    "market": "IN",
                }
            ],
        )

    def test_dates_are_extracted_from_message(self):
        market_data_tool = MagicMock(
            return_value={"last_price": 1287.0}
        )
        historical_data_tool = MagicMock(
            return_value={"candles": []}
        )
        agent = MarketAnalysisAgent(
            market_data_tool=market_data_tool,
            historical_data_tool=historical_data_tool,
            ticker="RELIANCE",
        )

        result = agent.run(
            "Show Reliance market data from 2026-08-01 to 2026-08-28."
        )

        market_data_tool.assert_called_once_with(
            ticker="RELIANCE",
            market="IN",
        )
        historical_data_tool.assert_called_once_with(
            ticker="RELIANCE",
            to_date="2026-08-28",
            from_date="2026-08-01",
            market="IN",
        )
        self.assertIsInstance(result, AgentResult)
        self.assertEqual(
            result.tools_used,
            ["get_market_data", "get_historical_data"],
        )

    def test_missing_ticker_returns_request_for_ticker(self):
        agent = MarketAnalysisAgent()

        result = agent.run("What is the current market price?")

        self.assertIn("Please provide a ticker symbol", result.response)
        self.assertEqual(result.tools_used, [])

    def test_tool_failure_returns_agent_result(self):
        def failing_market_data_tool(**kwargs):
            raise ValueError("Market data unavailable")

        agent = MarketAnalysisAgent(
            market_data_tool=failing_market_data_tool,
            ticker="RELIANCE",
        )

        result = agent.run("What is the current price?")

        self.assertIn("Market data unavailable", result.response)
        self.assertEqual(result.tools_used, [])

    def test_run_returns_agent_result(self):
        agent = MarketAnalysisAgent(
            market_data_tool=lambda **kwargs: {"last_price": 1287.0},
            ticker="RELIANCE",
        )

        self.assertIsInstance(
            agent.run("What is the current price?"),
            AgentResult,
        )

    def test_injected_tools_prevent_real_api_or_llm_calls(self):
        calls = []

        def market_data_tool(**kwargs):
            calls.append(kwargs)
            return {"last_price": 3500.0}

        agent = MarketAnalysisAgent(
            market_data_tool=market_data_tool,
            ticker="TCS",
        )

        agent.run("What is the current price?")

        self.assertEqual(
            calls,
            [{"ticker": "TCS", "market": "IN"}],
        )
