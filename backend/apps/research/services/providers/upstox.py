import os
import re
from datetime import datetime, timezone
from typing import Any

import requests
from django.conf import settings

from apps.research.services.exceptions import ProviderResponseError
from apps.research.services.instrument_resolver import UpstoxInstrumentResolver
from apps.research.services.schemas import (
    CompanyProfile,
    FinancialMetric,
    FinancialStatement,
    HistoricalCandle,
    HistoricalMarketData,
    KeyMetric,
    KeyMetricsResearch,
    NewsArticle,
    NewsResearch,
)
from apps.research.services.symbols import Market


def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        clean_val = value.replace("%", "").replace(",", "").strip()
        try:
            return float(clean_val)
        except (TypeError, ValueError):
            return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_year(period_str: str | None) -> str | None:
    if not period_str:
        return None
    match = re.search(r"\b(20\d{2})\b", str(period_str))
    if match:
        return match.group(1)
    return str(period_str)


class UpstoxProvider:
    BASE_URL = "https://api.upstox.com/v3"
    NEWS_BASE_URL = "https://api.upstox.com/v2"

    def __init__(self):
        self.access_token = settings.UPSTOX_ANALYTICS_ACCESS_TOKEN
        self.instrument_resolver = UpstoxInstrumentResolver()

    def _resolve_instrument_key(self, ticker: str) -> str:
        from apps.portfolio.backtest_builder import INDEX_INSTRUMENT_MAP, resolve_benchmark_instrument_key

        clean_ticker = ticker.strip()
        # 1. Benchmark index resolution (e.g. 'NIFTY 50', 'nifty 50', '^NSEI' -> 'NSE_INDEX|Nifty 50')
        if clean_ticker in INDEX_INSTRUMENT_MAP or clean_ticker.upper() in INDEX_INSTRUMENT_MAP:
            return resolve_benchmark_instrument_key(clean_ticker)

        # 2. Already an exact provider instrument key (contains '|')
        if "|" in clean_ticker:
            return clean_ticker

        # 3. Equity alias resolution (normalize alias before mapping, e.g. 'reliance' -> 'RELIANCE')
        upper_ticker = clean_ticker.upper()

        from apps.research.services.company_resolver import CanonicalCompanyResolver

        identity = CanonicalCompanyResolver.resolve(upper_ticker, Market.INDIA)
        if identity.instrument_key:
            return identity.instrument_key

        provider_sym = identity.get_provider_symbol("upstox")
        if provider_sym and "|" in provider_sym:
            return provider_sym

        return self.instrument_resolver.resolve_nse_equity(upper_ticker)

    def _resolve_isin(self, ticker: str, market: Market = Market.INDIA) -> str:
        from apps.research.services.company_resolver import CanonicalCompanyResolver

        identity = CanonicalCompanyResolver.resolve(ticker, market)
        if identity.isin:
            return identity.isin

        inst_key = identity.instrument_key or ""
        if "|" in inst_key:
            possible_isin = inst_key.split("|")[-1]
            if len(possible_isin) == 12:
                return possible_isin

        raise ValueError(f"Unable to resolve ISIN for {ticker}.")

    def _get(self, endpoint: str, params: dict, base_url: str | None = None) -> dict:
        response = requests.get(
            f"{base_url or self.BASE_URL}/{endpoint}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            },
            params=params,
            timeout=10,
        )

        response.raise_for_status()
        return response.json()

    @staticmethod
    def _validate_dict_response(
        data: dict,
        provider: str = "Upstox",
    ) -> dict:
        if not isinstance(data, dict):
            raise ProviderResponseError(f"{provider} returned an invalid response.")

        if not isinstance(data.get("data"), dict):
            raise ProviderResponseError(f"{provider} returned an invalid data payload.")

        return data

    @staticmethod
    def _validate_candle(candle) -> bool:
        if not isinstance(candle, list):
            return False
        if len(candle) < 7:
            return False
        return True

    def get_company_profile(
        self,
        ticker: str,
        market: Market = Market.INDIA,
    ) -> CompanyProfile:
        if market != Market.INDIA:
            raise ValueError("UpstoxProvider currently supports India only.")

        from apps.research.services.company_resolver import CanonicalCompanyResolver

        identity = CanonicalCompanyResolver.resolve(ticker, market)
        isin = self._resolve_isin(ticker, market)

        try:
            data = self._get(
                f"fundamentals/{isin}/profile",
                {},
                base_url=self.NEWS_BASE_URL,
            )
            payload = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) else {}
        except Exception:
            payload = {}

        return CompanyProfile(
            ticker=identity.ticker,
            name=payload.get("company_name") or payload.get("name") or identity.legal_name,
            exchange=payload.get("exchange") or identity.exchange,
            country="India",
            sector=payload.get("sector") or identity.sector,
            industry=payload.get("industry") or identity.industry,
            description=payload.get("company_profile") or payload.get("description"),
            isin=isin,
            nse_symbol=payload.get("symbol") or identity.ticker,
            bse_code=payload.get("bse_code"),
        )

    def _parse_income_statement(self, raw_data: dict[str, Any]) -> list[FinancialStatement]:
        inc_categories = raw_data.get("income_statement") or []
        if not isinstance(inc_categories, list):
            return []

        period_metrics: dict[str, list[FinancialMetric]] = {}

        for cat_item in inc_categories:
            if not isinstance(cat_item, dict):
                continue
            cat_name = cat_item.get("category", "")
            history = cat_item.get("history") or []
            if not isinstance(history, list):
                continue

            for hist_entry in history:
                if not isinstance(hist_entry, dict):
                    continue
                period = hist_entry.get("period") or "Unknown"
                val = _to_float(hist_entry.get("value"))
                display_name = cat_name.replace("_", " ").title()

                if period not in period_metrics:
                    period_metrics[period] = []

                period_metrics[period].append(
                    FinancialMetric(
                        name=display_name,
                        key=cat_name,
                        value=val,
                    )
                )

        statements: list[FinancialStatement] = []
        for period, metrics in period_metrics.items():
            year = _extract_year(period)
            statements.append(
                FinancialStatement(
                    statement_type="INC",
                    fiscal_year=year,
                    end_date=period,
                    period_type=raw_data.get("time_period", "yearly"),
                    period_length=12,
                    metrics=metrics,
                )
            )

        return statements

    def _parse_balance_sheet(self, raw_data: dict[str, Any]) -> list[FinancialStatement]:
        history = raw_data.get("history") or []
        if not isinstance(history, list):
            return []

        statements: list[FinancialStatement] = []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            period = entry.get("period") or "Unknown"
            year = _extract_year(period)
            metrics = []

            for key, val in entry.items():
                if key == "period":
                    continue
                display_name = key.replace("_", " ").title()
                metrics.append(
                    FinancialMetric(
                        name=display_name,
                        key=key,
                        value=_to_float(val),
                    )
                )

            statements.append(
                FinancialStatement(
                    statement_type="BAL",
                    fiscal_year=year,
                    end_date=period,
                    period_type=raw_data.get("time_period", "yearly"),
                    period_length=12,
                    metrics=metrics,
                )
            )

        return statements

    def _parse_cash_flow(self, raw_data: dict[str, Any]) -> list[FinancialStatement]:
        cf_categories = raw_data.get("cash_flow") or []
        if not isinstance(cf_categories, list):
            return []

        period_metrics: dict[str, list[FinancialMetric]] = {}

        for cat_item in cf_categories:
            if not isinstance(cat_item, dict):
                continue
            cat_name = cat_item.get("category", "")
            history = cat_item.get("history") or []
            if not isinstance(history, list):
                continue

            for hist_entry in history:
                if not isinstance(hist_entry, dict):
                    continue
                period = hist_entry.get("period") or "Unknown"
                val = _to_float(hist_entry.get("value"))
                display_name = f"{cat_name.replace('_', ' ').title()} Cash Flow"

                if period not in period_metrics:
                    period_metrics[period] = []

                period_metrics[period].append(
                    FinancialMetric(
                        name=display_name,
                        key=f"{cat_name}_cash_flow",
                        value=val,
                    )
                )

        statements: list[FinancialStatement] = []
        for period, metrics in period_metrics.items():
            year = _extract_year(period)
            statements.append(
                FinancialStatement(
                    statement_type="CAS",
                    fiscal_year=year,
                    end_date=period,
                    period_type=raw_data.get("time_period", "yearly"),
                    period_length=12,
                    metrics=metrics,
                )
            )

        return statements

    def get_financials(
        self,
        ticker: str,
        market: Market = Market.INDIA,
    ) -> list[FinancialStatement]:
        if market != Market.INDIA:
            raise ValueError("UpstoxProvider currently supports India only.")

        isin = self._resolve_isin(ticker, market)
        statements: list[FinancialStatement] = []

        # 1. Income Statement
        try:
            inc_res = self._get(f"fundamentals/{isin}/income-statement", {}, base_url=self.NEWS_BASE_URL)
            if isinstance(inc_res, dict) and isinstance(inc_res.get("data"), dict):
                statements.extend(self._parse_income_statement(inc_res["data"]))
        except Exception:
            pass

        # 2. Balance Sheet
        try:
            bal_res = self._get(f"fundamentals/{isin}/balance-sheet", {}, base_url=self.NEWS_BASE_URL)
            if isinstance(bal_res, dict) and isinstance(bal_res.get("data"), dict):
                statements.extend(self._parse_balance_sheet(bal_res["data"]))
        except Exception:
            pass

        # 3. Cash Flow
        try:
            cas_res = self._get(f"fundamentals/{isin}/cash-flow", {}, base_url=self.NEWS_BASE_URL)
            if isinstance(cas_res, dict) and isinstance(cas_res.get("data"), dict):
                statements.extend(self._parse_cash_flow(cas_res["data"]))
        except Exception:
            pass

        return statements

    def get_key_metrics(
        self,
        ticker: str,
        market: Market = Market.INDIA,
    ) -> KeyMetricsResearch:
        if market != Market.INDIA:
            raise ValueError("UpstoxProvider currently supports India only.")

        isin = self._resolve_isin(ticker, market)

        try:
            data = self._get(f"fundamentals/{isin}/key-ratios", {}, base_url=self.NEWS_BASE_URL)
            raw_data = data.get("data") if isinstance(data, dict) else []
        except Exception:
            raw_data = []

        metrics: list[KeyMetric] = []
        if isinstance(raw_data, list):
            for item in raw_data:
                if not isinstance(item, dict):
                    continue
                name = item.get("name", "")
                raw_val = item.get("company_value")
                val = _to_float(raw_val)
                key = name.lower().replace(" ", "_").replace("/", "_")

                if name in ("P/E", "P/B", "EV/EBITDA"):
                    category = "valuation"
                elif name in ("ROE", "ROCE", "ROA"):
                    category = "profitability"
                elif "Ratio" in name:
                    category = "liquidity"
                else:
                    category = "ratios"

                metrics.append(
                    KeyMetric(
                        category=category,
                        name=name,
                        key=key,
                        value=val,
                        raw_value=str(raw_val) if raw_val is not None else None,
                    )
                )

        return KeyMetricsResearch(
            ticker=ticker.upper(),
            metrics=metrics,
        )

    def get_stock(
        self,
        ticker: str,
        market: Market = Market.INDIA,
    ) -> dict:
        if market != Market.INDIA:
            raise ValueError("UpstoxProvider currently supports India only.")

        instrument_key = self._resolve_instrument_key(ticker)
        norm_ticker = ticker if "|" in ticker else ticker.strip().upper()

        data = self._get(
            "market-quote/ltp",
            {
                "instrument_key": instrument_key,
            },
        )
        data = self._validate_dict_response(data)

        quote = data["data"].get(f"NSE_EQ:{norm_ticker}") or data["data"].get(instrument_key)
        if quote is None:
            raise ValueError(f"No market data found for {ticker}.")

        if not isinstance(quote, dict):
            raise ProviderResponseError(
                f"Upstox returned invalid market data for {ticker}."
            )

        required_fields = (
            "instrument_token",
            "last_price",
            "ltq",
            "volume",
            "cp",
        )

        if not all(field in quote for field in required_fields):
            raise ProviderResponseError(
                f"Upstox returned incomplete market data for {ticker}."
            )

        return {
            "ticker": norm_ticker,
            "instrument_key": quote["instrument_token"],
            "last_price": quote["last_price"],
            "last_traded_quantity": quote["ltq"],
            "volume": quote["volume"],
            "previous_close": quote["cp"],
        }

    def get_historical(
        self,
        ticker: str,
        to_date: str,
        from_date: str | None = None,
        market: Market = Market.INDIA,
    ) -> HistoricalMarketData:
        if market != Market.INDIA:
            raise ValueError("UpstoxProvider currently supports India only.")

        instrument_key = self._resolve_instrument_key(ticker)

        endpoint = f"historical-candle/{instrument_key}/days/1/{to_date}"
        if from_date:
            endpoint = f"{endpoint}/{from_date}"

        data = self._get(endpoint, {})
        data = self._validate_dict_response(data)

        candles = data["data"].get("candles", [])
        if not isinstance(candles, list):
            raise ProviderResponseError(
                f"Upstox returned invalid historical data for {ticker}."
            )

        for candle in candles:
            if not self._validate_candle(candle):
                raise ProviderResponseError(
                    f"Upstox returned malformed historical data for {ticker}."
                )

        return HistoricalMarketData(
            ticker=ticker if "|" in ticker else ticker.strip().upper(),
            candles=[
                HistoricalCandle(
                    timestamp=candle[0],
                    open=candle[1],
                    high=candle[2],
                    low=candle[3],
                    close=candle[4],
                    volume=candle[5],
                    open_interest=candle[6],
                )
                for candle in candles
            ],
        )

    def get_news(
        self,
        ticker: str,
        market: Market = Market.INDIA,
        limit: int = 10,
    ) -> NewsResearch:
        if market != Market.INDIA:
            raise ValueError("UpstoxProvider currently supports India only.")

        instrument_key = self._resolve_instrument_key(ticker)

        data = self._get(
            "news",
            {
                "category": "instrument_keys",
                "instrument_keys": instrument_key,
                "page_number": 1,
                "page_size": limit,
            },
            base_url=self.NEWS_BASE_URL,
        )

        data = self._validate_dict_response(data)
        raw_articles = data["data"].get(instrument_key, [])

        if not isinstance(raw_articles, list):
            raise ProviderResponseError(
                f"Upstox returned invalid news data for {ticker}."
            )

        articles: list[NewsArticle] = []
        for item in raw_articles:
            if not isinstance(item, dict):
                raise ProviderResponseError(
                    f"Upstox returned malformed news data for {ticker}."
                )

            published_time = item.get("published_time")
            if published_time is not None:
                if not isinstance(published_time, (int, float)):
                    raise ProviderResponseError(
                        f"Upstox returned invalid publication time for {ticker}."
                    )

                try:
                    published_at = datetime.fromtimestamp(
                        published_time / 1000,
                        tz=timezone.utc,
                    ).isoformat()
                except (OverflowError, OSError, ValueError):
                    raise ProviderResponseError(
                        f"Upstox returned invalid publication time for {ticker}."
                    )
            else:
                published_at = None

            articles.append(
                NewsArticle(
                    title=item.get("heading", ""),
                    summary=item.get("summary"),
                    url=item.get("article_link", ""),
                    source="upstox.com",
                    published_at=published_at,
                    image_url=item.get("thumbnail"),
                    relevance_score=None,
                    target_match_score=None,
                    relevance_type=None,
                    entities=None,
                )
            )

        return NewsResearch(
            ticker=ticker,
            articles=articles,
        )