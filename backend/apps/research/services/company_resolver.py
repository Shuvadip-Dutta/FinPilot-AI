from dataclasses import dataclass, field
from typing import Optional

from apps.research.services.symbols import Market


@dataclass
class CompanyIdentity:
    ticker: str
    legal_name: str
    isin: str | None = None
    exchange: str = "NSE"
    country: str = "India"
    instrument_key: str | None = None
    sector: str | None = None
    industry: str | None = None
    provider_symbols: dict[str, str] = field(default_factory=dict)

    def get_provider_symbol(self, provider_name: str, fallback_ticker: str | None = None) -> str:
        """
        Retrieves the provider-specific symbol for this company.
        Defaults to fallback_ticker or canonical ticker if unmapped.
        """
        key = provider_name.lower()
        if key in self.provider_symbols and self.provider_symbols[key]:
            return self.provider_symbols[key]

        if fallback_ticker:
            return fallback_ticker

        return self.ticker


class CanonicalCompanyResolver:
    """
    Resolves ticker, ISIN, or company name queries to a canonical CompanyIdentity.
    Uses database lookups with dynamic fallbacks.
    """

    _cache: dict[str, CompanyIdentity] = {}

    @classmethod
    def from_model(cls, model_instance) -> CompanyIdentity:
        provider_symbols = model_instance.provider_symbols or {}
        return CompanyIdentity(
            ticker=model_instance.ticker,
            legal_name=model_instance.name,
            isin=model_instance.isin,
            exchange=model_instance.exchange,
            country=model_instance.country,
            instrument_key=model_instance.instrument_key,
            sector=model_instance.sector,
            industry=model_instance.industry,
            provider_symbols=dict(provider_symbols),
        )

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()

    @classmethod
    def resolve(cls, query: str, market: Market = Market.INDIA) -> CompanyIdentity:
        if not query or not isinstance(query, str):
            raise ValueError("Query string must be a non-empty string.")

        clean_query = query.strip()
        cache_key = f"{market.value}:{clean_query.upper()}"

        if cache_key in cls._cache:
            return cls._cache[cache_key]

        # Lazy import of Company model to avoid circular imports during app init
        from apps.research.models import Company

        upper_query = clean_query.upper()

        company_obj = None
        try:
            # 1. DB Lookup by Ticker
            company_obj = Company.objects.filter(
                ticker__iexact=upper_query
            ).first()

            # 2. DB Lookup by ISIN
            if not company_obj and len(upper_query) == 12 and upper_query.isalnum():
                company_obj = Company.objects.filter(
                    isin__iexact=upper_query
                ).first()

            # 3. DB Lookup by Legal Name
            if not company_obj:
                company_obj = Company.objects.filter(
                    name__iexact=clean_query
                ).first()
        except Exception:
            company_obj = None

        if company_obj:
            identity = cls.from_model(company_obj)
            cls._cache[cache_key] = identity
            return identity

        # Fallback for unseeded/unknown tickers
        provider_symbols = {}
        if market == Market.INDIA:
            provider_symbols["marketaux"] = f"{upper_query}.NS"

        identity = CompanyIdentity(
            ticker=upper_query,
            legal_name=clean_query,
            exchange="NSE" if market == Market.INDIA else "US",
            country="India" if market == Market.INDIA else "United States",
            provider_symbols=provider_symbols,
        )

        cls._cache[cache_key] = identity
        return identity
