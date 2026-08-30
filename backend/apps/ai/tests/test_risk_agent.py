from django.test import SimpleTestCase

from apps.ai.agents.risk import RiskAnalysisAgent
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult


class RiskAnalysisAgentTestCase(SimpleTestCase):

    def test_agent_name(self):
        agent = RiskAnalysisAgent()

        self.assertEqual(
            agent.name,
            "risk",
        )

    def test_successful_risk_analysis(self):
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

        self.assertIsInstance(
            result,
            AgentResult,
        )

        self.assertIn(
            "Financial, market, and news research are available",
            result.response,
        )

        self.assertEqual(
            result.tools_used,
            [],
        )

    def test_missing_research_data(self):
        state = AgentState(
            user_message="Assess Reliance risk.",
            ticker="RELIANCE",
            market="IN",
        )

        result = RiskAnalysisAgent().run(state)

        self.assertIn(
            "Financial research data is unavailable.",
            result.response,
        )

        self.assertIn(
            "Current market data is unavailable.",
            result.response,
        )

        self.assertIn(
            "News intelligence is unavailable.",
            result.response,
        )

    def test_partial_research_data(self):
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

        self.assertIn(
            "Financial research data is unavailable.",
            result.response,
        )

        self.assertIn(
            "News intelligence is unavailable.",
            result.response,
        )

        self.assertNotIn(
            "Current market data is unavailable.",
            result.response,
        )

    def test_run_returns_agent_result(self):
        state = AgentState(
            user_message="Assess TCS risk.",
            ticker="TCS",
            market="IN",
        )

        result = RiskAnalysisAgent().run(state)

        self.assertIsInstance(
            result,
            AgentResult,
        )