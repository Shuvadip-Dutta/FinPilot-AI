"""Deterministic quantitative portfolio risk calculations."""

import math
from statistics import fmean
from typing import Any

from apps.ai.portfolio.schemas import Portfolio, PortfolioRiskMetrics

TRADING_PERIODS_PER_YEAR = 252
VOLATILITY_EPSILON = 1e-12
WEIGHT_SUM_EPSILON = 1e-3


class PortfolioRiskError(ValueError):
    """Raised when portfolio risk metrics cannot be calculated due to invalid inputs."""


class PortfolioMarketDataError(ValueError):
    """Raised when current market price data is missing or invalid for weight calculation."""


def calculate_current_weights(
    portfolio: Portfolio,
    last_prices: dict[str, float],
) -> dict[str, float]:
    """Calculate normalized current market value weights for portfolio holdings."""
    if not portfolio.holdings:
        raise ValueError("Cannot calculate current weights for a portfolio with no holdings.")

    holding_values: dict[str, float] = {}

    for holding in portfolio.holdings:
        ticker = holding.ticker.strip().upper()
        market_key = f"{holding.market}:{ticker}"
        if market_key in last_prices:
            price = last_prices[market_key]
        elif ticker in last_prices:
            price = last_prices[ticker]
        else:
            raise PortfolioMarketDataError(f"Missing current market price for holding {ticker}.")
        if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            raise PortfolioMarketDataError(f"Invalid market price for holding {ticker}: {price}.")

        val = float(holding.quantity) * float(price)
        holding_values[ticker] = holding_values.get(ticker, 0.0) + val

    total_value = sum(holding_values.values())
    if not math.isfinite(total_value) or total_value <= 0:
        raise ValueError(f"Total current portfolio value must be positive, got {total_value}.")

    return {ticker: val / total_value for ticker, val in holding_values.items()}


