from apps.research.services.research_service import ResearchService
from apps.research.services.schemas import ExchangeQuote
from apps.research.services.symbols import Market


def get_company_profile(
    ticker: str,
    market: str,
) -> dict:

    service = ResearchService()

    return service.get_company_profile(
        ticker=ticker,
        market=Market(market.upper()),
    )


def get_market_data(
    ticker: str,
    market: str,
) -> dict:

    service = ResearchService()

    result = service.get_market_data(
        ticker=ticker,
        market=Market(market.upper()),
    )

    if not isinstance(result, list) or not all(
        isinstance(quote, ExchangeQuote) for quote in result
    ):
        raise TypeError(
            "ResearchService.get_market_data returned an unexpected result."
        )

    return {
        "ticker": ticker.upper(),
        "market": market.upper(),
        "quotes": [
            {
                "exchange": quote.exchange,
                "price": quote.price,
                "percent_change": quote.percent_change,
                "year_high": quote.year_high,
                "year_low": quote.year_low,
            }
            for quote in result
        ],
    }


def get_financials(
    ticker: str,
    market: str,
) -> dict:

    service = ResearchService()

    result = service.get_financials(
        ticker=ticker,
        market=Market(market.upper()),
    )

    return {
        "ticker": ticker.upper(),
        "market": market.upper(),
        "financials": [
            {
                "statement_type": statement.statement_type,
                "fiscal_year": statement.fiscal_year,
                "end_date": statement.end_date,
                "period_type": statement.period_type,
                "period_length": statement.period_length,
                "metrics": [
                    {
                        "name": metric.name,
                        "key": metric.key,
                        "value": metric.value,
                    }
                    for metric in statement.metrics
                ],
            }
            for statement in result
        ],
    }


def get_key_metrics(
    ticker: str,
    market: str,
) -> dict:

    service = ResearchService()

    result = service.get_key_metrics(
        ticker=ticker,
        market=Market(market.upper()),
    )

    return {
        "ticker": result.ticker,
        "market": market.upper(),
        "metrics": [
            {
                "category": metric.category,
                "name": metric.name,
                "key": metric.key,
                "value": metric.value,
                "raw_value": metric.raw_value,
            }
            for metric in result.metrics
        ],
    }


def get_historical_data(
    ticker: str,
    to_date: str,
    from_date: str | None = None,
    market: str = "IN",
) -> dict:

    service = ResearchService()

    result = service.get_historical_data(
        ticker=ticker,
        to_date=to_date,
        from_date=from_date,
        market=Market(market.upper()),
    )

    return {
        "ticker": result.ticker,
        "market": market.upper(),
        "candles": [
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
                "open_interest": candle.open_interest,
            }
            for candle in result.candles
        ],
    }


def get_news(
    ticker: str,
    market: str = "IN",
    limit: int = 10,
) -> dict:

    service = ResearchService()

    result = service.get_news(
        ticker=ticker,
        market=Market(market.upper()),
    )

    return {
        "ticker": result.ticker,
        "market": market.upper(),
        "articles": [
            {
                "title": article.title,
                "summary": article.summary,
                "url": article.url,
                "source": article.source,
                "published_at": article.published_at,
                "image_url": article.image_url,
                "relevance_score": article.relevance_score,
                "target_match_score": article.target_match_score,
                "relevance_type": article.relevance_type,
                "entities": [
                    {
                        "symbol": entity.symbol,
                        "name": entity.name,
                        "country": entity.country,
                        "entity_type": entity.entity_type,
                        "match_score": entity.match_score,
                        "sentiment_score": entity.sentiment_score,
                    }
                    for entity in article.entities or []
                ],
            }
            for article in result.articles[:limit]
        ],
    }