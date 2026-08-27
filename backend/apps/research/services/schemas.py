from dataclasses import dataclass
from typing import Optional


@dataclass
class CompanyProfile:
    ticker: str
    name: str
    exchange: str
    country: str

    sector: str | None = None
    industry: str | None = None

    description: str | None = None
    isin: str | None = None
    nse_symbol: str | None = None
    bse_code: str | None = None


@dataclass
class MarketQuote:
    ticker: str
    price: float | None
    change: float | None
    percent_change: float | None
    high: float | None
    low: float | None
    open: float | None
    previous_close: float | None
    
@dataclass
class ExchangeQuote:
    exchange: str
    price: float | None
    percent_change: float | None
    year_high: float | None
    year_low: float | None