from typing import Literal

from pydantic import BaseModel, Field


class AgentState(BaseModel):

    user_message: str

    ticker: str | None = None

    market: str | None = None

    route: Literal[
        "financial",
        "market",
        "news",
        "general",
    ] | None = None

    results: dict[str, object] = Field(
        default_factory=dict
    )

    errors: list[str] = Field(
        default_factory=list
    )
