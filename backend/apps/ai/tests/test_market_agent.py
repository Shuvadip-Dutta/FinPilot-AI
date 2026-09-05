import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.agents.market import MarketAnalysisAgent
from apps.ai.exceptions import LLMError
from apps.ai.services.schemas import AgentResult
from apps.ai.services.token_budget import (
    DegradationTier,
    LLMUsage,
    TokenBudgetManager,
)


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

        mock_llm_service.assert_called_once_with(model="market")

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

    def test_constrained_tier_reduces_historical_candles_and_caps_output(self):
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

        market_data = normalized_market_data()
        candles = [
            {"timestamp": f"2026-08-{i:02d}", "close": 1000 + i}
            for i in range(1, 31)
        ]
        historical_data_tool = MagicMock(return_value={"candles": candles})
        llm_service = MagicMock(return_value="Constrained analysis.")
        llm_service.token_budget_manager = manager

        agent = MarketAnalysisAgent(
            market_data_tool=MagicMock(return_value=market_data),
            historical_data_tool=historical_data_tool,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        result = agent.run("Show market data from 2026-08-01 to 2026-08-30.")

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "Constrained analysis.")
        llm_service.assert_called_once()
        _, kwargs = llm_service.call_args
        self.assertEqual(kwargs.get("max_completion_tokens"), 512)

        messages = llm_service.call_args[0][0]
        prompt_content = messages[1]["content"]
        self.assertIn("historical_market_data", prompt_content)
        prompt_json = json.loads(prompt_content)
        self.assertEqual(
            len(prompt_json["historical_market_data"]["candles"]), 15
        )
        self.assertEqual(len(result.data["historical_data"]["candles"]), 30)
        self.assertEqual(len(result.data["market_data"]["quotes"]), 2)

    def test_critical_tier_reduces_historical_candles_further_and_caps_output(
        self,
    ):
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

        market_data = normalized_market_data()
        candles = [
            {"timestamp": f"2026-08-{i:02d}", "close": 1000 + i}
            for i in range(1, 31)
        ]
        historical_data_tool = MagicMock(return_value={"candles": candles})
        llm_service = MagicMock(return_value="Critical analysis.")
        llm_service.token_budget_manager = manager

        agent = MarketAnalysisAgent(
            market_data_tool=MagicMock(return_value=market_data),
            historical_data_tool=historical_data_tool,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        result = agent.run("Show market data from 2026-08-01 to 2026-08-30.")

        self.assertEqual(result.response, "Critical analysis.")
        llm_service.assert_called_once()
        _, kwargs = llm_service.call_args
        self.assertEqual(kwargs.get("max_completion_tokens"), 256)

        messages = llm_service.call_args[0][0]
        prompt_json = json.loads(messages[1]["content"])
        self.assertEqual(
            len(prompt_json["historical_market_data"]["candles"]), 5
        )
        self.assertEqual(len(result.data["historical_data"]["candles"]), 30)

    def test_exhausted_tier_bypasses_llm_and_returns_deterministic_summary(
        self,
    ):
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

        market_data = normalized_market_data()
        candles = [{"timestamp": "2026-08-01", "close": 1250.0}]
        historical_data_tool = MagicMock(return_value={"candles": candles})
        llm_service = MagicMock(return_value="Should not be called.")
        llm_service.token_budget_manager = manager

        agent = MarketAnalysisAgent(
            market_data_tool=MagicMock(return_value=market_data),
            historical_data_tool=historical_data_tool,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        result = agent.run("Show market data from 2026-08-01 to 2026-08-30.")

        self.assertIsInstance(result, AgentResult)
        self.assertIn("BSE: 1307.35", result.response)
        self.assertIn("NSE: 1309.0", result.response)
        self.assertIn("Historical data: 1 candle(s)", result.response)
        self.assertEqual(
            result.tools_used, ["get_market_data", "get_historical_data"]
        )
        self.assertEqual(
            result.data["market_data"]["quotes"][0]["price"], 1307.35
        )
        llm_service.assert_not_called()

    def test_market_agent_consumes_canonical_research_context(self):
        from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
        from apps.research.services.schemas import ExchangeQuote, HistoricalMarketData

        quotes = [
            ExchangeQuote(exchange="NSE", price=1400.0, percent_change=1.2, year_high=1600.0, year_low=1200.0),
            ExchangeQuote(exchange="BSE", price=1398.5, percent_change=1.1, year_high=1600.0, year_low=1200.0),
        ]
        market_data = HistoricalMarketData(ticker="LT", candles=[])
        market_data.quotes = quotes
        prov = {
            "market_data": ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                fallback_used=False,
                data_status="complete",
            )
        }
        ctx = ResearchContext(
            ticker="LT",
            market="IN",
            market_data=market_data,
            provenance=prov,
        )

        llm_service = MagicMock(return_value="LT market data is active.")
        agent = MarketAnalysisAgent(llm_service=llm_service)

        result = agent.run(ctx)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "LT market data is active.")
        self.assertEqual(result.data["ticker"], "LT")
        self.assertIn("provenance", result.data)
        self.assertEqual(result.data["provenance"]["market_data"]["source"], "upstox")
        self.assertEqual(len(result.data["market_data"]["quotes"]), 2)

    def test_provenance_survives_from_market_tool_dict_into_agent_context(self):
        market_dict = {
            "ticker": "LT",
            "market": "IN",
            "primary_provider": "upstox",
            "source": "indian_api",
            "fallback_used": True,
            "data_status": "complete",
            "fallback_reason": "upstox_exception",
            "provenance": {
                "primary_provider": "upstox",
                "source": "indian_api",
                "fallback_used": True,
                "data_status": "complete",
                "fallback_reason": "upstox_exception",
            },
            "quotes": [{"exchange": "NSE", "price": 1400.0}],
        }

        llm_service = MagicMock(return_value="Market fallback analysis complete.")
        agent = MarketAnalysisAgent(
            market_data_tool=lambda **kwargs: market_dict,
            historical_data_tool=lambda **kwargs: {"candles": []},
            ticker="LT",
            llm_service=llm_service,
        )

        result = agent.run("Analyze LT market data.")

        self.assertIn("provenance", result.data)
        self.assertTrue(result.data["provenance"]["market_data"]["fallback_used"])
        self.assertEqual(result.data["provenance"]["market_data"]["source"], "indian_api")

    def test_missing_optional_market_sections_do_not_break_agent(self):
        from apps.ai.graph.contracts import ResearchContext

        ctx = ResearchContext(
            ticker="INFY",
            market="IN",
            market_data=None,
        )

        llm_service = MagicMock(return_value="No market data available.")
        agent = MarketAnalysisAgent(llm_service=llm_service)

        result = agent.run(ctx)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.data["ticker"], "INFY")
        self.assertNotIn("market_data", result.data)

    def test_context_payload_is_bounded_and_removes_unnecessary_raw_fields(self):
        market_dict = {
            "ticker": "LT",
            "market": "IN",
            "raw_provider_payload": "x" * 1000,
            "internal_debug_info": {"unparsed": "y" * 500},
            "quotes": [{"exchange": "NSE", "price": 1400.0, "raw_feed_flags": 12345}],
        }

        llm_service = MagicMock(return_value="Analyzed market data.")
        agent = MarketAnalysisAgent(
            market_data_tool=lambda **kwargs: market_dict,
            ticker="LT",
            llm_service=llm_service,
        )

        agent.run("Analyze LT market data.")

        prompt_content = llm_service.call_args[0][0][1]["content"]
        self.assertNotIn("raw_provider_payload", prompt_content)
        self.assertNotIn("internal_debug_info", prompt_content)
        self.assertNotIn("raw_feed_flags", prompt_content)

