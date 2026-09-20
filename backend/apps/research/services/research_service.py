from apps.research.services.providers.finnhub import FinnhubProvider
from apps.research.services.providers.indian_api import IndianAPIProvider
from apps.research.services.providers.upstox import UpstoxProvider
from apps.research.services.news_aggregator import NewsAggregator
from apps.research.services.schemas import DataStatus, ProvenanceList, ProvenanceMetadata
from apps.research.services.symbols import Market


def _attach_provenance(obj, prov: ProvenanceMetadata):
    if obj is None:
        return obj
    if isinstance(obj, dict):
        obj["_provenance"] = prov
        obj["source"] = prov.source
        obj["provider_used"] = prov.source
        obj["primary_provider"] = prov.primary_provider
        obj["fallback_used"] = prov.fallback_used
        obj["data_status"] = prov.data_status.value if hasattr(prov.data_status, "value") else str(prov.data_status)
        if prov.fallback_reason:
            obj["fallback_reason"] = prov.fallback_reason
        return obj
    if isinstance(obj, list):
        if not isinstance(obj, ProvenanceList):
            obj = ProvenanceList(obj, provenance=prov)
        else:
            obj._provenance = prov
        for item in obj:
            if hasattr(item, "__dict__"):
                setattr(item, "_provenance", prov)
        return obj
    if hasattr(obj, "__dict__"):
        setattr(obj, "_provenance", prov)
    return obj


