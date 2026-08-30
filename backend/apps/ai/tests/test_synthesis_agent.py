from django.test import SimpleTestCase

from apps.ai.agents.synthesis import FinalSynthesisAgent
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult


class FinalSynthesisAgentTestCase(SimpleTestCase):

    def test_agent_name(self):
        agent = FinalSynthesisAgent(
            llm_service=lambda messages: "Synthesized response."
        )

        self.assertEqual(
            agent.name,
            "synthesis",
        )

    def test_successful_synthesis(self):
        calls = []

        def llm_service(messages):
            calls.append(messages)

            return "Reliance has strong financial and market signals."

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
            },
        )

        agent = FinalSynthesisAgent(
            llm_service=llm_service,
        )

        result = agent.run(state)

        self.assertIsInstance(
            result,
            AgentResult,
        )

        self.assertEqual(
            result.response,
            "Reliance has strong financial and market signals.",
        )

        self.assertEqual(
            result.tools_used,
            [
                "get_financials",
                "get_market_data",
                "get_news",
                "llm_synthesis",
            ],
        )

        self.assertEqual(
            len(calls),
            1,
        )

        self.assertIn(
            "Financial analysis available.",
            calls[0][1]["content"],
        )

    def test_synthesis_includes_workflow_errors(self):
        captured_messages = []

        def llm_service(messages):
            captured_messages.extend(messages)
            return "Some data was unavailable."

        state = AgentState(
            user_message="Analyze Reliance.",
            ticker="RELIANCE",
            results={
                "market": AgentResult(
                    response="Market analysis available.",
                    tools_used=["get_market_data"],
                ),
            },
            errors=[
                "news: News provider unavailable",
            ],
        )

        agent = FinalSynthesisAgent(
            llm_service=llm_service,
        )

        result = agent.run(state)

        self.assertEqual(
            result.response,
            "Some data was unavailable.",
        )

        self.assertIn(
            "News provider unavailable",
            captured_messages[1]["content"],
        )

    def test_empty_llm_response_is_handled(self):
        agent = FinalSynthesisAgent(
            llm_service=lambda messages: "   "
        )

        state = AgentState(
            user_message="Analyze Reliance.",
            ticker="RELIANCE",
            market="IN",
        )

        result = agent.run(state)

        self.assertIn(
            "language model returned an empty response",
            result.response,
        )

        self.assertEqual(
            result.tools_used,
            [],
        )

    def test_llm_failure_is_handled(self):
        def failing_llm(messages):
            raise ValueError("Groq unavailable")

        agent = FinalSynthesisAgent(
            llm_service=failing_llm,
        )

        state = AgentState(
            user_message="Analyze Reliance.",
            ticker="RELIANCE",
            market="IN",
        )

        result = agent.run(state)

        self.assertIn(
            "Unable to generate the final synthesis",
            result.response,
        )

        self.assertIn(
            "Groq unavailable",
            result.response,
        )

        self.assertEqual(
            result.tools_used,
            [],
        )

    def test_tools_used_are_deduplicated(self):
        agent = FinalSynthesisAgent(
            llm_service=lambda messages: "Final answer."
        )

        state = AgentState(
            user_message="Analyze Reliance.",
            results={
                "financial": AgentResult(
                    response="Financial.",
                    tools_used=[
                        "get_financials",
                        "get_key_metrics",
                    ],
                ),
                "market": AgentResult(
                    response="Market.",
                    tools_used=[
                        "get_market_data",
                        "get_key_metrics",
                    ],
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

    def test_no_real_llm_call_with_injected_service(self):
        calls = []

        def fake_llm(messages):
            calls.append(messages)
            return "Mock final answer."

        agent = FinalSynthesisAgent(
            llm_service=fake_llm,
        )

        state = AgentState(
            user_message="Hello.",
        )

        result = agent.run(state)

        self.assertEqual(
            calls,
            [calls[0]],
        )

        self.assertEqual(
            result.response,
            "Mock final answer.",
        )