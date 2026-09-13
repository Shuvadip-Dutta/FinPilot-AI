"""Integration tests for portfolio integration into AgentService and LangGraph workflow."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.graph.state import AgentState
from apps.research.models import ResearchEvidence, ResearchSession
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
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("2500.00"),
        )
        self.other_portfolio = Portfolio.objects.create(
            user=self.other_user,
            name="Unowned Portfolio",
        )

    @classmethod
    def _make_deterministic_market_fixtures(cls):
        today = datetime.now(timezone.utc).date()
        dates = [
            (today - timedelta(days=i)).isoformat()
            for i in range(800)
            if (today - timedelta(days=i)).weekday() < 5
        ][:520]
        dates.sort()

        def mock_hist(ticker, to_date, from_date=None, market="IN"):
            norm = ticker.upper()
            mult = 1.0 if "RELIANCE" in norm else (1.5 if "TCS" in norm else 10.0)
            base = 2000.0 if "RELIANCE" in norm else (3000.0 if "TCS" in norm else 18000.0)
            return {
                "ticker": ticker,
                "market": market,
                "candles": [
                    {
                        "timestamp": d,
                        "open": base + i * mult,
                        "high": base + i * mult + 10.0,
                        "low": base + i * mult - 10.0,
                        "close": base + i * mult,
                        "volume": 1000,
                    }
                    for i, d in enumerate(dates)
                ],
            }

        def mock_mkt(ticker, market="IN"):
            norm = ticker.upper()
            price = 2500.0 if "RELIANCE" in norm else 3500.0
            return {
                "ticker": ticker,
                "market": market,
                "quotes": [
                    {
                        "exchange": "NSE",
                        "price": price,
                        "percent_change": 1.0,
                        "year_high": 4000.0,
                        "year_low": 2000.0,
                    }
                ],
            }

        def mock_llm_generate(messages, **kwargs):
            return (
                "Portfolio backtest against NIFTY 50 completed successfully. "
                "The strategy achieved a positive CAGR and sound risk-adjusted return."
            )

        return mock_hist, mock_mkt, mock_llm_generate

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

    def test_api_chat_backtest_without_portfolio_id_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/ai/chat/",
            {
                "message": "Backtest my portfolio against NIFTY 50",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("portfolio is required", response.data.get("error", "").lower())

    def test_api_chat_conversational_backtest_e2e_success(self):
        """Phase 3 Full User-Facing Public API E2E Test verifying requirements A through L."""
        mock_hist, mock_mkt, mock_llm = self._make_deterministic_market_fixtures()
        thread_id = "conversational-backtest-e2e"

        # A. Authenticated user
        self.client.force_authenticate(user=self.user)

        with patch("apps.ai.services.research_tools.get_historical_data", side_effect=mock_hist), \
             patch("apps.ai.services.research_tools.get_market_data", side_effect=mock_mkt), \
             patch("apps.ai.services.llm_service.LLMService.generate", side_effect=mock_llm):
            response = self.client.post(
                "/api/v1/ai/chat/",
                {
                    "message": "Backtest my portfolio against NIFTY 50 for the last 2 years",
                    "portfolio_id": str(self.portfolio.id),
                    "thread_id": thread_id,
                },
                format="json",
            )

        # A. Authentication succeeds
        # B. Portfolio ownership succeeds
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # C. Backtest intent is detected & routed to portfolio
        self.assertEqual(response.data["route"], "portfolio")
        self.assertEqual(response.data["thread_id"], thread_id)

        # D, E, F, G, H: Structured data received with deterministic backtest result
        self.assertIsNotNone(response.data["structured_data"])
        self.assertIn("portfolio_backtest", response.data["structured_data"])

        bt_data = response.data["structured_data"]["portfolio_backtest"]
        self.assertTrue(bt_data["success"])
        self.assertEqual(bt_data["benchmark_ticker"], "NIFTY 50")
        self.assertEqual(bt_data["tickers"], ["RELIANCE", "TCS"])

        # F. Deterministic backtest result produced
        self.assertIsNotNone(bt_data.get("strategy_metrics"))
        self.assertIn("cagr", bt_data["strategy_metrics"])
        self.assertIn("sharpe_ratio", bt_data["strategy_metrics"])
        self.assertIn("max_drawdown", bt_data["strategy_metrics"])

        # Benchmark metrics present
        self.assertIsNotNone(bt_data.get("benchmark_metrics"))
        self.assertIn("cagr", bt_data["benchmark_metrics"])

        # Relative metrics present
        self.assertIsNotNone(bt_data.get("relative_metrics"))

        # Equity curve sample present
        self.assertIn("equity_curve_sample", bt_data)
        self.assertGreater(len(bt_data["equity_curve_sample"]), 0)

        # H, L. Final response contains synthesis explaining backtest
        self.assertIn("backtest against NIFTY 50", response.data["response"])

        # I. Session is persisted
        session = ResearchSession.objects.filter(thread_id=thread_id, user=self.user).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.route, "portfolio")
        self.assertEqual(session.status, "COMPLETED")
        self.assertEqual(session.final_synthesis, response.data["response"])

        # J. ResearchEvidence contains agent_name="portfolio_backtest"
        evidence = session.evidence_items.filter(agent_name="portfolio_backtest").first()
        self.assertIsNotNone(evidence)

        # K. structured_data contains deterministic backtest evidence
        self.assertEqual(evidence.structured_data["benchmark_ticker"], "NIFTY 50")
        self.assertAlmostEqual(
            evidence.structured_data["strategy_metrics"]["cagr"],
            bt_data["strategy_metrics"]["cagr"],
        )

    def test_api_chat_conversational_backtest_deterministic_result_preservation(self):
        """Verify the result produced by the real backtest pipeline preserves all authoritative fields."""
        mock_hist, mock_mkt, mock_llm = self._make_deterministic_market_fixtures()
        thread_id = f"test-preservation-{uuid.uuid4()}"

        self.client.force_authenticate(user=self.user)

        with patch("apps.ai.services.research_tools.get_historical_data", side_effect=mock_hist), \
             patch("apps.ai.services.research_tools.get_market_data", side_effect=mock_mkt), \
             patch("apps.ai.services.llm_service.LLMService.generate", side_effect=mock_llm):
            response = self.client.post(
                "/api/v1/ai/chat/",
                {
                    "message": "Backtest my portfolio against NIFTY 50 for the last 2 years",
                    "portfolio_id": str(self.portfolio.id),
                    "thread_id": thread_id,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bt = response.data["structured_data"]["portfolio_backtest"]

        # Strategy metrics fields match Module 10
        strat = bt["strategy_metrics"]
        for field in ("cagr", "volatility", "sharpe_ratio", "sortino_ratio", "max_drawdown", "calmar_ratio"):
            self.assertIn(field, strat)

        # Buy-and-hold metrics
        self.assertIsNotNone(bt.get("buy_and_hold_metrics"))
        self.assertIn("cagr", bt["buy_and_hold_metrics"])

        # Benchmark metrics
        bmark = bt["benchmark_metrics"]
        self.assertIsNotNone(bmark)
        self.assertIn("cagr", bmark)
        self.assertIn("sharpe_ratio", bmark)
        self.assertIn("max_drawdown", bmark)

        # Relative metrics
        rel = bt["relative_metrics"]
        self.assertIsNotNone(rel)
        for field in ("excess_cagr", "total_return_difference", "tracking_error", "information_ratio"):
            self.assertIn(field, rel)

        # Rebalance info
        self.assertIn("rebalance_count", bt)
        self.assertGreaterEqual(bt["rebalance_count"], 1)
        self.assertIn("rebalance_events_summary", bt)

    def test_api_chat_conversational_backtest_session_persistence_contract(self):
        """Verify stored session evidence matches structured backtest evidence and reloads cleanly."""
        mock_hist, mock_mkt, mock_llm = self._make_deterministic_market_fixtures()
        thread_id = f"test-persistence-{uuid.uuid4()}"

        self.client.force_authenticate(user=self.user)

        with patch("apps.ai.services.research_tools.get_historical_data", side_effect=mock_hist), \
             patch("apps.ai.services.research_tools.get_market_data", side_effect=mock_mkt), \
             patch("apps.ai.services.llm_service.LLMService.generate", side_effect=mock_llm):
            response = self.client.post(
                "/api/v1/ai/chat/",
                {
                    "message": "Backtest my portfolio against NIFTY 50 for the last 2 years",
                    "portfolio_id": str(self.portfolio.id),
                    "thread_id": thread_id,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Reload from database directly
        session = ResearchSession.objects.get(thread_id=thread_id, user=self.user)
        self.assertEqual(session.final_synthesis, response.data["response"])

        ev = session.evidence_items.get(agent_name="portfolio_backtest")
        self.assertIsInstance(ev.structured_data, dict)
        self.assertTrue(ev.structured_data["success"])
        self.assertEqual(ev.structured_data["benchmark_ticker"], "NIFTY 50")
        self.assertIn("strategy_metrics", ev.structured_data)
        self.assertIn("cagr", ev.structured_data["strategy_metrics"])

    def test_api_chat_backtest_with_foreign_portfolio_returns_404(self):
        """Foreign portfolio requested for backtesting returns HTTP 404 and creates no session."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/ai/chat/",
            {
                "message": "Backtest my portfolio against NIFTY 50",
                "portfolio_id": str(self.other_portfolio.id),
                "thread_id": "foreign-portfolio-backtest-attempt",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            ResearchSession.objects.filter(thread_id="foreign-portfolio-backtest-attempt").exists()
        )

    def test_api_chat_backtest_invalid_configuration_returns_400(self):
        """Invalid configurations (negative capital, invalid dates, inverted weights) return HTTP 400."""
        self.client.force_authenticate(user=self.user)

        invalid_queries = [
            "Backtest my portfolio with initial capital -50000",
            "Backtest my portfolio from 2025-01-01 to 2024-01-01",
            "Backtest my portfolio from 2024-99-99 to 2025-01-01",
            "Backtest my portfolio with min weight 0.8 and max weight 0.2",
        ]

        for query in invalid_queries:
            thread_id = f"invalid-cfg-{uuid.uuid4()}"
            response = self.client.post(
                "/api/v1/ai/chat/",
                {
                    "message": query,
                    "portfolio_id": str(self.portfolio.id),
                    "thread_id": thread_id,
                },
                format="json",
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
                f"Expected 400 for query '{query}', got {response.status_code}",
            )
            self.assertFalse(
                ResearchSession.objects.filter(thread_id=thread_id).exists()
            )

    def test_api_chat_non_backtest_portfolio_requests_do_not_enable_backtest(self):
        """Non-backtest portfolio requests do not set include_backtest and omit portfolio_backtest evidence."""
        mock_hist, mock_mkt, mock_llm = self._make_deterministic_market_fixtures()
        thread_id = f"normal-portfolio-{uuid.uuid4()}"

        self.client.force_authenticate(user=self.user)

        with patch("apps.ai.services.research_tools.get_historical_data", side_effect=mock_hist), \
             patch("apps.ai.services.research_tools.get_market_data", side_effect=mock_mkt), \
             patch("apps.ai.services.llm_service.LLMService.generate", side_effect=mock_llm):
            response = self.client.post(
                "/api/v1/ai/chat/",
                {
                    "message": "Analyze my portfolio",
                    "portfolio_id": str(self.portfolio.id),
                    "thread_id": thread_id,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        structured = response.data.get("structured_data") or {}
        self.assertNotIn("portfolio_backtest", structured)

        session = ResearchSession.objects.get(thread_id=thread_id)
        self.assertFalse(session.evidence_items.filter(agent_name="portfolio_backtest").exists())

    def test_api_chat_optimize_and_backtest_interaction(self):
        """Optimize and backtest naturally executes both optimization and backtest in workflow."""
        mock_hist, mock_mkt, mock_llm = self._make_deterministic_market_fixtures()
        thread_id = f"opt-backtest-{uuid.uuid4()}"

        self.client.force_authenticate(user=self.user)

        with patch("apps.ai.services.research_tools.get_historical_data", side_effect=mock_hist), \
             patch("apps.ai.services.research_tools.get_market_data", side_effect=mock_mkt), \
             patch("apps.ai.services.llm_service.LLMService.generate", side_effect=mock_llm):
            response = self.client.post(
                "/api/v1/ai/chat/",
                {
                    "message": "Optimize and backtest my portfolio against NIFTY 50",
                    "portfolio_id": str(self.portfolio.id),
                    "thread_id": thread_id,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        structured = response.data.get("structured_data") or {}
        self.assertIn("portfolio_backtest", structured)
        self.assertTrue(structured["portfolio_backtest"]["success"])
