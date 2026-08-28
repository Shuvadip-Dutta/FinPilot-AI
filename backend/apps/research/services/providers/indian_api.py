import os
from typing import Any

import requests
from dotenv import load_dotenv

from apps.research.services.schemas import CompanyProfile, ExchangeQuote, FinancialMetric,FinancialStatement, KeyMetric,KeyMetricsResearch, NewsArticle, NewsResearch
from apps.research.services.symbols import Market

load_dotenv()


def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_financial_section(items: list[dict[str, Any]] | None) -> tuple[list[FinancialMetric], str | None, int | None]:
    if not items:
        return [], None, None
    metrics: list[FinancialMetric] = []

    period_type = None
    period_length = None

    for item in items:
        key = item.get("key", "")
        value = item.get("value")

        if key == "periodType":
            period_type = value
            continue

        if key == "periodLength":
            try:
                parsed_length = int(float(value))
                period_length = parsed_length if parsed_length > 0 else None
            except (TypeError, ValueError):
                period_length = None
            continue

        metrics.append(
            FinancialMetric(
                name=item.get(
                    "displayName",
                    "",
                ).strip(),
                key=key,
                value=_to_float(value),
            )
        )

    return metrics, period_type, period_length

def _parse_key_metric_value(value: Any) -> tuple[float | None, str | None]:
    if value is None:
        return None, None

    raw_value = str(value)

    try:
        return float(value), raw_value
    except (TypeError, ValueError):
        return None, raw_value

def _parse_key_metrics(data: dict[str, Any]) -> list[KeyMetric]:

        metrics: list[KeyMetric] = []

        for category, items in data.items():

            if not items:
                continue

            for item in items:

                value, raw_value = _parse_key_metric_value(
                    item.get("value")
                )

                metrics.append(
                    KeyMetric(
                        category=category,
                        name=item.get(
                            "displayName",
                            "",
                        ).strip(),
                        key=item.get(
                            "key",
                            "",
                        ),
                        value=value,
                        raw_value=raw_value,
                    )
                )

        return metrics


class IndianAPIProvider:

    BASE_URL = "https://stock.indianapi.in"

    def __init__(self) -> None:
        self.api_key = os.getenv("INDIAN_STOCK_MARKET_API_KEY")

        if not self.api_key:
            raise ValueError(
                "INDIAN_STOCK_MARKET_API_KEY is not configured."
            )

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:

        response = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            params=params,
            headers={
                "X-API-Key": self.api_key,
            },
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise RuntimeError(
                "Indian Stock Market API returned an unexpected response."
            )

        return data

    def get_stock(
        self,
        ticker: str,
        market: Market = Market.INDIA,
    ) -> dict[str, Any]:

        if market != Market.INDIA:
            raise ValueError(
                "IndianAPIProvider currently supports India only."
            )

        return self._get(
            "stock",
            {
                "name": ticker.upper(),
            },
        )

    def get_company_profile(
        self,
        ticker: str,
        market: Market = Market.INDIA,
    ) -> CompanyProfile:

        data = self.get_stock(ticker, market)

        profile = data.get("companyProfile") or {}

        return CompanyProfile(
            ticker=ticker.upper(),
            name=data.get("companyName", ""),
            exchange="NSE/BSE",
            country="India",
            sector=None,
            industry=(
                profile.get("mgIndustry")
                or data.get("industry")
            ),
            description=profile.get("companyDescription"),
            isin=profile.get("isInId"),
            nse_symbol=profile.get("exchangeCodeNse"),
            bse_code=profile.get("exchangeCodeBse"),
        )
    
    def get_quotes( self, ticker: str, market: Market = Market.INDIA) -> list[ExchangeQuote]:

        data = self.get_stock(ticker, market)

        current_price = data.get("currentPrice") or {}

        percent_change = _to_float(
            data.get("percentChange")
        )

        year_high = _to_float(
            data.get("yearHigh")
        )

        year_low = _to_float(
            data.get("yearLow")
        )

        quotes = []

        for exchange, price in current_price.items():
            quotes.append(
                ExchangeQuote(
                    exchange=exchange,
                    price=_to_float(price),
                    percent_change=percent_change,
                    year_high=year_high,
                    year_low=year_low,
                )
            )

        return quotes
    
    
    def get_financials(self, ticker: str, market: Market = Market.INDIA) -> list[FinancialStatement]:
        
        if market != Market.INDIA:
            raise ValueError(
                "IndianAPIProvider currently supports India only."
            )

        data = self.get_stock(ticker, market)

        statements: list[FinancialStatement] = []

        for record in data.get("financials", []):
            financial_map = (
                record.get("stockFinancialMap") or {}
            )

            for statement_type, items in financial_map.items():
                if not items:
                    continue

                metrics, period_type, period_length = (
                    _parse_financial_section(items)
                )

                statements.append(
                    FinancialStatement(
                        statement_type=statement_type,
                        fiscal_year=record.get("FiscalYear"),
                        end_date=record.get("EndDate"),
                        period_type=period_type,
                        period_length=period_length,
                        metrics=metrics,
                    )
                )

        return statements
    
    def get_key_metrics(self, ticker: str, market: Market = Market.INDIA) -> KeyMetricsResearch:

        if market != Market.INDIA:
            raise ValueError(
                "IndianAPIProvider currently supports India only."
            )

        data = self.get_stock(
            ticker,
            market,
        )

        metrics = _parse_key_metrics(
            data.get("keyMetrics") or {}
        )

        return KeyMetricsResearch(
            ticker=ticker,
            metrics=metrics,
        )
        
    def get_news(self, ticker: str, market: Market = Market.INDIA) -> NewsResearch:

        if market != Market.INDIA:
            raise ValueError(
                "IndianAPIProvider currently supports India only."
            )

        data = self.get_stock(
            ticker,
            market,
        )

        articles: list[NewsArticle] = []

        for item in data.get("recentNews") or []:
            relative_url = item.get("url") or ""

            if relative_url.startswith("http"):
                url = relative_url
            else:
                url = f"https://www.livemint.com{relative_url}"

            articles.append(
                NewsArticle(
                    title=item.get("headline", ""),
                    summary=item.get("summary"),
                    url=url,
                    source="livemint.com",
                    published_at=(
                        item.get("lastPublishedDate")
                        or item.get("date")
                    ),
                    image_url=(
                        item.get("thumbnailImage")
                        or item.get("listimage")
                    ),
                    relevance_score=None,
                    entities=None,
                )
            )

        return NewsResearch(
            ticker=ticker.upper(),
            articles=articles,
        )