from django.test import SimpleTestCase
from unittest.mock import patch

from apps.research.services.news_aggregator import NewsAggregator
from apps.research.services.schemas import (
    NewsArticle,
    NewsResearch,
)
from apps.research.services.symbols import Market

class NewsAggregatorTestCase(SimpleTestCase):

    @patch(
        "apps.research.services.news_aggregator.MarketauxProvider"
    )
    @patch(
        "apps.research.services.news_aggregator.IndianAPIProvider"
    )
    def test_combines_news(
        self,
        mock_indian_provider,
        mock_marketaux_provider,
    ):

        indian_article = NewsArticle(
            title="Reliance Indian News",
            summary="Indian API article",
            url="https://example.com/indian",
            source="livemint.com",
            published_at="2026-08-27T10:00:00Z",
        )

        marketaux_article = NewsArticle(
            title="Reliance Marketaux News",
            summary="Marketaux article",
            url="https://example.com/marketaux",
            source="example.com",
            published_at="2026-08-28T10:00:00Z",
        )

        mock_indian_provider.return_value.get_news.return_value = (
            NewsResearch(
                ticker="RELIANCE",
                articles=[indian_article],
            )
        )

        mock_marketaux_provider.return_value.get_news.return_value = (
            NewsResearch(
                ticker="RELIANCE",
                articles=[marketaux_article],
            )
        )

        aggregator = NewsAggregator()

        result = aggregator.get_news(
            "RELIANCE",
            Market.INDIA,
        )

        self.assertEqual(
            result.ticker,
            "RELIANCE",
        )

        self.assertEqual(
            len(result.articles),
            2,
        )

        self.assertEqual(
            result.articles[0].title,
            "Reliance Marketaux News",
        )

    @patch(
        "apps.research.services.news_aggregator.MarketauxProvider"
    )
    @patch(
        "apps.research.services.news_aggregator.IndianAPIProvider"
    )
    def test_deduplicates_by_url(
        self,
        mock_indian_provider,
        mock_marketaux_provider,
    ):

        duplicate_url = "https://example.com/reliance"

        indian_article = NewsArticle(
            title="Indian API version",
            summary="First version",
            url=duplicate_url,
            source="livemint.com",
            published_at="2026-08-27T10:00:00Z",
        )

        marketaux_article = NewsArticle(
            title="Marketaux version",
            summary="Second version",
            url=duplicate_url,
            source="livemint.com",
            published_at="2026-08-28T10:00:00Z",
        )

        mock_indian_provider.return_value.get_news.return_value = (
            NewsResearch(
                ticker="RELIANCE",
                articles=[indian_article],
            )
        )

        mock_marketaux_provider.return_value.get_news.return_value = (
            NewsResearch(
                ticker="RELIANCE",
                articles=[marketaux_article],
            )
        )

        aggregator = NewsAggregator()

        result = aggregator.get_news(
            "RELIANCE",
            Market.INDIA,
        )

        self.assertEqual(
            len(result.articles),
            1,
        )