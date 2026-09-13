"""Builder for constructing canonical PortfolioWorkflowInput from Django Portfolio ORM objects."""

import math
from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import Any

from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.portfolio.optimization import OptimizationInput
from apps.ai.portfolio.schemas import Portfolio as PortfolioSchema
from apps.portfolio.models import Portfolio as PortfolioModel


class PortfolioWorkflowInputBuilder:
    """Constructs canonical PortfolioWorkflowInput for analysis and optimization workflows."""

    def __init__(
        self,
        historical_data_fetcher: Callable[..., dict[str, Any]] | None = None,
    ):
        if historical_data_fetcher is None:
            from apps.ai.services.research_tools import get_historical_data

            historical_data_fetcher = get_historical_data
        self.historical_data_fetcher = historical_data_fetcher

    def fetch_portfolio_historical_prices(
        self,
        portfolio: PortfolioModel | PortfolioSchema,
        to_date: str | None = None,
        from_date: str | None = None,
    ) -> dict[str, list[float]]:
        """Fetch and align historical closing prices for all unique holdings in a portfolio."""
        canonical_portfolio = self._to_canonical_portfolio(portfolio)

        if not canonical_portfolio.holdings:
            raise ValueError("Historical prices require holdings, portfolio has none.")

        markets = {h.market for h in canonical_portfolio.holdings}
        if len(markets) > 1:
            raise ValueError(
                f"Historical prices across mixed markets/currencies ({sorted(markets)}) is not supported in a single numerical universe."
            )
        market = canonical_portfolio.holdings[0].market

        tickers: list[str] = []
        for holding in canonical_portfolio.holdings:
            normalized = holding.ticker.strip().upper()
            if normalized not in tickers:
                tickers.append(normalized)

        resolved_to_date = to_date or date.today().isoformat()
        raw_historical_prices: dict[str, list[float]] = {}

        for ticker in tickers:
            prices = self._fetch_closing_prices(
                ticker=ticker,
                market=market,
                to_date=resolved_to_date,
                from_date=from_date,
            )
            raw_historical_prices[ticker] = prices

        return self._align_price_series(raw_historical_prices)

    def build_analysis_input(
        self,
        portfolio: PortfolioModel | PortfolioSchema,
        to_date: str | None = None,
        from_date: str | None = None,
    ) -> PortfolioWorkflowInput:
        """Construct PortfolioWorkflowInput for portfolio analysis (no optimization)."""
        return self.build_workflow_input(
            portfolio=portfolio,
            include_optimization=False,
            to_date=to_date,
            from_date=from_date,
        )

    def build_optimization_input(
        self,
        portfolio: PortfolioModel | PortfolioSchema,
        risk_free_rate: float = 0.0,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        to_date: str | None = None,
        from_date: str | None = None,
        historical_prices: dict[str, list[float]] | None = None,
    ) -> OptimizationInput:
        """Construct OptimizationInput with historical price series for the portfolio's assets."""
        canonical_portfolio = self._to_canonical_portfolio(portfolio)

        if not canonical_portfolio.holdings:
            raise ValueError("Optimization requires at least two unique assets, portfolio has none.")

        tickers: list[str] = []
        for holding in canonical_portfolio.holdings:
            normalized = holding.ticker.strip().upper()
            if normalized not in tickers:
                tickers.append(normalized)

        if len(tickers) < 2:
            raise ValueError(
                f"Optimization requires at least two unique assets, found {len(tickers)} ({tickers})."
            )

        if historical_prices is None:
            historical_prices = self.fetch_portfolio_historical_prices(
                portfolio=canonical_portfolio,
                to_date=to_date,
                from_date=from_date,
            )

        return OptimizationInput(
            tickers=tickers,
            historical_prices=historical_prices,
            risk_free_rate=risk_free_rate,
            min_weight=min_weight,
            max_weight=max_weight,
        )

    def build_workflow_input(
        self,
        portfolio: PortfolioModel | PortfolioSchema,
        include_optimization: bool = False,
        risk_free_rate: float = 0.0,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        to_date: str | None = None,
        from_date: str | None = None,
    ) -> PortfolioWorkflowInput:
        """Construct complete PortfolioWorkflowInput with historical prices and optional OptimizationInput."""
        canonical_portfolio = self._to_canonical_portfolio(portfolio)
        historical_prices: dict[str, list[float]] | None = None

        if canonical_portfolio.holdings:
            try:
                historical_prices = self.fetch_portfolio_historical_prices(
                    portfolio=canonical_portfolio,
                    to_date=to_date,
                    from_date=from_date,
                )
            except ValueError:
                historical_prices = None

        opt_input = None
        if include_optimization:
            opt_input = self.build_optimization_input(
                portfolio=canonical_portfolio,
                risk_free_rate=risk_free_rate,
                min_weight=min_weight,
                max_weight=max_weight,
                to_date=to_date,
                from_date=from_date,
                historical_prices=historical_prices,
            )
            historical_prices = opt_input.historical_prices

        django_portfolio_id = str(portfolio.pk) if isinstance(portfolio, PortfolioModel) else None
        return PortfolioWorkflowInput(
            portfolio=canonical_portfolio,
            optimization_input=opt_input,
            historical_prices=historical_prices,
            django_portfolio_id=django_portfolio_id,
        )

    @staticmethod
    def _to_canonical_portfolio(
        portfolio: PortfolioModel | PortfolioSchema,
    ) -> PortfolioSchema:
        if isinstance(portfolio, PortfolioModel):
            return portfolio.to_pydantic()
        if isinstance(portfolio, PortfolioSchema):
            return portfolio
        raise TypeError(
            f"Expected Portfolio model or Portfolio schema, got {type(portfolio).__name__}."
        )

    def _fetch_closing_prices(
        self,
        ticker: str,
        market: str,
        to_date: str,
        from_date: str | None,
    ) -> list[float]:
        try:
            data = self.historical_data_fetcher(
                ticker=ticker,
                to_date=to_date,
                from_date=from_date,
                market=market,
            )
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Unable to retrieve historical market data for {ticker}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"Historical market data for {ticker} returned invalid format: expected dict, got {type(data).__name__}."
            )

        candles = data.get("candles")
        if not isinstance(candles, list) or not candles:
            raise ValueError(
                f"Historical market data for {ticker} contains no candles."
            )

        prices: list[float] = []
        for index, candle in enumerate(candles):
            if not isinstance(candle, dict):
                raise ValueError(
                    f"Invalid candle format for {ticker} at index {index}."
                )
            close = candle.get("close")
            if (
                close is None
                or not isinstance(close, (int, float))
                or not math.isfinite(close)
                or close <= 0
            ):
                raise ValueError(
                    f"Historical market data for {ticker} contains invalid or non-positive price at index {index}: {close}."
                )
            prices.append(float(close))

        if len(prices) < 3:
            raise ValueError(
                f"At least three historical prices per asset are required for {ticker}, found {len(prices)}."
            )

        return prices

    @staticmethod
    def _align_price_series(
        historical_prices: dict[str, list[float]],
    ) -> dict[str, list[float]]:
        """Align price series to identical length using the most recent common observations."""
        lengths = [len(prices) for prices in historical_prices.values()]
        min_length = min(lengths)

        if min_length < 3:
            raise ValueError(
                f"Insufficient common historical price observations across assets ({min_length} < 3)."
            )

        # Truncate each series from the tail (most recent min_length observations)
        return {
            ticker: prices[-min_length:]
            for ticker, prices in historical_prices.items()
        }

    @staticmethod
    def _normalize_iso_date(ts_val: Any) -> str:
        """Extract and normalize date to YYYY-MM-DD format."""
        if ts_val is None or ts_val == "":
            raise ValueError("Candle timestamp is missing or empty.")
        if isinstance(ts_val, (int, float)):
            if not math.isfinite(ts_val) or ts_val <= 0:
                raise ValueError(f"Invalid timestamp value: {ts_val}")
            dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        if isinstance(ts_val, datetime):
            return ts_val.strftime("%Y-%m-%d")
        if isinstance(ts_val, date):
            return ts_val.strftime("%Y-%m-%d")
        if isinstance(ts_val, str):
            cleaned = ts_val.strip()
            if len(cleaned) >= 10:
                date_part = cleaned[:10]
                try:
                    datetime.strptime(date_part, "%Y-%m-%d")
                    return date_part
                except ValueError:
                    pass
            raise ValueError(f"Invalid date format for timestamp: '{ts_val}'")
        raise ValueError(f"Unsupported timestamp type: {type(ts_val).__name__}")

    def fetch_portfolio_historical_candles(
        self,
        portfolio: PortfolioModel | PortfolioSchema,
        to_date: str | None = None,
        from_date: str | None = None,
    ) -> dict[str, dict[str, float]]:
        """Fetch date-aligned historical closing prices mapping ticker -> {ISO date -> close_price}."""
        canonical_portfolio = self._to_canonical_portfolio(portfolio)

        if not canonical_portfolio.holdings:
            raise ValueError("Historical prices require holdings, portfolio has none.")

        markets = {h.market for h in canonical_portfolio.holdings}
        if len(markets) > 1:
            raise ValueError(
                f"Historical prices across mixed markets/currencies ({sorted(markets)}) is not supported in a single numerical universe."
            )
        market = canonical_portfolio.holdings[0].market

        tickers: list[str] = []
        for holding in canonical_portfolio.holdings:
            normalized = holding.ticker.strip().upper()
            if normalized not in tickers:
                tickers.append(normalized)

        tickers.sort()

        resolved_to_date = to_date or date.today().isoformat()
        raw_candles: dict[str, dict[str, float]] = {}

        for ticker in tickers:
            date_price_map = self._fetch_date_aware_closing_prices(
                ticker=ticker,
                market=market,
                to_date=resolved_to_date,
                from_date=from_date,
            )
            raw_candles[ticker] = date_price_map

        return self.align_date_aware_candles(raw_candles)

    def _fetch_date_aware_closing_prices(
        self,
        ticker: str,
        market: str,
        to_date: str,
        from_date: str | None,
    ) -> dict[str, float]:
        """Fetch candles for a single ticker and extract validated date -> close_price mapping."""
        try:
            data = self.historical_data_fetcher(
                ticker=ticker,
                to_date=to_date,
                from_date=from_date,
                market=market,
            )
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Unable to retrieve historical market data for {ticker}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"Historical market data for {ticker} returned invalid format: expected dict, got {type(data).__name__}."
            )

        candles = data.get("candles")
        if not isinstance(candles, list) or not candles:
            raise ValueError(
                f"Historical market data for {ticker} contains no candles."
            )

        from_date_norm = self._normalize_iso_date(from_date) if from_date else None
        to_date_norm = self._normalize_iso_date(to_date) if to_date else None

        date_price_map: dict[str, float] = {}

        for index, candle in enumerate(candles):
            if not isinstance(candle, dict):
                raise ValueError(
                    f"Invalid candle format for {ticker} at index {index}."
                )

            close = candle.get("close")
            if (
                close is None
                or not isinstance(close, (int, float))
                or not math.isfinite(close)
                or close <= 0
            ):
                raise ValueError(
                    f"Historical market data for {ticker} contains invalid or non-positive price at index {index}: {close}."
                )

            ts_raw = candle.get("timestamp")
            iso_date = self._normalize_iso_date(ts_raw)

            if from_date_norm and iso_date < from_date_norm:
                continue
            if to_date_norm and iso_date > to_date_norm:
                continue

            if iso_date in date_price_map:
                raise ValueError(
                    f"Duplicate date observation '{iso_date}' found for ticker '{ticker}'."
                )

            date_price_map[iso_date] = float(close)

        sorted_map = dict(sorted(date_price_map.items(), key=lambda item: item[0]))
        return sorted_map

    @staticmethod
    def align_date_aware_candles(
        candles_dict: dict[str, dict[str, float]],
    ) -> dict[str, dict[str, float]]:
        """Align multi-asset date-aware candles to the common intersection of dates without interpolation."""
        if not candles_dict:
            return {}

        sorted_tickers = sorted(list(candles_dict.keys()))

        date_sets = [set(candles_dict[ticker].keys()) for ticker in sorted_tickers]
        common_dates = set.intersection(*date_sets) if date_sets else set()
        sorted_dates = sorted(list(common_dates))

        aligned: dict[str, dict[str, float]] = {}
        for ticker in sorted_tickers:
            aligned[ticker] = {
                d: candles_dict[ticker][d] for d in sorted_dates if d in candles_dict[ticker]
            }

        return aligned

