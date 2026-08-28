from apps.research.services.providers.indian_api import IndianAPIProvider
from apps.research.services.providers.marketaux import MarketauxProvider
from apps.research.services.providers.upstox import UpstoxProvider
from apps.research.services.schemas import (
    NewsArticle,
    NewsResearch,
)
from apps.research.services.symbols import Market


class NewsAggregator:

    def __init__(self):
        self.indian_api = IndianAPIProvider()
        self.marketaux = MarketauxProvider()
        self.upstox = UpstoxProvider()

    def get_news(
        self,
        ticker: str,
        market: Market,
        limit: int = 10,
    ) -> NewsResearch:

        if market != Market.INDIA:
            raise ValueError(
                "NewsAggregator currently supports India only."
            )

        ticker = ticker.upper()

        indian_news = self.indian_api.get_news(
            ticker,
            market,
        )

        marketaux_news = self.marketaux.get_news(
            ticker,
            market,
            limit=limit,
        )
        
        upstox_news = self.upstox.get_news(
            ticker,
            market,
            limit=limit,
        )

        articles = (
            indian_news.articles
            + marketaux_news.articles
            + upstox_news.articles
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