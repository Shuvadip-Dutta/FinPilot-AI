"""Unit tests for quantitative portfolio risk integration (current weights, risk node, graph topology, synthesis)."""

import math
from unittest.mock import MagicMock
from django.test import TestCase

from apps.ai.agents.base import AgentResult
from apps.ai.agents.synthesis import FinalSynthesisAgent
from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.graph.state import AgentState
from apps.ai.portfolio.optimization import OptimizationInput, OptimizationResult
from apps.ai.portfolio.risk import (
    PortfolioMarketDataError,
    PortfolioRiskEngine,
    calculate_current_weights,
)
from apps.ai.portfolio.schemas import (
    Holding,
    Portfolio,
    PortfolioRiskMetrics,
)


class CurrentWeightsTestCase(TestCase):
    """Test suite for calculate_current_weights helper."""

    def test_equal_value_holdings(self):
        portfolio = Portfolio(
            holdings=[
                Holding(ticker="AAPL", market="US", quantity=10.0, average_price=100.0),
                Holding(ticker="GOOGL", market="US", quantity=5.0, average_price=200.0),
            ]
        )
        last_prices = {"AAPL": 100.0, "GOOGL": 200.0}
        weights = calculate_current_weights(portfolio, last_prices)
        self.assertAlmostEqual(weights["AAPL"], 0.5)
        self.assertAlmostEqual(weights["GOOGL"], 0.5)

    def test_unequal_value_holdings(self):
        portfolio = Portfolio(
            holdings=[
                Holding(ticker="RELIANCE", market="IN", quantity=30.0, average_price=2000.0),
                Holding(ticker="TCS", market="IN", quantity=10.0, average_price=3000.0),
            ]
        )
        # RELIANCE: 30 * 2000 = 60000; TCS: 10 * 3000 = 30000; Total = 90000
        last_prices = {"RELIANCE": 2000.0, "TCS": 3000.0}
        weights = calculate_current_weights(portfolio, last_prices)
        self.assertAlmostEqual(weights["RELIANCE"], 60000.0 / 90000.0)
        self.assertAlmostEqual(weights["TCS"], 30000.0 / 90000.0)

    def test_invalid_zero_portfolio_value(self):
        portfolio = Portfolio(
            holdings=[
                Holding(ticker="ABC", market="US", quantity=1.0, average_price=10.0),
            ]
        )
        last_prices = {"ABC": 0.0}
        with self.assertRaises(PortfolioMarketDataError) as ctx:
            calculate_current_weights(portfolio, last_prices)
        self.assertIn("Invalid market price for holding ABC", str(ctx.exception))

    def test_missing_price_raises_market_data_error(self):
        portfolio = Portfolio(
            holdings=[
                Holding(ticker="AAPL", market="US", quantity=10.0, average_price=100.0),
            ]
        )
        last_prices = {}
        with self.assertRaises(PortfolioMarketDataError) as ctx:
            calculate_current_weights(portfolio, last_prices)
        self.assertIn("Missing current market price for holding AAPL", str(ctx.exception))

    def test_invalid_price_raises_market_data_error(self):
        portfolio = Portfolio(
            holdings=[
                Holding(ticker="AAPL", market="US", quantity=10.0, average_price=100.0),
            ]
        )
        last_prices = {"AAPL": -50.0}
        with self.assertRaises(PortfolioMarketDataError) as ctx:
            calculate_current_weights(portfolio, last_prices)
        self.assertIn("Invalid market price for holding AAPL", str(ctx.exception))


