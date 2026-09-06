"""Unit tests for PortfolioRiskEngine and PortfolioRiskMetrics."""

import math
from unittest import TestCase

from apps.ai.portfolio.risk import PortfolioRiskEngine, PortfolioRiskError
from apps.ai.portfolio.schemas import PortfolioRiskMetrics


class PortfolioRiskEngineTestCase(TestCase):
    """Test suite for deterministic quantitative portfolio risk calculations."""

    def setUp(self):
        self.engine = PortfolioRiskEngine()

    def test_positive_return_single_asset_portfolio(self):
        """Test single-asset portfolio with constant positive return."""
        prices = {"ASSET1": [100.0, 105.0, 110.25, 115.7625]}
        weights = {"ASSET1": 1.0}

        metrics = self.engine.calculate(prices, weights)

        self.assertIsInstance(metrics, PortfolioRiskMetrics)
        self.assertAlmostEqual(metrics.annualized_return, 12.6, places=4)
        self.assertAlmostEqual(metrics.total_period_return, 0.157625, places=5)
        self.assertAlmostEqual(metrics.volatility, 0.0, places=5)
        self.assertAlmostEqual(metrics.downside_volatility, 0.0, places=5)
        self.assertAlmostEqual(metrics.sharpe_ratio, 0.0, places=5)
        self.assertAlmostEqual(metrics.sortino_ratio, 0.0, places=5)
        self.assertAlmostEqual(metrics.max_drawdown, 0.0, places=5)
        self.assertEqual(metrics.max_drawdown_duration_days, 0)
        self.assertIsNone(metrics.calmar_ratio)

    def test_negative_return_portfolio(self):
        """Test single-asset portfolio with constant negative returns."""
        prices = {"STOCK_A": [100.0, 90.0, 81.0, 72.9]}
        weights = {"STOCK_A": 1.0}

        metrics = self.engine.calculate(prices, weights)

        self.assertLess(metrics.annualized_return, 0)
        self.assertLess(metrics.total_period_return, 0)

    def test_multi_asset_offsetting_portfolio(self):
        """Test multi-asset 50/50 portfolio with offsetting returns."""
        prices = {
            "STOCK_X": [100.0, 105.0, 110.25, 115.7625],
            "STOCK_Y": [100.0, 95.0, 90.25, 85.7375],
        }
        weights = {"STOCK_X": 0.5, "STOCK_Y": 0.5}

        metrics = self.engine.calculate(prices, weights)

        # Asset X daily return +5%, Asset Y daily return -5%
        # 50/50 portfolio daily return = 0.0
        self.assertAlmostEqual(metrics.annualized_return, 0.0, places=5)
        self.assertAlmostEqual(metrics.total_period_return, 0.0, places=5)
        self.assertAlmostEqual(metrics.volatility, 0.0, places=5)
        self.assertAlmostEqual(metrics.max_drawdown, 0.0, places=5)

    def test_drawdown_and_duration_calculation(self):
        """Test hand-constructed drawdown and underwater duration calculation."""
        # Day 0: 100, Day 1: 110 (Peak 110), Day 2: 99 (-10% from peak), Day 3: 88 (-20% from peak), Day 4: 120 (Peak 120)
        prices = {"TEST": [100.0, 110.0, 99.0, 88.0, 120.0]}
        weights = {"TEST": 1.0}

        metrics = self.engine.calculate(prices, weights)

        self.assertAlmostEqual(metrics.max_drawdown, 0.20, places=4)
        self.assertEqual(metrics.max_drawdown_duration_days, 2)
        self.assertIsNotNone(metrics.calmar_ratio)
        self.assertAlmostEqual(metrics.calmar_ratio, metrics.annualized_return / 0.20, places=4)

    def test_zero_volatility_flat_prices(self):
        """Test flat price series with zero volatility."""
        prices = {"FLAT": [50.0, 50.0, 50.0, 50.0]}
        weights = {"FLAT": 1.0}

        metrics = self.engine.calculate(prices, weights)

        self.assertEqual(metrics.volatility, 0.0)
        self.assertEqual(metrics.downside_volatility, 0.0)
        self.assertEqual(metrics.sharpe_ratio, 0.0)
        self.assertEqual(metrics.sortino_ratio, 0.0)
        self.assertEqual(metrics.max_drawdown, 0.0)
        self.assertEqual(metrics.max_drawdown_duration_days, 0)
        self.assertIsNone(metrics.calmar_ratio)

    def test_sortino_and_sharpe_with_downside(self):
        """Test Sharpe and Sortino ratios on volatile price series."""
        prices = {"VOL": [100.0, 105.0, 98.0, 108.0, 102.0, 112.0]}
        weights = {"VOL": 1.0}

        metrics = self.engine.calculate(prices, weights, risk_free_rate=0.01)

        self.assertGreater(metrics.volatility, 0)
        self.assertGreater(metrics.downside_volatility, 0)
        self.assertNotEqual(metrics.sharpe_ratio, 0)
        self.assertNotEqual(metrics.sortino_ratio, 0)

    def test_historical_var_cvar_95_sign_convention(self):
        """Test historical VaR 95 and CVaR 95 sign convention (positive = loss magnitude)."""
        # Create 20 price points yielding 20 daily returns from -10% to +14%
        base_price = 100.0
        daily_returns = [
            -0.10, -0.08, -0.06, -0.04, -0.02, 0.0, 0.01, 0.02, 0.03, 0.04,
            0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14
        ]
        prices_list = [base_price]
        curr = base_price
        for r in daily_returns:
            curr = curr * (1.0 + r)
            prices_list.append(curr)

        prices = {"TICK": prices_list}
        weights = {"TICK": 1.0}

        metrics = self.engine.calculate(prices, weights)

        # 5th percentile index = 0.05 * 19 = 0.95 => cutoff = -0.10 + 0.95 * 0.02 = -0.081
        # VaR95 = -(-0.081) = +0.081 (positive loss magnitude)
        # CVaR95 = tail returns <= -0.081 is [-0.10], mean = -0.10 => CVaR95 = +0.10
        self.assertGreater(metrics.var_95_historical, 0.0)
        self.assertGreater(metrics.cvar_95_historical, 0.0)
        self.assertAlmostEqual(metrics.var_95_historical, 0.081, places=4)
        self.assertAlmostEqual(metrics.cvar_95_historical, 0.10, places=4)
        self.assertGreaterEqual(metrics.cvar_95_historical, metrics.var_95_historical)

    def test_risk_free_rate_effect(self):
        """Test that higher risk-free rate reduces Sharpe and Sortino ratios."""
        prices = {"A": [100.0, 102.0, 101.0, 104.0, 103.0, 106.0]}
        weights = {"A": 1.0}

        metrics_rf0 = self.engine.calculate(prices, weights, risk_free_rate=0.0)
        metrics_rf5 = self.engine.calculate(prices, weights, risk_free_rate=0.05)

        self.assertGreater(metrics_rf0.sharpe_ratio, metrics_rf5.sharpe_ratio)
        self.assertGreater(metrics_rf0.sortino_ratio, metrics_rf5.sortino_ratio)

    def test_invalid_inputs_raise_portfolio_risk_error(self):
        """Test that invalid inputs raise PortfolioRiskError."""
        # 1. Invalid prices (less than 3 observations)
        with self.assertRaises(PortfolioRiskError):
            self.engine.calculate({"A": [100.0, 105.0]}, {"A": 1.0})

        # 2. Non-positive price
        with self.assertRaises(PortfolioRiskError):
            self.engine.calculate({"A": [100.0, -50.0, 100.0]}, {"A": 1.0})

        # 3. Missing ticker weight
        with self.assertRaises(PortfolioRiskError):
            self.engine.calculate({"A": [100.0, 105.0, 110.0]}, {})

        # 4. Extra ticker weight
        with self.assertRaises(PortfolioRiskError):
            self.engine.calculate({"A": [100.0, 105.0, 110.0]}, {"A": 0.5, "B": 0.5})

        # 5. Weights not summing to 1
        with self.assertRaises(PortfolioRiskError):
            self.engine.calculate({"A": [100.0, 105.0, 110.0]}, {"A": 0.5})

        # 6. Infinite price
        with self.assertRaises(PortfolioRiskError):
            self.engine.calculate({"A": [100.0, float("inf"), 110.0]}, {"A": 1.0})

        # 7. Infinite weight
        with self.assertRaises(PortfolioRiskError):
            self.engine.calculate({"A": [100.0, 105.0, 110.0]}, {"A": float("nan")})

        # 8. Infinite risk free rate
        with self.assertRaises(PortfolioRiskError):
            self.engine.calculate({"A": [100.0, 105.0, 110.0]}, {"A": 1.0}, risk_free_rate=float("inf"))
