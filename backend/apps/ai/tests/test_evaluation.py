from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.ai.evaluation.dataset import (
    ARCHITECTURE_TIER_MAP,
    EVALUATION_DATASET,
    validate_category_tier_mapping,
)
from apps.ai.evaluation.evaluator import FinanceModelEvaluator
from apps.ai.evaluation.report import EvaluationReportGenerator
from apps.ai.evaluation.schemas import EvaluationCase, EvaluationResult
from apps.ai.services.llm_service import ModelTier


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
            {"finance", "market", "news", "risk", "portfolio", "synthesis"},
        )

    def test_every_benchmark_case_has_expected_tier_metadata(self):
        self.assertTrue(EVALUATION_DATASET)

        for case in EVALUATION_DATASET:
            self.assertIsNotNone(case.expected_tier)
            self.assertIsInstance(case.expected_tier, ModelTier)
            self.assertEqual(
                case.expected_tier,
                ARCHITECTURE_TIER_MAP[case.category],
            )

    def test_expected_tier_mapping_matches_current_architecture(self):
        self.assertEqual(ARCHITECTURE_TIER_MAP["finance"], ModelTier.REASONING)
        self.assertEqual(ARCHITECTURE_TIER_MAP["market"], ModelTier.FAST)
        self.assertEqual(ARCHITECTURE_TIER_MAP["news"], ModelTier.FAST)
        self.assertEqual(ARCHITECTURE_TIER_MAP["risk"], ModelTier.REASONING)
        self.assertEqual(ARCHITECTURE_TIER_MAP["portfolio"], ModelTier.REASONING)
        self.assertEqual(ARCHITECTURE_TIER_MAP["synthesis"], ModelTier.REASONING)
        self.assertTrue(validate_category_tier_mapping())

    def test_no_real_llm_call_is_required_for_benchmark_unit_tests(self):
        calls = []

        def model(messages):
            calls.append(messages)
            return "TechCorp generated $500M in revenue with net income of $100M and solid cash flow."

        evaluator = FinanceModelEvaluator(model=model)
        result = evaluator.evaluate_case(EVALUATION_DATASET[0])

        self.assertTrue(result.passed)
        self.assertEqual(len(calls), 1)

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

    def test_concept_aliases_matching(self):
        case = EvaluationCase(
            case_id="test-aliases",
            category="finance",
            question="Analyze revenue",
            reference_answer="Revenue was $500 million",
            required_concepts=[["$500m", "$500M", "$500 million"]],
        )
        evaluator = FinanceModelEvaluator(
            model=lambda msgs: "The company reported $500 million in revenue."
        )
        result = evaluator.evaluate_case(case)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.missing_concepts, [])

    def test_numeric_alias_handling(self):
        case = EVALUATION_DATASET[1]  # finance-numerical-reasoning
        evaluator = FinanceModelEvaluator(
            model=lambda msgs: "Alpha Inc has a gross margin of 40 percent, debt-to-equity ratio of 0.5, gross margin, and D/E."
        )
        result = evaluator.evaluate_case(case)
        self.assertTrue(result.passed)

    def test_short_number_false_positive_prevention(self):
        case = EVALUATION_DATASET[1]  # finance-numerical-reasoning
        evaluator = FinanceModelEvaluator(
            model=lambda msgs: "Refer to Section 0.5 of the prospectus for gross margin 40% and debt-to-equity information."
        )
        result = evaluator.evaluate_case(case)
        self.assertFalse(result.passed)
        self.assertIn("0.5 debt-to-equity", result.missing_concepts)

    def test_case_5_numerical_grounding(self):
        case = EVALUATION_DATASET[4]  # finance-overall-conclusion
        evaluator_qualitative_only = FinanceModelEvaluator(
            model=lambda msgs: "Delta Corp displays strong liquidity, solid solvency, and an attractive profit margin."
        )
        result_qual = evaluator_qualitative_only.evaluate_case(case)
        self.assertFalse(result_qual.passed)
        self.assertIn("$1.2 billion", result_qual.missing_concepts)

        evaluator_full = FinanceModelEvaluator(
            model=lambda msgs: "Delta Corp generated $1.2B revenue with $450M cash, strong liquidity, solid solvency, and 15% profit margin."
        )
        result_full = evaluator_full.evaluate_case(case)
        self.assertTrue(result_full.passed)

    def test_think_leakage_detection_and_stripping(self):
        case = EVALUATION_DATASET[0]  # finance-statement-interpretation
        raw_response = (
            "<think>\nLet's calculate $500M revenue...\n</think>\n"
            "TechCorp generated $500M in revenue with net income of $100M and solid cash flow."
        )
        evaluator = FinanceModelEvaluator(model=lambda msgs: raw_response)
        result = evaluator.evaluate_case(case)

        self.assertTrue(result.has_think_leakage)
        self.assertTrue(result.passed)
        self.assertEqual(result.response, raw_response.strip())

        case_strict = EvaluationCase(
            case_id="test-think-isolation",
            category="finance",
            question="Question",
            reference_answer="Answer",
            required_concepts=["secret_concept"],
        )
        think_only_response = "<think>secret_concept is discussed here</think>Public summary without it."
        result_think_only = FinanceModelEvaluator(model=lambda msgs: think_only_response).evaluate_case(case_strict)
        self.assertTrue(result_think_only.has_think_leakage)
        self.assertFalse(result_think_only.passed)

    def test_backward_compatibility(self):
        legacy_case = EvaluationCase(
            case_id="legacy-case",
            category="finance",
            question="Legacy question?",
            reference_answer="Legacy answer",
            required_concepts=["legacy concept one", "legacy concept two"],
        )
        evaluator = FinanceModelEvaluator(
            model=lambda msgs: "This response contains legacy concept one and legacy concept two."
        )
        result = evaluator.evaluate_case(legacy_case)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertFalse(result.has_think_leakage)
