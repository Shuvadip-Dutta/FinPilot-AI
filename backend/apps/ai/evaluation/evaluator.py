import re
from collections.abc import Callable

from apps.ai.evaluation.report import EvaluationReportGenerator
from apps.ai.evaluation.schemas import (
    EvaluationCase,
    EvaluationReport,
    EvaluationResult,
)
from apps.ai.exceptions import LLMError


ModelCallable = Callable[[list[dict[str, str]]], str]

THINK_TAG_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
UNCLOSED_THINK_TAG_PATTERN = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)


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
            raw_response = self.model(self._build_messages(case))
        except (LLMError, ValueError, TypeError) as exc:
            return self._failed_result(
                case=case,
                response=f"[Evaluation model failure: {exc}]",
            )

        if not isinstance(raw_response, str) or not raw_response.strip():
            return self._failed_result(case=case, response="")

        has_think_leakage = "<think>" in raw_response.lower()

        # Remove <think>...</think> content BEFORE concept scoring
        cleaned_response = THINK_TAG_PATTERN.sub("", raw_response)
        cleaned_response = UNCLOSED_THINK_TAG_PATTERN.sub("", cleaned_response).strip()

        normalized_response = self._normalize(cleaned_response)

        missing_concepts: list[str] = []
        for concept in case.required_concepts:
            if isinstance(concept, list):
                primary = concept[0]
                if not any(self._normalize(alias) in normalized_response for alias in concept):
                    missing_concepts.append(primary)
            else:
                if self._normalize(concept) not in normalized_response:
                    missing_concepts.append(concept)

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
            response=raw_response.strip(),
            passed=score == 1.0,
            score=score,
            missing_concepts=missing_concepts,
            expected_tier=case.expected_tier,
            has_think_leakage=has_think_leakage,
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

    @classmethod
    def _failed_result(
        cls,
        case: EvaluationCase,
        response: str,
    ) -> EvaluationResult:
        missing = [
            c[0] if isinstance(c, list) else c
            for c in case.required_concepts
        ]
        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            question=case.question,
            response=response,
            passed=False,
            score=0.0,
            missing_concepts=missing,
            expected_tier=case.expected_tier,
            has_think_leakage="<think>" in response.lower() if isinstance(response, str) else False,
        )
