import os
from typing import Any

import requests
from dotenv import load_dotenv
from common.logger import get_logger
from apps.research.services.market_data import MarketDataProvider
from apps.research.services.schemas import (
    CompanyProfile,
    ExchangeQuote,
    FinancialMetric,
    FinancialStatement,
    KeyMetric,
    KeyMetricsResearch,
    MarketQuote,
)
from apps.research.services.symbols import Market, SymbolResolver

load_dotenv()

logger = get_logger("research.finnhub")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class FinnhubProvider(MarketDataProvider):
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self) -> None:
        self.api_key = os.getenv("FINNHUB_API_KEY")

        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY is not configured.")

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:

        params["token"] = self.api_key

        response = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()

    def get_company_profile(self, ticker: str, market: Market = Market.US) -> CompanyProfile:

        provider_symbol = SymbolResolver.resolve(
            ticker,
            market,
        )

        data = self._get(
            "stock/profile2",
            {"symbol": provider_symbol},
        )
        if not data.get("name"):
            raise ValueError(f"Company not found for ticker: {ticker}")

        return CompanyProfile(
            ticker=ticker.upper(),
            name=data.get("name", ""),
            exchange=data.get("exchange", ""),
            country=data.get("country", ""),
            sector=None,
            industry=data.get("finnhubIndustry"),
            description=None,
            isin=None,
            nse_symbol=None,
            bse_code=None,
        )

    def get_quote(self, ticker: str, market: Market = Market.US) -> MarketQuote:

        provider_symbol = SymbolResolver.resolve(
            ticker,
            market,
        )

        data = self._get(
            "quote",
            {"symbol": provider_symbol},
        )
        if data.get("c") is None:
            raise ValueError(
                f"Quote not found for ticker: {ticker}"
            )

        return MarketQuote(
            ticker=ticker.upper(),
            price=_to_float(data.get("c")),
            change=_to_float(data.get("d")),
            percent_change=_to_float(data.get("dp")),
            high=_to_float(data.get("h")),
            low=_to_float(data.get("l")),
            open=_to_float(data.get("o")),
            previous_close=_to_float(data.get("pc")),
        )

    def get_quotes(
        self,
        ticker: str,
        market: Market = Market.US,
    ) -> list[ExchangeQuote]:
        provider_symbol = SymbolResolver.resolve(ticker, market)
        quote = self.get_quote(ticker, market)

        year_high = None
        year_low = None
        try:
            metric_data = self._get(
                "stock/metric",
                {"symbol": provider_symbol, "metric": "all"},
            )
            if isinstance(metric_data, dict):
                raw_metric = metric_data.get("metric", {})
                if isinstance(raw_metric, dict):
                    year_high = _to_float(raw_metric.get("52WeekHigh"))
                    year_low = _to_float(raw_metric.get("52WeekLow"))
        except Exception as exc:
            logger.debug("Failed to retrieve 52-week metrics from Finnhub: %s", exc)

        return [
            ExchangeQuote(
                exchange="US",
                price=quote.price,
                percent_change=quote.percent_change,
                year_high=year_high,
                year_low=year_low,
            )
        ]

    def get_key_metrics(
        self,
        ticker: str,
        market: Market = Market.US,
    ) -> KeyMetricsResearch:
        provider_symbol = SymbolResolver.resolve(ticker, market)

        data = self._get(
            "stock/metric",
            {"symbol": provider_symbol, "metric": "all"},
        )
        if not isinstance(data, dict):
            return KeyMetricsResearch(ticker=ticker.upper(), metrics=[])

        raw_metrics = data.get("metric")
        if not isinstance(raw_metrics, dict):
            return KeyMetricsResearch(ticker=ticker.upper(), metrics=[])

        metrics: list[KeyMetric] = []

        primary_valuation_fields = [
            ("peTTM", "pe_ttm", "Trailing P/E", "valuation"),
            ("forwardPE", "forward_pe", "Forward P/E", "valuation"),
            ("evEbitdaTTM", "ev_ebitda_ttm", "EV/EBITDA", "valuation"),
            ("pb", "pb", "Price/Book", "valuation"),
        ]

        for finnhub_field, key, name, category in primary_valuation_fields:
            if finnhub_field in raw_metrics and raw_metrics[finnhub_field] is not None:
                raw_val = raw_metrics[finnhub_field]
                metrics.append(
                    KeyMetric(
                        category=category,
                        name=name,
                        key=key,
                        value=_to_float(raw_val),
                        raw_value=str(raw_val),
                    )
                )
            else:
                metrics.append(
                    KeyMetric(
                        category=category,
                        name=name,
                        key=key,
                        value=None,
                        raw_value=None,
                    )
                )

        other_field_mappings = [
            ("marketCapitalization", "market_capitalization", "Market Capitalization", "valuation"),
            ("enterpriseValue", "enterprise_value", "Enterprise Value", "valuation"),
            ("epsTTM", "eps_ttm", "EPS TTM", "profitability"),
            ("bookValuePerShareQuarterly", "book_value_per_share", "Book Value Per Share", "valuation"),
            ("52WeekHigh", "52_week_high", "52 Week High", "trading"),
            ("52WeekLow", "52_week_low", "52 Week Low", "trading"),
            ("roeTTM", "roe_ttm", "ROE TTM", "profitability"),
            ("roaTTM", "roa_ttm", "ROA TTM", "profitability"),
            ("netProfitMarginTTM", "net_profit_margin_ttm", "Net Profit Margin TTM", "profitability"),
            ("operatingMarginTTM", "operating_margin_ttm", "Operating Margin TTM", "profitability"),
            ("grossMarginTTM", "gross_margin_ttm", "Gross Margin TTM", "profitability"),
            ("revenueGrowthQuarterlyYoy", "revenue_growth_quarterly_yoy", "Quarterly Revenue Growth YoY", "growth"),
        ]

        for finnhub_field, key, name, category in other_field_mappings:
            if finnhub_field in raw_metrics and raw_metrics[finnhub_field] is not None:
                raw_val = raw_metrics[finnhub_field]
                parsed_val = _to_float(raw_val)
                if parsed_val is not None:
                    metrics.append(
                        KeyMetric(
                            category=category,
                            name=name,
                            key=key,
                            value=parsed_val,
                            raw_value=str(raw_val),
                        )
                    )

        return KeyMetricsResearch(
            ticker=ticker.upper(),
            metrics=metrics,
        )

    def get_financials(
        self,
        ticker: str,
        market: Market = Market.US,
    ) -> list[FinancialStatement]:
        provider_symbol = SymbolResolver.resolve(ticker, market)

        data = self._get(
            "stock/financials-reported",
            {"symbol": provider_symbol},
        )
        if not isinstance(data, dict):
            return []

        filings = data.get("data")
        if not isinstance(filings, list):
            return []

        statements: list[FinancialStatement] = []

        statement_section_map = [
            ("bs", "BAL"),
            ("ic", "INC"),
            ("cf", "CAS"),
        ]

        for filing in filings:
            if not isinstance(filing, dict):
                continue

            year = str(filing.get("year")) if filing.get("year") is not None else None
            end_date = filing.get("endDate")
            period_val = str(filing.get("period") or "").upper()
            form_val = str(filing.get("form") or "").upper()
            quarter = filing.get("quarter")

            is_annual = (quarter == 0 or "10-K" in form_val or "FY" in period_val or "ANNUAL" in period_val)
            if is_annual:
                period_type = "Annual"
                period_length = 12
            elif quarter is not None:
                period_type = f"Q{quarter}"
                period_length = 3
            elif period_val:
                period_type = period_val
                period_length = 3
            else:
                period_type = "Quarterly"
                period_length = 3

            report = filing.get("report")
            if not isinstance(report, dict):
                continue

            for section_key, stmt_type in statement_section_map:
                items = report.get(section_key)
                if not isinstance(items, list) or not items:
                    continue

                metrics: list[FinancialMetric] = []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    concept = item.get("concept", "")
                    label = item.get("label") or concept
                    val = _to_float(item.get("value"))
                    metrics.append(
                        FinancialMetric(
                            name=label,
                            key=concept,
                            value=val,
                        )
                    )

                if metrics:
                    statements.append(
                        FinancialStatement(
                            statement_type=stmt_type,
                            fiscal_year=year,
                            end_date=end_date,
                            period_type=period_type,
                            period_length=period_length,
                            metrics=metrics,
                        )
                    )

        return statements

    def get_historical_data(
        self,
        ticker: str,
        start: int,
        end: int,
        resolution: str = "D",
    ) -> dict[str, Any]:

        return self._get(
            "stock/candle",
            {
                "symbol": ticker.upper(),
                "resolution": resolution,
                "from": start,
                "to": end,
            },
        )