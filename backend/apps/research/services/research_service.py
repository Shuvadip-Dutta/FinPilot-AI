from apps.research.services.providers.finnhub import FinnhubProvider
from apps.research.services.providers.indian_api import IndianAPIProvider
from apps.research.services.symbols import Market


class ResearchService:

    def __init__(self):
        self.finnhub = FinnhubProvider()
        self.indian_api = IndianAPIProvider()

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
    
    def get_market_data(self, ticker: str, market: Market):
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