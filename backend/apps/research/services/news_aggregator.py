from apps.research.services.providers.indian_api import IndianAPIProvider
from apps.research.services.providers.marketaux import MarketauxProvider
from apps.research.services.providers.upstox import UpstoxProvider
from apps.research.services.schemas import (
    NewsArticle,
    NewsResearch,
)
from apps.research.services.symbols import Market
import logging

from requests import RequestException

logger = logging.getLogger("finpilot")

class NewsAggregator:

    def __init__(self):
        self.indian_api = IndianAPIProvider()
        self.marketaux = MarketauxProvider()
        self.upstox = UpstoxProvider()

    def get_news(self, ticker: str, market: Market, limit: int = 10) -> NewsResearch:

        if market != Market.INDIA:
            raise ValueError(
                "NewsAggregator currently supports India only."
            )

        ticker = ticker.upper()

        articles: list[NewsArticle] = []

        providers = [
            (
                "Indian API",
                lambda: self.indian_api.get_news(
                    ticker,
                    market,
                ),
            ),
            (
                "Marketaux",
                lambda: self.marketaux.get_news(
                    ticker,
                    market,
                    limit=limit,
                ),
            ),
            (
                "Upstox",
                lambda: self.upstox.get_news(
                    ticker,
                    market,
                    limit=limit,
                ),
            ),
        ]

        for provider_name, fetch_news in providers:
            try:
                result = fetch_news()
                articles.extend(result.articles)

            except RequestException:
                logger.exception(
                    "%s news provider unavailable for %s",
                    provider_name,
                    ticker,
                )

            except ValueError:
                logger.exception(
                    "%s returned invalid news data for %s",
                    provider_name,
                    ticker,
                )

        articles = self._deduplicate(articles)

        articles.sort(
            key=lambda article: article.published_at or "",
            reverse=True,
        )

        return NewsResearch(
            ticker=ticker,
            articles=articles,
        )

    @staticmethod
    def _deduplicate(
        articles: list[NewsArticle],
    ) -> list[NewsArticle]:

        seen_urls: set[str] = set()
        unique_articles: list[NewsArticle] = []

        for article in articles:

            if not article.url:
                unique_articles.append(article)
                continue

            if article.url in seen_urls:
                continue

            seen_urls.add(article.url)
            unique_articles.append(article)

        return unique_articles