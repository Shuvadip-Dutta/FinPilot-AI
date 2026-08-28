from unittest.mock import patch

from django.test import SimpleTestCase

from apps.research.services.news_aggregator import NewsAggregator
from apps.research.services.schemas import (
    NewsArticle,
    NewsResearch,
)
from apps.research.services.symbols import Market


class NewsAggregatorTestCase(SimpleTestCase):

    @patch(
        "apps.research.services.news_aggregator.UpstoxProvider"
    )
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
        mock_upstox_provider,
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

        upstox_article = NewsArticle(
            title="Reliance Upstox News",
            summary="Upstox article",
            url="https://example.com/upstox",
            source="upstox.com",
            published_at="2026-08-28T11:00:00Z",
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

        mock_upstox_provider.return_value.get_news.return_value = (
            NewsResearch(
                ticker="RELIANCE",
                articles=[upstox_article],
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
            3,
        )

        self.assertEqual(
            result.articles[0].title,
            "Reliance Upstox News",
        )

        self.assertEqual(
            result.articles[1].title,
            "Reliance Marketaux News",
        )

        self.assertEqual(
            result.articles[2].title,
            "Reliance Indian News",
        )

    @patch(
        "apps.research.services.news_aggregator.UpstoxProvider"
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
        mock_upstox_provider,
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

        upstox_article = NewsArticle(
            title="Upstox version",
            summary="Third version",
            url=duplicate_url,
            source="livemint.com",
            published_at="2026-08-29T10:00:00Z",
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

        mock_upstox_provider.return_value.get_news.return_value = (
            NewsResearch(
                ticker="RELIANCE",
                articles=[upstox_article],
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

        self.assertEqual(
            result.articles[0].title,
            "Indian API version",
        )