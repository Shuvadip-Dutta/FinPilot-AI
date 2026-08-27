from abc import ABC, abstractmethod
from typing import Any

from apps.research.services.schemas import CompanyProfile, MarketQuote
from apps.research.services.symbols import Market


class MarketDataProvider(ABC):

    @abstractmethod
    def get_company_profile(
        self,
        ticker: str,
        market: Market,
    ) -> CompanyProfile:
        """Return normalized company profile data."""
        raise NotImplementedError

    @abstractmethod
    def get_quote(
        self,
        ticker: str,
        market: Market,
    ) -> MarketQuote:
        """Return normalized current market quote."""
        raise NotImplementedError

    @abstractmethod
    def get_historical_data(
        self,
        ticker: str,
        market: Market,
        start: int,
        end: int,
        resolution: str = "D",
    ) -> dict[str, Any]:
        """Return normalized historical market data."""
        raise NotImplementedError