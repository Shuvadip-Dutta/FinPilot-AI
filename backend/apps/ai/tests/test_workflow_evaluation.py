from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from pydantic import BaseModel

from apps.ai.evaluation.evaluator import FinanceModelEvaluator
from apps.ai.evaluation.report import EvaluationReportGenerator
from apps.ai.evaluation.schemas import EvaluationCase, EvaluationReport, EvaluationResult
from apps.ai.evaluation.workflow_evaluator import (
    MultiAgentWorkflowEvaluator,
    WorkflowEvaluationResult,
)
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult


class WorkflowEvaluationResultModel(BaseModel):
    pass


class MultiAgentWorkflowEvaluatorTestCase(SimpleTestCase):
    @staticmethod
    def _case(category="finance", case_id="case-1", required_concepts=None):
        if required_concepts is None:
            required_concepts = ["revenue", "profit", "cash flow"]
        return EvaluationCase(
            case_id=case_id,
            category=category,
            question="What should a basic company analysis cover?",
            reference_answer="Revenue, profit, and cash flow are important.",
            required_concepts=required_concepts,
        )

    @staticmethod
    def _workflow_state(
        *,
        route="financial",
        results=None,
        errors=None,
    ) -> AgentState:
        return AgentState(
            user_message="What should a basic company analysis cover?",
            route=route,
            results=results or {},
            errors=errors or [],
        )

    def test_single_financial_workflow_evaluation(self):
        case = self._case(category="finance", case_id="financial-1")
        model = MagicMock(return_value="Revenue, profit, and cash flow matter.")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            results={
                "financial": AgentResult(
                    response="Financial view",
                    tools_used=["get_financials"],
                ),
                "synthesis": AgentResult(
                    response="Revenue, profit, and cash flow matter.",
                    tools_used=["llm_synthesis"],
                ),
            }
        )

        evaluator = MultiAgentWorkflowEvaluator(workflow=workflow, evaluator=model)

        result = evaluator.evaluate_case(case)

        self.assertIsInstance(result, WorkflowEvaluationResult)
        self.assertEqual(result.route, "financial")
        self.assertTrue(result.evaluation.passed)
        self.assertEqual(result.evaluation.score, 1.0)
        self.assertEqual(result.agents_executed, ["financial", "synthesis"])
        self.assertEqual(result.tools_used, ["get_financials", "llm_synthesis"])

    def test_single_market_workflow_evaluation(self):
        case = self._case(
            category="market",
            case_id="market-1",
            required_concepts=["price", "volume", "volatility"],
        )
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="market",
            results={
                "market": AgentResult(
                    response="Market view",
                    tools_used=["get_market_data"],
                ),
                "synthesis": AgentResult(
                    response="Price, volume, and volatility should be reviewed.",
                    tools_used=["llm_synthesis"],
                ),
            },
        )

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "price volume volatility",
        )

        result = evaluator.evaluate_case(case)

        self.assertEqual(result.route, "market")
        self.assertTrue(result.evaluation.passed)
        self.assertEqual(result.tools_used, ["get_market_data", "llm_synthesis"])

    def test_single_news_workflow_evaluation(self):
        case = self._case(
            category="news",
            case_id="news-1",
            required_concepts=["source", "relevance", "recency"],
        )
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="news",
            results={
                "news": AgentResult(
                    response="News view",
                    tools_used=["get_news"],
                ),
                "synthesis": AgentResult(
                    response="Assess source, relevance, and recency.",
                    tools_used=["llm_synthesis"],
                ),
            },
        )

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "source relevance recency",
        )

        result = evaluator.evaluate_case(case)

        self.assertEqual(result.route, "news")
        self.assertTrue(result.evaluation.passed)

    def test_general_multi_agent_evaluation(self):
        case = self._case(category="finance", case_id="general-1")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="general",
            results={
                "financial": AgentResult(
                    response="Financial view",
                    tools_used=["get_financials"],
                ),
                "market": AgentResult(
                    response="Market view",
                    tools_used=["get_market_data"],
                ),
                "news": AgentResult(
                    response="News view",
                    tools_used=["get_news"],
                ),
                "risk": AgentResult(
                    response="Risk view",
                    tools_used=[],
                ),
                "synthesis": AgentResult(
                    response="Revenue, profit, and cash flow matter.",
                    tools_used=["llm_synthesis"],
                ),
            },
        )

        model = MagicMock(return_value="Revenue and profit and cash flow.")
        evaluator = MultiAgentWorkflowEvaluator(workflow=workflow, evaluator=model)

        result = evaluator.evaluate_case(case)

        self.assertEqual(result.route, "general")
        self.assertEqual(
            result.agents_executed,
            ["financial", "market", "news", "risk", "synthesis"],
        )
        self.assertEqual(
            result.tools_used,
            ["get_financials", "get_market_data", "get_news", "llm_synthesis"],
        )
        self.assertTrue(result.evaluation.passed)

    def test_portfolio_evaluation(self):
        case = self._case(
            category="portfolio",
            case_id="portfolio-1",
            required_concepts=["allocation", "diversification", "performance"],
        )
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="portfolio",
            results={
                "portfolio": AgentResult(
                    response="Portfolio view",
                    tools_used=["portfolio_analysis"],
                ),
                "risk": AgentResult(
                    response="Risk view",
                    tools_used=["portfolio_risk"],
                ),
                "synthesis": AgentResult(
                    response="Allocation, diversification, and performance are key.",
                    tools_used=["llm_synthesis"],
                ),
            },
        )

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "allocation diversification performance",
        )

        result = evaluator.evaluate_case(case)

        self.assertEqual(result.route, "portfolio")
        self.assertTrue(result.evaluation.passed)

    def test_portfolio_optimization_evaluation(self):
        case = self._case(
            category="portfolio",
            case_id="portfolio-opt-1",
            required_concepts=["allocation", "diversification", "performance"],
        )
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="portfolio",
            results={
                "portfolio": AgentResult(
                    response="Portfolio view",
                    tools_used=["portfolio_analysis"],
                ),
                "risk": AgentResult(
                    response="Risk view",
                    tools_used=["portfolio_risk"],
                ),
                "portfolio_optimization": AgentResult(
                    response="Optimization view",
                    tools_used=["portfolio_optimization"],
                ),
                "synthesis": AgentResult(
                    response="Allocation, diversification, and performance are key.",
                    tools_used=["llm_synthesis"],
                ),
            },
        )

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "allocation diversification performance",
        )

        result = evaluator.evaluate_case(case)

        self.assertEqual(result.route, "portfolio")
        self.assertTrue(result.evaluation.passed)
        self.assertEqual(
            result.tools_used,
            [
                "portfolio_analysis",
                "portfolio_risk",
                "portfolio_optimization",
                "llm_synthesis",
            ],
        )

    def test_final_synthesis_response_is_what_gets_scored(self):
        case = self._case(case_id="synthesis-1")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            results={
                "financial": AgentResult(
                    response="Financial view",
                    tools_used=["get_financials"],
                ),
                "synthesis": AgentResult(
                    response="Revenue, profit, and cash flow matter.",
                    tools_used=["llm_synthesis"],
                ),
            }
        )

        model = MagicMock(return_value="Revenue and profit and cash flow.")
        evaluator = MultiAgentWorkflowEvaluator(workflow=workflow, evaluator=model)

        evaluator.evaluate_case(case)

        self.assertEqual(model.call_count, 1)
        self.assertEqual(
            model.call_args.args[0][0]["content"],
            "Revenue, profit, and cash flow matter.",
        )

    def test_intermediate_agent_results_are_not_independently_scored(self):
        case = self._case(case_id="intermediate-1")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            results={
                "financial": AgentResult(
                    response="Financial view",
                    tools_used=["get_financials"],
                ),
                "market": AgentResult(
                    response="Market view",
                    tools_used=["get_market_data"],
                ),
                "synthesis": AgentResult(
                    response="Revenue, profit, and cash flow matter.",
                    tools_used=["llm_synthesis"],
                ),
            }
        )

        model = MagicMock(return_value="Revenue and profit and cash flow.")
        evaluator = MultiAgentWorkflowEvaluator(workflow=workflow, evaluator=model)

        evaluator.evaluate_case(case)

        self.assertEqual(model.call_count, 1)

    def test_workflow_errors_are_preserved_in_result(self):
        case = self._case(case_id="errors-1")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="general",
            results={
                "financial": AgentResult(
                    response="Financial view",
                    tools_used=["get_financials"],
                ),
                "synthesis": AgentResult(
                    response="Revenue, profit, and cash flow matter.",
                    tools_used=["llm_synthesis"],
                ),
            },
            errors=["news: News unavailable"],
        )

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        result = evaluator.evaluate_case(case)

        self.assertIn("news: News unavailable", result.errors)

    def test_partial_failure_still_evaluates_synthesis_when_available(self):
        case = self._case(case_id="partial-1")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="general",
            results={
                "financial": AgentResult(
                    response="Financial view",
                    tools_used=["get_financials"],
                ),
                "news": AgentResult(
                    response="News view",
                    tools_used=["get_news"],
                ),
                "synthesis": AgentResult(
                    response="Revenue, profit, and cash flow matter.",
                    tools_used=["llm_synthesis"],
                ),
            },
            errors=["market: Market unavailable"],
        )

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        result = evaluator.evaluate_case(case)

        self.assertTrue(result.evaluation.passed)
        self.assertIn("market: Market unavailable", result.errors)

    def test_missing_synthesis_produces_failed_evaluation(self):
        case = self._case(case_id="missing-synthesis-1")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            route="general",
            results={
                "financial": AgentResult(
                    response="Financial view",
                    tools_used=["get_financials"],
                )
            },
            errors=["synthesis: Synthesis unavailable"],
        )

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        result = evaluator.evaluate_case(case)

        self.assertFalse(result.evaluation.passed)
        self.assertEqual(result.evaluation.score, 0.0)
        self.assertIn("Workflow failed to produce a synthesis response", result.evaluation.response)

    def test_tool_names_are_collected_deterministically(self):
        case = self._case(case_id="tools-1")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            results={
                "financial": AgentResult(
                    response="Financial view",
                    tools_used=["get_financials", "get_financials"],
                ),
                "synthesis": AgentResult(
                    response="Revenue, profit, and cash flow matter.",
                    tools_used=["llm_synthesis", "rag_lookup", "llm_synthesis"],
                ),
                "market": AgentResult(
                    response="Market view",
                    tools_used=["get_market_data"],
                ),
            }
        )

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        result = evaluator.evaluate_case(case)

        self.assertEqual(
            result.tools_used,
            ["get_financials", "llm_synthesis", "rag_lookup", "get_market_data"],
        )

    def test_aggregate_report_uses_existing_report_generator(self):
        case = self._case(case_id="report-1")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            results={
                "synthesis": AgentResult(
                    response="Revenue, profit, and cash flow matter.",
                    tools_used=["llm_synthesis"],
                )
            }
        )

        expected = EvaluationReport(
            total_cases=1,
            passed_cases=1,
            failed_cases=0,
            average_score=1.0,
            results=[
                EvaluationResult(
                    case_id=case.case_id,
                    category=case.category,
                    question=case.question,
                    response="Revenue, profit, and cash flow matter.",
                    passed=True,
                    score=1.0,
                    missing_concepts=[],
                )
            ],
        )
        report_generator = MagicMock()
        report_generator.generate.return_value = expected

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
            report_generator=report_generator,
        )

        report = evaluator.evaluate([case])

        self.assertIs(report, expected)
        report_generator.generate.assert_called_once()

    def test_repeated_evaluation_is_deterministic(self):
        case = self._case(case_id="repeat-1")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            results={
                "synthesis": AgentResult(
                    response="Revenue, profit, and cash flow matter.",
                    tools_used=["llm_synthesis"],
                )
            }
        )

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        first = evaluator.evaluate_case(case)
        second = evaluator.evaluate_case(case)

        self.assertEqual(first.evaluation, second.evaluation)
        self.assertEqual(first.tools_used, second.tools_used)

    def test_no_external_api_or_llm_calls(self):
        case = self._case(case_id="external-1")
        workflow = MagicMock()
        workflow.run.return_value = self._workflow_state(
            results={
                "synthesis": AgentResult(
                    response="Revenue, profit, and cash flow matter.",
                    tools_used=["llm_synthesis"],
                )
            }
        )

        model = MagicMock(return_value="revenue profit cash flow")
        evaluator = MultiAgentWorkflowEvaluator(workflow=workflow, evaluator=model)

        evaluator.evaluate_case(case)

        self.assertEqual(model.call_count, 1)
        self.assertIn("Revenue, profit, and cash flow matter.", model.call_args.args[0][0]["content"])

    def test_runtime_error_is_not_swallowed(self):
        case = self._case(case_id="runtime-1")
        workflow = MagicMock()
        workflow.run.side_effect = RuntimeError("unexpected bug")

        evaluator = MultiAgentWorkflowEvaluator(
            workflow=workflow,
            evaluator=lambda messages: "revenue profit cash flow",
        )

        with self.assertRaises(RuntimeError):
            evaluator.evaluate_case(case)

    def test_extract_synthesis_result_runtime_error_is_not_swallowed(self):
        with patch(
            "apps.ai.evaluation.workflow_evaluator.AgentResult.model_validate",
            side_effect=RuntimeError("unexpected helper bug"),
        ):
            with self.assertRaises(RuntimeError):
                MultiAgentWorkflowEvaluator._extract_synthesis_result({"synthesis": {"response": "x"}})

    def test_collect_tools_runtime_error_is_not_swallowed(self):
        with patch(
            "apps.ai.evaluation.workflow_evaluator.AgentResult.model_validate",
            side_effect=RuntimeError("unexpected helper bug"),
        ):
            with self.assertRaises(RuntimeError):
                MultiAgentWorkflowEvaluator._collect_tools({"branch": {"response": "x"}})
