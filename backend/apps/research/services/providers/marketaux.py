import os
from typing import Any

import requests
from dotenv import load_dotenv

from apps.research.services.schemas import (
    NewsArticle,
    NewsEntity,
    NewsResearch,
)
from apps.research.services.symbols import Market

load_dotenv()


def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class MarketauxProvider:

    BASE_URL = "https://api.marketaux.com/v1"

    def __init__(self) -> None:
        self.api_token = os.getenv("MARKETAUX_API_TOKEN")

        if not self.api_token:
            raise ValueError(
                "MARKETAUX_API_TOKEN is not configured."
            )

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:

        params = {
            **params,
            "api_token": self.api_token,
        }

        response = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            params=params,
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise RuntimeError(
                "Marketaux returned an unexpected response."
            )

        return data

    def _parse_entity(
        self,
        entity: dict[str, Any],
    ) -> NewsEntity:

        return NewsEntity(
            symbol=entity.get("symbol", ""),
            name=entity.get("name", ""),
            country=entity.get("country"),
            entity_type=entity.get("type"),
            match_score=_to_float(
                entity.get("match_score")
            ),
            sentiment_score=_to_float(
                entity.get("sentiment_score")
            ),
        )

    def _parse_article(self, article: dict[str, Any], target_symbol: str) -> NewsArticle:

        entities = [
            self._parse_entity(entity)
            for entity in (article.get("entities") or [])
        ]

        target_match_score = None

        for entity in entities:
            if entity.symbol == target_symbol:
                target_match_score = entity.match_score
                break

        return NewsArticle(
            title=article.get("title", ""),
            summary=article.get("description"),
            url=article.get("url", ""),
            source=article.get("source", ""),
            published_at=article.get("published_at"),
            image_url=article.get("image_url"),
            relevance_score=_to_float(
                article.get("relevance_score")
            ),
            target_match_score=target_match_score,
            relevance_type=None,
            entities=entities,
        )
    
    def _article_matches_symbol(self, article: NewsArticle, symbol: str) -> bool:

        for entity in article.entities or []:
            if entity.symbol == symbol:
                return True

        return False
    
    @staticmethod
    def _classify_relevance(
        article: NewsArticle,
    ) -> str:

        score = article.target_match_score

        if score is None:
            return "MARKET_CONTEXT"

        if score >= 30:
            return "DIRECT"

        if score >= 20:
            return "RELATED"

        return "MARKET_CONTEXT"

    def get_news(self, ticker: str, market: Market = Market.INDIA, limit: int = 3) -> NewsResearch:

        if market != Market.INDIA:
            raise ValueError(
                "MarketauxProvider currently supports India only."
            )

        symbol = f"{ticker.upper()}.NS"

        data = self._get(
            "news/all",
            {
                "symbols": symbol,
                "limit": limit,
            },
        )

        articles = [
            self._parse_article(
                article,
                symbol,
            )
            for article in (data.get("data") or [])
        ]

        articles = [
            article
            for article in articles
            if self._article_matches_symbol(
                article,
                symbol,
            )
        ]

        for article in articles:
            article.relevance_type = (
                self._classify_relevance(article)
            )

        return NewsResearch(
            ticker=ticker.upper(),
            articles=articles,
        )