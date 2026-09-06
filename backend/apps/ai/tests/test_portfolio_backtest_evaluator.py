"""Unit tests for PortfolioBacktestEvaluator."""

from django.test import TestCase

from apps.ai.portfolio.backtest import (
    PortfolioBacktestInput,
    PortfolioBacktestResult,
)
from apps.ai.portfolio.backtest_evaluator import PortfolioBacktestEvaluator


class TestPortfolioBacktestEvaluator(TestCase):
    """Test suite verifying deterministic backtest evaluator behavior."""

    def setUp(self):
        self.evaluator = PortfolioBacktestEvaluator()
        self.dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]

        self.historical_prices = {
            "ASSET_A": {
                "2024-01-01": 100.0,
                "2024-01-02": 102.0,
                "2024-01-03": 104.0,
                "2024-01-04": 106.0,
                "2024-01-05": 108.0,
            },
            "ASSET_B": {
                "2024-01-01": 50.0,
                "2024-01-02": 51.0,
                "2024-01-03": 52.0,
                "2024-01-04": 53.0,
                "2024-01-05": 54.0,
            },
        }

        self.equity_curve = [
            {"date": "2024-01-01", "portfolio_value": 1000.0, "daily_return": 0.0},
            {"date": "2024-01-02", "portfolio_value": 1020.0, "daily_return": 0.02},
            {"date": "2024-01-03", "portfolio_value": 1040.0, "daily_return": 0.019607843},
            {"date": "2024-01-04", "portfolio_value": 1060.0, "daily_return": 0.019230769},
            {"date": "2024-01-05", "portfolio_value": 1080.0, "daily_return": 0.018867925},
        ]

        self.backtest_result = PortfolioBacktestResult(
            success=True,
            message="Backtest completed.",
            final_portfolio_value=1080.0,
            total_transaction_costs=15.0,
            equity_curve=self.equity_curve,
            return_series={item["date"]: item["daily_return"] for item in self.equity_curve},
            rebalance_events=[],
        )

    def test_strategy_risk_metrics_calculated(self):
        """Verify strategy risk metrics are calculated correctly from equity curve."""
        input_data = PortfolioBacktestInput(
            tickers=["ASSET_A", "ASSET_B"],
            historical_prices=self.historical_prices,
            initial_capital=1000.0,
            in_sample_window_days=3,
            out_of_sample_step_days=1,
        )

        evaluated = self.evaluator.evaluate(input_data, self.backtest_result)

        self.assertIsNotNone(evaluated.strategy_metrics)
        self.assertAlmostEqual(evaluated.strategy_metrics.total_period_return, 0.08, places=6)
        self.assertGreater(evaluated.strategy_metrics.annualized_return, 0.0)
        self.assertEqual(evaluated.strategy_metrics.max_drawdown, 0.0)

    def test_buy_and_hold_metrics_and_transaction_costs_isolated(self):
        """Verify buy-and-hold baseline calculation does not apply periodic transaction costs."""
        input_data = PortfolioBacktestInput(
            tickers=["ASSET_A", "ASSET_B"],
            historical_prices=self.historical_prices,
            initial_capital=1000.0,
            initial_weights={"ASSET_A": 0.5, "ASSET_B": 0.5},
            in_sample_window_days=3,
            out_of_sample_step_days=1,
        )

        evaluated = self.evaluator.evaluate(input_data, self.backtest_result)

        self.assertIsNotNone(evaluated.buy_and_hold_metrics)
        # 500 / 100 = 5 shares of A; 500 / 50 = 10 shares of B
        # End value = 5*108 + 10*54 = 540 + 540 = 1080.0
        # Total return = (1080 - 1000) / 1000 = 0.08
        self.assertAlmostEqual(evaluated.buy_and_hold_metrics.total_period_return, 0.08, places=6)

    def test_benchmark_absent(self):
        """Verify when no benchmark prices are provided, benchmark and relative metrics are None."""
        input_data = PortfolioBacktestInput(
            tickers=["ASSET_A", "ASSET_B"],
            historical_prices=self.historical_prices,
            initial_capital=1000.0,
            in_sample_window_days=3,
            out_of_sample_step_days=1,
        )

        evaluated = self.evaluator.evaluate(input_data, self.backtest_result)

        self.assertIsNone(evaluated.benchmark_metrics)
        self.assertIsNone(evaluated.relative_metrics)
        self.assertIsNone(evaluated.benchmark_ticker)

    def test_benchmark_calculation_and_relative_metrics(self):
        """Verify benchmark metrics, excess CAGR, total return diff, tracking error, and IR."""
        bmark_prices = {
            "2024-01-01": 100.0,
            "2024-01-02": 101.0,
            "2024-01-03": 102.0,
            "2024-01-04": 103.0,
            "2024-01-05": 104.0,
        }
        input_data = PortfolioBacktestInput(
            tickers=["ASSET_A", "ASSET_B"],
            historical_prices=self.historical_prices,
            initial_capital=1000.0,
            benchmark_ticker="BENCHMARK_INDEX",
            benchmark_prices=bmark_prices,
            in_sample_window_days=3,
            out_of_sample_step_days=1,
        )

        evaluated = self.evaluator.evaluate(input_data, self.backtest_result)

        self.assertEqual(evaluated.benchmark_ticker, "BENCHMARK_INDEX")
        self.assertIsNotNone(evaluated.benchmark_metrics)
        # Benchmark total return = (104 - 100)/100 = 0.04
        self.assertAlmostEqual(evaluated.benchmark_metrics.total_period_return, 0.04, places=6)

        self.assertIsNotNone(evaluated.relative_metrics)
        rel = evaluated.relative_metrics
        # Total return difference = 0.08 - 0.04 = 0.04
        self.assertAlmostEqual(rel.total_return_difference, 0.04, places=6)
        self.assertAlmostEqual(rel.excess_cagr, evaluated.strategy_metrics.cagr - evaluated.benchmark_metrics.cagr, places=6)
        self.assertGreater(rel.tracking_error, 0.0)
        self.assertGreater(rel.information_ratio, 0.0)

    def test_benchmark_date_alignment_no_forward_fill(self):
        """Verify missing benchmark dates are omitted without forward filling."""
        # Benchmark missing 2024-01-03
        bmark_prices = {
            "2024-01-01": 100.0,
            "2024-01-02": 101.0,
            "2024-01-04": 103.0,
            "2024-01-05": 104.0,
        }
        input_data = PortfolioBacktestInput(
            tickers=["ASSET_A", "ASSET_B"],
            historical_prices=self.historical_prices,
            initial_capital=1000.0,
            benchmark_ticker="INDEX_SPARSE",
            benchmark_prices=bmark_prices,
            in_sample_window_days=3,
            out_of_sample_step_days=1,
        )

        evaluated = self.evaluator.evaluate(input_data, self.backtest_result)

        self.assertIsNotNone(evaluated.benchmark_metrics)
        # Benchmark evaluated over 4 common dates -> total period return = (104 - 100)/100 = 0.04
        self.assertAlmostEqual(evaluated.benchmark_metrics.total_period_return, 0.04, places=6)

    def test_zero_tracking_error_case(self):
        """Verify zero tracking error case produces 0.0 information ratio deterministically."""
        # Benchmark matches strategy equity curve normalized to 100.0
        bmark_prices = {
            "2024-01-01": 100.0,
            "2024-01-02": 102.0,
            "2024-01-03": 104.0,
            "2024-01-04": 106.0,
            "2024-01-05": 108.0,
        }
        input_data = PortfolioBacktestInput(
            tickers=["ASSET_A", "ASSET_B"],
            historical_prices=self.historical_prices,
            initial_capital=1000.0,
            benchmark_ticker="IDENTICAL_INDEX",
            benchmark_prices=bmark_prices,
            in_sample_window_days=3,
            out_of_sample_step_days=1,
        )

        evaluated = self.evaluator.evaluate(input_data, self.backtest_result)

        self.assertIsNotNone(evaluated.relative_metrics)
        self.assertAlmostEqual(evaluated.relative_metrics.tracking_error, 0.0, places=6)
        self.assertAlmostEqual(evaluated.relative_metrics.information_ratio, 0.0, places=6)

    def test_deterministic_repeated_execution(self):
        """Verify repeated calls with identical inputs produce identical evaluation outputs."""
        bmark_prices = {
            "2024-01-01": 100.0,
            "2024-01-02": 101.0,
            "2024-01-03": 102.0,
            "2024-01-04": 103.0,
            "2024-01-05": 104.0,
        }
        input_data = PortfolioBacktestInput(
            tickers=["ASSET_A", "ASSET_B"],
            historical_prices=self.historical_prices,
            initial_capital=1000.0,
            benchmark_ticker="BENCH",
            benchmark_prices=bmark_prices,
            in_sample_window_days=3,
            out_of_sample_step_days=1,
        )

        res1 = self.evaluator.evaluate(input_data, self.backtest_result)
        res2 = self.evaluator.evaluate(input_data, self.backtest_result)

        self.assertEqual(res1.model_dump(), res2.model_dump())

    def test_cagr_calculation_convention_and_observation_period(self):
        """Verify CAGR mathematical convention: (1 + R)^(252 / N) - 1 over N trading observations."""
        import math

        # Construct 100 equity curve points (N = 99 trading returns)
        v0 = 100000.0
        v_final = 80522.88
        n_obs = 99

        dates = [f"2025-01-{(i + 1):03d}" for i in range(n_obs + 1)]

        step = (v_final - v0) / n_obs
        eq_curve = [
            {
                "date": dates[i],
                "portfolio_value": v0 + step * i,
                "daily_return": (step / (v0 + step * (i - 1))) if i > 0 else 0.0,
            }
            for i in range(n_obs + 1)
        ]

        result = PortfolioBacktestResult(
            success=True,
            message="Backtest completed.",
            final_portfolio_value=v_final,
            equity_curve=eq_curve,
        )

        hist_prices = {
            "ASSET_A": {d: 100.0 + i for i, d in enumerate(dates)},
            "ASSET_B": {d: 50.0 + i * 0.5 for i, d in enumerate(dates)},
        }

        input_data = PortfolioBacktestInput(
            tickers=["ASSET_A", "ASSET_B"],
            historical_prices=hist_prices,
            initial_capital=v0,
            in_sample_window_days=3,
            out_of_sample_step_days=1,
        )

        evaluated = self.evaluator.evaluate(input_data, result)
        strat_m = evaluated.strategy_metrics

        expected_total_return = (v_final - v0) / v0  # -0.1947712
        years = n_obs / 252.0  # 0.3928571
        expected_cagr = math.pow(1.0 + expected_total_return, 1.0 / years) - 1.0  # -0.42244

        self.assertAlmostEqual(strat_m.total_period_return, expected_total_return, places=6)
        self.assertAlmostEqual(strat_m.cagr, expected_cagr, places=6)
        # Verify formula identity: (1 + R)^(252 / N) - 1
        self.assertAlmostEqual(strat_m.cagr, math.pow(1.0 + strat_m.total_period_return, 252.0 / n_obs) - 1.0, places=6)


