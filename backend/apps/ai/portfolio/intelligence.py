"""Deterministic portfolio valuation using injected market data."""

from collections.abc import Callable

from apps.ai.portfolio.schemas import CurrencySubtotal, Portfolio, PortfolioIntelligence


MarketDataTool = Callable[..., dict[str, object]]


class PortfolioMarketDataError(ValueError):
    """Raised when a holding cannot be valued from market data."""


class PortfolioIntelligenceService:
    """Calculate portfolio intelligence without provider or LLM dependencies."""

    def __init__(self, market_data_tool: MarketDataTool):
        self.market_data_tool = market_data_tool

    def analyze(self, portfolio: Portfolio) -> PortfolioIntelligence:
        """Value every holding and return aggregate or per-currency portfolio performance."""
        if not portfolio.holdings:
            return PortfolioIntelligence(
                invested_value=0.0,
                current_value=0.0,
                profit_loss=0.0,
                profit_loss_percentage=0.0,
                holdings_count=0,
                currency="INR",
                currency_context="INR (₹)",
                market_currency_context=None,
                currency_totals=None,
                is_mixed_currency=False,
            )

        markets = {holding.market for holding in portfolio.holdings}
        is_mixed = len(markets) > 1

        # Fetch last prices for every holding keyed by market + ticker
        prices_by_holding: dict[tuple[str, str], float] = {}
        for holding in portfolio.holdings:
            key = (holding.market, holding.ticker.strip().upper())
            if key not in prices_by_holding:
                last_price = self._get_last_price(
                    ticker=holding.ticker,
                    market=holding.market,
                )
                prices_by_holding[key] = last_price

        # Compute per-currency aggregates
        totals_by_currency: dict[str, dict[str, float | str | int]] = {}
        for holding in portfolio.holdings:
            curr = "INR" if holding.market == "IN" else "USD"
            symbol = "₹" if curr == "INR" else "$"
            if curr not in totals_by_currency:
                totals_by_currency[curr] = {
                    "invested_value": 0.0,
                    "current_value": 0.0,
                    "profit_loss": 0.0,
                    "profit_loss_percentage": 0.0,
                    "currency": curr,
                    "currency_symbol": symbol,
                    "holdings_count": 0,
                }
            inv = holding.quantity * holding.average_price
            holding_key = (holding.market, holding.ticker.strip().upper())
            cur = holding.quantity * prices_by_holding[holding_key]
            totals_by_currency[curr]["invested_value"] += inv
            totals_by_currency[curr]["current_value"] += cur
            totals_by_currency[curr]["holdings_count"] += 1

        for curr, data in totals_by_currency.items():
            data["profit_loss"] = data["current_value"] - data["invested_value"]
            inv_val = data["invested_value"]
            data["profit_loss_percentage"] = (
                (data["profit_loss"] / inv_val) * 100
                if inv_val > 0
                else 0.0
            )

        currency_subtotals = {
            curr: CurrencySubtotal(**data)
            for curr, data in totals_by_currency.items()
        }

        market_currency_context: dict[str, dict[str, str]] = {}
        for holding in portfolio.holdings:
            norm_ticker = holding.ticker.strip().upper()
            ctx = {
                "market": holding.market,
                "currency": "INR" if holding.market == "IN" else "USD",
                "currency_symbol": "₹" if holding.market == "IN" else "$",
            }
            # Key by market + ticker to guarantee cross-market safety
            market_currency_context[f"{holding.market}:{norm_ticker}"] = ctx
            # Provide simple ticker key if no cross-market conflict exists
            if norm_ticker not in market_currency_context:
                market_currency_context[norm_ticker] = ctx
            elif market_currency_context[norm_ticker]["market"] != holding.market:
                del market_currency_context[norm_ticker]

        if not is_mixed:
            single_curr = next(iter(totals_by_currency.keys()))
            single_data = totals_by_currency[single_curr]
            currency_context = "INR (₹)" if single_curr == "INR" else "USD ($)"
            return PortfolioIntelligence(
                invested_value=float(single_data["invested_value"]),
                current_value=float(single_data["current_value"]),
                profit_loss=float(single_data["profit_loss"]),
                profit_loss_percentage=float(single_data["profit_loss_percentage"]),
                holdings_count=len(portfolio.holdings),
                currency=single_curr,
                currency_context=currency_context,
                market_currency_context=market_currency_context,
                currency_totals=currency_subtotals,
                is_mixed_currency=False,
            )

        # Mixed currency: NEVER sum nominally across currencies without FX conversion
        return PortfolioIntelligence(
            invested_value=None,
            current_value=None,
            profit_loss=None,
            profit_loss_percentage=None,
            holdings_count=len(portfolio.holdings),
            currency="MIXED",
            currency_context="MIXED (Indian holdings in INR ₹, US holdings in USD $; separated per-currency totals provided, no cross-currency nominal aggregate)",
            market_currency_context=market_currency_context,
            currency_totals=currency_subtotals,
            is_mixed_currency=True,
        )

    def get_last_prices(self, portfolio: Portfolio) -> dict[str, float]:
        """Fetch current last prices for all holdings in a portfolio."""
        prices: dict[str, float] = {}
        ticker_markets: dict[str, set[str]] = {}
        for holding in portfolio.holdings:
            norm_ticker = holding.ticker.strip().upper()
            ticker_markets.setdefault(norm_ticker, set()).add(holding.market)

        for holding in portfolio.holdings:
            ticker = holding.ticker.strip().upper()
            market_key = f"{holding.market}:{ticker}"
            try:
                price = self._get_last_price(holding.ticker, holding.market)
                prices[market_key] = price
                if len(ticker_markets.get(ticker, set())) <= 1:
                    prices[ticker] = price
            except Exception:
                continue
        return prices

    def _get_last_price(self, ticker: str, market: str) -> float:
        try:
            market_data = self.market_data_tool(
                ticker=ticker,
                market=market,
            )
        except (ValueError, TypeError) as exc:
            raise PortfolioMarketDataError(
                f"Unable to retrieve market data for {ticker}: {exc}"
            ) from exc

        last_price = market_data.get("last_price")

        if not isinstance(last_price, (int, float)):
            raise PortfolioMarketDataError(
                f"Market data for {ticker} does not include a valid last_price."
            )

        return float(last_price)
