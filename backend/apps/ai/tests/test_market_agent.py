from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.agents.market import MarketAnalysisAgent
from apps.ai.exceptions import LLMError
from apps.ai.services.schemas import AgentResult


def normalized_market_data():
    return {
        "ticker": "RELIANCE",
        "market": "IN",
        "quotes": [
            {
                "exchange": "BSE",
                "price": 1307.35,
                "percent_change": 1.74,
                "year_high": 1611.2,
                "year_low": 1250.55,
            },
            {
                "exchange": "NSE",
                "price": 1309.0,
                "percent_change": 1.74,
                "year_high": 1611.2,
                "year_low": 1250.55,
            },
        ],
    }


class MarketAnalysisAgentTestCase(SimpleTestCase):

    def test_agent_name(self):
        agent = MarketAnalysisAgent()

        self.assertEqual(agent.name, "market")

    def test_current_market_analysis_uses_fast_model_and_llm(self):
        market_data_tool = MagicMock(return_value=normalized_market_data())
        historical_data_tool = MagicMock(return_value={"candles": []})
        llm_service = MagicMock(return_value="Current price is stable and the market is near recent levels.")

        agent = MarketAnalysisAgent(
            market_data_tool=market_data_tool,
            historical_data_tool=historical_data_tool,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        result = agent.run("What is the current price for RELIANCE?")

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(
            result.response,
            "Current price is stable and the market is near recent levels.",
        )
        self.assertEqual(result.tools_used, ["get_market_data"])
        market_data_tool.assert_called_once_with(ticker="RELIANCE", market="IN")
        historical_data_tool.assert_not_called()
        llm_service.assert_called_once()

        messages = llm_service.call_args[0][0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("current market information", messages[0]["content"])
        self.assertIn("RELIANCE", messages[1]["content"])
        self.assertIn("user_question", messages[1]["content"])
        self.assertIn("current_market_data", messages[1]["content"])
        self.assertIn('"exchange": "BSE"', messages[1]["content"])
        self.assertIn('"exchange": "NSE"', messages[1]["content"])
        self.assertEqual(len(result.data["market_data"]["quotes"]), 2)
        self.assertEqual(result.data["market_data"]["quotes"][0]["price"], 1307.35)
        self.assertIn("Multiple exchange quotes", messages[0]["content"])
        self.assertNotIn("last_price", messages[1]["content"])

    def test_empty_quotes_are_marked_unavailable_without_fabricated_price(self):
        llm_service = MagicMock(return_value="Current market data is unavailable.")
        agent = MarketAnalysisAgent(
            market_data_tool=MagicMock(return_value={
                "ticker": "RELIANCE",
                "market": "IN",
                "quotes": [],
            }),
            llm_service=llm_service,
            ticker="RELIANCE",
        )

        agent.run("What is the current market price for RELIANCE?")

        prompt = llm_service.call_args[0][0]
        self.assertIn("Current market data is unavailable", prompt[1]["content"])
        self.assertNotIn("last_price", prompt[1]["content"])

    def test_summary_preserves_exchange_specific_prices(self):
        summary = MarketAnalysisAgent._build_summary(
            "RELIANCE",
            normalized_market_data(),
            None,
        )

        self.assertIn("BSE: 1307.35", summary)
        self.assertIn("NSE: 1309.0", summary)
        self.assertNotIn("current price 1307.35", summary)

    @patch("apps.ai.agents.market.LLMService")
    def test_uses_fast_model_by_default(self, mock_llm_service):
        MarketAnalysisAgent(
            market_data_tool=lambda **kwargs: {"last_price": 1287.0},
            historical_data_tool=lambda **kwargs: {"candles": []},
            ticker="RELIANCE",
        )

        mock_llm_service.assert_called_once_with(model="fast")

    def test_historical_market_analysis_calls_both_tools(self):
        market_data_tool = MagicMock(return_value={"last_price": 1287.0})
        historical_data_tool = MagicMock(
            return_value={
                "candles": [
                    {"timestamp": "2026-08-01", "close": 1250.0},
                    {"timestamp": "2026-08-28", "close": 1287.0},
                ]
            }
        )
        llm_service = MagicMock(return_value="The recent trend is upward with a narrow range.")

        agent = MarketAnalysisAgent(
            market_data_tool=market_data_tool,
            historical_data_tool=historical_data_tool,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        result = agent.run("Compare RELIANCE market data from 2026-08-01 to 2026-08-28.")

        market_data_tool.assert_called_once_with(ticker="RELIANCE", market="IN")
        historical_data_tool.assert_called_once_with(
            ticker="RELIANCE",
            to_date="2026-08-28",
            from_date="2026-08-01",
            market="IN",
        )
        self.assertEqual(
            result.tools_used,
            ["get_market_data", "get_historical_data"],
        )
        self.assertEqual(
            result.response,
            "The recent trend is upward with a narrow range.",
        )

        prompt_content = llm_service.call_args[0][0][1]["content"]
        self.assertIn("historical_market_data", prompt_content)
        self.assertIn("2026-08-01", prompt_content)
        self.assertIn("2026-08-28", prompt_content)
        self.assertEqual(result.data["historical_data"]["candles"][-1]["close"], 1287.0)

    def test_explicit_constructor_date_range_is_preserved(self):
        market_data_tool = MagicMock(return_value={"last_price": 1287.0})
        historical_data_tool = MagicMock(return_value={"candles": []})
        llm_service = MagicMock(return_value="Range was supplied explicitly.")

        agent = MarketAnalysisAgent(
            market_data_tool=market_data_tool,
            historical_data_tool=historical_data_tool,
            ticker="RELIANCE",
            from_date="2026-08-01",
            to_date="2026-08-28",
            llm_service=llm_service,
        )

        agent.run("Analyze RELIANCE market data.")

        historical_data_tool.assert_called_once_with(
            ticker="RELIANCE",
            to_date="2026-08-28",
            from_date="2026-08-01",
            market="IN",
        )

    def test_dates_are_extracted_from_message(self):
        market_data_tool = MagicMock(return_value={"last_price": 1287.0})
        historical_data_tool = MagicMock(return_value={"candles": []})
        llm_service = MagicMock(return_value="The fetched range is clear.")

        agent = MarketAnalysisAgent(
            market_data_tool=market_data_tool,
            historical_data_tool=historical_data_tool,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        agent.run("Show Reliance market data from 2026-08-01 to 2026-08-28.")

        historical_data_tool.assert_called_once_with(
            ticker="RELIANCE",
            to_date="2026-08-28",
            from_date="2026-08-01",
            market="IN",
        )
        self.assertEqual(
            llm_service.call_args[0][0][1]["content"],
            llm_service.call_args[0][0][1]["content"],
        )

    def test_missing_ticker_returns_request_for_ticker(self):
        llm_service = MagicMock()
        agent = MarketAnalysisAgent(
            market_data_tool=lambda **kwargs: {"last_price": 1287.0},
            historical_data_tool=lambda **kwargs: {"candles": []},
            llm_service=llm_service,
        )

        result = agent.run("What is the current market price?")

        self.assertIn("Please provide a ticker symbol", result.response)
        self.assertEqual(result.tools_used, [])
        llm_service.assert_not_called()

    def test_tool_failure_returns_agent_result(self):
        def failing_market_data_tool(**kwargs):
            raise ValueError("Market data unavailable")

        llm_service = MagicMock()
        agent = MarketAnalysisAgent(
            market_data_tool=failing_market_data_tool,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        result = agent.run("What is the current price?")

        self.assertIn("Market data unavailable", result.response)
        self.assertEqual(result.tools_used, [])
        llm_service.assert_not_called()

    def test_llm_failure_is_not_silently_swallowed(self):
        llm_service = MagicMock(side_effect=LLMError("Groq unavailable"))
        agent = MarketAnalysisAgent(
            market_data_tool=lambda **kwargs: {"last_price": 1287.0},
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        with self.assertRaises(LLMError):
            agent.run("What is the current price for RELIANCE?")

    def test_empty_historical_data_is_explicitly_marked_unavailable(self):
        llm_service = MagicMock(return_value="Historical data was unavailable, so the current price is described alone.")
        agent = MarketAnalysisAgent(
            market_data_tool=lambda **kwargs: {"last_price": 1287.0},
            historical_data_tool=lambda **kwargs: {"candles": []},
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        agent.run("Analyze RELIANCE from 2026-08-01 to 2026-08-28.")

        messages = llm_service.call_args[0][0]
        self.assertIn("Historical data unavailable", messages[1]["content"])

    def test_run_returns_agent_result(self):
        llm_service = MagicMock(return_value="Analysis complete.")
        agent = MarketAnalysisAgent(
            market_data_tool=lambda **kwargs: {"last_price": 1287.0},
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        self.assertIsInstance(
            agent.run("What is the current price?"),
            AgentResult,
        )

    def test_injected_tools_prevent_real_api_calls(self):
        calls = []

        def market_data_tool(**kwargs):
            calls.append(kwargs)
            return {"last_price": 3500.0}

        llm_service = MagicMock(return_value="The latest quote is as expected.")
        agent = MarketAnalysisAgent(
            market_data_tool=market_data_tool,
            ticker="TCS",
            llm_service=llm_service,
        )

        agent.run("What is the current price?")

        self.assertEqual(
            calls,
            [{"ticker": "TCS", "market": "IN"}],
        )
        llm_service.assert_called_once()