class ResearchService:

    def __init__(self):
        self._finnhub = None
        self._indian_api = None
        self._upstox = None
        self._news_aggregator = None

    @property
    def finnhub(self):
        if self._finnhub is None:
            self._finnhub = FinnhubProvider()
        return self._finnhub

    @property
    def indian_api(self):
        if self._indian_api is None:
            self._indian_api = IndianAPIProvider()
        return self._indian_api

    @property
    def upstox(self):
        if self._upstox is None:
            self._upstox = UpstoxProvider()
        return self._upstox

    @property
    def news_aggregator(self):
        if self._news_aggregator is None:
            self._news_aggregator = NewsAggregator()
        return self._news_aggregator

    def get_company_profile(
        self,
        ticker: str,
        market: Market,
    ):
        if market == Market.US:
            profile = self.finnhub.get_company_profile(
                ticker,
                market,
            )
            status = DataStatus.COMPLETE if (profile and (getattr(profile, "name", None) or getattr(profile, "ticker", None))) else DataStatus.EMPTY
            prov = ProvenanceMetadata(
                primary_provider="finnhub",
                source="finnhub",
                fallback_used=False,
                data_status=status.value if hasattr(status, "value") else str(status),
            )
            return _attach_provenance(profile, prov)

        if market == Market.INDIA:
            fallback_reason = None
            try:
                profile = self.upstox.get_company_profile(
                    ticker,
                    market,
                )
                if profile and (getattr(profile, "name", None) or getattr(profile, "ticker", None)):
                    prov = ProvenanceMetadata(
                        primary_provider="upstox",
                        source="upstox",
                        fallback_used=False,
                        data_status=DataStatus.COMPLETE.value,
                    )
                    return _attach_provenance(profile, prov)
                else:
                    fallback_reason = "upstox_empty_data"
            except Exception as e:
                fallback_reason = f"upstox_exception: {type(e).__name__}"

            profile = self.indian_api.get_company_profile(
                ticker,
                market,
            )
            status = DataStatus.COMPLETE if (profile and (getattr(profile, "name", None) or getattr(profile, "ticker", None))) else DataStatus.EMPTY
            prov = ProvenanceMetadata(
                primary_provider="upstox",
                source="indian_api",
                fallback_used=True,
                data_status=status.value if hasattr(status, "value") else str(status),
                fallback_reason=fallback_reason,
            )
            return _attach_provenance(profile, prov)

        raise ValueError(
            f"Unsupported market: {market}"
        )

    def get_market_data(
        self,
        ticker: str,
        market: Market,
    ):
        if market == Market.US:
            quotes = self.finnhub.get_quotes(
                ticker,
                market,
            )
            prov = ProvenanceMetadata(
                primary_provider="finnhub",
                source="finnhub",
                fallback_used=False,
                data_status=DataStatus.COMPLETE.value if quotes else DataStatus.EMPTY.value,
            )
            return _attach_provenance(quotes, prov)

        if market == Market.INDIA:
            quotes = self.indian_api.get_quotes(
                ticker,
                market,
            )
            prov = ProvenanceMetadata(
                primary_provider="indian_api",
                source="indian_api",
                fallback_used=False,
                data_status=DataStatus.COMPLETE.value if quotes else DataStatus.EMPTY.value,
            )
            return _attach_provenance(quotes, prov)

        raise ValueError(
            f"Unsupported market: {market}"
        )

    def get_financials(
        self,
        ticker: str,
        market: Market,
    ):
        if market == Market.US:
            financials = self.finnhub.get_financials(
                ticker,
                market,
            )
            if isinstance(financials, list) and len(financials) > 0:
                statement_types = {getattr(s, "statement_type", None) for s in financials}
                status = DataStatus.COMPLETE.value if len(statement_types) >= 3 else DataStatus.PARTIAL.value
            else:
                status = DataStatus.EMPTY.value

            prov = ProvenanceMetadata(
                primary_provider="finnhub",
                source="finnhub",
                fallback_used=False,
                data_status=status,
            )
            return _attach_provenance(financials, prov)

        if market == Market.INDIA:
            fallback_reason = None
            try:
                financials = self.upstox.get_financials(
                    ticker,
                    market,
                )
                if isinstance(financials, list) and len(financials) > 0:
                    statement_types = {getattr(s, "statement_type", None) for s in financials}
                    status = DataStatus.COMPLETE.value if len(statement_types) >= 3 else DataStatus.PARTIAL.value
                    prov = ProvenanceMetadata(
                        primary_provider="upstox",
                        source="upstox",
                        fallback_used=False,
                        data_status=status,
                    )
                    return _attach_provenance(financials, prov)
                else:
                    fallback_reason = "upstox_empty_data"
            except Exception as e:
                fallback_reason = f"upstox_exception: {type(e).__name__}"

            financials = self.indian_api.get_financials(
                ticker,
                market,
            )
            status = DataStatus.COMPLETE.value if (isinstance(financials, list) and len(financials) > 0) else DataStatus.EMPTY.value
            prov = ProvenanceMetadata(
                primary_provider="upstox",
                source="indian_api",
                fallback_used=True,
                data_status=status,
                fallback_reason=fallback_reason,
            )
            return _attach_provenance(financials, prov)

        raise ValueError(
            f"Financial data is not yet supported for market: {market}"
        )

    def get_key_metrics(
        self,
        ticker: str,
        market: Market,
    ):
        if market == Market.US:
            metrics_res = self.finnhub.get_key_metrics(
                ticker,
                market,
            )
            if (
                metrics_res
                and hasattr(metrics_res, "metrics")
                and isinstance(metrics_res.metrics, list)
                and len(metrics_res.metrics) > 0
            ):
                present_keys = {
                    m.key
                    for m in metrics_res.metrics
                    if getattr(m, "value", None) is not None
                }
                primary_valuation_keys = {"pe_ttm", "forward_pe", "ev_ebitda_ttm", "pb"}
                if primary_valuation_keys.issubset(present_keys):
                    status = DataStatus.COMPLETE.value
                elif len(present_keys) > 0:
                    status = DataStatus.PARTIAL.value
                else:
                    status = DataStatus.EMPTY.value
            else:
                status = DataStatus.EMPTY.value

            prov = ProvenanceMetadata(
                primary_provider="finnhub",
                source="finnhub",
                fallback_used=False,
                data_status=status,
            )
            return _attach_provenance(metrics_res, prov)

        if market == Market.INDIA:
            fallback_reason = None
            try:
                metrics_res = self.upstox.get_key_metrics(
                    ticker,
                    market,
                )
                if (
                    metrics_res
                    and hasattr(metrics_res, "metrics")
                    and isinstance(metrics_res.metrics, list)
                    and len(metrics_res.metrics) > 0
                ):
                    status = DataStatus.COMPLETE.value if len(metrics_res.metrics) >= 10 else DataStatus.PARTIAL.value
                    prov = ProvenanceMetadata(
                        primary_provider="upstox",
                        source="upstox",
                        fallback_used=False,
                        data_status=status,
                    )
                    return _attach_provenance(metrics_res, prov)
                else:
                    fallback_reason = "upstox_empty_data"
            except Exception as e:
                fallback_reason = f"upstox_exception: {type(e).__name__}"

            metrics_res = self.indian_api.get_key_metrics(
                ticker,
                market,
            )
            has_metrics = bool(
                metrics_res
                and hasattr(metrics_res, "metrics")
                and isinstance(metrics_res.metrics, list)
                and len(metrics_res.metrics) > 0
            )
            status = DataStatus.COMPLETE.value if has_metrics else DataStatus.EMPTY.value
            prov = ProvenanceMetadata(
                primary_provider="upstox",
                source="indian_api",
                fallback_used=True,
                data_status=status,
                fallback_reason=fallback_reason,
            )
            return _attach_provenance(metrics_res, prov)

        raise ValueError(
            f"Key metrics are not yet supported for market: {market}"
        )

    def get_historical_data(
        self,
        ticker: str,
        to_date: str,
        from_date: str | None = None,
        market: Market = Market.INDIA,
    ):
        if market == Market.INDIA:
            hist = self.upstox.get_historical(
                ticker,
                to_date,
                from_date,
                market,
            )
            provider_used = getattr(hist, "provider_used", "upstox") or "upstox"
            has_candles = bool(hist and hasattr(hist, "candles") and hist.candles)
            prov = ProvenanceMetadata(
                primary_provider="upstox",
                source=provider_used,
                fallback_used=(provider_used != "upstox"),
                data_status=DataStatus.COMPLETE.value if has_candles else DataStatus.EMPTY.value,
            )
            return _attach_provenance(hist, prov)

        raise ValueError(
            f"Historical data is not yet supported for market: {market}"
        )

    def get_news(
        self,
        ticker: str,
        market: Market,
    ):
        news = self.news_aggregator.get_news(
            ticker,
            market,
        )
        has_articles = bool(news and hasattr(news, "articles") and news.articles)
        prov = ProvenanceMetadata(
            primary_provider="news_aggregator",
            source="news_aggregator",
            fallback_used=False,
            data_status=DataStatus.COMPLETE.value if has_articles else DataStatus.EMPTY.value,
        )
        return _attach_provenance(news, prov)