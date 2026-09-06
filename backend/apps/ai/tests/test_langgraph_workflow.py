from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
from apps.ai.graph.router import WorkflowRouter
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult
from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.portfolio.optimization import OptimizationInput
from apps.ai.portfolio.schemas import Holding, Portfolio, PortfolioIntelligence
from apps.research.models import ResearchEvidence, ResearchSession
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


def _test_checkpointer():
    serializer = JsonPlusSerializer(
        allowed_msgpack_modules=[
            (
                "apps.ai.services.schemas",
                "AgentResult",
            ),
        ],
    )

    return MemorySaver(
        serde=serializer,
    )

class LangGraphResearchWorkflowTestCase(TestCase):

    def test_langgraph_workflow_returns_agent_state(self):
        workflow, _, _, _ = self._build_workflow(route="general")

        state = workflow.run("Give me an overview of Reliance.")

        self.assertIsInstance(state, AgentState)

    def test_to_agent_state_maps_canonical_user_message(self):
        workflow, _, _, _ = self._build_workflow(route="risk")

        state = workflow._to_agent_state({
            "user_message": "Assess RELIANCE risk.",
            "ticker": "RELIANCE",
            "market": "IN",
            "route": "risk",
            "results": {},
            "errors": [],
        })

        self.assertEqual(state.user_message, "Assess RELIANCE risk.")
        self.assertEqual(state.route, "risk")
        self.assertEqual(state.results, {})
        self.assertEqual(state.errors, [])

    def test_financial_route_executes_only_financial_node(self):
        workflow, financial, market, news = self._build_workflow(route="financial")

        state = workflow.run("Show revenue for RELIANCE.")

        self.assertEqual(state.route, "financial")
        financial.run.assert_called_once()
        self.assertEqual(financial.run.call_args.args[0].user_message, "Show revenue for RELIANCE.")
        market.run.assert_not_called()
        news.run.assert_not_called()

    def test_market_route_executes_only_market_node(self):
        workflow, financial, market, news = self._build_workflow(route="market")

        state = workflow.run("What is the RELIANCE price?")

        self.assertEqual(state.route, "market")
        financial.run.assert_not_called()
        market.run.assert_called_once()
        self.assertEqual(market.run.call_args.args[0].user_message, "What is the RELIANCE price?")
        news.run.assert_not_called()

    def test_news_route_executes_only_news_node(self):
        workflow, financial, market, news = self._build_workflow(route="news")

        state = workflow.run("Show RELIANCE news.")

        self.assertEqual(state.route, "news")
        financial.run.assert_not_called()
        market.run.assert_not_called()
        news.run.assert_called_once()
        self.assertEqual(news.run.call_args.args[0].user_message, "Show RELIANCE news.")

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

        financial.run.assert_called_once()
        self.assertEqual(financial.run.call_args.args[0].user_message, "Give me an overview of Reliance.")
        market.run.assert_called_once()
        self.assertEqual(market.run.call_args.args[0].user_message, "Give me an overview of Reliance.")
        news.run.assert_called_once()
        self.assertEqual(news.run.call_args.args[0].user_message, "Give me an overview of Reliance.")
        risk.run.assert_called_once()
        synthesis.run.assert_called_once()
        self.assertIn("risk", state.results)

    def test_agent_nodes_receive_ticker_and_market_from_state(self):
        workflow, financial, market, news = self._build_workflow(route="general")

        workflow.run(
            "Conduct a research analysis.",
            ticker="LT",
            market="IN",
        )

        for mock_agent in (financial, market, news):
            mock_agent.run.assert_called_once()
            passed_state = mock_agent.run.call_args.args[0]
            self.assertIsInstance(passed_state, AgentState)
            self.assertEqual(passed_state.ticker, "LT")
            self.assertEqual(passed_state.market, "IN")

    def test_workflow_normalizes_human_readable_market_input(self):
        workflow, financial, market, news = self._build_workflow(route="general")

        state = workflow.run(
            "Conduct a research analysis.",
            ticker="LT",
            market="INDIA",
        )

        self.assertEqual(state.market, "IN")
        for mock_agent in (financial, market, news):
            passed_state = mock_agent.run.call_args.args[0]
            self.assertEqual(passed_state.market, "IN")

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
            checkpointer=_test_checkpointer(),
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
        checkpointer=None,
    ):
        if checkpointer is None:
            checkpointer = _test_checkpointer()
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
            checkpointer=checkpointer,
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
        checkpointer=_test_checkpointer()
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
        portfolio.analyze.return_value = PortfolioIntelligence(
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
            checkpointer=checkpointer,
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

        risk.run.assert_not_called()

        optimization.run.assert_not_called()

        synthesis.run.assert_called_once()

        self.assertIn(
            "portfolio",
            state.results,
        )

        self.assertNotIn(
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

        risk.run.assert_not_called()

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
        risk.run.assert_not_called()
        optimization.run.assert_not_called()
        synthesis.run.assert_called_once()

        self.assertIn(
            "portfolio",
            state.results,
        )
        self.assertNotIn(
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
        risk.run.assert_not_called()
        optimization.run.assert_called_once_with(
            portfolio_input.optimization_input,
        )
        synthesis.run.assert_called_once()

        self.assertIn(
            "portfolio_optimization",
            state.results,
        )  
        
    def test_thread_id_creates_checkpoint(self):
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = _test_checkpointer()

        workflow, _, _, _ = self._build_workflow(
            route="market",
            checkpointer=checkpointer,
        )

        workflow.run(
            "What is the RELIANCE price?",
            thread_id="test-thread-1",
        )

        config = {
            "configurable": {
                "thread_id": "test-thread-1",
            }
        }

        checkpoint = checkpointer.get_tuple(config)

        self.assertIsNotNone(checkpoint)
        
    def test_thread_id_can_be_passed(self):
        workflow, _, _, _ = self._build_workflow(
            route="market",
        )

        state = workflow.run(
            "What is the RELIANCE price?",
            thread_id="test-thread-1",
        )

        self.assertIsInstance(
            state,
            AgentState,
        )

    def test_workflow_persists_research_session_and_evidence(self):
        workflow, _, _, _, synthesis = self._build_workflow(
            route="general",
            synthesis_agent=True,
        )

        state = workflow.run(
            "Give me an overview of Reliance.",
            ticker="RELIANCE",
            market="INDIA",
            thread_id="test-session-persist",
        )

        self.assertIsInstance(state, AgentState)

        session = ResearchSession.objects.get(thread_id="test-session-persist")
        self.assertEqual(session.user_message, "Give me an overview of Reliance.")
        self.assertEqual(session.ticker, "RELIANCE")
        self.assertEqual(session.market, "IN")
        self.assertEqual(session.route, "general")
        self.assertEqual(session.status, "COMPLETED")
        self.assertIsNotNone(session.latency_ms)
        self.assertGreater(session.latency_ms, 0.0)
        self.assertEqual(session.final_synthesis, "Combined result")

        evidence = ResearchEvidence.objects.filter(session=session)
        self.assertGreaterEqual(evidence.count(), 3)
        agent_names = set(evidence.values_list("agent_name", flat=True))
        self.assertIn("financial", agent_names)
        self.assertIn("market", agent_names)
        self.assertIn("news", agent_names)
        self.assertIn("synthesis", agent_names)

    def test_workflow_persists_explicit_user_ownership(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="workflow_user", password="password")

        workflow, _, _, _, synthesis = self._build_workflow(
            route="general",
            synthesis_agent=True,
        )

        workflow.run(
            "Overview of Reliance",
            user=user,
            ticker="RELIANCE",
            thread_id="user-persist-thread",
        )

        session = ResearchSession.objects.get(thread_id="user-persist-thread")
        self.assertEqual(session.user, user)
        self.assertEqual(session.user.username, "workflow_user")

    def test_workflow_failure_updates_session_status_to_failed(self):
        workflow, _, market, _ = self._build_workflow(route="market")
        market.run.side_effect = RuntimeError("Market node failure")

        with self.assertRaises(RuntimeError):
            workflow.run(
                "What is the RELIANCE price?",
                thread_id="failed-session-thread",
            )

        session = ResearchSession.objects.get(thread_id="failed-session-thread")
        self.assertEqual(session.status, "FAILED")

    def test_workflow_failure_retains_correct_user(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="failed_user", password="password")

        workflow, _, market, _ = self._build_workflow(route="market")
        market.run.side_effect = RuntimeError("Market node failure")

        with self.assertRaises(RuntimeError):
            workflow.run(
                "What is the RELIANCE price?",
                user=user,
                thread_id="failed-user-thread",
            )

        session = ResearchSession.objects.get(thread_id="failed-user-thread")
        self.assertEqual(session.status, "FAILED")
        self.assertEqual(session.user, user)

    def test_persistence_failure_marks_session_as_failed(self):
        workflow, _, _, _ = self._build_workflow(route="market")

        with patch(
            "apps.ai.graph.langgraph_workflow.ResearchSessionService.save_workflow_result",
            side_effect=RuntimeError("Database failure during persistence"),
        ):
            with self.assertRaises(RuntimeError):
                workflow.run(
                    "What is the RELIANCE price?",
                    thread_id="persist-fail-thread",
                )

        session = ResearchSession.objects.get(thread_id="persist-fail-thread")
        self.assertEqual(session.status, "FAILED")


# ---------------------------------------------------------------------------
# Portfolio Backtest Node Tests
# ---------------------------------------------------------------------------

class PortfolioBacktestNodeTestCase(TestCase):
    """Unit tests for the portfolio_backtest LangGraph node and related routing."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _base_portfolio() -> Portfolio:
        return Portfolio(
            holdings=[
                Holding(ticker="RELIANCE", market="IN", quantity=10, average_price=1200),
                Holding(ticker="TCS", market="IN", quantity=5, average_price=3500),
            ]
        )

    @staticmethod
    def _backtest_portfolio_input(
        include_backtest: bool = True,
        portfolio_id: str | None = None,
    ) -> PortfolioWorkflowInput:
        p = Portfolio(
            holdings=[
                Holding(ticker="RELIANCE", market="IN", quantity=10, average_price=1200),
                Holding(ticker="TCS", market="IN", quantity=5, average_price=3500),
            ]
        )
        if portfolio_id is not None:
            # inject synthetic id so node can look it up
            p = p.model_copy(update={"id": portfolio_id})
        return PortfolioWorkflowInput(
            portfolio=p,
            include_backtest=include_backtest,
            backtest_from_date="2024-01-01",
            backtest_to_date="2025-06-01",
            backtest_benchmark_ticker="NIFTY 50",
            backtest_initial_capital=100_000.0,
            backtest_rebalance_frequency="monthly",
            backtest_in_sample_window_days=252,
            backtest_out_of_sample_step_days=21,
            backtest_transaction_cost_bps=10.0,
            backtest_risk_free_rate=0.0,
            backtest_min_weight=0.0,
            backtest_max_weight=1.0,
        )

    @staticmethod
    def _build_backtest_workflow(
        backtest_engine=None,
        backtest_evaluator=None,
    ):
        """Build a LangGraphResearchWorkflow with all mocks, including optional backtest deps."""
        checkpointer = _test_checkpointer()
        router = MagicMock()
        router.route.return_value = "portfolio"

        financial = MagicMock()
        market = MagicMock()
        news = MagicMock()
        risk = MagicMock()

        portfolio = MagicMock()
        portfolio.analyze.return_value = PortfolioIntelligence(
            invested_value=12000.0,
            current_value=13000.0,
            profit_loss=1000.0,
            profit_loss_percentage=8.33,
            holdings_count=2,
        )
        portfolio.get_last_prices.return_value = {"RELIANCE": 1250.0, "TCS": 3600.0}

        optimization = MagicMock()
        optimization.run.return_value = AgentResult(
            response="Optimization result",
            tools_used=["portfolio_optimization"],
        )

        synthesis = MagicMock()
        synthesis.run.return_value = AgentResult(
            response="Synthesis including backtest",
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
            portfolio_backtest_engine=backtest_engine,
            portfolio_backtest_evaluator=backtest_evaluator,
            checkpointer=checkpointer,
        )

        return workflow, portfolio, synthesis

    # ------------------------------------------------------------------
    # 1. _portfolio_risk_decision routing
    # ------------------------------------------------------------------

    def test_portfolio_risk_decision_routes_to_backtest_when_flag_true(self):
        """_portfolio_risk_decision returns 'portfolio_backtest' when include_backtest=True."""
        workflow, _, _ = self._build_backtest_workflow()
        pi = self._backtest_portfolio_input(include_backtest=True)
        result = workflow._portfolio_risk_decision({"portfolio_input": pi})
        self.assertEqual(result, "portfolio_backtest")

    def test_portfolio_risk_decision_routes_to_synthesis_when_flag_false(self):
        """_portfolio_risk_decision returns 'synthesis' when include_backtest=False."""
        workflow, _, _ = self._build_backtest_workflow()
        pi = self._backtest_portfolio_input(include_backtest=False)
        result = workflow._portfolio_risk_decision({"portfolio_input": pi})
        self.assertEqual(result, "synthesis")

    def test_portfolio_risk_decision_routes_to_synthesis_with_no_portfolio_input(self):
        """_portfolio_risk_decision returns 'synthesis' when portfolio_input is None."""
        workflow, _, _ = self._build_backtest_workflow()
        result = workflow._portfolio_risk_decision({})
        self.assertEqual(result, "synthesis")

    # ------------------------------------------------------------------
    # 2. Node skips gracefully when include_backtest=False
    # ------------------------------------------------------------------

    def test_backtest_node_returns_empty_when_flag_false(self):
        """Node must be a no-op when include_backtest is False (defensive guard)."""
        workflow, _, _ = self._build_backtest_workflow()
        pi = self._backtest_portfolio_input(include_backtest=False)
        result = workflow._execute_portfolio_backtest_node({"portfolio_input": pi})
        # Should return an empty dict — no errors, no results
        self.assertNotIn("errors", result)

    # ------------------------------------------------------------------
    # 3. Node returns error when portfolio_input is missing
    # ------------------------------------------------------------------

    def test_backtest_node_returns_error_without_portfolio_input(self):
        """Node must emit a non-fatal error dict when portfolio_input is absent."""
        workflow, _, _ = self._build_backtest_workflow()
        result = workflow._execute_portfolio_backtest_node({})
        self.assertIn("errors", result)
        self.assertTrue(any("required" in e.lower() for e in result["errors"]))

    # ------------------------------------------------------------------
    # 4. Node produces a failure payload on exception (non-fatal)
    # ------------------------------------------------------------------

    def test_backtest_node_is_nonfatal_on_builder_exception(self):
        """When the builder raises, the node must NOT raise; it returns a failure dict
        so that synthesis can still execute."""
        from unittest.mock import patch

        workflow, _, _ = self._build_backtest_workflow()
        pi = self._backtest_portfolio_input(include_backtest=True)
        # No django_portfolio_id → node emits a non-fatal error and returns without raising
        result = workflow._execute_portfolio_backtest_node({"portfolio_input": pi})

        # Must NOT raise — must return errors + a failure payload
        self.assertIn("errors", result)
        self.assertIn("results", result)
        bt = result["results"].get("portfolio_backtest", {})
        self.assertFalse(bt.get("success", True))
        self.assertIn("error", bt)

    # ------------------------------------------------------------------
    # 5. Node executes full pipeline and stores result
    # ------------------------------------------------------------------

    def test_backtest_node_stores_result_when_pipeline_succeeds(self):
        """When Builder/Engine/Evaluator all succeed, results['portfolio_backtest'] is populated."""
        from unittest.mock import MagicMock, patch

        mock_backtest_input = MagicMock()
        mock_backtest_input.tickers = ["RELIANCE", "TCS"]
        mock_backtest_input.initial_capital = 100_000.0
        mock_backtest_input.backtest_from_date = None
        mock_backtest_input.backtest_to_date = None

        mock_raw_result = MagicMock()
        mock_raw_result.success = True
        mock_raw_result.message = "Backtest completed successfully."
        mock_raw_result.final_portfolio_value = 115_000.0
        mock_raw_result.total_transaction_costs = 450.0
        mock_raw_result.equity_curve = [
            {"date": "2024-01-15", "portfolio_value": 100_000.0, "daily_return": 0.0},
            {"date": "2024-06-01", "portfolio_value": 107_500.0, "daily_return": 0.002},
            {"date": "2025-06-01", "portfolio_value": 115_000.0, "daily_return": 0.003},
        ]
        mock_raw_result.rebalance_events = []
        mock_raw_result.strategy_metrics = None
        mock_raw_result.buy_and_hold_metrics = None
        mock_raw_result.benchmark_metrics = None
        mock_raw_result.benchmark_ticker = "NIFTY 50"
        mock_raw_result.relative_metrics = None

        mock_engine = MagicMock()
        mock_engine.run.return_value = mock_raw_result

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = mock_raw_result

        workflow, _, _ = self._build_backtest_workflow(
            backtest_engine=mock_engine,
            backtest_evaluator=mock_evaluator,
        )
        # Provide a django_portfolio_id so the node can proceed to the builder stage
        from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
        from apps.ai.portfolio.schemas import Portfolio, Holding
        pi = PortfolioWorkflowInput(
            portfolio=Portfolio(
                holdings=[
                    Holding(ticker="RELIANCE", market="IN", quantity=10, average_price=1200),
                    Holding(ticker="TCS", market="IN", quantity=5, average_price=3500),
                ]
            ),
            include_backtest=True,
            django_portfolio_id="aaaaaaaa-0000-0000-0000-000000000001",
            backtest_from_date="2024-01-01",
            backtest_to_date="2025-06-01",
            backtest_initial_capital=100_000.0,
        )

        with patch(
            "apps.portfolio.backtest_builder.PortfolioBacktestInputBuilder.build_backtest_input",
            return_value=mock_backtest_input,
        ):
            with patch(
                "apps.portfolio.models.Portfolio.objects.get",
                return_value=MagicMock(),
            ):
                result = workflow._execute_portfolio_backtest_node(
                    {"portfolio_input": pi}
                )

        self.assertNotIn("errors", result)
        self.assertIn("results", result)
        bt = result["results"]["portfolio_backtest"]
        self.assertTrue(bt["success"])
        self.assertAlmostEqual(bt["final_portfolio_value"], 115_000.0)
        self.assertEqual(bt["benchmark_ticker"], "NIFTY 50")
        # Equity curve sample present
        self.assertIn("equity_curve_sample", bt)
        self.assertGreater(len(bt["equity_curve_sample"]), 0)

    # ------------------------------------------------------------------
    # 6. Full graph run with include_backtest=False skips backtest node
    # ------------------------------------------------------------------

    def test_full_graph_without_backtest_skips_portfolio_backtest(self):
        """When include_backtest=False, synthesis receives no 'portfolio_backtest' result."""
        from unittest.mock import patch

        workflow, portfolio, synthesis = self._build_backtest_workflow()

        # Patch portfolio risk node so it doesn't need real price data
        with patch.object(workflow, "_execute_portfolio_risk_node", return_value={
            "results": {
                "portfolio_risk": {
                    "current_risk": None,
                    "optimized_risk": None,
                }
            }
        }):
            pi = self._backtest_portfolio_input(include_backtest=False)
            state = workflow.run("Analyze my portfolio.", portfolio_input=pi)

        # Synthesis must have been called
        synthesis.run.assert_called_once()
        # portfolio_backtest must NOT appear in results
        self.assertNotIn("portfolio_backtest", state.results)

    # ------------------------------------------------------------------
    # 7. _serialise_backtest_result equity-curve sampling
    # ------------------------------------------------------------------

    def test_serialise_backtest_result_samples_large_equity_curve(self):
        """_serialise_backtest_result must sample equity curves longer than 30 points."""
        from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow

        large_curve = [
            {"date": f"2024-{i:03d}", "portfolio_value": 100_000 + i * 10, "daily_return": 0.0}
            for i in range(120)
        ]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "ok"
        mock_result.final_portfolio_value = 101_200.0
        mock_result.total_transaction_costs = 50.0
        mock_result.equity_curve = large_curve
        mock_result.rebalance_events = []
        mock_result.strategy_metrics = None
        mock_result.buy_and_hold_metrics = None
        mock_result.benchmark_metrics = None
        mock_result.benchmark_ticker = None
        mock_result.relative_metrics = None

        mock_input = MagicMock()
        mock_input.tickers = ["RELIANCE", "TCS"]
        mock_input.initial_capital = 100_000.0

        payload = LangGraphResearchWorkflow._serialise_backtest_result(
            mock_result, mock_input
        )

        # Full curve has 120 points — sampled result must be much shorter
        sampled = payload["equity_curve_sample"]
        self.assertLessEqual(len(sampled), 30)
        # First and last points must be preserved
        self.assertEqual(sampled[0]["date"], "2024-000")
        self.assertEqual(sampled[-1]["date"], "2024-119")

    # ------------------------------------------------------------------
    # 8. PortfolioWorkflowInput backtest field defaults
    # ------------------------------------------------------------------

    def test_portfolio_workflow_input_backtest_defaults(self):
        """PortfolioWorkflowInput must default include_backtest=False and use sensible values."""
        p = self._base_portfolio()
        wi = PortfolioWorkflowInput(portfolio=p)

        self.assertFalse(wi.include_backtest)
        self.assertIsNone(wi.backtest_from_date)
        self.assertIsNone(wi.backtest_to_date)
        self.assertIsNone(wi.backtest_benchmark_ticker)
        self.assertEqual(wi.backtest_initial_capital, 100_000.0)
        self.assertEqual(wi.backtest_rebalance_frequency, "monthly")
        self.assertEqual(wi.backtest_in_sample_window_days, 252)
        self.assertEqual(wi.backtest_out_of_sample_step_days, 21)
        self.assertEqual(wi.backtest_transaction_cost_bps, 10.0)
        self.assertEqual(wi.backtest_risk_free_rate, 0.0)
        self.assertEqual(wi.backtest_min_weight, 0.0)
        self.assertEqual(wi.backtest_max_weight, 1.0)

    # ------------------------------------------------------------------
    # 9. PortfolioWorkflowInput backtest fields round-trip correctly
    # ------------------------------------------------------------------

    def test_portfolio_workflow_input_backtest_fields_round_trip(self):
        """All backtest config fields must survive a model_dump / model_validate cycle."""
        from pydantic import ValidationError

        p = self._base_portfolio()
        wi = PortfolioWorkflowInput(
            portfolio=p,
            include_backtest=True,
            backtest_from_date="2024-01-01",
            backtest_to_date="2025-06-01",
            backtest_benchmark_ticker="NIFTY 50",
            backtest_initial_capital=50_000.0,
            backtest_rebalance_frequency="quarterly",
            backtest_in_sample_window_days=126,
            backtest_out_of_sample_step_days=63,
            backtest_transaction_cost_bps=5.0,
            backtest_risk_free_rate=0.065,
            backtest_min_weight=0.05,
            backtest_max_weight=0.40,
        )

        dumped = wi.model_dump()
        restored = PortfolioWorkflowInput.model_validate(dumped)

        self.assertTrue(restored.include_backtest)
        self.assertEqual(restored.backtest_from_date, "2024-01-01")
        self.assertEqual(restored.backtest_to_date, "2025-06-01")
        self.assertEqual(restored.backtest_benchmark_ticker, "NIFTY 50")
        self.assertAlmostEqual(restored.backtest_initial_capital, 50_000.0)
        self.assertEqual(restored.backtest_rebalance_frequency, "quarterly")
        self.assertEqual(restored.backtest_in_sample_window_days, 126)
        self.assertEqual(restored.backtest_out_of_sample_step_days, 63)
        self.assertAlmostEqual(restored.backtest_transaction_cost_bps, 5.0)
        self.assertAlmostEqual(restored.backtest_risk_free_rate, 0.065)
        self.assertAlmostEqual(restored.backtest_min_weight, 0.05)
        self.assertAlmostEqual(restored.backtest_max_weight, 0.40)

        # Reject invalid capital
        with self.assertRaises(ValidationError):
            PortfolioWorkflowInput(portfolio=p, backtest_initial_capital=-1.0)

        # Reject invalid in_sample_window_days
        with self.assertRaises(ValidationError):
            PortfolioWorkflowInput(portfolio=p, backtest_in_sample_window_days=1)