class PortfolioRiskNodeTestCase(TestCase):
    """Test suite for _execute_portfolio_risk_node in LangGraphResearchWorkflow."""

    def setUp(self):
        self.portfolio = Portfolio(
            holdings=[
                Holding(ticker="RELIANCE", market="IN", quantity=10.0, average_price=100.0),
                Holding(ticker="TCS", market="IN", quantity=10.0, average_price=100.0),
            ]
        )
        self.historical_prices = {
            "RELIANCE": [100.0, 102.0, 104.0, 103.0, 105.0, 107.0, 106.0, 108.0, 110.0, 109.0],
            "TCS": [200.0, 201.0, 203.0, 202.0, 205.0, 204.0, 206.0, 208.0, 207.0, 210.0],
        }
        self.portfolio_input = PortfolioWorkflowInput(
            portfolio=self.portfolio,
            historical_prices=self.historical_prices,
        )
        self.mock_intel = MagicMock()
        self.mock_intel.get_last_prices.return_value = {"RELIANCE": 100.0, "TCS": 100.0}

        self.workflow = LangGraphResearchWorkflow(
            router=MagicMock(),
            financial_agent=MagicMock(),
            market_agent=MagicMock(),
            news_agent=MagicMock(),
            portfolio_intelligence=self.mock_intel,
        )

    def test_current_risk_produced_without_optimization(self):
        state = {
            "thread_id": "test-1",
            "route": "portfolio",
            "portfolio_input": self.portfolio_input,
            "results": {},
        }
        res = self.workflow._execute_portfolio_risk_node(state)
        self.assertIn("results", res)
        self.assertIn("portfolio_risk", res["results"])

        risk_data = res["results"]["portfolio_risk"]
        self.assertIsInstance(risk_data["current_risk"], PortfolioRiskMetrics)
        self.assertIsNone(risk_data["optimized_risk"])

    def test_current_and_optimized_risk_produced_when_optimization_exists(self):
        opt_result = OptimizationResult(
            success=True,
            status="optimal",
            objective_value=1.5,
            optimized_weights={"RELIANCE": 0.7, "TCS": 0.3},
            holding_allocations={"RELIANCE": 0.7, "TCS": 0.3},
            expected_annual_return=0.15,
            expected_annual_volatility=0.10,
            sharpe_ratio=1.5,
            message="Optimal solution found",
        )
        state = {
            "thread_id": "test-2",
            "route": "portfolio",
            "portfolio_input": self.portfolio_input,
            "results": {
                "portfolio_optimization": opt_result,
            },
        }
        res = self.workflow._execute_portfolio_risk_node(state)
        risk_data = res["results"]["portfolio_risk"]
        self.assertIsInstance(risk_data["current_risk"], PortfolioRiskMetrics)
        self.assertIsInstance(risk_data["optimized_risk"], PortfolioRiskMetrics)


class PortfolioGraphTopologyTestCase(TestCase):
    """Test suite ensuring portfolio workflows follow specified routing topology."""

    def test_portfolio_only_route_decision(self):
        workflow = LangGraphResearchWorkflow(
            router=MagicMock(),
            financial_agent=MagicMock(),
            market_agent=MagicMock(),
            news_agent=MagicMock(),
        )
        state = {
            "user_message": "Analyze my portfolio risk",
            "portfolio_input": PortfolioWorkflowInput(
                portfolio=Portfolio(holdings=[]),
            ),
        }
        next_step = workflow._portfolio_decision(state)
        self.assertEqual(next_step, "portfolio_risk")

    def test_portfolio_optimization_route_decision(self):
        workflow = LangGraphResearchWorkflow(
            router=MagicMock(),
            financial_agent=MagicMock(),
            market_agent=MagicMock(),
            news_agent=MagicMock(),
        )
        state = {
            "user_message": "Optimize my portfolio allocations",
            "portfolio_input": PortfolioWorkflowInput(
                portfolio=Portfolio(holdings=[]),
            ),
        }
        next_step = workflow._portfolio_decision(state)
        self.assertEqual(next_step, "portfolio_optimization")


class PortfolioSynthesisRiskTestCase(TestCase):
    """Test suite for FinalSynthesisAgent portfolio quantitative risk evidence formatting."""

    def test_synthesis_context_and_structured_evidence_with_portfolio_risk(self):
        current_metrics = PortfolioRiskMetrics(
            volatility=0.12,
            downside_volatility=0.08,
            sharpe_ratio=1.2,
            sortino_ratio=1.8,
            calmar_ratio=1.0,
            max_drawdown=0.10,
            max_drawdown_duration_days=15,
            var_95_historical=0.02,
            cvar_95_historical=0.03,
            annualized_return=0.10,
            cagr=0.10,
            total_period_return=0.15,
        )
        optimized_metrics = PortfolioRiskMetrics(
            volatility=0.09,
            downside_volatility=0.05,
            sharpe_ratio=1.6,
            sortino_ratio=2.2,
            calmar_ratio=1.5,
            max_drawdown=0.06,
            max_drawdown_duration_days=10,
            var_95_historical=0.015,
            cvar_95_historical=0.022,
            annualized_return=0.12,
            cagr=0.12,
            total_period_return=0.18,
        )

        state = AgentState(
            user_message="Analyze risk",
            route="portfolio",
            results={
                "portfolio_risk": {
                    "current_risk": current_metrics,
                    "optimized_risk": optimized_metrics,
                }
            },
        )

        agent = FinalSynthesisAgent(llm_service=lambda msgs: "Synthesis output")
        evidence = agent._collect_structured_evidence(state)
        self.assertIn("portfolio_risk", evidence)
        self.assertEqual(evidence["portfolio_risk"]["current_risk"]["sharpe_ratio"], 1.2)
        self.assertEqual(evidence["portfolio_risk"]["optimized_risk"]["sharpe_ratio"], 1.6)

        context = agent._build_context(state)
        self.assertIn("PORTFOLIO QUANTITATIVE RISK EVIDENCE", context)
        risk_sec = context["PORTFOLIO QUANTITATIVE RISK EVIDENCE"]
        self.assertIn("Current Portfolio Risk", risk_sec)
        self.assertIn("Optimized Portfolio Risk", risk_sec)
