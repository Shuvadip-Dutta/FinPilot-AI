import os
from typing import Any

import requests
from dotenv import load_dotenv
from common.logger import get_logger
from apps.research.services.market_data import MarketDataProvider
from apps.research.services.schemas import CompanyProfile, MarketQuote
from apps.research.services.symbols import Market, SymbolResolver
load_dotenv()

logger = get_logger("research.finnhub")
def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None

class FinnhubProvider(MarketDataProvider):
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self) -> None:
        self.api_key = os.getenv("FINNHUB_API_KEY")

        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY is not configured.")

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:

        params["token"] = self.api_key

        response = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()

    def get_company_profile(self, ticker: str, market: Market = Market.US) -> CompanyProfile:

        provider_symbol = SymbolResolver.resolve(
            ticker,
            market,
        )

        data = self._get(
            "stock/profile2",
            {"symbol": provider_symbol},
        )

        return CompanyProfile(
            ticker=ticker.upper(),
            name=data.get("name", ""),
            exchange=data.get("exchange", ""),
            country=data.get("country", ""),
            sector=None,
            industry=data.get("finnhubIndustry"),
            description=None,
            isin=None,
            nse_symbol=None,
            bse_code=None,
        )

    def get_quote(self, ticker: str, market: Market = Market.US,) -> MarketQuote:

        provider_symbol = SymbolResolver.resolve(
            ticker,
            market,
        )

        data = self._get(
            "quote",
            {"symbol": provider_symbol},
        )

        return MarketQuote(
            ticker=ticker.upper(),
            price=_to_float(data.get("c")),
            change=_to_float(data.get("d")),
            percent_change=_to_float(data.get("dp")),
            high=_to_float(data.get("h")),
            low=_to_float(data.get("l")),
            open=_to_float(data.get("o")),
            previous_close=_to_float(data.get("pc")),
        )

    def get_historical_data(
        self,
        ticker: str,
        start: int,
        end: int,
        resolution: str = "D",
    ) -> dict[str, Any]:

        return self._get(
            "stock/candle",
            {
                "symbol": ticker.upper(),
                "resolution": resolution,
                "from": start,
                "to": end,
            },
        )