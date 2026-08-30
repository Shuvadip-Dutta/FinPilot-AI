"""Deterministic long-only mean-variance portfolio optimization.

Returns are annualized using 252 trading periods per year.  The risk-free
rate is therefore interpreted as an annual rate.
"""

import math
from statistics import fmean
from typing import Literal

from pydantic import BaseModel, Field, model_validator


TRADING_PERIODS_PER_YEAR = 252
VOLATILITY_EPSILON = 1e-12


class PortfolioOptimizationError(ValueError):
    """Raised when valid portfolio statistics cannot be optimized."""


class OptimizationInput(BaseModel):
    """Historical closing prices and constraints for long-only optimization."""

    tickers: list[str]
    historical_prices: dict[str, list[float]]
    risk_free_rate: float = 0.0
    min_weight: float = Field(default=0.0, ge=0)
    max_weight: float = Field(default=1.0, le=1)

    @model_validator(mode="after")
    def validate_optimization_input(self) -> "OptimizationInput":
        if len(self.tickers) < 2:
            raise ValueError("At least two assets are required.")

        normalized_tickers = [ticker.strip().upper() for ticker in self.tickers]

        if any(not ticker for ticker in normalized_tickers):
            raise ValueError("Tickers must not be empty.")

        if len(set(normalized_tickers)) != len(normalized_tickers):
            raise ValueError("Tickers must be unique.")

        self.tickers = normalized_tickers

        if set(self.historical_prices) != set(self.tickers):
            raise ValueError(
                "Historical prices must be provided for every ticker."
            )

        series_lengths = {len(prices) for prices in self.historical_prices.values()}

        if len(series_lengths) != 1:
            raise ValueError("All price series must have compatible lengths.")

        observations = series_lengths.pop()

        if observations < 3:
            raise ValueError(
                "At least three prices per asset are required for covariance estimation."
            )

        for ticker, prices in self.historical_prices.items():
            if any(not math.isfinite(price) or price <= 0 for price in prices):
                raise ValueError(
                    f"Historical prices for {ticker} must be positive and finite."
                )

        if not math.isfinite(self.risk_free_rate):
            raise ValueError("Risk-free rate must be finite.")

        if self.min_weight > self.max_weight:
            raise ValueError("min_weight must not exceed max_weight.")

        asset_count = len(self.tickers)

        if self.min_weight * asset_count > 1 + VOLATILITY_EPSILON:
            raise ValueError("Minimum weights make a portfolio infeasible.")

        if self.max_weight * asset_count < 1 - VOLATILITY_EPSILON:
            raise ValueError("Maximum weights make a portfolio infeasible.")

        return self


class OptimizationResult(BaseModel):
    """The optimized portfolio performance, or a controlled failure result."""

    optimized_weights: dict[str, float] | None = None
    expected_return: float | None = None
    volatility: float | None = None
    sharpe_ratio: float | None = None
    total_weight: float | None = None
    success: bool
    message: str


