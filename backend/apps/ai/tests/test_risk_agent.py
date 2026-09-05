import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.agents.risk import RiskAnalysisAgent
from apps.ai.exceptions import LLMError
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult
from apps.ai.services.token_budget import (
    DegradationTier,
    LLMUsage,
    TokenBudgetManager,
)



class RiskAnalysisAgentTestCase(SimpleTestCase):

    def test_agent_name(self):
        agent = RiskAnalysisAgent()
        self.assertEqual(agent.name, "risk")

    @patch("apps.ai.agents.risk.LLMService")
    def test_all_research_results_available(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Risk is moderate and balanced.")

        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(
                    response="Financial analysis available.",
                    tools_used=[],
                ),
                "market": AgentResult(
                    response="Market analysis available.",
                    tools_used=[],
                ),
                "news": AgentResult(
                    response="News analysis available.",
                    tools_used=[],
                ),
            },
        )

        result = RiskAnalysisAgent().run(state)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "Risk is moderate and balanced.")
        self.assertEqual(result.tools_used, [])
        mock_llm_service.assert_called_once_with(model="risk")

        messages = mock_llm_service.return_value.call_args[0][0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Assess Reliance risk.", messages[1]["content"])

        context = json.loads(messages[1]["content"])
        self.assertEqual(context["TICKER"], "RELIANCE")
        self.assertEqual(context["MARKET"], "IN")
        self.assertEqual(context["FINANCIAL RESEARCH"], "Financial analysis available.")
        self.assertEqual(context["MARKET RESEARCH"], "Market analysis available.")
        self.assertEqual(context["NEWS INTELLIGENCE"], "News analysis available.")
        self.assertIn("FINANCIAL RESEARCH", messages[1]["content"])

    @patch("apps.ai.agents.risk.LLMService")
    def test_partial_research_data_uses_available_results_and_missing_indicators(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Risk is moderate due to market weakness.")

        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "market": AgentResult(
                    response="Market analysis available.",
                    tools_used=[],
                ),
            },
        )

        result = RiskAnalysisAgent().run(state)

        self.assertEqual(result.response, "Risk is moderate due to market weakness.")
        self.assertEqual(result.tools_used, [])
        mock_llm_service.assert_called_once_with(model="risk")

        messages = mock_llm_service.return_value.call_args[0][0]
        context = json.loads(messages[1]["content"])
        self.assertEqual(context["MARKET RESEARCH"], "Market analysis available.")
        self.assertIn("Financial research data is unavailable.", context["MISSING INFORMATION"])
        self.assertIn("News intelligence is unavailable.", context["MISSING INFORMATION"])
        self.assertNotIn("Current market data is unavailable.", context["MISSING INFORMATION"])

    @patch("apps.ai.agents.risk.LLMService")
    def test_no_research_results_available_returns_deterministic_message(self, mock_llm_service):
        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
        )

        result = RiskAnalysisAgent().run(state)

        self.assertEqual(
            result.response,
            "Risk analysis for RELIANCE: Financial research data is unavailable. Current market data is unavailable. News intelligence is unavailable.",
        )
        self.assertEqual(result.tools_used, [])
        mock_llm_service.return_value.assert_not_called()

    @patch("apps.ai.agents.risk.LLMService")
    def test_missing_financial_result_is_explicitly_flagged(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Risk is driven by market and news pressure.")

        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "market": AgentResult(
                    response="Market analysis available.",
                    tools_used=[],
                ),
                "news": AgentResult(
                    response="News analysis available.",
                    tools_used=[],
                ),
            },
        )

        result = RiskAnalysisAgent().run(state)

        self.assertEqual(result.response, "Risk is driven by market and news pressure.")
        context = json.loads(mock_llm_service.return_value.call_args[0][0][1]["content"])
        self.assertIn("Financial research data is unavailable.", context["MISSING INFORMATION"])
        self.assertEqual(context["MARKET RESEARCH"], "Market analysis available.")
        self.assertEqual(context["NEWS INTELLIGENCE"], "News analysis available.")

    @patch("apps.ai.agents.risk.LLMService")
    def test_missing_market_result_is_explicitly_flagged(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Risk is shaped by financial and news conditions.")

        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(
                    response="Financial analysis available.",
                    tools_used=[],
                ),
                "news": AgentResult(
                    response="News analysis available.",
                    tools_used=[],
                ),
            },
        )

        result = RiskAnalysisAgent().run(state)

        self.assertEqual(result.response, "Risk is shaped by financial and news conditions.")
        context = json.loads(mock_llm_service.return_value.call_args[0][0][1]["content"])
        self.assertIn("Current market data is unavailable.", context["MISSING INFORMATION"])
        self.assertEqual(context["FINANCIAL RESEARCH"], "Financial analysis available.")
        self.assertEqual(context["NEWS INTELLIGENCE"], "News analysis available.")

    @patch("apps.ai.agents.risk.LLMService")
    def test_missing_news_result_is_explicitly_flagged(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Risk is dominated by financial and market conditions.")

        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(
                    response="Financial analysis available.",
                    tools_used=[],
                ),
                "market": AgentResult(
                    response="Market analysis available.",
                    tools_used=[],
                ),
            },
        )

        result = RiskAnalysisAgent().run(state)

        self.assertEqual(result.response, "Risk is dominated by financial and market conditions.")
        context = json.loads(mock_llm_service.return_value.call_args[0][0][1]["content"])
        self.assertIn("News intelligence is unavailable.", context["MISSING INFORMATION"])
        self.assertEqual(context["FINANCIAL RESEARCH"], "Financial analysis available.")
        self.assertEqual(context["MARKET RESEARCH"], "Market analysis available.")

    @patch("apps.ai.agents.risk.LLMService")
    def test_llm_error_is_not_silently_swallowed(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(side_effect=LLMError("Groq unavailable"))

        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(
                    response="Financial analysis available.",
                    tools_used=[],
                ),
                "market": AgentResult(
                    response="Market analysis available.",
                    tools_used=[],
                ),
                "news": AgentResult(
                    response="News analysis available.",
                    tools_used=[],
                ),
            },
        )

        with self.assertRaises(LLMError):
            RiskAnalysisAgent().run(state)

    def test_run_returns_agent_result_on_deterministic_and_llm_paths(self):
        deterministic = RiskAnalysisAgent().run(
            AgentState(user_message="Assess TCS risk.", ticker="TCS", market="IN")
        )
        self.assertIsInstance(deterministic, AgentResult)

        llm = RiskAnalysisAgent(llm_service=lambda messages: "Risk is moderate.").run(
            AgentState(
                user_message="Assess TCS risk.",
                ticker="TCS",
                market="IN",
                results={
                    "financial": AgentResult(response="Financial analysis available.", tools_used=[]),
                    "market": AgentResult(response="Market analysis available.", tools_used=[]),
                    "news": AgentResult(response="News analysis available.", tools_used=[]),
                },
            )
        )
        self.assertIsInstance(llm, AgentResult)

    @patch("apps.ai.agents.risk.LLMService")
    def test_prompt_context_safety_uses_specialist_result_content_not_agent_state(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Risk is moderate.")
        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(response="Financial analysis available.", tools_used=[]),
                "market": AgentResult(response="Market analysis available.", tools_used=[]),
                "news": AgentResult(response="News analysis available.", tools_used=[]),
            },
            errors=["unexpected bug"],
        )

        RiskAnalysisAgent().run(state)

        context = json.loads(mock_llm_service.return_value.call_args[0][0][1]["content"])
        self.assertEqual(context["FINANCIAL RESEARCH"], "Financial analysis available.")
        self.assertEqual(context["MARKET RESEARCH"], "Market analysis available.")
        self.assertEqual(context["NEWS INTELLIGENCE"], "News analysis available.")
        self.assertNotIn("unexpected bug", json.dumps(context))

    @patch("apps.ai.agents.risk.LLMService")
    def test_prompt_explicitly_prohibits_hallucinated_quantitative_risk_metrics(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Risk is moderate.")

        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(response="Financial analysis available.", tools_used=[]),
                "market": AgentResult(response="Market analysis available.", tools_used=[]),
                "news": AgentResult(response="News analysis available.", tools_used=[]),
            },
        )

        RiskAnalysisAgent().run(state)

        system_prompt = mock_llm_service.return_value.call_args[0][0][0]["content"]
        self.assertIn("Do not invent unsupported quantitative risk metrics", system_prompt)
        self.assertIn("VaR", system_prompt)
        self.assertIn("Sharpe", system_prompt)

    @patch("apps.ai.agents.risk.LLMService")
    def test_structured_market_and_news_evidence_is_passed_to_risk(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Risk uses the supplied evidence.")
        market_data = {
            "ticker": "RELIANCE",
            "market": "IN",
            "market_data": {"quotes": [
                {"exchange": "BSE", "price": 1307.35},
                {"exchange": "NSE", "price": 1309.0},
            ]},
        }
        news_data = {
            "ticker": "RELIANCE",
            "articles": [{"sentiment": {"label": "positive", "confidence": 0.9}}],
            "aggregated_sentiment": {
                "positive": 1, "neutral": 0, "negative": 0,
                "unavailable": 0, "average_confidence": 0.9,
            },
        }
        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(response="Financial prose.", tools_used=[], data={"revenue": 100}),
                "market": AgentResult(response="Market prose omits prices.", tools_used=[], data=market_data),
                "news": AgentResult(response="Sentiment: 90% positive.", tools_used=[], data=news_data),
            },
        )

        RiskAnalysisAgent().run(state)

        context = json.loads(mock_llm_service.return_value.call_args[0][0][1]["content"])
        self.assertEqual(context["FINANCIAL RESEARCH"], "Financial prose.")
        self.assertEqual(context["MARKET RESEARCH"], "Market prose omits prices.")
        self.assertEqual(context["NEWS INTELLIGENCE"], "Sentiment: 90% positive.")
        self.assertEqual(context["MARKET STRUCTURED EVIDENCE"], market_data)
        self.assertEqual(context["NEWS STRUCTURED EVIDENCE"], news_data)
        self.assertEqual(context["FINANCIAL STRUCTURED EVIDENCE"], {"revenue": 100})
        serialized_context = json.dumps(context)
        self.assertEqual(serialized_context.count('"revenue": 100'), 1)
        self.assertEqual(serialized_context.count('"exchange": "BSE"'), 1)
        self.assertEqual(serialized_context.count('"exchange": "NSE"'), 1)
        self.assertEqual(serialized_context.count('"positive": 1'), 1)

    def test_prose_only_agent_results_remain_supported(self):
        agent = RiskAnalysisAgent(llm_service=lambda messages: "Fallback risk.")
        result = agent.run(AgentState(
            user_message="Assess risk.",
            results={
                "financial": AgentResult(response="Financial prose.", tools_used=[]),
                "market": AgentResult(response="Market prose.", tools_used=[]),
                "news": AgentResult(response="News prose.", tools_used=[]),
            },
        ))

        self.assertEqual(result.response, "Fallback risk.")

    @patch("apps.ai.agents.risk.LLMService")
    def test_news_aggregate_is_forwarded_exactly_without_recalculation(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Risk uses authoritative sentiment.")
        aggregate = {
            "positive": 4,
            "neutral": 4,
            "negative": 2,
            "unavailable": 0,
            "average_confidence": 0.7638,
        }
        news_data = {
            "ticker": "RELIANCE",
            "articles": [{"sentiment": {"label": "positive", "confidence": 0.9}}] * 10,
            "aggregated_sentiment": aggregate,
        }
        state = AgentState(
            user_message="Assess risk.",
            ticker="RELIANCE",
            results={
                "news": AgentResult(response="News prose says 3 negative.", tools_used=[], data=news_data),
            },
        )

        RiskAnalysisAgent().run(state)

        context = json.loads(mock_llm_service.return_value.call_args[0][0][1]["content"])
        self.assertEqual(
            context["NEWS STRUCTURED EVIDENCE"]["aggregated_sentiment"],
            aggregate,
        )

    @patch("apps.ai.agents.risk.LLMService")
    def test_structured_context_is_reduced_without_losing_authoritative_values(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Risk uses reduced evidence.")
        market_data = {
            "ticker": "RELIANCE", "market": "IN",
            "market_data": {"quotes": [{"exchange": "BSE", "price": 1307.35}, {"exchange": "NSE", "price": 1309.0}]},
            "historical_data": {"candles": [{"timestamp": str(index), "close": index} for index in range(30)]},
        }
        news_data = {
            "ticker": "RELIANCE",
            "articles": [{"title": "Headline", "summary": "x" * 5000, "source": "source", "sentiment": {"label": "positive", "confidence": 0.9}}],
            "aggregated_sentiment": {"positive": 1, "neutral": 0, "negative": 0, "unavailable": 0, "average_confidence": 0.9},
        }
        financial_data = {
            "ticker": "RELIANCE",
            "financials": [{"fiscal_year": "2026", "metrics": [{"key": "revenue", "value": 100}, {"key": "irrelevant", "value": "x"}]}],
            "unnecessary": "x" * 5000,
        }
        state = AgentState(user_message="Assess risk.", ticker="RELIANCE", market="IN", results={
            "financial": AgentResult(response="Financial prose.", tools_used=[], data=financial_data),
            "market": AgentResult(response="Market prose.", tools_used=[], data=market_data),
            "news": AgentResult(response="News prose.", tools_used=[], data=news_data),
        })

        RiskAnalysisAgent().run(state)

        context = json.loads(mock_llm_service.return_value.call_args[0][0][1]["content"])
        self.assertLess(len(mock_llm_service.return_value.call_args[0][0][1]["content"]), 10000)
        self.assertEqual(context["MARKET STRUCTURED EVIDENCE"]["market_data"]["quotes"][1]["price"], 1309.0)
        self.assertEqual(len(context["MARKET STRUCTURED EVIDENCE"]["historical_data"]["candles"]), 20)
        self.assertEqual(context["NEWS STRUCTURED EVIDENCE"]["aggregated_sentiment"]["positive"], 1)
        self.assertEqual(context["FINANCIAL STRUCTURED EVIDENCE"]["financials"][0]["metrics"][0]["value"], 100)
        serialized = json.dumps(context)
        self.assertEqual(serialized.count('"price": 1309.0'), 1)
        self.assertNotIn("x" * 5000, serialized)

    @patch("apps.ai.agents.risk.LLMService")
    def test_risk_context_bound_is_deterministic(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Bounded risk.")
        oversized = {"payload": "large " * 5000}
        state = AgentState(
            user_message="Assess risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(response="financial " * 1000, tools_used=[], data=oversized),
                "market": AgentResult(response="market " * 1000, tools_used=[], data={
                    "ticker": "RELIANCE", "market": "IN",
                    "market_data": {"quotes": [
                        {"exchange": "BSE", "price": 1307.35},
                        {"exchange": "NSE", "price": 1309.0},
                    ]},
                }),
                "news": AgentResult(response="news " * 1000, tools_used=[], data={
                    "ticker": "RELIANCE",
                    "aggregated_sentiment": {"positive": 2, "neutral": 1, "negative": 0, "unavailable": 0},
                    "articles": [{"title": "Headline", "sentiment": {"label": "positive"}}] * 20,
                }),
            },
        )

        agent = RiskAnalysisAgent()
        first = agent._build_bounded_context(
            state, state.results["financial"], state.results["market"], state.results["news"], []
        )
        second = agent._build_bounded_context(
            state, state.results["financial"], state.results["market"], state.results["news"], []
        )

        self.assertEqual(first, second)
        self.assertLessEqual(agent._serialized_size(first), agent.RISK_CONTEXT_CHAR_LIMIT)

    def test_constrained_tier_uses_compact_context_and_1000_token_limit(self):
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

        llm_service = MagicMock(return_value="Constrained risk assessment.")
        llm_service.token_budget_manager = manager

        agent = RiskAnalysisAgent(llm_service=llm_service)
        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(response="Financial prose." * 50, tools_used=[]),
                "market": AgentResult(response="Market prose." * 50, tools_used=[]),
                "news": AgentResult(response="News prose." * 50, tools_used=[]),
            },
        )

        result = agent.run(state)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "Constrained risk assessment.")
        self.assertEqual(result.tools_used, [])
        llm_service.assert_called_once()

        _, kwargs = llm_service.call_args
        self.assertEqual(kwargs.get("max_completion_tokens"), 1000)

    def test_critical_tier_uses_minimal_context_and_512_token_limit(self):
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

        llm_service = MagicMock(return_value="Critical risk assessment.")
        llm_service.token_budget_manager = manager

        agent = RiskAnalysisAgent(llm_service=llm_service)
        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(response="Financial prose.", tools_used=[], data={"revenue": 100}),
                "market": AgentResult(response="Market prose.", tools_used=[]),
                "news": AgentResult(response="News prose.", tools_used=[]),
            },
        )

        result = agent.run(state)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "Critical risk assessment.")
        llm_service.assert_called_once()

        _, kwargs = llm_service.call_args
        self.assertEqual(kwargs.get("max_completion_tokens"), 512)

        messages = llm_service.call_args[0][0]
        context = json.loads(messages[1]["content"])
        self.assertEqual(context["FINANCIAL RESEARCH"], "")

    def test_exhausted_tier_bypasses_llm_and_returns_valid_agent_result(self):
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

        llm_service = MagicMock(return_value="Should not be called.")
        llm_service.token_budget_manager = manager

        agent = RiskAnalysisAgent(llm_service=llm_service)
        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(response="Financial prose.", tools_used=[], data={"revenue": 100}),
            },
        )

        result = agent.run(state)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(
            result.response,
            "Risk analysis for RELIANCE could not be completed: the LLM budget is exhausted.",
        )
        self.assertEqual(result.tools_used, [])
        self.assertIn("financial", result.data)
        self.assertIn("missing_information", result.data)
        llm_service.assert_not_called()

    def test_risk_agent_consumes_canonical_research_context(self):
        from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
        from apps.research.services.schemas import (
            CompanyProfile,
            ExchangeQuote,
            HistoricalMarketData,
            NewsArticle,
            NewsResearch,
        )

        profile = CompanyProfile(ticker="LT", name="Larsen & Toubro Ltd", exchange="NSE", country="India")
        market_data = HistoricalMarketData(
            ticker="LT",
            candles=[],
        )
        market_data.quotes = [ExchangeQuote(exchange="NSE", price=1400.0, percent_change=None, year_high=None, year_low=None)]
        news = NewsResearch(
            ticker="LT",
            articles=[NewsArticle(title="Order win", summary="Mega order.", source="Reuters", url="", published_at="2026-09-01")],
        )
        prov = {
            "financials": ProviderProvenance(primary_provider="upstox", source="upstox", fallback_used=False, data_status="complete"),
            "market_data": ProviderProvenance(primary_provider="upstox", source="upstox", fallback_used=False, data_status="complete"),
            "news": ProviderProvenance(primary_provider="news_aggregator", source="marketaux", fallback_used=False, data_status="complete"),
        }
        ctx = ResearchContext(
            ticker="LT",
            market="IN",
            company_profile=profile,
            market_data=market_data,
            news=news,
            provenance=prov,
        )

        llm_service = MagicMock(return_value="LT risk is well managed.")
        agent = RiskAnalysisAgent(llm_service=llm_service)

        result = agent.run(ctx)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "LT risk is well managed.")
        self.assertIn("provenance", result.data)
        self.assertEqual(result.data["provenance"]["financials"]["source"], "upstox")
        self.assertEqual(result.data["provenance"]["market_data"]["source"], "upstox")
        self.assertEqual(result.data["provenance"]["news"]["source"], "marketaux")

    def test_provenance_survives_from_specialist_results_into_risk_context(self):
        financial_result = AgentResult(
            response="Financial analysis.",
            tools_used=[],
            data={
                "provenance": {
                    "financials": {
                        "primary_provider": "upstox",
                        "source": "indian_api",
                        "fallback_used": True,
                        "data_status": "complete",
                    }
                }
            },
        )
        market_result = AgentResult(
            response="Market analysis.",
            tools_used=[],
            data={
                "provenance": {
                    "market_data": {
                        "primary_provider": "upstox",
                        "source": "upstox",
                        "fallback_used": False,
                        "data_status": "complete",
                    }
                }
            },
        )
        state = AgentState(
            user_message="Assess risk for LT",
            ticker="LT",
            market="IN",
            results={
                "financial": financial_result,
                "market": market_result,
            },
        )

        llm_service = MagicMock(return_value="Risk evaluation complete.")
        agent = RiskAnalysisAgent(llm_service=llm_service)

        result = agent.run(state)

        self.assertIn("provenance", result.data)
        self.assertTrue(result.data["provenance"]["financials"]["fallback_used"])
        self.assertEqual(result.data["provenance"]["financials"]["source"], "indian_api")
        self.assertFalse(result.data["provenance"]["market_data"]["fallback_used"])

    def test_missing_optional_sections_in_risk_research_context(self):
        from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
        from apps.research.services.schemas import ExchangeQuote, HistoricalMarketData

        market_data = HistoricalMarketData(ticker="INFY", candles=[])
        market_data.quotes = [ExchangeQuote(exchange="NSE", price=1500.0, percent_change=None, year_high=None, year_low=None)]
        ctx = ResearchContext(
            ticker="INFY",
            market="IN",
            market_data=market_data,
            financials=None,
            news=None,
        )

        llm_service = MagicMock(return_value="Market-only risk assessment.")
        agent = RiskAnalysisAgent(llm_service=llm_service)

        result = agent.run(ctx)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "Market-only risk assessment.")
        prompt_content = llm_service.call_args[0][0][1]["content"]
        self.assertIn("Financial research data is unavailable", prompt_content)
        self.assertIn("News intelligence is unavailable", prompt_content)

    def test_risk_agent_bounded_context_no_raw_data_duplication(self):
        from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
        from apps.research.services.schemas import (
            CompanyProfile,
            ExchangeQuote,
            HistoricalMarketData,
            NewsArticle,
            NewsResearch,
        )

        profile = CompanyProfile(ticker="LT", name="Larsen & Toubro Ltd", exchange="NSE", country="India")
        market_data = HistoricalMarketData(
            ticker="LT",
            candles=[],
        )
        market_data.quotes = [ExchangeQuote(exchange="NSE", price=1400.0, percent_change=None, year_high=None, year_low=None)]
        news = NewsResearch(
            ticker="LT",
            articles=[NewsArticle(title="Order win", summary="Order details " * 200, source="Reuters", url="", published_at="2026-09-01")],
        )
        ctx = ResearchContext(
            ticker="LT",
            market="IN",
            company_profile=profile,
            market_data=market_data,
            news=news,
        )

        llm_service = MagicMock(return_value="Bounded risk assessment.")
        agent = RiskAnalysisAgent(llm_service=llm_service)

        result = agent.run(ctx)

        self.assertIsInstance(result, AgentResult)
        prompt_content = llm_service.call_args[0][0][1]["content"]
        self.assertLess(len(prompt_content), 12000)


