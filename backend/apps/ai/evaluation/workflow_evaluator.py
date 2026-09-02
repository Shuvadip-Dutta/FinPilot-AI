"""End-to-end evaluation of the real multi-agent LangGraph workflow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from apps.ai.evaluation.evaluator import FinanceModelEvaluator
from apps.ai.evaluation.report import EvaluationReportGenerator
from apps.ai.evaluation.schemas import (
    EvaluationCase,
    EvaluationReport,
    EvaluationResult,
)
from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
from apps.ai.services.schemas import AgentResult


class WorkflowEvaluationResult(BaseModel):
    """Workflow-scoped evaluation outcome preserving metadata and workflow errors."""

    evaluation: EvaluationResult
    route: str | None = None
    errors: list[str] = Field(default_factory=list)
    agents_executed: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)


ResponseEvaluator = FinanceModelEvaluator | Callable[[list[dict[str, str]]], str]


class MultiAgentWorkflowEvaluator:
    """Evaluate the final synthesis response produced by the real workflow."""

    def __init__(
        self,
        workflow: LangGraphResearchWorkflow,
        evaluator: ResponseEvaluator,
        report_generator: EvaluationReportGenerator | None = None,
    ):
        self.workflow = workflow
        self.evaluator = evaluator
        self.report_generator = report_generator or EvaluationReportGenerator()

    def evaluate_case(self, case: EvaluationCase) -> WorkflowEvaluationResult:
        """Run the workflow and evaluate the final synthesis artifact."""
        thread_id = f"eval-{case.case_id}"
        state = self.workflow.run(case.question, thread_id=thread_id)
        errors = list(state.errors)
        route = state.route
        agents_executed = list(state.results.keys())
        tools_used = self._collect_tools(state.results)

        synthesis = self._extract_synthesis_result(state.results)
        if synthesis is None:
            return WorkflowEvaluationResult(
                evaluation=EvaluationResult(
                    case_id=case.case_id,
                    category=case.category,
                    question=case.question,
                    response=(
                        "Workflow failed to produce a synthesis response. "
                        f"Errors: {', '.join(errors) if errors else 'No synthesis output available.'}"
                    ),
                    passed=False,
                    score=0.0,
                    missing_concepts=case.required_concepts,
                    expected_tier=case.expected_tier,
                ),
                route=route,
                errors=errors,
                agents_executed=agents_executed,
                tools_used=tools_used,
            )

        response = self._coerce_response(synthesis)
        if not response or not response.strip():
            return WorkflowEvaluationResult(
                evaluation=EvaluationResult(
                    case_id=case.case_id,
                    category=case.category,
                    question=case.question,
                    response="Workflow failed to produce a non-empty synthesis response.",
                    passed=False,
                    score=0.0,
                    missing_concepts=case.required_concepts,
                    expected_tier=case.expected_tier,
                ),
                route=route,
                errors=errors,
                agents_executed=agents_executed,
                tools_used=tools_used,
            )

        evaluation = self._evaluate_response(case, response)
        evaluation.question = case.question
        evaluation.expected_tier = case.expected_tier
        return WorkflowEvaluationResult(
            evaluation=evaluation,
            route=route,
            errors=errors,
            agents_executed=agents_executed,
            tools_used=tools_used,
        )

    def evaluate(self, cases: list[EvaluationCase]) -> EvaluationReport:
        """Evaluate a batch and aggregate using the existing report generator."""
        return self.report_generator.generate(
            [result.evaluation for result in (self.evaluate_case(case) for case in cases)]
        )

    @staticmethod
    def _extract_synthesis_result(results: dict[str, Any]) -> AgentResult | None:
        synthesis = results.get("synthesis")
        if synthesis is None:
            return None
        if isinstance(synthesis, AgentResult):
            return synthesis
        if isinstance(synthesis, dict):
            try:
                return AgentResult.model_validate(synthesis)
            except ValidationError:
                return None
        return None

    @staticmethod
    def _coerce_response(value: AgentResult) -> str:
        if hasattr(value, "response"):
            response = value.response
            if isinstance(response, str):
                return response.strip()
        return ""

    def _evaluate_response(
        self,
        case: EvaluationCase,
        response: str,
    ) -> EvaluationResult:
        if isinstance(self.evaluator, FinanceModelEvaluator):
            candidate_case = case.model_copy(update={"question": response})
            result = self.evaluator.evaluate_case(candidate_case)
            result.case_id = case.case_id
            result.category = case.category
            result.question = case.question
            result.response = response
            return result

        model_response = self.evaluator([{"role": "user", "content": response}])
        if not isinstance(model_response, str) or not model_response.strip():
            return EvaluationResult(
                case_id=case.case_id,
                category=case.category,
                question=case.question,
                response=response,
                passed=False,
                score=0.0,
                missing_concepts=case.required_concepts,
                expected_tier=case.expected_tier,
            )

        normalized_response = self._normalize(model_response)
        missing_concepts = [
            concept
            for concept in case.required_concepts
            if self._normalize(concept) not in normalized_response
        ]
        total_concepts = len(case.required_concepts)
        score = (
            (total_concepts - len(missing_concepts)) / total_concepts
            if total_concepts
            else 1.0
        )

        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            question=case.question,
            response=response,
            passed=score == 1.0,
            score=score,
            missing_concepts=missing_concepts,
            expected_tier=case.expected_tier,
        )

    @staticmethod
    def _collect_tools(results: dict[str, Any]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in results.values():
            result = None
            if isinstance(value, AgentResult):
                result = value
            elif isinstance(value, dict):
                try:
                    result = AgentResult.model_validate(value)
                except ValidationError:
                    result = None
            if result is None:
                continue
            for tool_name in result.tools_used:
                if tool_name not in seen:
                    seen.add(tool_name)
                    ordered.append(tool_name)
        return ordered

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())
