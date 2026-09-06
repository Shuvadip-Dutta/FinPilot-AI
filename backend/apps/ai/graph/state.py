from typing import Literal

from pydantic import BaseModel, Field

from apps.ai.graph.contracts import ResearchContext
from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput


class AgentState(BaseModel):

    user_message: str

    ticker: str | None = None

    market: str | None = None

    portfolio_input: PortfolioWorkflowInput | None = None

    route: Literal[
        "financial",
        "market",
        "news",
        "risk",
        "portfolio",
        "general",
    ] | None = None

    research_context: ResearchContext | None = None

    results: dict[str, object] = Field(
        default_factory=dict
    )

    errors: list[str] = Field(
        default_factory=list
    )
