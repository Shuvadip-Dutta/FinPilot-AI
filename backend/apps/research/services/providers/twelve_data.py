import os
from typing import Any

import requests
from dotenv import load_dotenv

from apps.research.services.market_data import MarketDataProvider
from apps.research.services.schemas import CompanyProfile, MarketQuote
from apps.research.services.symbols import Market, SymbolResolver
from common.logger import get_logger


load_dotenv()

logger = get_logger("research.twelve_data")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class TwelveDataProvider(MarketDataProvider):
    BASE_URL = "https://api.twelvedata.com"

    def __init__(self) -> None:
        self.api_key = os.getenv("TWELVE_DATA_API_KEY")

        if not self.api_key:
            raise ValueError(
                "TWELVE_DATA_API_KEY is not configured."
            )

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:

        params["apikey"] = self.api_key

        response = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") == "error":
            raise RuntimeError(
                data.get(
                    "message",
                    "Twelve Data request failed.",
                )
            )

        return data

    def get_company_profile(
        self,
        ticker: str,
        market: Market,
    ) -> CompanyProfile:

        if market != Market.INDIA:
            raise ValueError(
                "TwelveDataProvider currently supports India only."
            )

        symbol = SymbolResolver.resolve(ticker, market)

        data = self._get(
            "profile",
            {"symbol": symbol},
        )

        return CompanyProfile(
            ticker=ticker.upper(),
            name=data.get("name", ""),
            exchange=data.get("exchange", ""),
            country=data.get("country", "India"),
            sector=data.get("sector"),
            industry=data.get("industry"),
        )

    def get_quote(
        self,
        ticker: str,
        market: Market,
    ) -> MarketQuote:

        if market != Market.INDIA:
            raise ValueError(
                "TwelveDataProvider currently supports India only."
            )

        symbol = SymbolResolver.resolve(ticker, market)

        data = self._get(
            "quote",
            {"symbol": symbol},
        )

        return MarketQuote(
            ticker=ticker.upper(),
            price=_to_float(data.get("close")),
            change=_to_float(data.get("change")),
            percent_change=_to_float(
                data.get("percent_change")
            ),
            high=_to_float(data.get("high")),
            low=_to_float(data.get("low")),
            open=_to_float(data.get("open")),
            previous_close=_to_float(
                data.get("previous_close")
            ),
        )

    def get_historical_data(
        self,
        ticker: str,
        market: Market,
        start: int,
        end: int,
        resolution: str = "1day",
    ) -> dict[str, Any]:

        if market != Market.INDIA:
            raise ValueError(
                "TwelveDataProvider currently supports India only."
            )

        symbol = SymbolResolver.resolve(ticker, market)

        return self._get(
            "time_series",
            {
                "symbol": symbol,
                "interval": resolution,
                "start_date": start,
                "end_date": end,
            },
        )