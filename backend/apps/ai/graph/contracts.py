"""Typed contracts shared by graph workflow components."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.research.services.schemas import (
    CompanyProfile,
    DataStatus,
    FinancialStatement,
    HistoricalMarketData,
    KeyMetricsResearch,
    NewsResearch,
)


class WorkflowDecision(BaseModel):
    """The selected workflow route and its routing rationale."""

    route: Literal[
        "financial",
        "market",
        "news",
        "general",
    ]
    reason: str


class ProviderProvenance(BaseModel):
    """Provenance metadata tracking provider origin and data status for a research section."""

    primary_provider: str
    source: str
    fallback_used: bool = False
    data_status: str = "complete"
    fallback_reason: Optional[str] = None

    @field_validator("data_status")
    @classmethod
    def validate_data_status(cls, v: str) -> str:
        valid_statuses = {s.value for s in DataStatus} | {"complete", "partial", "empty", "failed"}
        if v not in valid_statuses:
            raise ValueError(
                f"Invalid data_status: '{v}'. Must be one of {sorted(valid_statuses)}"
            )
        return v


class ResearchContext(BaseModel):
    """Canonical research context unifying domain research sections and section-level provenance."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ticker: str
    market: str

    company_profile: Optional[CompanyProfile] = None
    financials: Optional[List[FinancialStatement]] = None
    key_metrics: Optional[KeyMetricsResearch] = None
    market_data: Optional[HistoricalMarketData] = None
    news: Optional[NewsResearch] = None

    document_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: Dict[str, ProviderProvenance] = Field(default_factory=dict)
