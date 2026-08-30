"""Report aggregation for deterministic evaluation results."""

from apps.ai.evaluation.schemas import EvaluationReport, EvaluationResult


class EvaluationReportGenerator:
    """Aggregate case-level results without model or provider dependencies."""

    def generate(self, results: list[EvaluationResult]) -> EvaluationReport:
        total_cases = len(results)
        passed_cases = sum(result.passed for result in results)

        return EvaluationReport(
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=total_cases - passed_cases,
            average_score=(
                sum(result.score for result in results) / total_cases
                if total_cases
                else 0.0
            ),
            results=results,
        )
