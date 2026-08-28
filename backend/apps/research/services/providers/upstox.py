import requests

from django.conf import settings
from apps.research.services.exceptions import ProviderResponseError
from apps.research.services.symbols import Market
from apps.research.services.schemas import (
    HistoricalCandle,
    HistoricalMarketData,
)
from datetime import datetime, timezone
from apps.research.services.instrument_resolver import (
    UpstoxInstrumentResolver,
)

from apps.research.services.schemas import (
    HistoricalCandle,
    HistoricalMarketData,
    NewsArticle,
    NewsResearch,
)

class UpstoxProvider:
    BASE_URL = "https://api.upstox.com/v3"
    NEWS_BASE_URL = "https://api.upstox.com/v2"

    def __init__(self):
        self.access_token = (
            settings.UPSTOX_ANALYTICS_ACCESS_TOKEN
        )
        self.instrument_resolver = UpstoxInstrumentResolver()

    def _get(self, endpoint: str, params: dict, base_url: str | None = None) -> dict:

        response = requests.get(
            f"{base_url or self.BASE_URL}/{endpoint}",
            headers={
                "Accept": "application/json",
                "Authorization": (
                    f"Bearer {self.access_token}"
                ),
            },
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()
    
    @staticmethod
    def _validate_dict_response(
        data: dict,
        provider: str = "Upstox",
    ) -> dict:

        if not isinstance(data, dict):
            raise ProviderResponseError(
                f"{provider} returned an invalid response."
            )

        if not isinstance(data.get("data"), dict):
            raise ProviderResponseError(
                f"{provider} returned an invalid data payload."
            )

        return data
    
    @staticmethod
    def _validate_candle(
        candle,
    ) -> bool:

        if not isinstance(candle, list):
            return False

        if len(candle) < 7:
            return False

        return True
    
    
    def get_stock(
    self,
    ticker: str,
    market: Market = Market.INDIA,
    ) -> dict:

        if market != Market.INDIA:
            raise ValueError(
                "UpstoxProvider currently supports India only."
            )

        ticker = ticker.upper()

        instrument_key = self.instrument_resolver.resolve_nse_equity(ticker)

        data = self._get(
            "market-quote/ltp",
            {
                "instrument_key": instrument_key,
            },
        )

        data = self._validate_dict_response(data)

        quote = data["data"].get(
            f"NSE_EQ:{ticker}"
        )
        
        if quote is None:
            raise ValueError(
                f"No market data found for {ticker}."
            )
                    

        if not isinstance(quote, dict):
            raise ProviderResponseError(
                f"Upstox returned invalid market data for {ticker}."
            )

        required_fields = (
            "instrument_token",
            "last_price",
            "ltq",
            "volume",
            "cp",
        )

        if not all(
            field in quote
            for field in required_fields
        ):
            raise ProviderResponseError(
                f"Upstox returned incomplete market data for {ticker}."
            )    

        return {
            "ticker": ticker,
            "instrument_key": quote["instrument_token"],
            "last_price": quote["last_price"],
            "last_traded_quantity": quote["ltq"],
            "volume": quote["volume"],
            "previous_close": quote["cp"],
        }
        
    def get_historical(
    self,
    ticker: str,
    to_date: str,
    from_date: str | None = None,
    market: Market = Market.INDIA,
    ) -> HistoricalMarketData:

        if market != Market.INDIA:
            raise ValueError(
                "UpstoxProvider currently supports India only."
            )

        ticker = ticker.upper()

        instrument_key = self.instrument_resolver.resolve_nse_equity(
            ticker
        )

        endpoint = (
            f"historical-candle/"
            f"{instrument_key}/"
            f"days/1/"
            f"{to_date}"
        )

        if from_date:
            endpoint = f"{endpoint}/{from_date}"

        data = self._get(
            endpoint,
            {},
        )

        data = self._validate_dict_response(data)

        candles = data["data"].get("candles", [])

        if not isinstance(candles, list):
            raise ProviderResponseError(
                f"Upstox returned invalid historical data for {ticker}."
            )

        for candle in candles:
            if not self._validate_candle(candle):
                raise ProviderResponseError(
                    f"Upstox returned malformed historical data for {ticker}."
                )

        return HistoricalMarketData(
            ticker=ticker,
            candles=[
                HistoricalCandle(
                    timestamp=candle[0],
                    open=candle[1],
                    high=candle[2],
                    low=candle[3],
                    close=candle[4],
                    volume=candle[5],
                    open_interest=candle[6],
                )
                for candle in candles
            ],
        )
        
    def get_news(self, ticker: str, market: Market = Market.INDIA, limit: int = 10) -> NewsResearch:

        if market != Market.INDIA:
            raise ValueError(
                "UpstoxProvider currently supports India only."
            )

        ticker = ticker.upper()

        instrument_key = self.instrument_resolver.resolve_nse_equity(ticker)

        data = self._get(
            "news",
            {
                "category": "instrument_keys",
                "instrument_keys": instrument_key,
                "page_number": 1,
                "page_size": limit,
            },
            base_url=self.NEWS_BASE_URL,
        )

        data = self._validate_dict_response(data)

        raw_articles = data["data"].get(
            instrument_key,
            [],
        )

        if not isinstance(raw_articles, list):
            raise ProviderResponseError(
                f"Upstox returned invalid news data for {ticker}."
            )

        articles: list[NewsArticle] = []

        for item in raw_articles:

            if not isinstance(item, dict):
                raise ProviderResponseError(
                    f"Upstox returned malformed news data for {ticker}."
                )

            published_time = item.get("published_time")

            if published_time is not None:
                if not isinstance(
                    published_time,
                    (int, float),
                ):
                    raise ProviderResponseError(
                        f"Upstox returned invalid publication time for {ticker}."
                    )

                try:
                    published_at = datetime.fromtimestamp(
                        published_time / 1000,
                        tz=timezone.utc,
                    ).isoformat()
                except (OverflowError, OSError, ValueError):
                    raise ProviderResponseError(
                        f"Upstox returned invalid publication time for {ticker}."
                    )
            else:
                published_at = None

            articles.append(
                NewsArticle(
                    title=item.get("heading", ""),
                    summary=item.get("summary"),
                    url=item.get("article_link", ""),
                    source="upstox.com",
                    published_at=published_at,
                    image_url=item.get("thumbnail"),
                    relevance_score=None,
                    target_match_score=None,
                    relevance_type=None,
                    entities=None,
                )
            )

        return NewsResearch(
            ticker=ticker,
            articles=articles,
        )