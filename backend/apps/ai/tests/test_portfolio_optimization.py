from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.ai.portfolio.optimization import (
    OptimizationInput,
    PortfolioOptimizationEngine,
    PortfolioOptimizationError,
    TRADING_PERIODS_PER_YEAR,
)


class PortfolioOptimizationTestCase(SimpleTestCase):

    def setUp(self):
        self.engine = PortfolioOptimizationEngine()

    def test_valid_optimization_with_two_assets(self):
        result = self.engine.optimize(self._two_asset_input())

        self.assertTrue(result.success)
        self.assertEqual(set(result.optimized_weights), {"AAA", "BBB"})

    def test_valid_optimization_with_multiple_assets(self):
        input = OptimizationInput(
            tickers=["AAA", "BBB", "CCC"],
            historical_prices={
                "AAA": [100, 102, 101, 105, 107, 110, 108],
                "BBB": [100, 101, 103, 102, 105, 106, 108],
                "CCC": [100, 99, 101, 102, 104, 103, 106],
            },
        )

        result = self.engine.optimize(input)

        self.assertTrue(result.success)
        self.assertEqual(len(result.optimized_weights), 3)

    def test_return_calculation(self):
        returns = self.engine.calculate_returns(self._two_asset_input())

        self.assertAlmostEqual(returns["AAA"][0], 0.02)
        self.assertAlmostEqual(returns["BBB"][1], 0.0198019802)

    def test_annualized_expected_return(self):
        returns = {"AAA": [0.01, 0.03], "BBB": [0.02, 0.04]}

        expected_returns = self.engine.calculate_annualized_expected_returns(returns)

        self.assertAlmostEqual(
            expected_returns[0],
            0.02 * TRADING_PERIODS_PER_YEAR,
        )

    def test_annualized_covariance_calculation(self):
        covariance = self.engine.calculate_annualized_covariance(
            {"AAA": [0.01, 0.03], "BBB": [0.02, 0.04]}
        )

        self.assertAlmostEqual(covariance[0][0], 0.0002 * TRADING_PERIODS_PER_YEAR)
        self.assertAlmostEqual(covariance[0][1], 0.0002 * TRADING_PERIODS_PER_YEAR)

    def test_weights_respect_sum_and_bounds(self):
        input_data = self._two_asset_input().model_dump()
        input_data.update(min_weight=0.2, max_weight=0.8)
        result = self.engine.optimize(
            OptimizationInput(**input_data)
        )

        self.assertTrue(result.success)
        self.assertAlmostEqual(result.total_weight, 1.0, places=8)
        for weight in result.optimized_weights.values():
            self.assertGreaterEqual(weight, 0.2 - 1e-8)
            self.assertLessEqual(weight, 0.8 + 1e-8)

    def test_expected_return_volatility_and_sharpe_calculation(self):
        expected_return, volatility, sharpe = self.engine.calculate_portfolio_metrics(
            weights=[0.5, 0.5],
            expected_returns=[0.12, 0.08],
            covariance=[[0.04, 0.0], [0.0, 0.01]],
            risk_free_rate=0.02,
        )

        self.assertAlmostEqual(expected_return, 0.10)
        self.assertAlmostEqual(volatility, math_sqrt(0.0125))
        self.assertAlmostEqual(sharpe, 0.08 / math_sqrt(0.0125))

    def test_insufficient_asset_count(self):
        with self.assertRaises(ValidationError):
            OptimizationInput(
                tickers=["AAA"],
                historical_prices={"AAA": [100, 101, 102]},
            )

    def test_invalid_or_negative_prices(self):
        with self.assertRaises(ValidationError):
            OptimizationInput(
                tickers=["AAA", "BBB"],
                historical_prices={"AAA": [100, -1, 102], "BBB": [100, 101, 102]},
            )

    def test_incompatible_series_lengths(self):
        with self.assertRaises(ValidationError):
            OptimizationInput(
                tickers=["AAA", "BBB"],
                historical_prices={"AAA": [100, 101, 102], "BBB": [100, 101, 102, 103]},
            )

    def test_invalid_risk_free_rate(self):
        input_data = self._two_asset_input().model_dump()
        input_data["risk_free_rate"] = float("nan")

        with self.assertRaises(ValidationError):
            OptimizationInput(**input_data)

    def test_invalid_min_max_constraints(self):
        input_data = self._two_asset_input().model_dump()
        input_data.update(min_weight=0.8, max_weight=0.2)

        with self.assertRaises(ValidationError):
            OptimizationInput(**input_data)

    def test_infeasible_constraints(self):
        input_data = self._two_asset_input().model_dump()
        input_data["min_weight"] = 0.6

        with self.assertRaises(ValidationError):
            OptimizationInput(**input_data)

    def test_deterministic_repeated_result(self):
        first = self.engine.optimize(self._two_asset_input())
        second = self.engine.optimize(self._two_asset_input())

        self.assertEqual(first.success, second.success)
        for ticker, weight in first.optimized_weights.items():
            self.assertAlmostEqual(weight, second.optimized_weights[ticker], places=12)

    def test_optimization_failure_is_controlled(self):
        class FailingEngine(PortfolioOptimizationEngine):
            def _maximize_sharpe(self, **kwargs):
                raise PortfolioOptimizationError("Solver failed")

        result = FailingEngine().optimize(self._two_asset_input())

        self.assertFalse(result.success)
        self.assertIsNone(result.optimized_weights)
        self.assertIn("Solver failed", result.message)

    def test_zero_volatility_is_handled_without_division_by_zero(self):
        input = OptimizationInput(
            tickers=["AAA", "BBB"],
            historical_prices={
                "AAA": [100, 101, 102.01, 103.0301],
                "BBB": [200, 202, 204.02, 206.0602],
            },
        )

        result = self.engine.optimize(input)

        self.assertFalse(result.success)
        self.assertIn("volatility is too close to zero", result.message)

    def test_no_external_api_or_llm_calls(self):
        result = self.engine.optimize(self._two_asset_input())

        self.assertTrue(result.success)

    @staticmethod
    def _two_asset_input() -> OptimizationInput:
        return OptimizationInput(
            tickers=["AAA", "BBB"],
            historical_prices={
                "AAA": [100, 102, 101, 105, 107, 110, 108],
                "BBB": [100, 101, 103, 102, 105, 106, 108],
            },
            risk_free_rate=0.02,
        )


def math_sqrt(value: float) -> float:
    """Keep expected-value calculations explicit without optimizer dependencies."""
    return value ** 0.5
