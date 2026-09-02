"""Lightweight benchmark execution for comparing configured model tiers on the same cases."""

from __future__ import annotations

import time
from collections.abc import Callable

from pydantic import BaseModel, Field

from apps.ai.evaluation.dataset import EVALUATION_DATASET
from apps.ai.evaluation.evaluator import FinanceModelEvaluator
from apps.ai.evaluation.schemas import EvaluationCase, EvaluationResult
from apps.ai.exceptions import LLMError
from apps.ai.services.llm_service import LLMService, ModelTier


class ModelBenchmarkResult(BaseModel):
    """Observed result for one case evaluated under a selected model tier."""

    case_id: str
    category: str
    expected_tier: ModelTier | None = None
    tested_tier: ModelTier
    score: float
    passed: bool
    response: str
    latency_ms: float
    error: str | None = None


class ModelBenchmarkReport(BaseModel):
    """Aggregate benchmark evidence for a set of tiered runs."""

    total_cases: int
    average_score: float
    pass_rate: float
    average_latency_ms: float
    results_by_tier: dict[str, list[ModelBenchmarkResult]] = Field(default_factory=dict)
    results_by_category: dict[str, list[ModelBenchmarkResult]] = Field(default_factory=dict)


class ModelBenchmarkRunner:
    """Run a deterministic benchmark against the configured LLMService tier abstraction."""

    def __init__(
        self,
        llm_service_factory: Callable[[ModelTier], LLMService] | None = None,
        evaluator_factory: Callable[[Callable[[list[dict[str, str]]], str]], FinanceModelEvaluator] | None = None,
        clock: Callable[[], float] | None = None,
    ):
        self.llm_service_factory = llm_service_factory or (lambda tier: LLMService(model=tier))
        self.evaluator_factory = evaluator_factory or (lambda model: FinanceModelEvaluator(model=model))
        self.clock = clock or time.perf_counter

    def evaluate_case(
        self,
        case: EvaluationCase,
        tested_tier: ModelTier | str,
    ) -> ModelBenchmarkResult:
        tier = self._coerce_tier(tested_tier)
        start = self.clock()

        try:
            service = self.llm_service_factory(tier)
            evaluator = self.evaluator_factory(service.generate)
            result = evaluator.evaluate_case(case)
            response = result.response
            passed = result.passed
            score = result.score
            error = None
        except (LLMError, ValueError, TypeError) as exc:
            response = f"[Benchmark failure: {exc}]"
            passed = False
            score = 0.0
            error = str(exc)

        latency_ms = max(0.0, (self.clock() - start) * 1000)

        return ModelBenchmarkResult(
            case_id=case.case_id,
            category=case.category,
            expected_tier=case.expected_tier,
            tested_tier=tier,
            score=score,
            passed=passed,
            response=response,
            latency_ms=latency_ms,
            error=error,
        )

    def evaluate_tier(
        self,
        cases: list[EvaluationCase] | None = None,
        tested_tier: ModelTier | str = ModelTier.FAST,
    ) -> list[ModelBenchmarkResult]:
        selected_cases = cases or EVALUATION_DATASET
        return [self.evaluate_case(case, tested_tier) for case in selected_cases]

    def build_report(
        self,
        results: list[ModelBenchmarkResult],
    ) -> ModelBenchmarkReport:
        total_cases = len(results)
        average_score = (
            sum(result.score for result in results) / total_cases if total_cases else 0.0
        )
        pass_rate = (
            sum(1 for result in results if result.passed) / total_cases if total_cases else 0.0
        )
        average_latency_ms = (
            sum(result.latency_ms for result in results) / total_cases if total_cases else 0.0
        )

        by_tier: dict[str, list[ModelBenchmarkResult]] = {}
        by_category: dict[str, list[ModelBenchmarkResult]] = {}

        for result in results:
            tier_key = result.tested_tier.value
            by_tier.setdefault(tier_key, []).append(result)
            by_category.setdefault(result.category, []).append(result)

        return ModelBenchmarkReport(
            total_cases=total_cases,
            average_score=average_score,
            pass_rate=pass_rate,
            average_latency_ms=average_latency_ms,
            results_by_tier=by_tier,
            results_by_category=by_category,
        )

    def compare_tiers(
        self,
        expected_results: list[ModelBenchmarkResult],
        alternative_results: list[ModelBenchmarkResult],
    ) -> dict[str, object]:
        expected_mean = (
            sum(result.score for result in expected_results) / len(expected_results)
            if expected_results
            else 0.0
        )
        alternative_mean = (
            sum(result.score for result in alternative_results) / len(alternative_results)
            if alternative_results
            else 0.0
        )

        if not expected_results or not alternative_results:
            return {
                "status": "failed_benchmark_execution",
                "expected_tier": expected_results[0].tested_tier if expected_results else None,
                "alternative_tier": alternative_results[0].tested_tier if alternative_results else None,
                "expected_score": expected_mean,
                "alternative_score": alternative_mean,
            }

        if expected_mean > alternative_mean:
            status = "expected_tier_scored_higher"
        elif alternative_mean > expected_mean:
            status = "alternative_tier_scored_higher"
        elif abs(expected_mean - alternative_mean) < 1e-9:
            status = "tied_score"
        else:
            status = "tied_score"

        return {
            "status": status,
            "expected_tier": expected_results[0].expected_tier,
            "alternative_tier": alternative_results[0].tested_tier,
            "expected_score": expected_mean,
            "alternative_score": alternative_mean,
        }

    @staticmethod
    def _coerce_tier(tier: ModelTier | str) -> ModelTier:
        if isinstance(tier, ModelTier):
            return tier
        return ModelTier(str(tier).strip().lower())


def compare_benchmark_scores(
    expected_results: list[ModelBenchmarkResult],
    alternative_results: list[ModelBenchmarkResult],
) -> dict[str, object]:
    """Informational comparison between two benchmark runs."""
    return ModelBenchmarkRunner().compare_tiers(expected_results, alternative_results)
