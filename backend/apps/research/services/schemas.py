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
    
@dataclass
class FinancialMetric:
    name: str
    key: str
    value: float | None


@dataclass
class FinancialStatement:
    #CAS = Cash Flow, BAL = Balance Sheet, INC = Income Statement
    statement_type: str
    fiscal_year: str | None
    end_date: str | None
    period_type: str | None
    period_length: int | None
    metrics: list[FinancialMetric]


@dataclass
class FinancialResearch:
    ticker: str
    statements: list[FinancialStatement]
    
@dataclass
class KeyMetric:
    category: str
    name: str
    key: str
    value: float | None
    raw_value: str | None = None
    
@dataclass
class KeyMetricsResearch:
    ticker: str
    metrics: list[KeyMetric]
    
@dataclass
class NewsEntity:
    symbol: str
    name: str
    country: str | None = None
    entity_type: str | None = None
    match_score: float | None = None
    sentiment_score: float | None = None
    
@dataclass
class NewsArticle:
    title: str
    summary: str | None
    url: str
    source: str
    published_at: str | None
    image_url: str | None = None

    relevance_score: float | None = None
    target_match_score: float | None = None
    relevance_type: str | None = None

    entities: list[NewsEntity] | None = None

@dataclass
class NewsResearch:
    ticker: str
    articles: list[NewsArticle]
    
@dataclass
class HistoricalCandle:
    timestamp: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None
    open_interest: int | None
    
@dataclass
class HistoricalMarketData:
    ticker: str
    candles: list[HistoricalCandle]