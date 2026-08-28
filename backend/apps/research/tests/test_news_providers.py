from unittest.mock import patch

from django.test import SimpleTestCase

from apps.research.services.providers.indian_api import IndianAPIProvider
from apps.research.services.providers.marketaux import MarketauxProvider
from apps.research.services.schemas import NewsArticle
from apps.research.services.symbols import Market

from requests import RequestException
class IndianAPINewsProviderTestCase(SimpleTestCase):

    @patch(
        "apps.research.services.providers.indian_api.IndianAPIProvider.get_stock"
    )
    def test_get_news(self, mock_get_stock):

        mock_get_stock.return_value = {
            "recentNews": [
                {
                    "headline": "Reliance announces new investment",
                    "summary": "Reliance plans a major investment.",
                    "url": "/companies/news/reliance-investment.html",
                    "lastPublishedDate": "2026-08-27T10:00:00+0000",
                    "thumbnailImage": "https://example.com/image.jpg",
                }
            ]
        }

        provider = IndianAPIProvider()

        result = provider.get_news(
            "RELIANCE",
            Market.INDIA,
        )

        self.assertEqual(result.ticker, "RELIANCE")
        self.assertEqual(len(result.articles), 1)

        article = result.articles[0]

        self.assertIsInstance(article, NewsArticle)
        self.assertEqual(
            article.title,
            "Reliance announces new investment",
        )
        self.assertEqual(
            article.source,
            "livemint.com",
        )
        self.assertEqual(
            article.url,
            "https://www.livemint.com/companies/news/reliance-investment.html",
        )
        
    @patch(
        "apps.research.services.providers.indian_api.IndianAPIProvider.get_stock"
    )
    def test_missing_recent_news(self, mock_get_stock):

        mock_get_stock.return_value = {}

        provider = IndianAPIProvider()

        result = provider.get_news(
            "RELIANCE",
            Market.INDIA,
        )

        self.assertEqual(result.ticker, "RELIANCE")
        self.assertEqual(result.articles, [])
        
class MarketauxNewsProviderTestCase(SimpleTestCase):

    @patch(
        "apps.research.services.providers.marketaux.MarketauxProvider._get"
    )
    def test_get_news(self, mock_get):

        mock_get.return_value = {
            "data": [
                {
                    "title": "Reliance reports strong results",
                    "description": "Reliance reported strong financial results.",
                    "url": "https://example.com/reliance",
                    "source": "example.com",
                    "published_at": "2026-08-27T10:00:00.000000Z",
                    "image_url": "https://example.com/image.jpg",
                    "relevance_score": 85.5,
                    "entities": [
                        {
                            "symbol": "RELIANCE.NS",
                            "name": "Reliance Industries Limited",
                            "country": "in",
                            "type": "equity",
                            "match_score": 90.0,
                            "sentiment_score": 0.65,
                        }
                    ],
                }
            ]
        }

        provider = MarketauxProvider()

        result = provider.get_news(
            "RELIANCE",
            Market.INDIA,
            limit=3,
        )

        self.assertEqual(result.ticker, "RELIANCE")
        self.assertEqual(len(result.articles), 1)

        article = result.articles[0]

        self.assertEqual(
            article.title,
            "Reliance reports strong results",
        )

        self.assertEqual(
            article.source,
            "example.com",
        )

        self.assertEqual(
            len(article.entities),
            1,
        )

        self.assertEqual(
            article.entities[0].symbol,
            "RELIANCE.NS",
        )

        self.assertEqual(
            article.entities[0].sentiment_score,
            0.65,
        )
        self.assertEqual(
            article.target_match_score,
            90.0,
        )

        self.assertEqual(
            article.relevance_type,
            "DIRECT",
        )
        
    @patch(
        "apps.research.services.providers.marketaux.MarketauxProvider._get"
    )
    def test_marketaux_api_failure(self, mock_get):

        mock_get.side_effect = RequestException(
            "Marketaux unavailable"
        )

        provider = MarketauxProvider()

        with self.assertRaises(RequestException):
            provider.get_news(
                "RELIANCE",
                Market.INDIA,
            )
    
    @patch(
        "apps.research.services.providers.marketaux.MarketauxProvider._get"
    )
    def test_marketaux_empty_news(self, mock_get):

        mock_get.return_value = {
            "data": []
        }

        provider = MarketauxProvider()

        result = provider.get_news(
            "RELIANCE",
            Market.INDIA,
        )

        self.assertEqual(result.ticker, "RELIANCE")
        self.assertEqual(result.articles, [])
        
    @patch(
    "apps.research.services.providers.marketaux.MarketauxProvider._get"
    )
    def test_marketaux_market_context(
        self,
        mock_get,
    ):

        mock_get.return_value = {
            "data": [
                {
                    "title": "Indian market update",
                    "description": "Broader market news mentioning Reliance.",
                    "url": "https://example.com/market",
                    "source": "example.com",
                    "published_at": "2026-08-27T10:00:00.000000Z",
                    "image_url": None,
                    "relevance_score": None,
                    "entities": [
                        {
                            "symbol": "RELIANCE.NS",
                            "name": "Reliance Industries Limited",
                            "country": "in",
                            "type": "equity",
                            "match_score": 17.0,
                            "sentiment_score": 0.2,
                        }
                    ],
                }
            ]
        }

        provider = MarketauxProvider()

        result = provider.get_news(
            "RELIANCE",
            Market.INDIA,
            limit=3,
        )

        self.assertEqual(
            len(result.articles),
            1,
        )

        article = result.articles[0]

        self.assertEqual(
            article.target_match_score,
            17.0,
        )

        self.assertEqual(
            article.relevance_type,
            "MARKET_CONTEXT",
        )