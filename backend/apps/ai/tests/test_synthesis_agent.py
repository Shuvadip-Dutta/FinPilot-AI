from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.agents.synthesis import FinalSynthesisAgent
from apps.ai.exceptions import LLMError
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult
from apps.ai.services.token_budget import (
    DegradationTier,
    LLMUsage,
    TokenBudgetManager,
)


class FinalSynthesisAgentTestCase(SimpleTestCase):

    def test_agent_name(self):
        agent = FinalSynthesisAgent(
            llm_service=lambda messages: "Synthesized response."
        )

        self.assertEqual(
            agent.name,
            "synthesis",
        )

    def test_successful_synthesis_uses_synthesis_model_by_default(self):
        service = MagicMock()
        service.generate.return_value = "Reliance has strong financial and market signals."

        with patch("apps.ai.agents.synthesis.LLMService", return_value=service) as llm_factory:
            agent = FinalSynthesisAgent()

            state = AgentState(
                user_message="Give me an overview of Reliance.",
                ticker="RELIANCE",
                market="IN",
                results={
                    "financial": AgentResult(
                        response="Financial analysis available.",
                        tools_used=["get_financials"],
                    ),
                    "market": AgentResult(
                        response="Market analysis available.",
                        tools_used=["get_market_data"],
                    ),
                    "news": AgentResult(
                        response="News analysis available.",
                        tools_used=["get_news"],
                    ),
                    "risk": AgentResult(
                        response="Risk assessment available.",
                        tools_used=["risk_analysis"],
                    ),
                    "portfolio_optimization": AgentResult(
                        response="Portfolio optimization result available.",
                        tools_used=["portfolio_optimization"],
                    ),
                },
            )

            result = agent.run(state)

        llm_factory.assert_called_once_with(model="synthesis")
        service.generate.assert_called_once()
        self.assertEqual(result.response, "Reliance has strong financial and market signals.")
        self.assertEqual(
            result.tools_used,
            [
                "get_financials",
                "get_market_data",
                "get_news",
                "risk_analysis",
                "portfolio_optimization",
                "llm_synthesis",
            ],
        )

    def test_structured_sections_are_included_in_context(self):
        captured_messages = []

        def llm_service(messages):
            captured_messages.extend(messages)
            return "Combined overview."

        state = AgentState(
            user_message="Assess Reliance for me.",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(
                    response="Financial analysis available.",
                    tools_used=["get_financials"],
                ),
                "market": AgentResult(
                    response="Current price: 2800 INR.",
                    tools_used=["get_market_data"],
                ),
                "news": AgentResult(
                    response="Sentiment is mildly positive.",
                    tools_used=["get_news"],
                ),
                "risk": AgentResult(
                    response="Risk is moderate.",
                    tools_used=["risk_analysis"],
                ),
                "portfolio_optimization": AgentResult(
                    response="Weights: 50% energy, 30% telecom, 20% cash.",
                    tools_used=["portfolio_optimization"],
                ),
            },
        )

        agent = FinalSynthesisAgent(llm_service=llm_service)
        result = agent.run(state)

        self.assertEqual(result.response, "Combined overview.")
        content = captured_messages[1]["content"]
        self.assertIn("FINANCIAL ANALYSIS", content)
        self.assertIn("MARKET ANALYSIS", content)
        self.assertIn("NEWS INTELLIGENCE", content)
        self.assertIn("RISK ANALYSIS", content)
        self.assertIn("PORTFOLIO ANALYSIS", content)
        self.assertIn("Financial analysis available.", content)
        self.assertIn("Current price: 2800 INR.", content)
        self.assertIn("Weights: 50% energy, 30% telecom, 20% cash.", content)

    def test_structured_evidence_is_included_as_authoritative_context(self):
        captured_messages = []

        def llm_service(messages):
            captured_messages.extend(messages)
            return "Synthesis."

        state = AgentState(
            user_message="Assess Reliance.",
            results={
                "market": AgentResult(
                    response="Price omitted from prose.",
                    tools_used=["get_market_data"],
                    data={"market_data": {"quotes": [{"exchange": "NSE", "price": 1309.0}]}},
                ),
                "news": AgentResult(
                    response="The model says positive 99%.",
                    tools_used=["get_news"],
                    data={"aggregated_sentiment": {"positive": 1, "neutral": 0, "negative": 0, "unavailable": 0}},
                ),
            },
        )

        FinalSynthesisAgent(llm_service=llm_service).run(state)

        content = captured_messages[1]["content"]
        self.assertIn('"price": 1309.0', content)
        self.assertIn('"positive": 1', content)
        self.assertIn("Structured specialist evidence is authoritative", captured_messages[0]["content"])

    def test_prompt_rejects_unsupported_leverage_claims(self):
        captured_messages = []

        def llm_service(messages):
            captured_messages.extend(messages)
            return "Leverage cannot be assessed from the supplied data."

        FinalSynthesisAgent(llm_service=llm_service).run(
            AgentState(user_message="Assess Reliance.")
        )

        self.assertIn("debt-heavy", captured_messages[0]["content"])
        self.assertIn("leverage cannot be assessed", captured_messages[0]["content"])

    def test_missing_specialist_data_is_explicitly_reported(self):
        captured_messages = []

        def llm_service(messages):
            captured_messages.extend(messages)
            return "Partial overview is available."

        state = AgentState(
            user_message="Analyze Reliance.",
            ticker="RELIANCE",
            results={
                "financial": AgentResult(
                    response="Financial analysis available.",
                    tools_used=["get_financials"],
                ),
            },
            errors=[
                "market: market provider unavailable",
                "risk: risk analysis unavailable",
            ],
        )

        agent = FinalSynthesisAgent(llm_service=llm_service)
        result = agent.run(state)

        self.assertEqual(result.response, "Partial overview is available.")
        content = captured_messages[1]["content"]
        self.assertIn("WORKFLOW ERRORS / MISSING INFORMATION", content)
        self.assertIn("market: market provider unavailable", content)
        self.assertIn("MISSING INFORMATION", content)
        self.assertIn("Risk analysis was not available.", content)

    def test_empty_llm_response_is_handled(self):
        agent = FinalSynthesisAgent(llm_service=lambda messages: "   ")

        state = AgentState(
            user_message="Analyze Reliance.",
            ticker="RELIANCE",
            market="IN",
        )

        result = agent.run(state)

        self.assertIn("language model returned an empty response", result.response)
        self.assertEqual(result.tools_used, [])

    def test_llm_failure_propagates(self):
        def failing_llm(messages):
            raise LLMError("Groq unavailable")

        agent = FinalSynthesisAgent(llm_service=failing_llm)

        state = AgentState(
            user_message="Analyze Reliance.",
            ticker="RELIANCE",
            market="IN",
        )

        with self.assertRaises(LLMError):
            agent.run(state)

    def test_tools_used_are_deduplicated(self):
        agent = FinalSynthesisAgent(llm_service=lambda messages: "Final answer.")

        state = AgentState(
            user_message="Analyze Reliance.",
            results={
                "financial": AgentResult(
                    response="Financial.",
                    tools_used=["get_financials", "get_key_metrics"],
                ),
                "market": AgentResult(
                    response="Market.",
                    tools_used=["get_market_data", "get_key_metrics"],
                ),
            },
        )

        result = agent.run(state)

        self.assertEqual(
            result.tools_used,
            [
                "get_financials",
                "get_key_metrics",
                "get_market_data",
                "llm_synthesis",
            ],
        )

    def test_injected_service_still_works_without_real_provider(self):
        calls = []

        def fake_llm(messages):
            calls.append(messages)
            return "Mock final answer."

        agent = FinalSynthesisAgent(llm_service=fake_llm)
        state = AgentState(user_message="Hello.")

        result = agent.run(state)

        self.assertEqual(len(calls), 1)
        self.assertEqual(result.response, "Mock final answer.")
        self.assertEqual(result.tools_used, ["llm_synthesis"])

    def test_large_context_is_bounded_without_losing_authoritative_evidence(self):
        captured_messages = []

        def llm_service(messages):
            captured_messages.extend(messages)
            return "Bounded synthesis."

        state = AgentState(
            user_message="Assess Reliance.",
            results={
                "financial": AgentResult(
                    response="Financial prose " * 1000,
                    tools_used=["get_financials"],
                    data={
                        "ticker": "RELIANCE",
                        "financials": [{
                            "fiscal_year": "2026",
                            "metrics": [{"key": "revenue", "value": 100}],
                        }] * 20,
                        "irrelevant": "x" * 10000,
                    },
                ),
                "market": AgentResult(
                    response="Market prose " * 1000,
                    tools_used=["get_market_data"],
                    data={
                        "market_data": {"quotes": [
                            {"exchange": "BSE", "price": 1307.35},
                            {"exchange": "NSE", "price": 1309.0},
                        ]},
                    },
                ),
                "news": AgentResult(
                    response="News prose " * 1000,
                    tools_used=["get_news"],
                    data={
                        "aggregated_sentiment": {
                            "positive": 4, "neutral": 4, "negative": 2, "unavailable": 0,
                        },
                        "articles": [{
                            "title": "Headline",
                            "summary": "long " * 3000,
                            "sentiment": {"label": "positive", "confidence": 0.9},
                        }] * 10,
                    },
                ),
                "risk": AgentResult(response="Risk conclusion " * 1000, tools_used=[]),
                "portfolio_optimization": AgentResult(
                    response="Weights: 50%; expected return 0.12; volatility 0.08; Sharpe 1.5; bounds 0.1 to 0.7.",
                    tools_used=["portfolio_optimization"],
                ),
            },
        )

        FinalSynthesisAgent(llm_service=llm_service).run(state)

        content = captured_messages[1]["content"]
        self.assertLessEqual(
            len(content),
            FinalSynthesisAgent.SYNTHESIS_CONTEXT_CHAR_LIMIT + 2500,
        )
        self.assertIn('"price": 1309.0', content)
        self.assertIn('"positive": 4', content)
        self.assertIn('"key": "revenue"', content)
        self.assertIn('"value": 100', content)
        self.assertIn("Sharpe 1.5", content)
        self.assertNotIn("x" * 10000, content)
        self.assertNotIn("long " * 1000, content)
        self.assertEqual(content.count('"price": 1309.0'), 1)

    def test_constrained_degradation_caps_tokens_and_reduces_context(self):
        llm = MagicMock()
        llm.generate.return_value = "Constrained synthesis response."
        manager = TokenBudgetManager(tpd_limit=10000)
        manager.record_actual_usage(
            LLMUsage(prompt_tokens=7500, completion_tokens=0, total_tokens=7500, model="synthesis")
        )
        llm.token_budget_manager = manager
        llm.generate.token_budget_manager = manager
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.CONSTRAINED)

        with patch("apps.ai.agents.synthesis.LLMService", return_value=llm):
            agent = FinalSynthesisAgent()
            state = AgentState(
                user_message="Analyze TCS.",
                ticker="TCS",
                results={
                    "financial": AgentResult(
                        response="Financial detailed explanation " * 50,
                        tools_used=["get_financials"],
                        data={"ticker": "TCS", "key_metrics": [{"pe_ratio": 25.5}]},
                    ),
                    "market": AgentResult(
                        response="Market analysis " * 50,
                        tools_used=["get_market_data"],
                        data={"ticker": "TCS", "current_market_data": {"quotes": [{"exchange": "NSE", "price": 4000}]}},
                    ),
                },
            )
            result = agent.run(state)

        llm.generate.assert_called_once()
        _, kwargs = llm.generate.call_args
        self.assertEqual(kwargs.get("max_completion_tokens"), 2000)
        self.assertEqual(result.response, "Constrained synthesis response.")
        self.assertIn("llm_synthesis", result.tools_used)

    def test_critical_degradation_caps_tokens_and_uses_minimal_context(self):
        llm = MagicMock()
        llm.generate.return_value = "Critical synthesis response."
        manager = TokenBudgetManager(tpd_limit=10000)
        manager.record_actual_usage(
            LLMUsage(prompt_tokens=9200, completion_tokens=0, total_tokens=9200, model="synthesis")
        )
        llm.token_budget_manager = manager
        llm.generate.token_budget_manager = manager
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.CRITICAL)

        with patch("apps.ai.agents.synthesis.LLMService", return_value=llm):
            agent = FinalSynthesisAgent()
            state = AgentState(
                user_message="Analyze TCS.",
                ticker="TCS",
                results={
                    "financial": AgentResult(
                        response="Financial detailed explanation " * 50,
                        tools_used=["get_financials"],
                        data={"ticker": "TCS", "key_metrics": [{"pe_ratio": 25.5}]},
                    ),
                    "news": AgentResult(
                        response="News detailed prose " * 50,
                        tools_used=["get_news"],
                        data={"ticker": "TCS", "aggregated_sentiment": {"positive": 5, "negative": 1}},
                    ),
                },
            )
            result = agent.run(state)

        llm.generate.assert_called_once()
        _, kwargs = llm.generate.call_args
        self.assertEqual(kwargs.get("max_completion_tokens"), 1000)
        self.assertEqual(result.response, "Critical synthesis response.")

    def test_exhausted_degradation_makes_zero_llm_calls_and_returns_agent_result(self):
        llm = MagicMock()
        manager = TokenBudgetManager(tpd_limit=10000)
        manager.record_actual_usage(
            LLMUsage(prompt_tokens=10000, completion_tokens=0, total_tokens=10000, model="synthesis")
        )
        llm.token_budget_manager = manager
        llm.generate.token_budget_manager = manager
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.EXHAUSTED)

        with patch("apps.ai.agents.synthesis.LLMService", return_value=llm):
            agent = FinalSynthesisAgent()
            state = AgentState(
                user_message="Analyze TCS.",
                ticker="TCS",
                market="IN",
                results={
                    "financial": AgentResult(
                        response="Financial response",
                        tools_used=["get_financials"],
                        data={"ticker": "TCS", "revenue": 1000},
                    ),
                    "market": AgentResult(
                        response="Market response",
                        tools_used=["get_market_data"],
                        data={"ticker": "TCS", "price": 4000},
                    ),
                },
                errors=["risk: risk analysis unavailable"],
            )
            result = agent.run(state)

        llm.generate.assert_not_called()
        self.assertIn("could not be completed", result.response)
        self.assertIn("budget is exhausted", result.response)
        self.assertIn("Available specialist results: Financial, Market", result.response)
        self.assertIn("Missing:", result.response)
        self.assertIn("Risk analysis was not available.", result.response)
        self.assertNotIn("Buy", result.response)
        self.assertNotIn("Sell", result.response)
        self.assertIn("financial", result.data)
        self.assertIn("market", result.data)
        self.assertEqual(result.data["financial"], {"ticker": "TCS", "revenue": 1000})
        self.assertEqual(result.data["market"], {"ticker": "TCS", "price": 4000})
        self.assertEqual(result.tools_used, ["get_financials", "get_market_data"])

