from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.ai.evaluation.dataset import EVALUATION_DATASET
from apps.ai.evaluation.evaluator import FinanceModelEvaluator
from apps.ai.evaluation.report import EvaluationReportGenerator
from apps.ai.evaluation.schemas import EvaluationCase, EvaluationResult


class FinanceModelEvaluatorTestCase(SimpleTestCase):

    def setUp(self):
        self.case = EvaluationCase(
            case_id="test-finance",
            category="finance",
            question="What should financial analysis cover?",
            reference_answer="Revenue and profit are important.",
            required_concepts=["revenue", "profit"],
        )

    def test_valid_evaluation_case(self):
        self.assertEqual(self.case.category, "finance")

    def test_invalid_category(self):
        with self.assertRaises(ValidationError):
            EvaluationCase(
                case_id="invalid",
                category="invalid",
                question="Question",
                reference_answer="Answer",
                required_concepts=[],
            )

    def test_dataset_is_non_empty_and_has_all_categories(self):
        self.assertTrue(EVALUATION_DATASET)
        self.assertEqual(
            {case.category for case in EVALUATION_DATASET},
            {"finance", "market", "news", "risk", "portfolio"},
        )

    def test_successful_full_score_evaluation(self):
        evaluator = FinanceModelEvaluator(
            model=lambda messages: "Revenue and PROFIT both matter."
        )

        result = evaluator.evaluate_case(self.case)

        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.missing_concepts, [])

    def test_partial_score_and_missing_concepts(self):
        evaluator = FinanceModelEvaluator(
            model=lambda messages: "Revenue matters."
        )

        result = evaluator.evaluate_case(self.case)

        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.5)
        self.assertEqual(result.missing_concepts, ["profit"])

    def test_empty_model_response(self):
        evaluator = FinanceModelEvaluator(model=lambda messages: "  ")

        result = evaluator.evaluate_case(self.case)

        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.missing_concepts, ["revenue", "profit"])

    def test_model_failure(self):
        def failing_model(messages):
            raise ValueError("Model unavailable")

        result = FinanceModelEvaluator(failing_model).evaluate_case(self.case)

        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)
        self.assertIn("Model unavailable", result.response)

    def test_multi_case_evaluation(self):
        evaluator = FinanceModelEvaluator(
            model=lambda messages: "revenue profit cash flow"
        )

        report = evaluator.evaluate(EVALUATION_DATASET[:2])

        self.assertEqual(report.total_cases, 2)
        self.assertEqual(len(report.results), 2)

    def test_report_aggregation(self):
        results = [
            EvaluationResult(
                case_id="one",
                category="finance",
                question="One",
                response="Response",
                passed=True,
                score=1.0,
                missing_concepts=[],
            ),
            EvaluationResult(
                case_id="two",
                category="market",
                question="Two",
                response="Response",
                passed=False,
                score=0.5,
                missing_concepts=["price"],
            ),
        ]

        report = EvaluationReportGenerator().generate(results)

        self.assertEqual(report.total_cases, 2)
        self.assertEqual(report.passed_cases, 1)
        self.assertEqual(report.failed_cases, 1)
        self.assertEqual(report.average_score, 0.75)

    def test_deterministic_repeated_evaluation(self):
        evaluator = FinanceModelEvaluator(
            model=lambda messages: "Revenue and profit."
        )

        self.assertEqual(
            evaluator.evaluate_case(self.case),
            evaluator.evaluate_case(self.case),
        )

    def test_injected_model_prevents_external_api_or_llm_calls(self):
        calls = []

        def model(messages):
            calls.append(messages)
            return "Revenue and profit."

        FinanceModelEvaluator(model).evaluate_case(self.case)

        self.assertEqual(
            calls,
            [[{"role": "user", "content": self.case.question}]],
        )
