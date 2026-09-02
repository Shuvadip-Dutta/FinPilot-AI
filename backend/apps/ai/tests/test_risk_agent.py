import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.agents.risk import RiskAnalysisAgent
from apps.ai.exceptions import LLMError
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult


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
        mock_llm_service.assert_called_once_with(model="reasoning")

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
        mock_llm_service.assert_called_once_with(model="reasoning")

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
        mock_llm_service.assert_not_called()

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
