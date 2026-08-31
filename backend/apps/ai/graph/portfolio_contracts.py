"""Contracts for portfolio-oriented LangGraph workflows."""

from pydantic import BaseModel

from apps.ai.portfolio.optimization import OptimizationInput
from apps.ai.portfolio.schemas import Portfolio


class PortfolioWorkflowInput(BaseModel):
    """Validated inputs supplied to a portfolio LangGraph workflow."""

    portfolio: Portfolio
    optimization_input: OptimizationInput | None = None