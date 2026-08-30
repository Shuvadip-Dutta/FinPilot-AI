"""Provider-agnostic deterministic finance-response evaluation."""

from collections.abc import Callable

from apps.ai.evaluation.report import EvaluationReportGenerator
from apps.ai.evaluation.schemas import (
    EvaluationCase,
    EvaluationReport,
    EvaluationResult,
)


ModelCallable = Callable[[list[dict[str, str]]], str]


class FinanceModelEvaluator:
    """Evaluate model responses by deterministic required-concept matching."""

    def __init__(
        self,
        model: ModelCallable,
        report_generator: EvaluationReportGenerator | None = None,
    ):
        self.model = model
        self.report_generator = report_generator or EvaluationReportGenerator()

    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        """Evaluate one case while containing model-boundary failures."""
        try:
            response = self.model(self._build_messages(case))
        except Exception as exc:
            return self._failed_result(
                case=case,
                response=f"[Evaluation model failure: {exc}]",
            )

        if not isinstance(response, str) or not response.strip():
            return self._failed_result(case=case, response="")

        normalized_response = self._normalize(response)
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
            response=response.strip(),
            passed=score == 1.0,
            score=score,
            missing_concepts=missing_concepts,
        )

    def evaluate(self, cases: list[EvaluationCase]) -> EvaluationReport:
        """Evaluate a dataset and return its deterministic aggregate report."""
        return self.report_generator.generate(
            [self.evaluate_case(case) for case in cases]
        )

    @staticmethod
    def _build_messages(case: EvaluationCase) -> list[dict[str, str]]:
        return [
            {
                "role": "user",
                "content": case.question,
            }
        ]

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _failed_result(
        case: EvaluationCase,
        response: str,
    ) -> EvaluationResult:
        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            question=case.question,
            response=response,
            passed=False,
            score=0.0,
            missing_concepts=case.required_concepts,
        )
