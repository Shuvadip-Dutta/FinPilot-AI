from apps.research.services.research_service import ResearchService
from apps.research.services.schemas import ExchangeQuote
from apps.research.services.symbols import Market


def _extract_provenance(result) -> dict:
    if result is None:
        return {}

    prov = getattr(result, "_provenance", None) or getattr(result, "provenance", None)

    if not prov and isinstance(result, list):
        prov = getattr(result, "_provenance", None) or getattr(result, "provenance", None)
        if not prov and len(result) > 0:
            prov = getattr(result[0], "_provenance", None) or getattr(result[0], "provenance", None)

    if not prov and isinstance(result, dict):
        if "primary_provider" in result or "source" in result or "fallback_used" in result:
            prov_dict = {
                "primary_provider": result.get("primary_provider"),
                "source": result.get("source") or result.get("provider_used"),
                "provider_used": result.get("provider_used") or result.get("source"),
                "fallback_used": result.get("fallback_used", False),
                "data_status": result.get("data_status", "complete"),
                "fallback_reason": result.get("fallback_reason"),
            }
            return prov_dict

    if not prov:
        return {}

    if isinstance(prov, dict):
        prov_dict = dict(prov)
    else:
        prov_dict = {
            "primary_provider": getattr(prov, "primary_provider", None),
            "source": getattr(prov, "source", None),
            "provider_used": getattr(prov, "source", None),
            "fallback_used": getattr(prov, "fallback_used", False),
            "data_status": getattr(prov, "data_status", "complete"),
            "fallback_reason": getattr(prov, "fallback_reason", None),
        }

    if hasattr(prov_dict.get("data_status"), "value"):
        prov_dict["data_status"] = prov_dict["data_status"].value

    return prov_dict


def get_company_profile(
    ticker: str,
    market: str,
) -> dict:

    service = ResearchService()

    profile = service.get_company_profile(
        ticker=ticker,
        market=Market(market.upper()),
    )

    prov = _extract_provenance(profile)

    if isinstance(profile, dict):
        res = dict(profile)
    elif profile is not None:
        res = {
            "ticker": getattr(profile, "ticker", ticker.upper()),
            "name": getattr(profile, "name", None),
            "exchange": getattr(profile, "exchange", None),
            "country": getattr(profile, "country", None),
            "sector": getattr(profile, "sector", None),
            "industry": getattr(profile, "industry", None),
            "description": getattr(profile, "description", None),
            "isin": getattr(profile, "isin", None),
            "nse_symbol": getattr(profile, "nse_symbol", None),
            "bse_code": getattr(profile, "bse_code", None),
        }
    else:
        res = {
            "ticker": ticker.upper(),
            "market": market.upper(),
        }

    if prov:
        res.update(prov)
        res["provenance"] = prov

    return res


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

    prov = _extract_provenance(result)

    res = {
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

    if prov:
        res.update(prov)
        res["provenance"] = prov

    return res


def get_financials(
    ticker: str,
    market: str,
) -> dict:

    service = ResearchService()

    result = service.get_financials(
        ticker=ticker,
        market=Market(market.upper()),
    )

    prov = _extract_provenance(result)

    res = {
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

    if prov:
        res.update(prov)
        res["provenance"] = prov

    return res


def get_key_metrics(
    ticker: str,
    market: str,
) -> dict:

    service = ResearchService()

    result = service.get_key_metrics(
        ticker=ticker,
        market=Market(market.upper()),
    )

    prov = _extract_provenance(result)

    res = {
        "ticker": getattr(result, "ticker", ticker.upper()),
        "market": market.upper(),
        "metrics": [
            {
                "category": metric.category,
                "name": metric.name,
                "key": metric.key,
                "value": metric.value,
                "raw_value": metric.raw_value,
            }
            for metric in (getattr(result, "metrics", []) or [])
        ],
    }

    if prov:
        res.update(prov)
        res["provenance"] = prov

    return res


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

    prov = _extract_provenance(result)

    res = {
        "ticker": getattr(result, "ticker", ticker.upper()),
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
            for candle in (getattr(result, "candles", []) or [])
        ],
    }

    if prov:
        res.update(prov)
        res["provenance"] = prov

    return res


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

    prov = _extract_provenance(result)

    res = {
        "ticker": getattr(result, "ticker", ticker.upper()),
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
            for article in (getattr(result, "articles", []) or [])[:limit]
        ],
    }

    if prov:
        res.update(prov)
        res["provenance"] = prov

    return res