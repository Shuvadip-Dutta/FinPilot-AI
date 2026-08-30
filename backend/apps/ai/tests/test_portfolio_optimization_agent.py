from django.test import SimpleTestCase

from apps.ai.agents.portfolio_optimization import (
    PortfolioOptimizationAgent,
)
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
                "AAA": [
                    100,
                    102,
                    101,
                    105,
                    107,
                    110,
                    108,
                ],
                "BBB": [
                    100,
                    101,
                    103,
                    102,
                    105,
                    106,
                    108,
                ],
            },
            risk_free_rate=0.02,
        )

    @staticmethod
    def _success_result() -> OptimizationResult:
        return OptimizationResult(
            optimized_weights={
                "AAA": 0.70,
                "BBB": 0.30,
            },
            expected_return=0.12,
            volatility=0.18,
            sharpe_ratio=0.556,
            total_weight=1.0,
            success=True,
            message="Optimization completed successfully.",
        )

    def test_agent_name(self):
        agent = PortfolioOptimizationAgent()

        self.assertEqual(
            agent.name,
            "portfolio_optimization",
        )

    def test_successful_optimization(self):
        calls = []

        def optimizer(input_data):
            calls.append(input_data)
            return self._success_result()

        agent = PortfolioOptimizationAgent(
            optimizer=optimizer,
        )

        result = agent.run(self._input())

        self.assertIsInstance(
            result,
            AgentResult,
        )

        self.assertIn(
            "Recommended allocation",
            result.response,
        )

        self.assertIn(
            "AAA: 70.00%",
            result.response,
        )

        self.assertIn(
            "BBB: 30.00%",
            result.response,
        )

        self.assertIn(
            "Expected annual return: 12.00%",
            result.response,
        )

        self.assertEqual(
            result.tools_used,
            ["portfolio_optimization"],
        )

        self.assertEqual(
            calls,
            [self._input()],
        )

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

        agent = PortfolioOptimizationAgent(
            optimizer=failing_optimizer,
        )

        result = agent.run(self._input())

        self.assertIn(
            "Portfolio optimization could not be completed",
            result.response,
        )

        self.assertIn(
            "volatility is too close to zero",
            result.response,
        )

        self.assertEqual(
            result.tools_used,
            [],
        )

    def test_optimization_input_error(self):
        def failing_optimizer(input_data):
            raise ValueError(
                "At least two assets are required."
            )

        agent = PortfolioOptimizationAgent(
            optimizer=failing_optimizer,
        )

        result = agent.run(self._input())

        self.assertIn(
            "Unable to optimize the portfolio",
            result.response,
        )

        self.assertIn(
            "At least two assets are required",
            result.response,
        )

        self.assertEqual(
            result.tools_used,
            [],
        )

    def test_no_real_external_dependency(self):
        called = []

        def optimizer(input_data):
            called.append(True)
            return self._success_result()

        agent = PortfolioOptimizationAgent(
            optimizer=optimizer,
        )

        result = agent.run(self._input())

        self.assertTrue(called)
        self.assertIsInstance(result, AgentResult)