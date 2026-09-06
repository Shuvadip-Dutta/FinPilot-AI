"""Unit tests for deterministic walk-forward portfolio backtesting engine."""

from unittest.mock import MagicMock
from django.test import TestCase

from apps.ai.portfolio.backtest import (
    PortfolioBacktestEngine,
    PortfolioBacktestInput,
    RebalanceEvent,
)
from apps.ai.portfolio.optimization import OptimizationResult


class PortfolioBacktestEngineTestCase(TestCase):
    """Test suite for PortfolioBacktestEngine."""

    def setUp(self):
        self.tickers = ["RELIANCE", "TCS"]
        # Synthetic dataset with variable prices (non-zero variance)
        self.historical_prices = {
            "RELIANCE": {
                "2025-01-01": 100.0,
                "2025-01-02": 105.0,
                "2025-01-03": 101.0,
                "2025-01-04": 107.0,
                "2025-01-05": 103.0,
                "2025-01-06": 109.0,
            },
            "TCS": {
                "2025-01-01": 200.0,
                "2025-01-02": 202.0,
                "2025-01-03": 208.0,
                "2025-01-04": 204.0,
                "2025-01-05": 210.0,
                "2025-01-06": 206.0,
            },
        }

    def test_basic_successful_backtest(self):
        input_data = PortfolioBacktestInput(
            tickers=self.tickers,
            historical_prices=self.historical_prices,
            initial_capital=100000.0,
            in_sample_window_days=3,
            out_of_sample_step_days=2,
            transaction_cost_bps=10.0,
        )

        engine = PortfolioBacktestEngine()
        result = engine.run(input_data)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Backtest completed successfully.")
        self.assertIsNotNone(result.equity_curve)
        self.assertIsNotNone(result.rebalance_events)
        self.assertGreater(result.final_portfolio_value, 0.0)
        self.assertGreaterEqual(result.total_transaction_costs, 0.0)

    def test_correct_chronological_ordering_and_no_look_ahead_bias(self):
        mock_optimizer = MagicMock()
        mock_optimizer.optimize.return_value = OptimizationResult(
            success=True,
            status="optimal",
            objective_value=1.0,
            optimized_weights={"RELIANCE": 0.6, "TCS": 0.4},
            message="Optimal",
        )

        engine = PortfolioBacktestEngine(optimizer_engine=mock_optimizer)
        input_data = PortfolioBacktestInput(
            tickers=self.tickers,
            historical_prices=self.historical_prices,
            initial_capital=100000.0,
            in_sample_window_days=3,
            out_of_sample_step_days=2,
        )

        result = engine.run(input_data)
        self.assertTrue(result.success)

        # Inspect calls to mock_optimizer.optimize
        calls = mock_optimizer.optimize.call_args_list
        self.assertEqual(len(calls), 2)  # Two rebalances (index 2 and index 4)

        # First call: in-sample dates 2025-01-01 to 2025-01-03
        first_opt_input = calls[0][0][0]
        self.assertEqual(
            len(first_opt_input.historical_prices["RELIANCE"]), 3
        )
        self.assertEqual(
            first_opt_input.historical_prices["RELIANCE"], [100.0, 105.0, 101.0]
        )
        # Ensure 2025-01-04 (107.0) and 2025-01-05 (103.0) were NOT in the first optimizer call
        self.assertNotIn(107.0, first_opt_input.historical_prices["RELIANCE"])
        self.assertNotIn(103.0, first_opt_input.historical_prices["RELIANCE"])

        # Second call: in-sample dates 2025-01-03 to 2025-01-05
        second_opt_input = calls[1][0][0]
        self.assertEqual(
            second_opt_input.historical_prices["RELIANCE"], [101.0, 107.0, 103.0]
        )

    def test_transaction_cost_and_turnover_calculation(self):
        input_data = PortfolioBacktestInput(
            tickers=self.tickers,
            historical_prices=self.historical_prices,
            initial_capital=100000.0,
            in_sample_window_days=3,
            out_of_sample_step_days=2,
            transaction_cost_bps=10.0,  # 0.1% = 0.001
        )

        engine = PortfolioBacktestEngine()
        result = engine.run(input_data)

        self.assertTrue(result.success)
        self.assertEqual(len(result.rebalance_events), 2)

        event1 = result.rebalance_events[0]
        self.assertEqual(event1.date, "2025-01-03")
        self.assertEqual(event1.portfolio_value_before, 100000.0)
        self.assertEqual(event1.turnover, 1.0)
        # 100,000 * 1.0 * 0.0010 = 100.0
        self.assertAlmostEqual(event1.transaction_cost, 100.0)
        self.assertAlmostEqual(event1.portfolio_value_after, 99900.0)

    def test_insufficient_history(self):
        input_data = PortfolioBacktestInput(
            tickers=self.tickers,
            historical_prices=self.historical_prices,
            in_sample_window_days=10,  # History has only 5 dates
            out_of_sample_step_days=2,
        )

        engine = PortfolioBacktestEngine()
        result = engine.run(input_data)

        self.assertFalse(result.success)
        self.assertIn("Insufficient historical observations", result.message)

    def test_optimizer_failure_handled_gracefully(self):
        mock_optimizer = MagicMock()
        mock_optimizer.optimize.return_value = OptimizationResult(
            success=False,
            status="infeasible",
            message="Optimization problem infeasible",
        )

        engine = PortfolioBacktestEngine(optimizer_engine=mock_optimizer)
        input_data = PortfolioBacktestInput(
            tickers=self.tickers,
            historical_prices=self.historical_prices,
            in_sample_window_days=3,
            out_of_sample_step_days=2,
        )

        result = engine.run(input_data)
        self.assertFalse(result.success)
        self.assertIn("Optimizer returned failure", result.message)

    def test_invalid_prices_rejected_by_input_validation(self):
        invalid_prices = {
            "RELIANCE": {
                "2025-01-01": 100.0,
                "2025-01-02": -50.0,  # Negative price
            },
            "TCS": {
                "2025-01-01": 200.0,
                "2025-01-02": 202.0,
            },
        }
        with self.assertRaises(ValueError) as ctx:
            PortfolioBacktestInput(
                tickers=self.tickers,
                historical_prices=invalid_prices,
            )
        self.assertIn("must be positive and finite", str(ctx.exception))

    def test_missing_dates_after_alignment(self):
        # Dates do not align between RELIANCE and TCS
        unaligned_prices = {
            "RELIANCE": {"2025-01-01": 100.0, "2025-01-02": 102.0},
            "TCS": {"2025-01-03": 200.0, "2025-01-04": 202.0},
        }
        input_data = PortfolioBacktestInput(
            tickers=self.tickers,
            historical_prices=unaligned_prices,
            in_sample_window_days=3,
        )
        engine = PortfolioBacktestEngine()
        result = engine.run(input_data)
        self.assertFalse(result.success)
        self.assertIn("Insufficient historical observations", result.message)

    def test_deterministic_repeated_execution(self):
        input_data = PortfolioBacktestInput(
            tickers=self.tickers,
            historical_prices=self.historical_prices,
            initial_capital=100000.0,
            in_sample_window_days=3,
            out_of_sample_step_days=2,
        )

        engine = PortfolioBacktestEngine()
        res1 = engine.run(input_data)
        res2 = engine.run(input_data)

        self.assertEqual(res1.final_portfolio_value, res2.final_portfolio_value)
        self.assertEqual(res1.total_transaction_costs, res2.total_transaction_costs)
        self.assertEqual(res1.equity_curve, res2.equity_curve)

    def test_equity_curve_continuity(self):
        input_data = PortfolioBacktestInput(
            tickers=self.tickers,
            historical_prices=self.historical_prices,
            initial_capital=100000.0,
            in_sample_window_days=3,
            out_of_sample_step_days=2,
        )

        engine = PortfolioBacktestEngine()
        result = engine.run(input_data)

        self.assertTrue(result.success)
        dates = [item["date"] for item in result.equity_curve]
        self.assertEqual(dates, ["2025-01-03", "2025-01-04", "2025-01-05", "2025-01-06"])
        # Check initial date portfolio value equals after-cost value (99900.0)
        self.assertAlmostEqual(result.equity_curve[0]["portfolio_value"], 99900.0)
