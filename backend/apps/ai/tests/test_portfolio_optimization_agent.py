import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.agents.portfolio_optimization import (
    PortfolioOptimizationAgent,
)
from apps.ai.exceptions import LLMError
from apps.ai.portfolio.optimization import (
    OptimizationInput,
    OptimizationResult,
)
from apps.ai.services.schemas import AgentResult


class PortfolioOptimizationAgentTestCase(SimpleTestCase):

    @staticmethod
    def _input() -> OptimizationInput:
        return OptimizationInput(
            tickers=["AAA", "BBB"],
            historical_prices={
                "AAA": [100, 102, 101, 105, 107, 110, 108],
                "BBB": [100, 101, 103, 102, 105, 106, 108],
            },
            risk_free_rate=0.02,
            min_weight=0.1,
            max_weight=0.9,
        )

    @staticmethod
    def _success_result() -> OptimizationResult:
        return OptimizationResult(
            optimized_weights={"AAA": 0.70, "BBB": 0.30},
            expected_return=0.12,
            volatility=0.18,
            sharpe_ratio=0.556,
            total_weight=1.0,
            success=True,
            message="Optimization completed successfully.",
        )

    def test_agent_name(self):
        agent = PortfolioOptimizationAgent()
        self.assertEqual(agent.name, "portfolio_optimization")

    @patch("apps.ai.agents.portfolio_optimization.LLMService")
    def test_successful_optimization_and_explanation(self, mock_llm_service):
        calls = []

        def optimizer(input_data):
            calls.append(input_data)
            return self._success_result()

        mock_llm_service.return_value = MagicMock(return_value="The allocation balances risk and return.")

        agent = PortfolioOptimizationAgent(
            optimizer=optimizer,
        )

        result = agent.run(self._input())

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "The allocation balances risk and return.")
        self.assertEqual(result.tools_used, ["portfolio_optimization"])
        self.assertEqual(calls, [self._input()])
        mock_llm_service.assert_called_once_with(model="portfolio")

        messages = mock_llm_service.return_value.call_args[0][0]
        self.assertEqual(messages[0]["role"], "system")
        context = json.loads(messages[1]["content"])
        self.assertEqual(context["OPTIMIZATION RESULT"]["optimized_weights"], {"AAA": 0.7, "BBB": 0.3})
        self.assertEqual(context["OPTIMIZATION RESULT"]["expected_return"], 0.12)
        self.assertEqual(context["OPTIMIZATION RESULT"]["volatility"], 0.18)
        self.assertEqual(context["OPTIMIZATION RESULT"]["sharpe_ratio"], 0.556)
        self.assertEqual(context["OPTIMIZATION INPUT"]["tickers"], ["AAA", "BBB"])
        self.assertEqual(context["CONSTRAINTS"]["min_weight"], 0.1)
        self.assertEqual(context["CONSTRAINTS"]["max_weight"], 0.9)
        self.assertIn("Numerical values from OPTIMIZATION RESULT are authoritative.", messages[1]["content"])

    @patch("apps.ai.agents.portfolio_optimization.LLMService")
    def test_numerical_source_of_truth_behavior(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="Interpretation only.")

        result = PortfolioOptimizationAgent(
            optimizer=lambda input_data: self._success_result(),
        ).run(self._input())

        self.assertEqual(result.response, "Interpretation only.")
        context = json.loads(mock_llm_service.return_value.call_args[0][0][1]["content"])
        self.assertEqual(context["OPTIMIZATION RESULT"]["optimized_weights"], {"AAA": 0.7, "BBB": 0.3})
        self.assertEqual(context["OPTIMIZATION RESULT"]["expected_return"], 0.12)
        self.assertEqual(context["OPTIMIZATION RESULT"]["volatility"], 0.18)
        self.assertEqual(context["OPTIMIZATION RESULT"]["sharpe_ratio"], 0.556)

    def test_optimization_failure(self):
        def failing_optimizer(input_data):
            return OptimizationResult(
                optimized_weights=None,
                expected_return=None,
                volatility=None,
                sharpe_ratio=None,
                total_weight=None,
                success=False,
                message="Portfolio volatility is too close to zero.",
            )

        agent = PortfolioOptimizationAgent(optimizer=failing_optimizer)
        result = agent.run(self._input())

        self.assertIn("Portfolio optimization could not be completed", result.response)
        self.assertIn("volatility is too close to zero", result.response)
        self.assertEqual(result.tools_used, [])

    @patch("apps.ai.agents.portfolio_optimization.LLMService")
    def test_llm_error_is_not_silently_swallowed(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(side_effect=LLMError("Groq unavailable"))

        agent = PortfolioOptimizationAgent(
            optimizer=lambda input_data: self._success_result(),
        )

        with self.assertRaises(LLMError):
            agent.run(self._input())

    @patch("apps.ai.agents.portfolio_optimization.LLMService")
    def test_min_and_max_weight_are_supplied_for_constraint_interpretation(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="The bounds shape the final mix.")

        agent = PortfolioOptimizationAgent(
            optimizer=lambda input_data: self._success_result(),
        )
        agent.run(self._input())

        context = json.loads(mock_llm_service.return_value.call_args[0][0][1]["content"])
        self.assertEqual(context["CONSTRAINTS"]["min_weight"], 0.1)
        self.assertEqual(context["CONSTRAINTS"]["max_weight"], 0.9)
        self.assertEqual(context["CONSTRAINTS"]["total_weight_target"], 1.0)

    @patch("apps.ai.agents.portfolio_optimization.LLMService")
    def test_multiple_assets_are_all_present_in_llm_context(self, mock_llm_service):
        mock_llm_service.return_value = MagicMock(return_value="The allocation is diversified.")
        input_data = OptimizationInput(
            tickers=["AAA", "BBB", "CCC"],
            historical_prices={
                "AAA": [100, 102, 101, 105, 107, 110, 108],
                "BBB": [100, 101, 103, 104, 106, 108, 109],
                "CCC": [100, 99, 101, 102, 101, 104, 105],
            },
            risk_free_rate=0.02,
            min_weight=0.05,
            max_weight=0.6,
        )
        result = OptimizationResult(
            optimized_weights={"AAA": 0.45, "BBB": 0.35, "CCC": 0.20},
            expected_return=0.14,
            volatility=0.22,
            sharpe_ratio=0.636,
            total_weight=1.0,
            success=True,
            message="Optimization completed successfully.",
        )

        agent = PortfolioOptimizationAgent(optimizer=lambda _: result)
        agent.run(input_data)

        context = json.loads(mock_llm_service.return_value.call_args[0][0][1]["content"])
        self.assertEqual(context["OPTIMIZATION INPUT"]["tickers"], ["AAA", "BBB", "CCC"])
        self.assertEqual(context["OPTIMIZATION RESULT"]["optimized_weights"], {"AAA": 0.45, "BBB": 0.35, "CCC": 0.2})

    def test_result_contract_is_agent_result(self):
        agent = PortfolioOptimizationAgent(
            optimizer=lambda input_data: self._success_result(),
        )

        result = agent.run(self._input())
        self.assertIsInstance(result, AgentResult)

    def test_agent_does_not_recalculate_optimizer_metrics(self):
        optimizer = MagicMock(return_value=self._success_result())
        agent = PortfolioOptimizationAgent(optimizer=optimizer)
        agent.run(self._input())

        optimizer.assert_called_once_with(self._input())

    def test_optimization_input_error(self):
        def failing_optimizer(input_data):
            raise ValueError("At least two assets are required.")

        agent = PortfolioOptimizationAgent(optimizer=failing_optimizer)
        result = agent.run(self._input())

        self.assertIn("Unable to optimize the portfolio", result.response)
        self.assertIn("At least two assets are required", result.response)
        self.assertEqual(result.tools_used, [])

    def test_no_real_external_dependency(self):
        called = []

        def optimizer(input_data):
            called.append(True)
            return self._success_result()

        agent = PortfolioOptimizationAgent(optimizer=optimizer)
        result = agent.run(self._input())

        self.assertTrue(called)
        self.assertIsInstance(result, AgentResult)
