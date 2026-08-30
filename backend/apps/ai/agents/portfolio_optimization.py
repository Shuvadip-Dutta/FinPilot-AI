"""Agent for explaining deterministic portfolio optimization results."""

from collections.abc import Callable

from apps.ai.agents.base import BaseAgent
from apps.ai.portfolio.optimization import (
    OptimizationInput,
    OptimizationResult,
    PortfolioOptimizationEngine,
)
from apps.ai.services.schemas import AgentResult


class PortfolioOptimizationAgent(BaseAgent):
    """Run portfolio optimization and explain the resulting allocation."""

    def __init__(
        self,
        optimization_engine: PortfolioOptimizationEngine | None = None,
        optimizer: Callable[
            [OptimizationInput],
            OptimizationResult,
        ]
        | None = None,
    ):
        self.optimization_engine = (
            optimization_engine
            or PortfolioOptimizationEngine()
        )
        self.optimizer = optimizer or self.optimization_engine.optimize

    @property
    def name(self) -> str:
        return "portfolio_optimization"

    def run(
        self,
        optimization_input: OptimizationInput,
    ) -> AgentResult:
        """Optimize a portfolio and return a concise explanation."""

        try:
            result = self.optimizer(
                optimization_input
            )
        except ValueError as exc:
            return AgentResult(
                response=(
                    "Unable to optimize the portfolio: "
                    f"{exc}"
                ),
                tools_used=[],
            )

        if not result.success:
            return AgentResult(
                response=(
                    "Portfolio optimization could not be completed: "
                    f"{result.message}"
                ),
                tools_used=[],
            )

        return AgentResult(
            response=self._build_response(result),
            tools_used=["portfolio_optimization"],
        )

    @staticmethod
    def _build_response(
        result: OptimizationResult,
    ) -> str:
        weights = result.optimized_weights or {}

        allocation_parts = [
            f"{ticker}: {weight * 100:.2f}%"
            for ticker, weight in weights.items()
        ]

        allocation_text = (
            ", ".join(allocation_parts)
            if allocation_parts
            else "No allocation available"
        )

        expected_return = (
            f"{result.expected_return * 100:.2f}%"
            if result.expected_return is not None
            else "N/A"
        )

        volatility = (
            f"{result.volatility * 100:.2f}%"
            if result.volatility is not None
            else "N/A"
        )

        sharpe = (
            f"{result.sharpe_ratio:.3f}"
            if result.sharpe_ratio is not None
            else "N/A"
        )

        return (
            "Portfolio optimization completed. "
            f"Recommended allocation: {allocation_text}. "
            f"Expected annual return: {expected_return}. "
            f"Annual volatility: {volatility}. "
            f"Sharpe ratio: {sharpe}."
        )