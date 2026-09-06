"""Deterministic evaluator service for portfolio backtest results."""

import math
from statistics import fmean

from apps.ai.portfolio.backtest import (
    PortfolioBacktestInput,
    PortfolioBacktestResult,
    RelativeMetrics,
)
from apps.ai.portfolio.risk import PortfolioRiskEngine
from apps.ai.portfolio.schemas import PortfolioRiskMetrics


class PortfolioBacktestEvaluator:
    """Deterministic evaluator for portfolio backtest results.

    Responsibilities:
    1. Strategy risk metrics via PortfolioRiskEngine
    2. Static Buy-and-Hold baseline risk metrics
    3. Benchmark risk metrics (when benchmark_prices provided)
    4. Relative performance metrics (excess CAGR, return diff, tracking error, IR)
    """

    def __init__(self, risk_engine: PortfolioRiskEngine | None = None):
        self.risk_engine = risk_engine or PortfolioRiskEngine()

    def evaluate(
        self,
        input_data: PortfolioBacktestInput,
        backtest_result: PortfolioBacktestResult,
    ) -> PortfolioBacktestResult:
        """Evaluate backtest results and return an updated PortfolioBacktestResult."""
        if not backtest_result.success or not backtest_result.equity_curve or len(backtest_result.equity_curve) < 3:
            return backtest_result

        oos_dates = [item["date"] for item in backtest_result.equity_curve]
        strat_values = [float(item["portfolio_value"]) for item in backtest_result.equity_curve]

        # 1. Strategy Risk Metrics
        strategy_metrics = self.risk_engine.calculate(
            historical_prices={"STRATEGY": strat_values},
            weights={"STRATEGY": 1.0},
            risk_free_rate=input_data.risk_free_rate,
        )

        # 2. Static Buy-and-Hold Baseline Metrics
        buy_and_hold_metrics = self._calculate_buy_and_hold_metrics(
            input_data=input_data,
            oos_dates=oos_dates,
        )

        # 3. Benchmark & Relative Metrics
        benchmark_metrics = None
        benchmark_ticker = input_data.benchmark_ticker
        relative_metrics = None

        if input_data.benchmark_prices:
            common_dates = [d for d in oos_dates if d in input_data.benchmark_prices]
            if len(common_dates) >= 3:
                bmark_prices = [float(input_data.benchmark_prices[d]) for d in common_dates]
                benchmark_metrics = self.risk_engine.calculate(
                    historical_prices={"BENCHMARK": bmark_prices},
                    weights={"BENCHMARK": 1.0},
                    risk_free_rate=input_data.risk_free_rate,
                )

                # Compute aligned daily returns on common dates for tracking error & IR
                strat_prices_map = {item["date"]: float(item["portfolio_value"]) for item in backtest_result.equity_curve}
                bmark_prices_map = input_data.benchmark_prices

                strat_common_returns = []
                bmark_common_returns = []

                for idx in range(1, len(common_dates)):
                    d_prev = common_dates[idx - 1]
                    d_curr = common_dates[idx]

                    r_strat = (strat_prices_map[d_curr] / strat_prices_map[d_prev]) - 1.0
                    r_bmark = (float(bmark_prices_map[d_curr]) / float(bmark_prices_map[d_prev])) - 1.0

                    strat_common_returns.append(r_strat)
                    bmark_common_returns.append(r_bmark)

                relative_metrics = self._calculate_relative_metrics(
                    strategy_metrics=strategy_metrics,
                    benchmark_metrics=benchmark_metrics,
                    strat_returns=strat_common_returns,
                    bmark_returns=bmark_common_returns,
                )

        updated_result = backtest_result.model_copy(deep=True)
        updated_result.strategy_metrics = strategy_metrics
        updated_result.buy_and_hold_metrics = buy_and_hold_metrics
        updated_result.benchmark_metrics = benchmark_metrics
        updated_result.benchmark_ticker = benchmark_ticker
        updated_result.relative_metrics = relative_metrics

        return updated_result

    def _calculate_buy_and_hold_metrics(
        self,
        input_data: PortfolioBacktestInput,
        oos_dates: list[str],
    ) -> PortfolioRiskMetrics:
        """Construct static buy-and-hold equity path and calculate risk metrics."""
        tickers = sorted(input_data.tickers)
        t0_date = oos_dates[0]

        # Determine initial static weights
        if input_data.initial_weights:
            w0 = {t.upper(): float(w) for t, w in input_data.initial_weights.items() if t.upper() in tickers}
            total_w = sum(w0.values())
            if abs(total_w - 1.0) > 1e-3 or len(w0) != len(tickers):
                equal_w = 1.0 / len(tickers)
                w0 = {t: equal_w for t in tickers}
            else:
                w0 = {t: w / total_w for t, w in w0.items()}
        else:
            equal_w = 1.0 / len(tickers)
            w0 = {t: equal_w for t in tickers}

        initial_capital = input_data.initial_capital

        # Calculate static share quantities allocated at initial valuation date t0
        shares = {}
        for t in tickers:
            p0 = float(input_data.historical_prices[t][t0_date])
            shares[t] = (initial_capital * w0[t]) / p0

        # Construct deterministic buy-and-hold value path over identical oos_dates
        bnh_values = []
        for d in oos_dates:
            val = sum(shares[t] * float(input_data.historical_prices[t][d]) for t in tickers)
            bnh_values.append(val)

        return self.risk_engine.calculate(
            historical_prices={"BUY_AND_HOLD": bnh_values},
            weights={"BUY_AND_HOLD": 1.0},
            risk_free_rate=input_data.risk_free_rate,
        )

    @staticmethod
    def _calculate_relative_metrics(
        strategy_metrics: PortfolioRiskMetrics,
        benchmark_metrics: PortfolioRiskMetrics,
        strat_returns: list[float],
        bmark_returns: list[float],
    ) -> RelativeMetrics:
        """Calculate relative performance metrics comparing strategy against benchmark."""
        excess_cagr = strategy_metrics.cagr - benchmark_metrics.cagr
        total_return_difference = strategy_metrics.total_period_return - benchmark_metrics.total_period_return

        n = len(strat_returns)
        if n >= 2:
            return_diffs = [r_s - r_b for r_s, r_b in zip(strat_returns, bmark_returns)]
            mean_diff = fmean(return_diffs)
            var_diff = sum((d - mean_diff) ** 2 for d in return_diffs) / (n - 1)
            tracking_error = math.sqrt(var_diff * 252) if var_diff > 1e-12 else 0.0
        else:
            tracking_error = 0.0

        # Excess return convention: annualized return difference
        excess_return = strategy_metrics.annualized_return - benchmark_metrics.annualized_return

        if tracking_error > 1e-12:
            information_ratio = excess_return / tracking_error
        else:
            information_ratio = 0.0

        return RelativeMetrics(
            excess_cagr=excess_cagr,
            total_return_difference=total_return_difference,
            tracking_error=tracking_error,
            information_ratio=information_ratio,
        )