class PortfolioOptimizationEngine:
    """Maximize annualized Sharpe ratio subject to long-only weight bounds."""

    def optimize(self, input: OptimizationInput) -> OptimizationResult:
        """Optimize a portfolio, returning a failure result for solver failures."""
        try:
            returns = self.calculate_returns(input)
            expected_returns = self.calculate_annualized_expected_returns(returns)
            covariance = self.calculate_annualized_covariance(returns)
            weights = self._maximize_sharpe(
                expected_returns=expected_returns,
                covariance=covariance,
                risk_free_rate=input.risk_free_rate,
                min_weight=input.min_weight,
                max_weight=input.max_weight,
            )
            expected_return, volatility, sharpe_ratio = self.calculate_portfolio_metrics(
                weights=weights,
                expected_returns=expected_returns,
                covariance=covariance,
                risk_free_rate=input.risk_free_rate,
            )
        except PortfolioOptimizationError as exc:
            return OptimizationResult(success=False, message=str(exc))

        return OptimizationResult(
            optimized_weights=dict(zip(input.tickers, weights, strict=True)),
            expected_return=expected_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            total_weight=sum(weights),
            success=True,
            message="Optimization completed successfully.",
        )

    @staticmethod
    def calculate_returns(input: OptimizationInput) -> dict[str, list[float]]:
        """Calculate simple periodic returns: price[t] / price[t-1] - 1."""
        return {
            ticker: [
                (current / previous) - 1
                for previous, current in zip(prices, prices[1:])
            ]
            for ticker, prices in input.historical_prices.items()
        }

    @staticmethod
    def calculate_annualized_expected_returns(
        returns: dict[str, list[float]],
    ) -> list[float]:
        """Return arithmetic mean periodic returns annualized to 252 periods."""
        return [
            fmean(asset_returns) * TRADING_PERIODS_PER_YEAR
            for asset_returns in returns.values()
        ]

    @staticmethod
    def calculate_annualized_covariance(
        returns: dict[str, list[float]],
    ) -> list[list[float]]:
        """Return the sample covariance matrix annualized to 252 periods."""
        return_series = list(returns.values())
        observations = len(return_series[0])

        if observations < 2:
            raise PortfolioOptimizationError(
                "At least two return observations are required for covariance estimation."
            )

        means = [fmean(series) for series in return_series]

        return [
            [
                sum(
                    (left[index] - means[left_index])
                    * (right[index] - means[right_index])
                    for index in range(observations)
                )
                / (observations - 1)
                * TRADING_PERIODS_PER_YEAR
                for right_index, right in enumerate(return_series)
            ]
            for left_index, left in enumerate(return_series)
        ]

    @staticmethod
    def calculate_portfolio_metrics(
        weights: list[float],
        expected_returns: list[float],
        covariance: list[list[float]],
        risk_free_rate: float,
    ) -> tuple[float, float, float]:
        """Return annual expected return, volatility, and annual Sharpe ratio."""
        expected_return = sum(
            weight * expected_return
            for weight, expected_return in zip(
                weights, expected_returns, strict=True
            )
        )
        variance = sum(
            weights[row]
            * covariance[row][column]
            * weights[column]
            for row in range(len(weights))
            for column in range(len(weights))
        )

        if variance <= VOLATILITY_EPSILON:
            raise PortfolioOptimizationError(
                "Portfolio volatility is too close to zero to calculate Sharpe ratio."
            )

        volatility = math.sqrt(variance)
        sharpe_ratio = (expected_return - risk_free_rate) / volatility

        return expected_return, volatility, sharpe_ratio

    def _maximize_sharpe(
        self,
        expected_returns: list[float],
        covariance: list[list[float]],
        risk_free_rate: float,
        min_weight: float,
        max_weight: float,
    ) -> list[float]:
        asset_count = len(expected_returns)
        weights = self._project_to_bounded_simplex(
            [1 / asset_count] * asset_count,
            min_weight,
            max_weight,
        )

        # Fixed iteration limits and no random initialization keep this fallback
        # deterministic when SciPy is unavailable.
        for _ in range(500):
            _, volatility, sharpe_ratio = self.calculate_portfolio_metrics(
                weights,
                expected_returns,
                covariance,
                risk_free_rate,
            )
            excess_returns = [
                expected_return - risk_free_rate
                for expected_return in expected_returns
            ]
            covariance_weights = [
                sum(covariance[row][column] * weights[column] for column in range(asset_count))
                for row in range(asset_count)
            ]
            variance = volatility * volatility
            gradient = [
                (excess_returns[index] / volatility)
                - (sharpe_ratio * covariance_weights[index] / variance)
                for index in range(asset_count)
            ]

            improved = False
            step_size = 0.1

            for _ in range(20):
                candidate = self._project_to_bounded_simplex(
                    [
                        weight + step_size * direction
                        for weight, direction in zip(weights, gradient, strict=True)
                    ],
                    min_weight,
                    max_weight,
                )
                _, _, candidate_sharpe = self.calculate_portfolio_metrics(
                    candidate,
                    expected_returns,
                    covariance,
                    risk_free_rate,
                )

                if candidate_sharpe > sharpe_ratio + 1e-12:
                    weights = candidate
                    improved = True
                    break

                step_size /= 2

            if not improved:
                break

        return weights

    @staticmethod
    def _project_to_bounded_simplex(
        values: list[float],
        min_weight: float,
        max_weight: float,
    ) -> list[float]:
        """Project values onto ``sum(weights)=1`` with per-asset bounds."""
        low = min(values) - max_weight
        high = max(values) - min_weight

        for _ in range(100):
            midpoint = (low + high) / 2
            projected = [
                min(max(value - midpoint, min_weight), max_weight)
                for value in values
            ]

            if sum(projected) > 1:
                low = midpoint
            else:
                high = midpoint

        return [
            min(max(value - ((low + high) / 2), min_weight), max_weight)
            for value in values
        ]
