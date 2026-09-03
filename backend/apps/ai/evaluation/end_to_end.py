"""End-to-end workflow evaluation that reuses the established evaluation stack."""

from __future__ import annotations

import time
from collections.abc import Callable

from pydantic import BaseModel, Field

from apps.ai.evaluation.dataset import EVALUATION_DATASET
from apps.ai.evaluation.evaluator import FinanceModelEvaluator
from apps.ai.evaluation.schemas import EvaluationCase, EvaluationResult
from apps.ai.evaluation.workflow_evaluator import MultiAgentWorkflowEvaluator
from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow


class WorkflowEvaluationSummary(BaseModel):
    """Detailed evidence for a workflow-level evaluation result."""

    case_id: str
    category: str
    expected_route: str | None = None
    actual_route: str | None = None
    route_passed: bool = False
    expected_agents: list[str] = Field(default_factory=list)
    actual_agents: list[str] = Field(default_factory=list)
    missing_agents: list[str] = Field(default_factory=list)
    unexpected_agents: list[str] = Field(default_factory=list)
    evaluation_score: float = 0.0
    required_concepts_missing: list[str | list[str]] = Field(default_factory=list)
    workflow_errors: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    final_response: str = ""
    expected_tier: str | None = None


class EndToEndWorkflowReport(BaseModel):
    """Aggregate workflow evaluation evidence."""

    total_cases: int
    route_accuracy: float = 0.0
    agent_execution_accuracy: float = 0.0
    average_score: float = 0.0
    final_response_pass_rate: float = 0.0
    average_latency_ms: float = 0.0
    failed_workflows: list[str] = Field(default_factory=list)
    results: list[WorkflowEvaluationSummary] = Field(default_factory=list)


class EndToEndWorkflowEvaluator:
    """Run end-to-end workflow evaluations using the same evaluation contracts."""

    def __init__(
        self,
        workflow: LangGraphResearchWorkflow,
        evaluator: FinanceModelEvaluator | Callable[[list[dict[str, str]]], str],
        clock: Callable[[], float] | None = None,
    ):
        self.workflow = workflow
        self.evaluator = evaluator
        self.clock = clock or time.perf_counter

    def evaluate_case(self, case: EvaluationCase) -> WorkflowEvaluationSummary:
        start = self.clock()
        workflow_result = MultiAgentWorkflowEvaluator(
            workflow=self.workflow,
            evaluator=self.evaluator,
        ).evaluate_case(case)
        elapsed_ms = max(0.0, (self.clock() - start) * 1000)

        actual_agents = list(workflow_result.agents_executed)
        expected_agents = list(case.expected_agents)
        missing_agents = [agent for agent in expected_agents if agent not in actual_agents]
        unexpected_agents = [agent for agent in actual_agents if agent not in expected_agents]
        route_passed = workflow_result.route == case.expected_route

        if workflow_result.evaluation is not None:
            evaluation_result = workflow_result.evaluation
        else:
            evaluation_result = EvaluationResult(
                case_id=case.case_id,
                category=case.category,
                question=case.question,
                response="",
                passed=False,
                score=0.0,
                missing_concepts=case.required_concepts,
                expected_tier=case.expected_tier,
            )

        return WorkflowEvaluationSummary(
            case_id=case.case_id,
            category=case.category,
            expected_route=case.expected_route,
            actual_route=workflow_result.route,
            route_passed=route_passed,
            expected_agents=expected_agents,
            actual_agents=actual_agents,
            missing_agents=missing_agents,
            unexpected_agents=unexpected_agents,
            evaluation_score=evaluation_result.score,
            required_concepts_missing=evaluation_result.missing_concepts,
            workflow_errors=workflow_result.errors,
            tools_used=workflow_result.tools_used,
            latency_ms=elapsed_ms,
            final_response=evaluation_result.response,
            expected_tier=(case.expected_tier.value if case.expected_tier else None),
        )

    def evaluate(self, cases: list[EvaluationCase] | None = None) -> EndToEndWorkflowReport:
        selected_cases = cases or EVALUATION_DATASET
        results = [self.evaluate_case(case) for case in selected_cases]

        total_cases = len(results)
        route_accuracy = (
            sum(1 for result in results if result.route_passed) / total_cases if total_cases else 0.0
        )
        agent_execution_accuracy = (
            sum(1 for result in results if not result.missing_agents and not result.unexpected_agents)
            / total_cases if total_cases else 0.0
        )
        average_score = (
            sum(result.evaluation_score for result in results) / total_cases if total_cases else 0.0
        )
        final_response_pass_rate = (
            sum(1 for result in results if result.evaluation_score == 1.0) / total_cases if total_cases else 0.0
        )
        average_latency_ms = (
            sum(result.latency_ms for result in results) / total_cases if total_cases else 0.0
        )
        failed_workflows = [
            result.case_id for result in results if not result.route_passed or result.missing_agents or result.workflow_errors
        ]

        return EndToEndWorkflowReport(
            total_cases=total_cases,
            route_accuracy=route_accuracy,
            agent_execution_accuracy=agent_execution_accuracy,
            average_score=average_score,
            final_response_pass_rate=final_response_pass_rate,
            average_latency_ms=average_latency_ms,
            failed_workflows=failed_workflows,
            results=results,
        )
