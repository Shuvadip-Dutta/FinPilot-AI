from unittest.mock import patch

from django.test import SimpleTestCase
from requests import RequestException

from apps.research.services.providers.upstox import (
    UpstoxProvider,
)

from apps.research.services.symbols import Market
from datetime import datetime

class UpstoxProviderTestCase(SimpleTestCase):

    @patch(
        "apps.research.services.providers.upstox.UpstoxProvider._get"
    )
    def test_get_stock(self, mock_get):

        mock_get.return_value = {
            "status": "success",
            "data": {
                "NSE_EQ:RELIANCE": {
                    "last_price": 1287.0,
                    "instrument_token": (
                        "NSE_EQ|INE002A01018"
                    ),
                    "ltq": 200,
                    "volume": 6830228,
                    "cp": 1282.2,
                }
            },
        }

        provider = UpstoxProvider()

        result = provider.get_stock(
            "RELIANCE",
            Market.INDIA,
        )

        self.assertEqual(
            result["ticker"],
            "RELIANCE",
        )

        self.assertEqual(
            result["instrument_key"],
            "NSE_EQ|INE002A01018",
        )

        self.assertEqual(
            result["last_price"],
            1287.0,
        )

        self.assertEqual(
            result["last_traded_quantity"],
            200,
        )

        self.assertEqual(
            result["volume"],
            6830228,
        )

        self.assertEqual(
            result["previous_close"],
            1282.2,
        )

    @patch(
        "apps.research.services.providers.upstox.UpstoxProvider._get"
    )
    def test_api_failure(self, mock_get):

        mock_get.side_effect = RequestException(
            "Upstox unavailable"
        )

        provider = UpstoxProvider()

        with self.assertRaises(RequestException):
            provider.get_stock(
                "RELIANCE",
                Market.INDIA,
            )

    def test_unsupported_market(self):

        provider = UpstoxProvider()

        with self.assertRaises(ValueError) as context:
            provider.get_stock(
                "RELIANCE",
                Market.US,
            )

        self.assertEqual(
            str(context.exception),
            "UpstoxProvider currently supports India only.",
        )

    def test_unsupported_ticker(self):

        provider = UpstoxProvider()

        with self.assertRaises(ValueError) as context:
            provider.get_stock(
                "UNKNOWN",
                Market.INDIA,
            )

        self.assertEqual(
            str(context.exception),
            "Unsupported Upstox ticker: UNKNOWN",
        )

    @patch(
        "apps.research.services.providers.upstox.UpstoxProvider._get"
    )
    def test_missing_quote(self, mock_get):

        mock_get.return_value = {
            "status": "success",
            "data": {},
        }

        provider = UpstoxProvider()

        with self.assertRaises(ValueError) as context:
            provider.get_stock(
                "RELIANCE",
                Market.INDIA,
            )

        self.assertEqual(
            str(context.exception),
            "No market data found for RELIANCE.",
        )
        
    @patch(
    "apps.research.services.providers.upstox.UpstoxProvider._get"
    )
    def test_get_historical(self, mock_get):

        mock_get.return_value = {
            "status": "success",
            "data": {
                "candles": [
                    [
                        "2026-08-28T00:00:00+05:30",
                        1282.2,
                        1295.0,
                        1278.5,
                        1287.0,
                        6830228,
                        0,
                    ],
                    [
                        "2026-08-27T00:00:00+05:30",
                        1275.0,
                        1288.0,
                        1269.5,
                        1282.2,
                        7200000,
                        0,
                    ],
                ]
            },
        }

        provider = UpstoxProvider()

        result = provider.get_historical(
            "RELIANCE",
            to_date="2026-08-28",
            from_date="2026-08-27",
            market=Market.INDIA,
        )

        self.assertEqual(
            result.ticker,
            "RELIANCE",
        )

        self.assertEqual(
            len(result.candles),
            2,
        )

        candle = result.candles[0]

        self.assertEqual(
            candle.open,
            1282.2,
        )

        self.assertEqual(
            candle.high,
            1295.0,
        )

        self.assertEqual(
            candle.low,
            1278.5,
        )

        self.assertEqual(
            candle.close,
            1287.0,
        )

        self.assertEqual(
            candle.volume,
            6830228,
        )
        
    @patch(
    "apps.research.services.providers.upstox.UpstoxProvider._get"
    )
    def test_get_historical_empty(self, mock_get):

        mock_get.return_value = {
            "status": "success",
            "data": {
                "candles": [],
            },
        }

        provider = UpstoxProvider()

        result = provider.get_historical(
            "RELIANCE",
            to_date="2026-08-28",
            market=Market.INDIA,
        )

        self.assertEqual(
            result.candles,
            [],
        )
        
    @patch(
    "apps.research.services.providers.upstox.UpstoxProvider._get"
    )
    def test_get_news(self, mock_get):

        mock_get.return_value = {
            "status": "success",
            "data": {
                "NSE_EQ|INE002A01018": [
                    {
                        "heading": "Reliance market update",
                        "summary": "Reliance related market news.",
                        "thumbnail": "https://example.com/image.jpg",
                        "article_link": (
                            "https://upstox.com/news/reliance"
                        ),
                        "published_time": 1787740313933,
                    }
                ]
            },
            "metadata": {
                "page": {
                    "page_number": 1,
                    "page_size": 3,
                    "total_records": 1,
                    "total_pages": 1,
                }
            },
        }

        provider = UpstoxProvider()

        result = provider.get_news(
            "RELIANCE",
            Market.INDIA,
            limit=3,
        )

        self.assertEqual(
            result.ticker,
            "RELIANCE",
        )

        self.assertEqual(
            len(result.articles),
            1,
        )

        article = result.articles[0]

        self.assertEqual(
            article.title,
            "Reliance market update",
        )

        self.assertEqual(
            article.summary,
            "Reliance related market news.",
        )

        self.assertEqual(
            article.url,
            "https://upstox.com/news/reliance",
        )

        self.assertEqual(
            article.source,
            "upstox.com",
        )

        self.assertEqual(
            article.image_url,
            "https://example.com/image.jpg",
        )

        self.assertIsNotNone(
            article.published_at,
        )
        
        
    @patch(
    "apps.research.services.providers.upstox.UpstoxProvider._get"
    )
    def test_get_news_empty(self, mock_get):

        mock_get.return_value = {
            "status": "success",
            "data": {},
        }

        provider = UpstoxProvider()

        result = provider.get_news(
            "RELIANCE",
            Market.INDIA,
        )

        self.assertEqual(
            result.ticker,
            "RELIANCE",
        )

        self.assertEqual(
            result.articles,
            [],
        )
        
    @patch(
    "apps.research.services.providers.upstox.UpstoxProvider._get"
    )
    def test_get_news_api_failure(self, mock_get):

        mock_get.side_effect = RequestException(
            "Upstox news unavailable"
        )

        provider = UpstoxProvider()

        with self.assertRaises(RequestException):
            provider.get_news(
                "RELIANCE",
                Market.INDIA,
            )
            
    def test_get_news_unsupported_ticker(self):

        provider = UpstoxProvider()

        with self.assertRaises(ValueError) as context:
            provider.get_news(
                "UNKNOWN",
                Market.INDIA,
            )

        self.assertEqual(
            str(context.exception),
            "Unsupported Upstox ticker: UNKNOWN",
        )
    