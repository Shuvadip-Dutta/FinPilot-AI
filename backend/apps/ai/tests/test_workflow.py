from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.ai.graph.workflow import ResearchWorkflow
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult


class ResearchWorkflowTestCase(SimpleTestCase):

    def test_single_financial_route(self):
        workflow, router, financial, market, news = self._workflow(
            route="financial"
        )

        state = workflow.run("Show revenue for RELIANCE.")

        self.assertEqual(state.route, "financial")
        financial.run.assert_called_once_with("Show revenue for RELIANCE.")
        market.run.assert_not_called()
        news.run.assert_not_called()
        router.route.assert_called_once_with("Show revenue for RELIANCE.")

    def test_single_market_route(self):
        workflow, _, financial, market, news = self._workflow(route="market")

        state = workflow.run("What is the RELIANCE price?")

        self.assertEqual(state.route, "market")
        financial.run.assert_not_called()
        market.run.assert_called_once_with("What is the RELIANCE price?")
        news.run.assert_not_called()

    def test_single_news_route(self):
        workflow, _, financial, market, news = self._workflow(route="news")

        state = workflow.run("Show RELIANCE news.")

        self.assertEqual(state.route, "news")
        financial.run.assert_not_called()
        market.run.assert_not_called()
        news.run.assert_called_once_with("Show RELIANCE news.")

    def test_overview_query_executes_all_research_agents(self):
        workflow, _, financial, market, news = self._workflow(route="general")

        state = workflow.run("Give me an overview of Reliance.")

        self.assertEqual(
            set(state.results),
            {"financial", "market", "news"},
        )
        financial.run.assert_called_once()
        market.run.assert_called_once()
        news.run.assert_called_once()

    def test_overview_workflow_includes_synthesis(self):
        synthesis = MagicMock()
        synthesis_result = AgentResult(
            response="Combined result",
            tools_used=["llm_synthesis"],
        )
        synthesis.run.return_value = synthesis_result
        workflow, _, financial, market, news = self._workflow(
            route="general",
            synthesis_agent=synthesis,
        )

        state = workflow.run("Give me an overview of Reliance.")

        financial.run.assert_called_once()
        market.run.assert_called_once()
        news.run.assert_called_once()
        synthesis.run.assert_called_once_with(state)
        self.assertIs(state.results["synthesis"], synthesis_result)

    def test_synthesis_receives_final_agent_state(self):
        synthesis = MagicMock()
        synthesis.run.return_value = AgentResult(
            response="Combined result",
            tools_used=[],
        )
        workflow, _, _, _, _ = self._workflow(
            route="general",
            synthesis_agent=synthesis,
        )

        state = workflow.run("Give me an overview of Reliance.")

        received_state = synthesis.run.call_args.args[0]
        self.assertIs(received_state, state)
        self.assertEqual(
            set(received_state.results),
            {"financial", "market", "news", "synthesis"},
        )

    def test_synthesis_failure_is_stored_in_errors(self):
        synthesis = MagicMock()
        synthesis.run.side_effect = ValueError("Synthesis unavailable")
        workflow, _, _, _, _ = self._workflow(
            route="general",
            synthesis_agent=synthesis,
        )

        state = workflow.run("Give me an overview of Reliance.")

        self.assertEqual(state.errors, ["synthesis: Synthesis unavailable"])
        self.assertNotIn("synthesis", state.results)

    def test_single_routes_do_not_run_injected_synthesis_agent(self):
        synthesis = MagicMock()
        workflow, _, _, _, _ = self._workflow(
            route="financial",
            synthesis_agent=synthesis,
        )

        workflow.run("Show revenue for RELIANCE.")

        synthesis.run.assert_not_called()

    def test_agent_result_is_stored_in_state(self):
        financial_result = AgentResult(
            response="Financial result",
            tools_used=["get_financials"],
        )
        workflow, _, _, _, _ = self._workflow(
            route="financial",
            financial_result=financial_result,
        )

        state = workflow.run("Show RELIANCE revenue.")

        self.assertIs(state.results["financial"], financial_result)

    def test_agent_failure_is_stored_in_errors(self):
        workflow, _, _, market, _ = self._workflow(route="market")
        market.run.side_effect = ValueError("Market data unavailable")

        state = workflow.run("What is the RELIANCE price?")

        self.assertEqual(state.results, {})
        self.assertEqual(state.errors, ["market: Market data unavailable"])

    def test_workflow_returns_agent_state(self):
        workflow, _, _, _, _ = self._workflow(route="general")

        state = workflow.run("Hello")

        self.assertIsInstance(state, AgentState)

    def test_injected_dependencies_prevent_real_api_or_llm_calls(self):
        workflow, _, financial, _, _ = self._workflow(route="financial")

        workflow.run("Show RELIANCE revenue.")

        financial.run.assert_called_once()

    @staticmethod
    def _workflow(
        route: str,
        financial_result: AgentResult | None = None,
        synthesis_agent: MagicMock | None = None,
    ):
        router = MagicMock()
        router.route.return_value = route

        financial = MagicMock()
        financial.run.return_value = financial_result or AgentResult(
            response="Financial result",
            tools_used=[],
        )
        market = MagicMock()
        market.run.return_value = AgentResult(
            response="Market result",
            tools_used=[],
        )
        news = MagicMock()
        news.run.return_value = AgentResult(
            response="News result",
            tools_used=[],
        )

        return (
            ResearchWorkflow(
                router=router,
                financial_agent=financial,
                market_agent=market,
                news_agent=news,
                synthesis_agent=synthesis_agent,
            ),
            router,
            financial,
            market,
            news,
        )
