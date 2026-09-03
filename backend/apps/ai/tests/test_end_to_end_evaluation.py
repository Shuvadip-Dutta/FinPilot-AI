from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.ai.evaluation.dataset import EVALUATION_DATASET
from apps.ai.evaluation.end_to_end import EndToEndWorkflowEvaluator
from apps.ai.evaluation.schemas import EvaluationCase
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult


class EndToEndWorkflowEvaluationTestCase(SimpleTestCase):

    @staticmethod
    def _workflow_state(route, results, errors=None):
        return AgentState(
            user_message="What should a basic company analysis cover?",
            route=route,
            results=results,
            errors=errors or [],
        )

    def test_successful_finance_end_to_end_case(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="financial",
            results={
                "financial": AgentResult(response="TechCorp generated $500M revenue, net income of $100M, and cash flow of $120M.", tools_used=["get_financials", "get_key_metrics"]),
                "synthesis": AgentResult(response="TechCorp generated $500M revenue, net income of $100M, and cash flow of $120M.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "$500m net income cash flow",
        )

        result = evaluator.evaluate_case(case)

        self.assertEqual(result.actual_route, "financial")
        self.assertTrue(result.route_passed)
        self.assertEqual(result.evaluation_score, 1.0)
        self.assertEqual(result.final_response, "TechCorp generated $500M revenue, net income of $100M, and cash flow of $120M.")

    def test_successful_market_end_to_end_case(self):
        case = next(c for c in EVALUATION_DATASET if c.category == "market")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="market",
            results={
                "market": AgentResult(response="Apex Corp (NASDAQ: APEX) is trading at $185.50, reflecting a gain of +$4.25 (+2.35%) over its previous close of $181.25.", tools_used=["get_market_data"]),
                "synthesis": AgentResult(response="Apex Corp (NASDAQ: APEX) is trading at $185.50, reflecting a gain of +$4.25 (+2.35%) over its previous close of $181.25.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "$185.50 2.35% +$4.25 $181.25",
        )

        result = evaluator.evaluate_case(case)

        self.assertEqual(result.actual_route, "market")
        self.assertTrue(result.route_passed)
        self.assertEqual(result.evaluation_score, 1.0)

    def test_successful_news_end_to_end_case(self):
        case = next(c for c in EVALUATION_DATASET if c.category == "news")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="news",
            results={
                "news": AgentResult(response="Revenue grew 22% YoY to $310M. News sentiment is positive as results exceeded estimates.", tools_used=["get_news"]),
                "synthesis": AgentResult(response="Revenue grew 22% YoY to $310M. News sentiment is positive as results exceeded estimates.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "22% $310M positive exceeded",
        )

        result = evaluator.evaluate_case(case)

        self.assertEqual(result.actual_route, "news")
        self.assertTrue(result.route_passed)
        self.assertEqual(result.evaluation_score, 1.0)

    def test_successful_risk_end_to_end_case(self):
        case = next(c for c in EVALUATION_DATASET if c.category == "risk")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="risk",
            results={
                "risk": AgentResult(response="Portfolio exhibits 65% concentration risk and limited diversification.", tools_used=[]),
                "synthesis": AgentResult(response="Portfolio exhibits 65% concentration risk and limited diversification.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "65% concentration diversification",
        )

        result = evaluator.evaluate_case(case)

        self.assertEqual(result.actual_route, "risk")
        self.assertTrue(result.route_passed)
        self.assertEqual(result.evaluation_score, 1.0)

    def test_successful_portfolio_end_to_end_case(self):
        case = next(c for c in EVALUATION_DATASET if c.category == "portfolio")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="portfolio",
            results={
                "portfolio": AgentResult(response="Portfolio allocation is important.", tools_used=["portfolio_analysis"]),
                "risk": AgentResult(response="Risk matters.", tools_used=["portfolio_risk"]),
                "portfolio_optimization": AgentResult(response="Reduce equities from 70% to 50% with a $100,000 trim and increase fixed income to 40% via $100,000 addition for rebalancing.", tools_used=["portfolio_optimization"]),
                "synthesis": AgentResult(response="Reduce equities from 70% to 50% with a $100,000 trim and increase fixed income to 40% via $100,000 addition for rebalancing.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "reduce equities increase fixed income $100,000 rebalancing",
        )

        result = evaluator.evaluate_case(case)

        self.assertEqual(result.actual_route, "portfolio")
        self.assertTrue(result.route_passed)
        self.assertEqual(result.evaluation_score, 1.0)

    def test_portfolio_numerical_fidelity_is_preserved(self):
        case = next(c for c in EVALUATION_DATASET if c.case_id == "portfolio-optimization-fidelity")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="portfolio",
            results={
                "portfolio_optimization": AgentResult(response="Allocation: 40% energy, 35% financials, 25% cash. Expected return of 12.5%. Volatility of 8.0%. Sharpe ratio of 1.15.", tools_used=["portfolio_optimization"]),
                "synthesis": AgentResult(response="Allocation: 40% energy, 35% financials, 25% cash. Expected return of 12.5%. Volatility of 8.0%. Sharpe ratio of 1.15.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "40% energy 12.5% return 8.0% volatility sharpe ratio of 1.15",
        )

        result = evaluator.evaluate_case(case)
        self.assertIn("12.5%", result.final_response)
        self.assertIn("8.0%", result.final_response)
        self.assertIn("1.15", result.final_response)

    def test_route_mismatch_is_recorded(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="market",
            results={
                "financial": AgentResult(response="Revenue, profit, and cash flow matter.", tools_used=["get_financials"]),
                "synthesis": AgentResult(response="Revenue, profit, and cash flow matter.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        result = evaluator.evaluate_case(case)
        self.assertFalse(result.route_passed)
        self.assertEqual(result.actual_route, "market")

    def test_missing_expected_agent_is_reported(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="financial",
            results={
                "synthesis": AgentResult(response="Revenue, profit, and cash flow matter.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        result = evaluator.evaluate_case(case)
        self.assertIn("financial", result.missing_agents)

    def test_unexpected_agent_is_reported(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="financial",
            results={
                "financial": AgentResult(response="Revenue, profit, and cash flow matter.", tools_used=["get_financials"]),
                "market": AgentResult(response="Market view", tools_used=["get_market_data"]),
                "synthesis": AgentResult(response="Revenue, profit, and cash flow matter.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        result = evaluator.evaluate_case(case)
        self.assertIn("market", result.unexpected_agents)

    def test_missing_synthesis_is_reported(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="financial",
            results={
                "financial": AgentResult(response="Revenue, profit, and cash flow matter.", tools_used=["get_financials"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        result = evaluator.evaluate_case(case)
        self.assertIn("synthesis", result.expected_agents)
        self.assertIn("synthesis", result.missing_agents)
        self.assertTrue(result.route_passed)

    def test_empty_synthesis_is_handled(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="financial",
            results={
                "financial": AgentResult(response="Revenue, profit, and cash flow matter.", tools_used=["get_financials"]),
                "synthesis": AgentResult(response="   ", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        result = evaluator.evaluate_case(case)
        self.assertIn("empty", result.final_response.lower())

    def test_workflow_errors_are_preserved(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="financial",
            results={
                "financial": AgentResult(response="Revenue, profit, and cash flow matter.", tools_used=["get_financials"]),
                "synthesis": AgentResult(response="Revenue, profit, and cash flow matter.", tools_used=["llm_synthesis"]),
            },
            errors=["market: Market unavailable"],
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        result = evaluator.evaluate_case(case)
        self.assertIn("Market unavailable", result.workflow_errors[0])

    def test_missing_data_acknowledgment_is_not_fabricated(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="financial",
            results={
                "financial": AgentResult(response="Financial data is unavailable.", tools_used=["get_financials"]),
                "synthesis": AgentResult(response="Financial data is unavailable; the synthesis cannot claim it otherwise.", tools_used=["llm_synthesis"]),
            },
            errors=["market: Market unavailable"],
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "financial data is unavailable",
        )

        result = evaluator.evaluate_case(case)
        self.assertIn("unavailable", result.final_response.lower())

    def test_latency_is_recorded(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="financial",
            results={
                "financial": AgentResult(response="TechCorp generated $500M revenue, net income of $100M, and cash flow of $120M.", tools_used=["get_financials"]),
                "synthesis": AgentResult(response="TechCorp generated $500M revenue, net income of $100M, and cash flow of $120M.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "$500m net income cash flow",
            clock=lambda: 0.0,
        )

        result = evaluator.evaluate_case(case)
        self.assertGreaterEqual(result.latency_ms, 0.0)

    def test_expected_tier_is_preserved(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="financial",
            results={
                "financial": AgentResult(response="TechCorp generated $500M revenue, net income of $100M, and cash flow of $120M.", tools_used=["get_financials"]),
                "synthesis": AgentResult(response="TechCorp generated $500M revenue, net income of $100M, and cash flow of $120M.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "$500m net income cash flow",
        )

        result = evaluator.evaluate_case(case)
        self.assertEqual(result.expected_tier, case.expected_tier.value)

    def test_end_to_end_report_aggregates(self):
        case = EVALUATION_DATASET[0]
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="financial",
            results={
                "financial": AgentResult(response="TechCorp generated $500M revenue, net income of $100M, and cash flow of $120M.", tools_used=["get_financials"]),
                "synthesis": AgentResult(response="TechCorp generated $500M revenue, net income of $100M, and cash flow of $120M.", tools_used=["llm_synthesis"]),
            },
        )

        evaluator = EndToEndWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "$500m net income cash flow",
        )

        report = evaluator.evaluate([case])

        self.assertEqual(report.total_cases, 1)
        self.assertEqual(report.results[0].case_id, case.case_id)
        self.assertEqual(report.average_score, 1.0)