class PortfolioRiskEngine:
    """Calculate deterministic quantitative risk and performance analytics.

    Sign Convention for VaR / CVaR:
    - Positive VaR95 / CVaR95 represents a LOSS magnitude.
      For example, if the 5th percentile daily return is -0.04 (-4%),
      var_95_historical = +0.04 (4% loss magnitude).
      CVaR95 is the average of returns in the tail (<= 5th percentile cutoff),
      also expressed as a positive loss magnitude (+0.05 for -5% average tail return).
    """

    def calculate(
        self,
        historical_prices: dict[str, list[float]],
        weights: dict[str, float],
        risk_free_rate: float = 0.0,
        dates: list[str] | None = None,
    ) -> PortfolioRiskMetrics:
        """Calculate comprehensive risk metrics from historical prices and weights."""
        norm_weights, norm_prices = self._validate_inputs(
            historical_prices=historical_prices,
            weights=weights,
            risk_free_rate=risk_free_rate,
        )

        portfolio_returns = self._calculate_portfolio_returns(
            historical_prices=norm_prices,
            weights=norm_weights,
        )

        obs_count = len(portfolio_returns)
        mean_daily_return = fmean(portfolio_returns)
        annualized_return = mean_daily_return * TRADING_PERIODS_PER_YEAR

        # 1. Total Period Return & Wealth Path
        total_period_return, wealth_path = self._calculate_wealth_path(portfolio_returns)

        # 2. Drawdown Series
        drawdown_series = None
        if dates is not None:
            if len(dates) != len(wealth_path):
                raise PortfolioRiskError(
                    f"Dates count ({len(dates)}) does not match historical observation count ({len(wealth_path)})."
                )
            drawdown_series = self.calculate_drawdown_series(wealth_path, dates)

        # 3. CAGR
        cagr = self._calculate_cagr(total_period_return, obs_count)

        # 4. Volatility
        volatility = self._calculate_annualized_volatility(portfolio_returns, mean_daily_return)

        # 5. Downside Volatility
        daily_rf = risk_free_rate / TRADING_PERIODS_PER_YEAR
        downside_volatility = self._calculate_downside_volatility(portfolio_returns, daily_rf)

        # 6. Sharpe Ratio
        if volatility > VOLATILITY_EPSILON:
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility
        else:
            sharpe_ratio = 0.0

        # 7. Sortino Ratio
        if downside_volatility > VOLATILITY_EPSILON:
            sortino_ratio = (annualized_return - risk_free_rate) / downside_volatility
        else:
            sortino_ratio = 0.0

        # 8. Maximum Drawdown & Duration
        max_drawdown, max_drawdown_duration = self._calculate_max_drawdown(wealth_path)

        # 9. Calmar Ratio
        if max_drawdown > VOLATILITY_EPSILON:
            calmar_ratio = annualized_return / max_drawdown
        else:
            calmar_ratio = None

        # 10. Historical VaR & CVaR (95%)
        var_95, cvar_95 = self._calculate_historical_var_cvar(portfolio_returns)

        return PortfolioRiskMetrics(
            volatility=volatility,
            downside_volatility=downside_volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration_days=max_drawdown_duration,
            var_95_historical=var_95,
            cvar_95_historical=cvar_95,
            annualized_return=annualized_return,
            cagr=cagr,
            total_period_return=total_period_return,
            drawdown_series=drawdown_series,
        )

    def _validate_inputs(
        self,
        historical_prices: dict[str, list[float]],
        weights: dict[str, float],
        risk_free_rate: float,
    ) -> tuple[dict[str, float], dict[str, list[float]]]:
        if not isinstance(weights, dict) or not weights:
            raise PortfolioRiskError("Weights must be a non-empty dictionary.")

        if not isinstance(historical_prices, dict) or not historical_prices:
            raise PortfolioRiskError("Historical prices must be a non-empty dictionary.")

        if not math.isfinite(risk_free_rate):
            raise PortfolioRiskError("Risk-free rate must be finite.")

        norm_weights = {}
        for ticker, weight in weights.items():
            if not isinstance(ticker, str) or not ticker.strip():
                raise PortfolioRiskError("Ticker symbols in weights must be non-empty strings.")
            norm_ticker = ticker.strip().upper()
            if not isinstance(weight, (int, float)) or not math.isfinite(weight):
                raise PortfolioRiskError(f"Weight for {ticker} must be a finite number.")
            norm_weights[norm_ticker] = float(weight)

        norm_prices = {}
        for ticker, prices in historical_prices.items():
            if not isinstance(ticker, str) or not ticker.strip():
                raise PortfolioRiskError("Ticker symbols in historical prices must be non-empty strings.")
            norm_ticker = ticker.strip().upper()
            if not isinstance(prices, list):
                raise PortfolioRiskError(f"Historical prices for {ticker} must be a list.")
            if len(prices) < 3:
                raise PortfolioRiskError(f"At least three prices are required for {ticker}, found {len(prices)}.")
            float_prices = []
            for p in prices:
                if not isinstance(p, (int, float)) or not math.isfinite(p) or p <= 0:
                    raise PortfolioRiskError(f"Historical prices for {ticker} must be positive finite numbers.")
                float_prices.append(float(p))
            norm_prices[norm_ticker] = float_prices

        # Matching assets check
        if set(norm_weights.keys()) != set(norm_prices.keys()):
            raise PortfolioRiskError(
                f"Asset mismatch between weights ({set(norm_weights.keys())}) and prices ({set(norm_prices.keys())})."
            )

        # Check equal length across all price series
        lengths = {len(p) for p in norm_prices.values()}
        if len(lengths) > 1:
            raise PortfolioRiskError(f"All historical price series must have equal length, found lengths: {lengths}.")

        # Check weights sum approximately to 1
        total_w = sum(norm_weights.values())
        if abs(total_w - 1.0) > WEIGHT_SUM_EPSILON:
            raise PortfolioRiskError(f"Portfolio weights must sum approximately to 1.0, got {total_w:.6f}.")

        return norm_weights, norm_prices

    @staticmethod
    def _calculate_portfolio_returns(
        historical_prices: dict[str, list[float]],
        weights: dict[str, float],
    ) -> list[float]:

        asset_returns: dict[str, list[float]] = {}
        for ticker, prices in historical_prices.items():
            asset_returns[ticker] = [
                (prices[t] / prices[t - 1]) - 1.0
                for t in range(1, len(prices))
            ]

        tickers = list(weights.keys())
        obs_count = len(asset_returns[tickers[0]])

        portfolio_returns = []
        for t in range(obs_count):
            r_pt = sum(weights[ticker] * asset_returns[ticker][t] for ticker in tickers)
            portfolio_returns.append(r_pt)

        return portfolio_returns

    @staticmethod
    def _calculate_wealth_path(portfolio_returns: list[float]) -> tuple[float, list[float]]:
        wealth = 1.0
        path = [wealth]
        for r in portfolio_returns:
            wealth *= (1.0 + r)
            path.append(wealth)
        total_return = wealth - 1.0
        return total_return, path

    @staticmethod
    def calculate_drawdown_series(
        wealth_path: list[float],
        dates: list[str],
    ) -> list[dict[str, Any]]:
        """Calculate date-indexed cumulative return and peak-to-trough drawdown series."""
        series: list[dict[str, Any]] = []
        peak = wealth_path[0] if wealth_path else 1.0

        for d, wealth in zip(dates, wealth_path):
            if wealth > peak:
                peak = wealth
            dd = (peak - wealth) / peak if peak > 0 else 0.0
            cum_ret = (wealth - 1.0) * 100.0
            series.append({
                "date": str(d),
                "cumulative_return": round(cum_ret, 4),
                "drawdown": round(-dd * 100.0, 4),
            })

        return series

    @staticmethod
    def _calculate_cagr(total_return: float, obs_count: int) -> float:
        cumulative_factor = 1.0 + total_return
        if cumulative_factor <= 0.0:
            return -1.0
        years = obs_count / TRADING_PERIODS_PER_YEAR
        if years <= 0:
            return 0.0
        return math.pow(cumulative_factor, 1.0 / years) - 1.0

    @staticmethod
    def _calculate_annualized_volatility(
        returns: list[float],
        mean_return: float,
    ) -> float:
        n = len(returns)
        if n < 2:
            return 0.0
        var_daily = sum((r - mean_return) ** 2 for r in returns) / (n - 1)
        if var_daily <= VOLATILITY_EPSILON:
            return 0.0
        return math.sqrt(var_daily * TRADING_PERIODS_PER_YEAR)

    @staticmethod
    def _calculate_downside_volatility(
        returns: list[float],
        target_daily_return: float,
    ) -> float:
        n = len(returns)
        if n < 2:
            return 0.0
        downside_sq_sum = sum(
            min(r - target_daily_return, 0.0) ** 2 for r in returns
        )
        downside_var = downside_sq_sum / (n - 1)
        if downside_var <= VOLATILITY_EPSILON:
            return 0.0
        return math.sqrt(downside_var * TRADING_PERIODS_PER_YEAR)

    @staticmethod
    def _calculate_max_drawdown(wealth_path: list[float]) -> tuple[float, int]:
        max_dd = 0.0
        max_duration = 0
        current_duration = 0
        peak = wealth_path[0]

        for wealth in wealth_path:
            if wealth > peak:
                peak = wealth
                current_duration = 0
            else:
                dd = (peak - wealth) / peak
                if dd > max_dd:
                    max_dd = dd
                if wealth < peak:
                    current_duration += 1
                    if current_duration > max_duration:
                        max_duration = current_duration

        return max_dd, max_duration

    @staticmethod
    def _calculate_historical_var_cvar(
        returns: list[float],
        confidence_level: float = 0.95,
    ) -> tuple[float, float]:
        sorted_r = sorted(returns)
        n = len(sorted_r)

        p = 1.0 - confidence_level  # 0.05
        idx = p * (n - 1)
        low_i = int(math.floor(idx))
        high_i = min(low_i + 1, n - 1)
        frac = idx - low_i

        cutoff_return = sorted_r[low_i] + frac * (sorted_r[high_i] - sorted_r[low_i])

        var_95 = -cutoff_return

        tail = [r for r in sorted_r if r <= cutoff_return]
        if not tail:
            tail = [sorted_r[0]]
        cvar_95 = -fmean(tail)

        return var_95, cvar_95
