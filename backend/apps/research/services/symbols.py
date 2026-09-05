from enum import StrEnum


class Market(StrEnum):
    US = "US"
    INDIA = "IN"

    @classmethod
    def normalize(cls, value: str | None) -> str | None:
        if not value or not isinstance(value, str):
            return None

        val = value.strip().upper()
        if val in ("IN", "INDIA"):
            return cls.INDIA.value
        if val in ("US", "USA", "UNITED STATES", "UNITED_STATES"):
            return cls.US.value

        try:
            return cls(val).value
        except ValueError:
            return val


class SymbolResolver:
    """
    Resolves application-level symbols to provider-specific symbols
    using the CanonicalCompanyResolver under the hood.
    """

    @staticmethod
    def resolve(ticker: str, market: Market, provider: str | None = None) -> str:
        ticker = ticker.strip().upper()

        from apps.research.services.company_resolver import CanonicalCompanyResolver

        identity = CanonicalCompanyResolver.resolve(ticker, market)

        if provider:
            return identity.get_provider_symbol(provider)

        if market == Market.US:
            return identity.ticker

        if market == Market.INDIA:
            return identity.ticker

        raise ValueError(f"Unsupported market: {market}")