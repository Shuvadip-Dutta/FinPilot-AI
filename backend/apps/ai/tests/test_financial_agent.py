from django.test import SimpleTestCase

from apps.ai.agents.financial import FinancialAnalysisAgent
from apps.ai.services.schemas import AgentResult


class FinancialAnalysisAgentTestCase(SimpleTestCase):

    def test_agent_name(self):
        agent = FinancialAnalysisAgent()

        self.assertEqual(agent.name, "financial")

    def test_successful_financial_analysis(self):
        financials_tool = self._financials_tool()
        key_metrics_tool = self._key_metrics_tool()
        agent = FinancialAnalysisAgent(
            financials_tool=financials_tool,
            key_metrics_tool=key_metrics_tool,
            ticker="RELIANCE",
        )

        result = agent.run("Analyze Reliance financials.")

        self.assertIn("Financial analysis for RELIANCE", result.response)
        self.assertIn("1 financial statement(s)", result.response)
        self.assertIn("1 key metric(s)", result.response)
        self.assertEqual(
            result.tools_used,
            ["get_financials", "get_key_metrics"],
        )

    def test_research_tool_failure_is_returned_in_result(self):
        def failing_financials_tool(**kwargs):
            raise ValueError("Financial data unavailable")

        agent = FinancialAnalysisAgent(
            financials_tool=failing_financials_tool,
            key_metrics_tool=self._key_metrics_tool(),
            ticker="RELIANCE",
        )

        result = agent.run("Analyze RELIANCE financials.")

        self.assertIn("Financial data unavailable", result.response)
        self.assertEqual(result.tools_used, [])

    def test_run_returns_agent_result(self):
        agent = FinancialAnalysisAgent(
            financials_tool=self._financials_tool(),
            key_metrics_tool=self._key_metrics_tool(),
            ticker="RELIANCE",
        )

        result = agent.run("Analyze RELIANCE financials.")

        self.assertIsInstance(result, AgentResult)

    def test_injected_tools_avoid_real_api_or_llm_calls(self):
        calls = []

        def financials_tool(**kwargs):
            calls.append(("financials", kwargs))
            return {"financials": []}

        def key_metrics_tool(**kwargs):
            calls.append(("key_metrics", kwargs))
            return {"metrics": []}

        agent = FinancialAnalysisAgent(
            financials_tool=financials_tool,
            key_metrics_tool=key_metrics_tool,
            ticker="TCS",
        )

        agent.run("Analyze TCS financials.")

        self.assertEqual(
            calls,
            [
                ("financials", {"ticker": "TCS", "market": "IN"}),
                ("key_metrics", {"ticker": "TCS", "market": "IN"}),
            ],
        )

    @staticmethod
    def _financials_tool():
        return lambda **kwargs: {"financials": [{"metrics": []}]}

    @staticmethod
    def _key_metrics_tool():
        return lambda **kwargs: {"metrics": [{"key": "pe_ratio"}]}
