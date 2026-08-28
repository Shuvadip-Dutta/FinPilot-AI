from apps.research.services.providers.finnhub import FinnhubProvider
from apps.research.services.providers.indian_api import IndianAPIProvider
from apps.research.services.providers.upstox import UpstoxProvider
from apps.research.services.news_aggregator import NewsAggregator
from apps.research.services.symbols import Market


class ResearchService:

    def __init__(self):
        self._finnhub = None
        self._indian_api = None
        self._upstox = None
        self._news_aggregator = None

    @property
    def finnhub(self):
        if self._finnhub is None:
            self._finnhub = FinnhubProvider()
        return self._finnhub

    @property
    def indian_api(self):
        if self._indian_api is None:
            self._indian_api = IndianAPIProvider()
        return self._indian_api

    @property
    def upstox(self):
        if self._upstox is None:
            self._upstox = UpstoxProvider()
        return self._upstox

    @property
    def news_aggregator(self):
        if self._news_aggregator is None:
            self._news_aggregator = NewsAggregator()
        return self._news_aggregator

    def get_company_profile(
        self,
        ticker: str,
        market: Market,
    ):
        if market == Market.US:
            return self.finnhub.get_company_profile(
                ticker,
                market,
            )

        if market == Market.INDIA:
            return self.indian_api.get_company_profile(
                ticker,
                market,
            )

        raise ValueError(
            f"Unsupported market: {market}"
        )

    def get_market_data(
        self,
        ticker: str,
        market: Market,
    ):
        if market == Market.US:
            return self.finnhub.get_quote(
                ticker,
                market,
            )

        if market == Market.INDIA:
            return self.indian_api.get_quotes(
                ticker,
                market,
            )

        raise ValueError(
            f"Unsupported market: {market}"
        )

    def get_financials(
        self,
        ticker: str,
        market: Market,
    ):
        if market == Market.INDIA:
            return self.indian_api.get_financials(
                ticker,
                market,
            )

        raise ValueError(
            f"Financial data is not yet supported for market: {market}"
        )

    def get_key_metrics(
        self,
        ticker: str,
        market: Market,
    ):
        if market == Market.INDIA:
            return self.indian_api.get_key_metrics(
                ticker,
                market,
            )

        raise ValueError(
            f"Key metrics are not yet supported for market: {market}"
        )

    def get_historical_data(
        self,
        ticker: str,
        to_date: str,
        from_date: str | None = None,
        market: Market = Market.INDIA,
    ):
        if market == Market.INDIA:
            return self.upstox.get_historical(
                ticker,
                to_date,
                from_date,
                market,
            )

        raise ValueError(
            f"Historical data is not yet supported for market: {market}"
        )

    def get_news(
        self,
        ticker: str,
        market: Market,
    ):
        return self.news_aggregator.get_news(
            ticker,
            market,
        )