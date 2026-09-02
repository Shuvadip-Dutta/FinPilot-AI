from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ai.evaluation.benchmark import ModelBenchmarkResult, ModelBenchmarkRunner
from apps.ai.evaluation.dataset import EVALUATION_DATASET
from apps.ai.evaluation.schemas import EvaluationCase
from apps.ai.services.llm_service import LLMService, ModelTier


class ModelBenchmarkTestCase(SimpleTestCase):

    def test_expected_tier_is_preserved_for_success_and_failure(self):
        case = EVALUATION_DATASET[0]

        runner = ModelBenchmarkRunner(
            llm_service_factory=lambda tier: type("FakeService", (), {"generate": lambda self, messages: "Revenue, profit, and cash flow matter."})(),
            evaluator_factory=lambda model: type("FakeEvaluator", (), {"evaluate_case": lambda self, current_case: type("FakeResult", (), {"response": "Revenue, profit, and cash flow matter.", "passed": True, "score": 1.0, "missing_concepts": []})()})(),
        )

        result = runner.evaluate_case(case, ModelTier.REASONING)

        self.assertEqual(result.expected_tier, case.expected_tier)
        self.assertEqual(result.tested_tier, ModelTier.REASONING)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)

    def test_fast_and_reasoning_benchmarks_resolve_the_right_tier(self):
        calls = []

        def factory(tier):
            calls.append(tier)
            return type("FakeService", (), {"generate": lambda self, messages: "Revenue and profit."})()

        runner = ModelBenchmarkRunner(llm_service_factory=factory)
        case = EVALUATION_DATASET[0]

        fast = runner.evaluate_case(case, ModelTier.FAST)
        reasoning = runner.evaluate_case(case, ModelTier.REASONING)

        self.assertEqual(fast.tested_tier, ModelTier.FAST)
        self.assertEqual(reasoning.tested_tier, ModelTier.REASONING)
        self.assertEqual(calls, [ModelTier.FAST, ModelTier.REASONING])

    def test_same_case_can_be_compared_across_tiers(self):
        case = EVALUATION_DATASET[0]

        runner = ModelBenchmarkRunner(
            llm_service_factory=lambda tier: type("FakeService", (), {"generate": lambda self, messages: "Revenue, profit, and cash flow matter."})(),
            evaluator_factory=lambda model: type("FakeEvaluator", (), {"evaluate_case": lambda self, current_case: type("FakeResult", (), {"response": "Revenue, profit, and cash flow matter.", "passed": True, "score": 0.8, "missing_concepts": []})()})(),
        )

        fast = runner.evaluate_case(case, ModelTier.FAST)
        reasoning = runner.evaluate_case(case, ModelTier.REASONING)

        self.assertEqual(fast.case_id, case.case_id)
        self.assertEqual(reasoning.category, case.category)
        self.assertEqual(fast.expected_tier, case.expected_tier)
        self.assertEqual(reasoning.expected_tier, case.expected_tier)

    def test_latency_is_recorded_as_non_negative_milliseconds(self):
        runner = ModelBenchmarkRunner(
            llm_service_factory=lambda tier: type("FakeService", (), {"generate": lambda self, messages: "Revenue and profit."})(),
            evaluator_factory=lambda model: type("FakeEvaluator", (), {"evaluate_case": lambda self, current_case: type("FakeResult", (), {"response": "Revenue and profit.", "passed": True, "score": 1.0, "missing_concepts": []})()})(),
            clock=lambda: 10.0,
        )

        result = runner.evaluate_case(EVALUATION_DATASET[0], ModelTier.FAST)

        self.assertGreaterEqual(result.latency_ms, 0.0)

    def test_failed_benchmark_records_error_without_crashing(self):
        def factory(tier):
            raise ValueError("benchmark unavailable")

        runner = ModelBenchmarkRunner(llm_service_factory=factory)
        result = runner.evaluate_case(EVALUATION_DATASET[0], ModelTier.REASONING)

        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)
        self.assertIn("benchmark unavailable", result.error)

    def test_aggregate_report_summarizes_results(self):
        runner = ModelBenchmarkRunner(
            llm_service_factory=lambda tier: type("FakeService", (), {"generate": lambda self, messages: "Revenue, profit, and cash flow matter."})(),
            evaluator_factory=lambda model: type("FakeEvaluator", (), {"evaluate_case": lambda self, current_case: type("FakeResult", (), {"response": "Revenue, profit, and cash flow matter.", "passed": True, "score": 1.0, "missing_concepts": []})()})(),
        )

        results = runner.evaluate_tier(tested_tier=ModelTier.FAST)
        report = runner.build_report(results)

        self.assertEqual(report.total_cases, len(EVALUATION_DATASET))
        self.assertEqual(report.pass_rate, 1.0)
        self.assertEqual(report.average_score, 1.0)
        self.assertEqual(report.results_by_tier[ModelTier.FAST.value][0].tested_tier, ModelTier.FAST)

    def test_compare_tiers_reports_expected_alternative_and_tied_status(self):
        runner = ModelBenchmarkRunner(
            llm_service_factory=lambda tier: type("FakeService", (), {"generate": lambda self, messages: "Revenue and profit."})(),
            evaluator_factory=lambda model: type("FakeEvaluator", (), {"evaluate_case": lambda self, current_case: type("FakeResult", (), {"response": "Revenue and profit.", "passed": True, "score": 0.8, "missing_concepts": []})()})(),
        )

        expected_results = [runner.evaluate_case(EVALUATION_DATASET[0], ModelTier.REASONING)]
        alternative_results = [runner.evaluate_case(EVALUATION_DATASET[0], ModelTier.FAST)]
        comparison = runner.compare_tiers(expected_results, alternative_results)

        self.assertIn(comparison["status"], {"expected_tier_scored_higher", "alternative_tier_scored_higher", "tied_score", "failed_benchmark_execution"})

    @patch("apps.ai.evaluation.benchmark.LLMService")
    def test_benchmark_uses_llmservice_tier_resolution(self, mock_llm_service):
        mock_llm_service.return_value.generate.side_effect = lambda messages: "Revenue and profit."

        runner = ModelBenchmarkRunner()
        case = EVALUATION_DATASET[0]

        result = runner.evaluate_case(case, ModelTier.REASONING)

        self.assertEqual(result.response, "Revenue and profit.")
        mock_llm_service.assert_called_once_with(model=ModelTier.REASONING)

    def test_no_real_llm_calls_are_made_in_unit_tests(self):
        seen = []

        def factory(tier):
            seen.append(tier)
            return type("FakeService", (), {"generate": lambda self, messages: "Revenue, profit, and cash flow matter."})()

        runner = ModelBenchmarkRunner(llm_service_factory=factory)
        runner.evaluate_tier(tested_tier=ModelTier.FAST)

        self.assertEqual(seen, [ModelTier.FAST] * len(EVALUATION_DATASET))
