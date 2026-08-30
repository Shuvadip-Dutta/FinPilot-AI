"""Typed contracts shared by graph workflow components."""

from typing import Literal

from pydantic import BaseModel


class WorkflowDecision(BaseModel):
    """The selected workflow route and its routing rationale."""

    route: Literal[
        "financial",
        "market",
        "news",
        "general",
    ]
    reason: str
