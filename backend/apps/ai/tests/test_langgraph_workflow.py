from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
from apps.ai.graph.router import WorkflowRouter
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult
from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.portfolio.optimization import OptimizationInput
from apps.ai.portfolio.schemas import Holding, Portfolio

class LangGraphResearchWorkflowTestCase(SimpleTestCase):

    def test_langgraph_workflow_returns_agent_state(self):
        workflow, _, _, _ = self._build_workflow(route="general")

        state = workflow.run("Give me an overview of Reliance.")

        self.assertIsInstance(state, AgentState)

    def test_financial_route_executes_only_financial_node(self):
        workflow, financial, market, news = self._build_workflow(route="financial")

        state = workflow.run("Show revenue for RELIANCE.")

        self.assertEqual(state.route, "financial")
        financial.run.assert_called_once_with("Show revenue for RELIANCE.")
        market.run.assert_not_called()
        news.run.assert_not_called()

    def test_market_route_executes_only_market_node(self):
        workflow, financial, market, news = self._build_workflow(route="market")

        state = workflow.run("What is the RELIANCE price?")

        self.assertEqual(state.route, "market")
        financial.run.assert_not_called()
        market.run.assert_called_once_with("What is the RELIANCE price?")
        news.run.assert_not_called()

    def test_news_route_executes_only_news_node(self):
        workflow, financial, market, news = self._build_workflow(route="news")

        state = workflow.run("Show RELIANCE news.")

        self.assertEqual(state.route, "news")
        financial.run.assert_not_called()
        market.run.assert_not_called()
        news.run.assert_called_once_with("Show RELIANCE news.")

    def test_general_route_executes_financial_market_and_news(self):
        workflow, financial, market, news = self._build_workflow(route="general")

        state = workflow.run("Give me an overview of Reliance.")

        self.assertEqual(state.route, "general")
        self.assertEqual(set(state.results), {"financial", "market", "news"})
        financial.run.assert_called_once()
        market.run.assert_called_once()
        news.run.assert_called_once()

    def test_general_route_stores_all_successful_branch_results(self):
        workflow, _, _, _ = self._build_workflow(route="general")

        state = workflow.run("Give me an overview of Reliance.")

        self.assertEqual(set(state.results), {"financial", "market", "news"})
        self.assertIn("financial", state.results)
        self.assertIn("market", state.results)
        self.assertIn("news", state.results)

    def test_general_route_executes_financial_market_news_then_risk(self):
        workflow, financial, market, news, risk, synthesis = self._build_workflow(
            route="general",
            risk_agent=True,
            synthesis_agent=True,
        )

        state = workflow.run("Give me an overview of Reliance.")

        financial.run.assert_called_once_with("Give me an overview of Reliance.")
        market.run.assert_called_once_with("Give me an overview of Reliance.")
        news.run.assert_called_once_with("Give me an overview of Reliance.")
        risk.run.assert_called_once()
        synthesis.run.assert_called_once()
        self.assertIn("risk", state.results)

    def test_general_route_risk_receives_merged_research_state(self):
        workflow, _, _, _, risk = self._build_workflow(
            route="general",
            risk_agent=True,
        )

        workflow.run("Give me an overview of Reliance.")

        received_state = risk.run.call_args.args[0]
        self.assertIsInstance(received_state, AgentState)
        self.assertEqual(
            set(received_state.results),
            {"financial", "market", "news"},
        )
        self.assertNotIn("synthesis", received_state.results)

    def test_general_route_with_branch_failure_still_runs_risk(self):
        workflow, financial, market, news, risk = self._build_workflow(
            route="general",
            risk_agent=True,
        )
        news.run.side_effect = TypeError("News unavailable")

        state = workflow.run("Give me an overview of Reliance.")

        self.assertIn("financial", state.results)
        self.assertIn("market", state.results)
        self.assertNotIn("news", state.results)
        self.assertIn("news: News unavailable", state.errors)
        risk.run.assert_called_once()

    def test_general_route_risk_failure_is_recorded(self):
        workflow, _, _, _, risk, synthesis = self._build_workflow(
            route="general",
            risk_agent=True,
            synthesis_agent=True,
        )
        risk.run.side_effect = ValueError("Risk unavailable")

        state = workflow.run("Give me an overview of Reliance.")

        self.assertIn("risk: Risk unavailable", state.errors)
        self.assertEqual(set(state.results), {"financial", "market", "news", "synthesis"})
        self.assertIn("financial", state.results)
        self.assertIn("market", state.results)
        self.assertIn("news", state.results)
        synthesis.run.assert_called_once()

    def test_single_routes_still_skip_risk(self):
        workflow, financial, market, news, risk = self._build_workflow(
            route="financial",
            risk_agent=True,
        )
        workflow.run("Show revenue for RELIANCE.")
        financial.run.assert_called_once()
        market.run.assert_not_called()
        news.run.assert_not_called()
        risk.run.assert_not_called()

        workflow, financial, market, news, risk = self._build_workflow(
            route="market",
            risk_agent=True,
        )
        workflow.run("What is the RELIANCE price?")
        financial.run.assert_not_called()
        market.run.assert_called_once()
        news.run.assert_not_called()
        risk.run.assert_not_called()

        workflow, financial, market, news, risk = self._build_workflow(
            route="news",
            risk_agent=True,
        )
        workflow.run("Show RELIANCE news.")
        financial.run.assert_not_called()
        market.run.assert_not_called()
        news.run.assert_called_once()
        risk.run.assert_not_called()

    def test_branch_failure_preserves_successful_sibling_results(self):
        workflow, financial, market, news = self._build_workflow(route="general")
        news.run.side_effect = TypeError("News unavailable")

        state = workflow.run("Give me an overview of Reliance.")

        self.assertIn("financial", state.results)
        self.assertIn("market", state.results)
        self.assertNotIn("news", state.results)
        self.assertIn("news: News unavailable", state.errors)

    def test_general_route_invokes_synthesis_after_research_branches(self):
        workflow, _, _, _, synthesis = self._build_workflow(
            route="general",
            synthesis_agent=True,
        )

        state = workflow.run("Give me an overview of Reliance.")

        synthesis.run.assert_called_once()
        self.assertIn("synthesis", state.results)

    def test_synthesis_receives_final_state(self):
        workflow, _, _, _, synthesis = self._build_workflow(
            route="general",
            synthesis_agent=True,
        )

        state = workflow.run("Give me an overview of Reliance.")

        received_state = synthesis.run.call_args.args[0]
        self.assertIsInstance(received_state, AgentState)
        self.assertEqual(
            set(received_state.results),
            {"financial", "market", "news"},
        )
        self.assertEqual(
            set(state.results),
            {"financial", "market", "news", "synthesis"},
        )

    def test_synthesis_failure_is_recorded_in_state_errors(self):
        workflow, _, _, _, synthesis = self._build_workflow(
            route="general",
            synthesis_agent=True,
        )
        synthesis.run.side_effect = ValueError("Synthesis unavailable")

        state = workflow.run("Give me an overview of Reliance.")

        self.assertIn("synthesis: Synthesis unavailable", state.errors)
        self.assertEqual(set(state.results), {"financial", "market", "news"})

    def test_unexpected_runtime_error_propagates(self):
        workflow, _, market, _ = self._build_workflow(route="market")
        market.run.side_effect = RuntimeError("unexpected bug")

        with self.assertRaises(RuntimeError):
            workflow.run("What is the RELIANCE price?")

    def test_injected_agents_prevent_external_api_or_llm_calls(self):
        workflow, financial, _, _ = self._build_workflow(route="financial")

        workflow.run("Show RELIANCE revenue.")

        financial.run.assert_called_once()

    def test_graph_routing_remains_deterministic(self):
        workflow, _, _, _ = self._build_workflow(route="market")

        routes = [
            workflow.run("What is the current price of Reliance?").route
            for _ in range(3)
        ]

        self.assertEqual(routes, ["market", "market", "market"])

    def test_graph_can_be_invoked_more_than_once_safely(self):
        workflow, _, _, _ = self._build_workflow(route="general")

        first = workflow.run("Give me an overview of Reliance.")
        second = workflow.run("Give me an overview of Infosys.")

        self.assertIsInstance(first, AgentState)
        self.assertIsInstance(second, AgentState)
        self.assertEqual(first.route, "general")
        self.assertEqual(second.route, "general")

    def test_compiled_graph_has_no_overview_node(self):
        workflow, _, _, _ = self._build_workflow(route="general")

        self.assertNotIn("overview", workflow._graph.get_graph().nodes.keys())

    def test_real_router_is_deterministic_in_graph(self):
        workflow = LangGraphResearchWorkflow(
            router=WorkflowRouter(),
            financial_agent=self._make_agent(),
            market_agent=self._make_agent(),
            news_agent=self._make_agent(),
            synthesis_agent=self._make_agent(),
        )

        routes = [
            workflow.run("What is the current price of Reliance?").route
            for _ in range(3)
        ]

        self.assertEqual(routes, ["market", "market", "market"])

    @staticmethod
    def _make_agent():
        agent = MagicMock()
        agent.run.return_value = AgentResult(
            response="result",
            tools_used=[],
        )
        return agent

    @staticmethod
    def _build_workflow(
        route="general",
        synthesis_agent=False,
        risk_agent=False,
        portfolio_intelligence=False,
        portfolio_optimization_agent=False,
    ):
        router = MagicMock()
        router.route.return_value = route

        financial = MagicMock()
        financial.run.return_value = AgentResult(
            response="Financial result",
            tools_used=["get_financials"],
        )

        market = MagicMock()
        market.run.return_value = AgentResult(
            response="Market result",
            tools_used=["get_market_data"],
        )

        news = MagicMock()
        news.run.return_value = AgentResult(
            response="News result",
            tools_used=["get_news"],
        )

        risk = MagicMock()
        risk.run.return_value = AgentResult(
            response="Risk result",
            tools_used=[],
        )

        portfolio = MagicMock()
        portfolio.analyze.return_value = MagicMock(
            invested_value=12000.0,
            current_value=13000.0,
            profit_loss=1000.0,
            profit_loss_percentage=8.3333333,
            holdings_count=1,
        )

        optimization = MagicMock()
        optimization.run.return_value = AgentResult(
            response="Optimization result",
            tools_used=["portfolio_optimization"],
        )

        synthesis = MagicMock()
        synthesis.run.return_value = AgentResult(
            response="Combined result",
            tools_used=["llm_synthesis"],
        )

        workflow = LangGraphResearchWorkflow(
            router=router,
            financial_agent=financial,
            market_agent=market,
            news_agent=news,
            synthesis_agent=synthesis if synthesis_agent else None,
            risk_agent=risk if risk_agent else None,
            portfolio_intelligence=(
                portfolio
                if portfolio_intelligence
                else None
            ),
            portfolio_optimization_agent=(
                optimization
                if portfolio_optimization_agent
                else None
            ),
        )

        if synthesis_agent and risk_agent:
            return (
                workflow,
                financial,
                market,
                news,
                risk,
                synthesis,
            )

        if synthesis_agent:
            return (
                workflow,
                financial,
                market,
                news,
                synthesis,
            )

        if risk_agent:
            return (
                workflow,
                financial,
                market,
                news,
                risk,
            )

        return (
            workflow,
            financial,
            market,
            news,
        )
        
    @staticmethod
    def _build_portfolio_workflow(
        route="portfolio",
    ):
        router = MagicMock()
        router.route.return_value = route

        financial = MagicMock()
        market = MagicMock()
        news = MagicMock()

        risk = MagicMock()
        risk.run.return_value = AgentResult(
            response="Risk result",
            tools_used=[],
        )

        portfolio = MagicMock()
        portfolio.analyze.return_value = MagicMock(
            invested_value=12000.0,
            current_value=13000.0,
            profit_loss=1000.0,
            profit_loss_percentage=8.3333333,
            holdings_count=1,
        )

        optimization = MagicMock()
        optimization.run.return_value = AgentResult(
            response="Optimization result",
            tools_used=["portfolio_optimization"],
        )

        synthesis = MagicMock()
        synthesis.run.return_value = AgentResult(
            response="Combined result",
            tools_used=["llm_synthesis"],
        )

        workflow = LangGraphResearchWorkflow(
            router=router,
            financial_agent=financial,
            market_agent=market,
            news_agent=news,
            synthesis_agent=synthesis,
            risk_agent=risk,
            portfolio_intelligence=portfolio,
            portfolio_optimization_agent=optimization,
        )

        return (
            workflow,
            portfolio,
            risk,
            optimization,
            synthesis,
        )
        
        
    @staticmethod
    def _portfolio_input(
        include_optimization=True,
    ):
        optimization_input = None

        if include_optimization:
            optimization_input = OptimizationInput(
                tickers=["RELIANCE", "TCS"],
                historical_prices={
                    "RELIANCE": [
                        1200,
                        1210,
                        1190,
                        1220,
                    ],
                    "TCS": [
                        3500,
                        3520,
                        3480,
                        3510,
                    ],
                },
                risk_free_rate=0.02,
            )

        return PortfolioWorkflowInput(
            portfolio=Portfolio(
                holdings=[
                    Holding(
                        ticker="RELIANCE",
                        market="IN",
                        quantity=10,
                        average_price=1200,
                    ),
                    Holding(
                        ticker="TCS",
                        market="IN",
                        quantity=5,
                        average_price=3500,
                    ),
                ]
            ),
            optimization_input=optimization_input,
        )
        
    def test_portfolio_route_executes_portfolio_and_risk(self):
        (
            workflow,
            portfolio,
            risk,
            optimization,
            synthesis,
        ) = self._build_portfolio_workflow()

        portfolio_input = self._portfolio_input(
            include_optimization=False,
        )

        state = workflow.run(
            "Analyze my portfolio.",
            portfolio_input=portfolio_input,
        )

        portfolio.analyze.assert_called_once_with(
            portfolio_input.portfolio
        )

        risk.run.assert_called_once()

        optimization.run.assert_not_called()

        synthesis.run.assert_called_once()

        self.assertIn(
            "portfolio",
            state.results,
        )

        self.assertIn(
            "risk",
            state.results,
        )
        
        
    def test_portfolio_optimization_executes_optimization_agent(self):
        (
            workflow,
            portfolio,
            risk,
            optimization,
            synthesis,
        ) = self._build_portfolio_workflow()

        portfolio_input = self._portfolio_input(
            include_optimization=True,
        )

        state = workflow.run(
            "Optimize my portfolio.",
            portfolio_input=portfolio_input,
        )

        portfolio.analyze.assert_called_once_with(
            portfolio_input.portfolio
        )

        risk.run.assert_called_once()

        optimization.run.assert_called_once_with(
            portfolio_input.optimization_input
        )

        synthesis.run.assert_called_once()

        self.assertIn(
            "portfolio_optimization",
            state.results,
        )
        
        
    def test_portfolio_analysis_skips_optimization(self):
        (
            workflow,
            portfolio,
            risk,
            optimization,
            synthesis,
        ) = self._build_portfolio_workflow()

        portfolio_input = self._portfolio_input(
            include_optimization=False,
        )

        state = workflow.run(
            "Analyze my portfolio.",
            portfolio_input=portfolio_input,
        )

        portfolio.analyze.assert_called_once_with(
            portfolio_input.portfolio,
        )
        risk.run.assert_called_once()
        optimization.run.assert_not_called()
        synthesis.run.assert_called_once()

        self.assertIn(
            "portfolio",
            state.results,
        )
        self.assertIn(
            "risk",
            state.results,
        )
        
        
    def test_portfolio_optimization_runs_optimization_agent(self):
        (
            workflow,
            portfolio,
            risk,
            optimization,
            synthesis,
        ) = self._build_portfolio_workflow()

        portfolio_input = self._portfolio_input(
            include_optimization=True,
        )

        state = workflow.run(
            "Optimize my portfolio.",
            portfolio_input=portfolio_input,
        )

        portfolio.analyze.assert_called_once_with(
            portfolio_input.portfolio,
        )
        risk.run.assert_called_once()
        optimization.run.assert_called_once_with(
            portfolio_input.optimization_input,
        )
        synthesis.run.assert_called_once()

        self.assertIn(
            "portfolio_optimization",
            state.results,
        )    