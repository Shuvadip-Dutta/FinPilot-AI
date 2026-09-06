"""Builder for constructing validated PortfolioBacktestInput from Django Portfolio ORM objects."""

import math
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from apps.ai.portfolio.backtest import PortfolioBacktestInput
from apps.ai.portfolio.schemas import Portfolio as PortfolioSchema
from apps.portfolio.builder import PortfolioWorkflowInputBuilder
from apps.portfolio.models import Portfolio as PortfolioModel

INDEX_INSTRUMENT_MAP: dict[str, str] = {
    "NIFTY 50": "NSE_INDEX|Nifty 50",
    "NIFTY50": "NSE_INDEX|Nifty 50",
    "^NSEI": "NSE_INDEX|Nifty 50",
    "NIFTY": "NSE_INDEX|Nifty 50",
    "NIFTY 500": "NSE_INDEX|Nifty 500",
    "NIFTY500": "NSE_INDEX|Nifty 500",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "NIFTY BANK": "NSE_INDEX|Nifty Bank",
    "SENSEX": "BSE_INDEX|SENSEX",
    "^BSESN": "BSE_INDEX|SENSEX",
}


class PortfolioBacktestInputBuilder:
    """Deterministic builder converting persisted Django Portfolio objects into validated PortfolioBacktestInput."""

    def __init__(
        self,
        workflow_input_builder: PortfolioWorkflowInputBuilder | None = None,
        historical_data_fetcher: Callable[..., dict[str, Any]] | None = None,
    ):
        if workflow_input_builder is None:
            workflow_input_builder = PortfolioWorkflowInputBuilder(
                historical_data_fetcher=historical_data_fetcher
            )
        self.workflow_input_builder = workflow_input_builder
        self.historical_data_fetcher = (
            historical_data_fetcher or workflow_input_builder.historical_data_fetcher
        )

    def build_backtest_input(
        self,
        portfolio: PortfolioModel | PortfolioSchema,
        to_date: str | None = None,
        from_date: str | None = None,
        benchmark_ticker: str | None = None,
        initial_capital: float = 100000.0,
        rebalance_frequency: Literal["monthly", "quarterly", "annually", "periodic"] = "periodic",
        in_sample_window_days: int = 252,
        out_of_sample_step_days: int = 21,
        transaction_cost_bps: float = 10.0,
        risk_free_rate: float = 0.0,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> PortfolioBacktestInput:
        """Construct and validate a PortfolioBacktestInput from a Django Portfolio or PortfolioSchema."""
        canonical_portfolio = self.workflow_input_builder._to_canonical_portfolio(portfolio)

        if not canonical_portfolio.holdings:
            raise ValueError("Backtesting requires holdings, portfolio has none.")

        # Single market validation
        markets = {h.market for h in canonical_portfolio.holdings}
        if len(markets) > 1:
            raise ValueError(
                f"Historical backtesting across mixed markets/currencies ({sorted(markets)}) is not supported in a single numerical universe."
            )
        market = canonical_portfolio.holdings[0].market

        # Extract unique tickers and aggregate quantities
        tickers_map: dict[str, float] = {}
        for holding in canonical_portfolio.holdings:
            ticker = holding.ticker.strip().upper()
            qty = float(holding.quantity)
            if qty <= 0:
                raise ValueError(f"Holding quantity for {ticker} must be strictly positive.")
            tickers_map[ticker] = tickers_map.get(ticker, 0.0) + qty

        tickers = sorted(list(tickers_map.keys()))
        if len(tickers) < 2:
            raise ValueError(
                f"Backtesting requires at least two unique assets, found {len(tickers)} ({tickers})."
            )

        # Fetch date-aware historical prices aligned across portfolio assets
        historical_prices = self.workflow_input_builder.fetch_portfolio_historical_candles(
            portfolio=canonical_portfolio,
            to_date=to_date,
            from_date=from_date,
        )

        date_sets = [set(historical_prices[t].keys()) for t in tickers]
        common_dates = set.intersection(*date_sets) if date_sets else set()
        sorted_dates = sorted(list(common_dates))

        required_obs = in_sample_window_days + out_of_sample_step_days
        if len(sorted_dates) < required_obs:
            raise ValueError(
                f"Insufficient historical observations ({len(sorted_dates)}) for in-sample window ({in_sample_window_days}) "
                f"plus out-of-sample step ({out_of_sample_step_days}). Required at least {required_obs} observations."
            )

        # Compute actual initial portfolio market-value weights at t0
        t0 = sorted_dates[0]
        holding_values: dict[str, float] = {}
        for t in tickers:
            p0 = historical_prices[t].get(t0)
            if p0 is None or not math.isfinite(p0) or p0 <= 0:
                raise ValueError(f"Missing or invalid initial price for holding '{t}' on start date '{t0}'.")
            holding_values[t] = tickers_map[t] * float(p0)

        total_value = sum(holding_values.values())
        if not math.isfinite(total_value) or total_value <= 0:
            raise ValueError(f"Total initial portfolio value must be strictly positive, got {total_value}.")

        initial_weights = {t: val / total_value for t, val in holding_values.items()}

        # Fetch and align benchmark prices if benchmark_ticker provided
        benchmark_prices: dict[str, float] | None = None
        norm_benchmark_ticker: str | None = None

        if benchmark_ticker:
            norm_benchmark_ticker = benchmark_ticker.strip().upper()
            lookup_symbol = INDEX_INSTRUMENT_MAP.get(norm_benchmark_ticker, norm_benchmark_ticker)

            resolved_to = to_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            try:
                bmark_data = self.historical_data_fetcher(
                    ticker=lookup_symbol,
                    to_date=resolved_to,
                    from_date=from_date,
                    market=market,
                )
            except Exception as exc:
                raise ValueError(
                    f"Unable to fetch benchmark historical data for '{norm_benchmark_ticker}': {exc}"
                ) from exc

            if not isinstance(bmark_data, dict) or not bmark_data.get("candles"):
                raise ValueError(
                    f"Benchmark '{norm_benchmark_ticker}' returned invalid or empty historical candles."
                )

            bmark_candles = bmark_data["candles"]
            raw_bmark_prices: dict[str, float] = {}
            for candle in bmark_candles:
                if not isinstance(candle, dict):
                    continue
                close_val = candle.get("close")
                ts_val = candle.get("timestamp")
                if close_val is None or not math.isfinite(close_val) or close_val <= 0 or not ts_val:
                    continue
                iso_d = PortfolioWorkflowInputBuilder._normalize_iso_date(ts_val)
                raw_bmark_prices[iso_d] = float(close_val)

            common_set = set(sorted_dates)
            benchmark_prices = {d: price for d, price in raw_bmark_prices.items() if d in common_set}

            if len(benchmark_prices) < 3:
                raise ValueError(
                    f"Benchmark '{norm_benchmark_ticker}' has insufficient overlapping observations ({len(benchmark_prices)}) with portfolio evaluation dates."
                )

        return PortfolioBacktestInput(
            tickers=tickers,
            historical_prices=historical_prices,
            initial_capital=initial_capital,
            in_sample_window_days=in_sample_window_days,
            out_of_sample_step_days=out_of_sample_step_days,
            rebalance_frequency=rebalance_frequency,
            transaction_cost_bps=transaction_cost_bps,
            risk_free_rate=risk_free_rate,
            min_weight=min_weight,
            max_weight=max_weight,
            initial_weights=initial_weights,
            benchmark_ticker=norm_benchmark_ticker,
            benchmark_prices=benchmark_prices,
        )
