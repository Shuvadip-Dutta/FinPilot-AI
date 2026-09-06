"""Integration tests for portfolio integration into AgentService and LangGraph workflow."""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.graph.state import AgentState
from apps.ai.portfolio.optimization import (
    OptimizationInput,
    OptimizationResult,
)
from apps.ai.portfolio.schemas import Holding as PydanticHolding
from apps.ai.portfolio.schemas import Portfolio as PydanticPortfolio
from apps.ai.portfolio.schemas import PortfolioIntelligence
from apps.ai.services.agent_service import AgentService
from apps.ai.services.schemas import AgentResult
from apps.portfolio.builder import PortfolioWorkflowInputBuilder
from apps.portfolio.models import Holding, Portfolio

User = get_user_model()


class PortfolioIntegrationTestCase(TestCase):
    """Integration test suite for Portfolio AI Workflow Requirements 1 to 12."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="password123",
        )

        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Tech Growth",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("2500.00"),
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5.0"),
            average_price=Decimal("3500.00"),
        )

        self.other_portfolio = Portfolio.objects.create(
            user=self.other_user,
            name="Other Portfolio",
        )
        Holding.objects.create(
            portfolio=self.other_portfolio,
            ticker="INFY",
            market="IN",
            quantity=Decimal("20.0"),
            average_price=Decimal("1500.00"),
        )

    def test_1_agent_service_injects_portfolio_dependencies(self):
        """1. AgentService injects portfolio dependencies (PortfolioIntelligenceService & PortfolioOptimizationAgent)."""
        service = AgentService.create_canonical()
        self.assertIsNotNone(service.workflow.portfolio_intelligence)
        self.assertIsNotNone(service.workflow.portfolio_optimization_agent)

    def test_2_existing_research_request_works_without_portfolio_input(self):
        """2. Existing research request still works without portfolio_input."""
        mock_workflow = MagicMock()
        mock_workflow.run.return_value = AgentState(
            user_message="Analyze RELIANCE",
            ticker="RELIANCE",
            market="IN",
            results={
                "financial": AgentResult(response="Financial data", tools_used=[]),
                "synthesis": AgentResult(response="Synthesis output", tools_used=[]),
            },
        )
        service = AgentService(workflow=mock_workflow)
        res = service.run("Analyze RELIANCE", ticker="RELIANCE", market="IN")
        self.assertEqual(res.response, "Synthesis output")
        mock_workflow.run.assert_called_once()
        _, kwargs = mock_workflow.run.call_args
        self.assertIsNone(kwargs.get("portfolio_input"))

    def test_3_authenticated_portfolio_id_resolved_to_user_portfolio(self):
        """3. Authenticated portfolio_id is resolved to the correct user's portfolio."""
        mock_workflow = MagicMock()
        mock_workflow.run.return_value = AgentState(
            user_message="Analyze portfolio",
            results={"synthesis": AgentResult(response="Portfolio summary", tools_used=[])},
        )
        service = AgentService(workflow=mock_workflow)
        res = service.run(
            "Analyze portfolio",
            user=self.user,
            portfolio_id=self.portfolio.id,
        )
        self.assertEqual(res.response, "Portfolio summary")
        _, kwargs = mock_workflow.run.call_args
        portfolio_input = kwargs.get("portfolio_input")
        self.assertIsNotNone(portfolio_input)
        self.assertIsInstance(portfolio_input, PortfolioWorkflowInput)
        self.assertEqual(len(portfolio_input.portfolio.holdings), 2)

    def test_4_another_users_portfolio_returns_404_not_found(self):
        """4. Another user's portfolio returns 404/not-found (raises Http404)."""
        from django.http import Http404

        service = AgentService.create_canonical()
        with self.assertRaises(Http404):
            service.run(
                "Analyze portfolio",
                user=self.user,
                portfolio_id=self.other_portfolio.id,
            )

    def test_5_portfolio_orm_converted_through_builder(self):
        """5. Portfolio ORM is converted through PortfolioWorkflowInputBuilder."""
        fake_hist_fetcher = lambda ticker, to_date, from_date, market: {
            "candles": [{"close": 2500.0}, {"close": 2550.0}, {"close": 2600.0}]
        }
        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=fake_hist_fetcher)
        workflow_input = builder.build_workflow_input(self.portfolio, include_optimization=True)

        self.assertIsInstance(workflow_input, PortfolioWorkflowInput)
        self.assertEqual(len(workflow_input.portfolio.holdings), 2)
        self.assertEqual(workflow_input.portfolio.holdings[0].ticker, "RELIANCE")
        self.assertEqual(workflow_input.portfolio.holdings[1].ticker, "TCS")
        self.assertIsNotNone(workflow_input.optimization_input)
        self.assertIn("RELIANCE", workflow_input.optimization_input.tickers)
        self.assertIn("TCS", workflow_input.optimization_input.tickers)

    def test_6_portfolio_only_workflow_reaches_portfolio_node(self):
        """6. Portfolio-only workflow reaches portfolio node."""
        fake_hist_fetcher = lambda ticker, to_date, from_date, market: {
            "candles": [{"close": 2500.0}, {"close": 2550.0}, {"close": 2600.0}]
        }
        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=fake_hist_fetcher)
        p_input = builder.build_workflow_input(self.portfolio)

        mock_intel_service = MagicMock()
        mock_intel_service.analyze.return_value = PortfolioIntelligence(
            invested_value=42500.0,
            current_value=45000.0,
            profit_loss=2500.0,
            profit_loss_percentage=5.88,
            holdings_count=2,
        )

        canonical_wf = AgentService.create_canonical().workflow
        canonical_wf.portfolio_intelligence = mock_intel_service
        canonical_wf.synthesis_agent = MagicMock(run=MagicMock(return_value=AgentResult(response="Synthesis output", tools_used=[])))

        thread_id = f"test-6-{uuid.uuid4()}"
        final_state = canonical_wf.run(
            user_message="Evaluate portfolio",
            portfolio_input=p_input,
            thread_id=thread_id,
        )

        self.assertEqual(final_state.route, "portfolio")
        mock_intel_service.analyze.assert_called_once()
        self.assertIn("portfolio", final_state.results)

    def test_7_portfolio_analysis_result_stored_in_state_results_portfolio(self):
        """7. Portfolio analysis result is stored in state.results['portfolio']."""
        intel = PortfolioIntelligence(
            invested_value=42500.0,
            current_value=45000.0,
            profit_loss=2500.0,
            profit_loss_percentage=5.88,
            holdings_count=2,
        )
        mock_intel_service = MagicMock()
        mock_intel_service.analyze.return_value = intel

        fake_hist_fetcher = lambda ticker, to_date, from_date, market: {
            "candles": [{"close": 2500.0}, {"close": 2550.0}, {"close": 2600.0}]
        }
        p_input = PortfolioWorkflowInputBuilder(historical_data_fetcher=fake_hist_fetcher).build_workflow_input(self.portfolio)

        canonical_wf = AgentService.create_canonical().workflow
        canonical_wf.portfolio_intelligence = mock_intel_service
        canonical_wf.synthesis_agent = MagicMock(run=MagicMock(return_value=AgentResult(response="Synthesis output", tools_used=[])))

        thread_id = f"test-7-{uuid.uuid4()}"
        final_state = canonical_wf.run("Analyze portfolio", portfolio_input=p_input, thread_id=thread_id)
        stored_result = final_state.results.get("portfolio")
        self.assertEqual(stored_result, intel)

    def test_8_optimization_request_reaches_portfolio_optimization_node(self):
        """8. Optimization request reaches portfolio_optimization node."""
        mock_opt_agent = MagicMock()
        mock_opt_agent.run.return_value = AgentResult(
            response="Optimization completed",
            tools_used=["portfolio_optimization"],
            data={"weights": {"RELIANCE": 0.6, "TCS": 0.4}},
        )
        mock_intel_service = MagicMock()
        mock_intel_service.analyze.return_value = PortfolioIntelligence(
            invested_value=1000.0, current_value=1100.0, profit_loss=100.0, profit_loss_percentage=10.0, holdings_count=2
        )

        fake_hist_fetcher = lambda ticker, to_date, from_date, market: {
            "candles": [{"close": 2500.0}, {"close": 2550.0}, {"close": 2600.0}]
        }
        p_input = PortfolioWorkflowInputBuilder(historical_data_fetcher=fake_hist_fetcher).build_workflow_input(
            self.portfolio, include_optimization=True
        )

        canonical_wf = AgentService.create_canonical().workflow
        canonical_wf.portfolio_intelligence = mock_intel_service
        canonical_wf.portfolio_optimization_agent = mock_opt_agent
        canonical_wf.synthesis_agent = MagicMock(run=MagicMock(return_value=AgentResult(response="Synthesis output", tools_used=[])))

        thread_id = f"test-8-{uuid.uuid4()}"
        final_state = canonical_wf.run("Optimize my portfolio", portfolio_input=p_input, thread_id=thread_id)
        mock_opt_agent.run.assert_called_once()
        self.assertIn("portfolio_optimization", final_state.results)

    def test_9_optimization_result_stored_in_state_results_portfolio_optimization(self):
        """9. Optimization result is stored in state.results['portfolio_optimization']."""
        expected_opt_result = AgentResult(
            response="Optimal allocation calculated",
            tools_used=["portfolio_optimization"],
            data={"weights": {"RELIANCE": 0.5, "TCS": 0.5}},
        )
        mock_opt_agent = MagicMock()
        mock_opt_agent.run.return_value = expected_opt_result

        mock_intel_service = MagicMock()
        mock_intel_service.analyze.return_value = PortfolioIntelligence(
            invested_value=1000.0, current_value=1100.0, profit_loss=100.0, profit_loss_percentage=10.0, holdings_count=2
        )

        fake_hist_fetcher = lambda ticker, to_date, from_date, market: {
            "candles": [{"close": 2500.0}, {"close": 2550.0}, {"close": 2600.0}]
        }
        p_input = PortfolioWorkflowInputBuilder(historical_data_fetcher=fake_hist_fetcher).build_workflow_input(
            self.portfolio, include_optimization=True
        )

        canonical_wf = AgentService.create_canonical().workflow
        canonical_wf.portfolio_intelligence = mock_intel_service
        canonical_wf.portfolio_optimization_agent = mock_opt_agent
        canonical_wf.synthesis_agent = MagicMock(run=MagicMock(return_value=AgentResult(response="Synthesis output", tools_used=[])))

        thread_id = f"test-9-{uuid.uuid4()}"
        final_state = canonical_wf.run("Optimize my portfolio", portfolio_input=p_input, thread_id=thread_id)
        self.assertEqual(final_state.results.get("portfolio_optimization"), expected_opt_result)

    def test_10_portfolio_only_request_does_not_execute_single_stock_risk_path(self):
        """10. Portfolio-only request does not execute the single-stock risk path."""
        mock_risk_agent = MagicMock()
        mock_intel_service = MagicMock()
        mock_intel_service.analyze.return_value = PortfolioIntelligence(
            invested_value=1000.0, current_value=1100.0, profit_loss=100.0, profit_loss_percentage=10.0, holdings_count=2
        )

        fake_hist_fetcher = lambda ticker, to_date, from_date, market: {
            "candles": [{"close": 2500.0}, {"close": 2550.0}, {"close": 2600.0}]
        }
        p_input = PortfolioWorkflowInputBuilder(historical_data_fetcher=fake_hist_fetcher).build_workflow_input(self.portfolio)

        canonical_wf = AgentService.create_canonical().workflow
        canonical_wf.portfolio_intelligence = mock_intel_service
        canonical_wf.risk_agent = mock_risk_agent
        canonical_wf.synthesis_agent = MagicMock(run=MagicMock(return_value=AgentResult(response="Synthesis output", tools_used=[])))
        canonical_wf._graph = canonical_wf._build_graph()

        thread_id = f"test-10-{uuid.uuid4()}"
        final_state = canonical_wf.run("Analyze portfolio", portfolio_input=p_input, thread_id=thread_id)
        mock_risk_agent.run.assert_not_called()
        self.assertNotIn("risk", final_state.results)

    def test_11_final_synthesis_receives_portfolio_analysis(self):
        """11. Final synthesis receives portfolio analysis."""
        mock_synthesis = MagicMock()
        mock_synthesis.run.return_value = AgentResult(response="Synthesized portfolio overview", tools_used=[])

        intel = PortfolioIntelligence(
            invested_value=42500.0,
            current_value=45000.0,
            profit_loss=2500.0,
            profit_loss_percentage=5.88,
            holdings_count=2,
        )
        mock_intel_service = MagicMock()
        mock_intel_service.analyze.return_value = intel

        fake_hist_fetcher = lambda ticker, to_date, from_date, market: {
            "candles": [{"close": 2500.0}, {"close": 2550.0}, {"close": 2600.0}]
        }
        p_input = PortfolioWorkflowInputBuilder(historical_data_fetcher=fake_hist_fetcher).build_workflow_input(self.portfolio)

        canonical_wf = AgentService.create_canonical().workflow
        canonical_wf.portfolio_intelligence = mock_intel_service
        canonical_wf.synthesis_agent = mock_synthesis

        thread_id = f"test-11-{uuid.uuid4()}"
        final_state = canonical_wf.run("Analyze portfolio", portfolio_input=p_input, thread_id=thread_id)
        self.assertIn("synthesis", final_state.results)
        self.assertEqual(final_state.results["synthesis"].response, "Synthesized portfolio overview")

    def test_12_existing_research_workflow_tests_continue_passing(self):
        """12. Existing research workflow still routes single-stock requests properly."""
        canonical_wf = AgentService.create_canonical().workflow
        canonical_wf.financial_agent = MagicMock(run=MagicMock(return_value=AgentResult(response="Fin ok", tools_used=[])))
        canonical_wf.market_agent = MagicMock(run=MagicMock(return_value=AgentResult(response="Mkt ok", tools_used=[])))
        canonical_wf.news_agent = MagicMock(run=MagicMock(return_value=AgentResult(response="News ok", tools_used=[])))
        canonical_wf.risk_agent = MagicMock(run=MagicMock(return_value=AgentResult(response="Risk ok", tools_used=[])))
        canonical_wf.synthesis_agent = MagicMock(run=MagicMock(return_value=AgentResult(response="Single stock synthesis", tools_used=[])))

        thread_id = f"test-12-{uuid.uuid4()}"
        state = canonical_wf.run("Analyze RELIANCE", ticker="RELIANCE", market="IN", thread_id=thread_id)
        self.assertEqual(state.route, "general")
        self.assertIn("financial", state.results)
        self.assertIn("market", state.results)
        self.assertIn("news", state.results)
        self.assertIn("risk", state.results)


class PortfolioAPIChatEndpointTestCase(APITestCase):
    """API view level test for portfolio_id in AIChatView."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="chatuser",
            email="chat@example.com",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="otherchatuser",
            email="otherchat@example.com",
            password="password123",
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Chat Portfolio",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5.0"),
            average_price=Decimal("3000.00"),
        )
        self.other_portfolio = Portfolio.objects.create(
            user=self.other_user,
            name="Unowned Portfolio",
        )

    def test_api_chat_with_unowned_portfolio_id_returns_404(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/ai/chat/",
            {
                "message": "Analyze portfolio",
                "portfolio_id": str(self.other_portfolio.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
