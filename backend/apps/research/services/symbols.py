from enum import StrEnum


class Market(StrEnum):
    US = "US"
    INDIA = "IN"


class SymbolResolver:
    """
    Resolves application-level symbols to provider-specific symbols.
    """

    @staticmethod
    def resolve(ticker: str, market: Market) -> str:
        ticker = ticker.strip().upper()

        if market == Market.US:
            return ticker

        if market == Market.INDIA:
            if ":" in ticker:
                return ticker

            return f"{ticker}:NSE"

        raise ValueError(f"Unsupported market: {market}")