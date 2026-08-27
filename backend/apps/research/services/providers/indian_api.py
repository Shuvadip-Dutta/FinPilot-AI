import os
from typing import Any

import requests
from dotenv import load_dotenv

from apps.research.services.schemas import CompanyProfile, ExchangeQuote
from apps.research.services.symbols import Market

load_dotenv()


def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class IndianAPIProvider:

    BASE_URL = "https://stock.indianapi.in"

    def __init__(self) -> None:
        self.api_key = os.getenv("INDIAN_STOCK_MARKET_API_KEY")

        if not self.api_key:
            raise ValueError(
                "INDIAN_STOCK_MARKET_API_KEY is not configured."
            )

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:

        response = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            params=params,
            headers={
                "X-API-Key": self.api_key,
            },
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise RuntimeError(
                "Indian Stock Market API returned an unexpected response."
            )

        return data

    def get_stock(
        self,
        ticker: str,
        market: Market = Market.INDIA,
    ) -> dict[str, Any]:

        if market != Market.INDIA:
            raise ValueError(
                "IndianAPIProvider currently supports India only."
            )

        return self._get(
            "stock",
            {
                "name": ticker.upper(),
            },
        )

    def get_company_profile(
        self,
        ticker: str,
        market: Market = Market.INDIA,
    ) -> CompanyProfile:

        data = self.get_stock(ticker, market)

        profile = data.get("companyProfile") or {}

        return CompanyProfile(
            ticker=ticker.upper(),
            name=data.get("companyName", ""),
            exchange="NSE/BSE",
            country="India",
            sector=None,
            industry=(
                profile.get("mgIndustry")
                or data.get("industry")
            ),
            description=profile.get("companyDescription"),
            isin=profile.get("isInId"),
            nse_symbol=profile.get("exchangeCodeNse"),
            bse_code=profile.get("exchangeCodeBse"),
        )
    
    def get_quotes( self, ticker: str, market: Market = Market.INDIA) -> list[ExchangeQuote]:

        data = self.get_stock(ticker, market)

        current_price = data.get("currentPrice") or {}

        percent_change = _to_float(
            data.get("percentChange")
        )

        year_high = _to_float(
            data.get("yearHigh")
        )

        year_low = _to_float(
            data.get("yearLow")
        )

        quotes = []

        for exchange, price in current_price.items():
            quotes.append(
                ExchangeQuote(
                    exchange=exchange,
                    price=_to_float(price),
                    percent_change=percent_change,
                    year_high=year_high,
                    year_low=year_low,
                )
            )

        return quotes