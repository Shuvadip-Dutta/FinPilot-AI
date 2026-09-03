"""Agent for explaining deterministic portfolio optimization results."""

import json
from collections.abc import Callable

from apps.ai.agents.base import BaseAgent
from apps.ai.exceptions import LLMError
from apps.ai.portfolio.optimization import (
    OptimizationInput,
    OptimizationResult,
    PortfolioOptimizationEngine,
)
from apps.ai.services.llm_service import LLMService
from apps.ai.services.schemas import AgentResult


class PortfolioOptimizationAgent(BaseAgent):
    """Run deterministic optimization and interpret the result with the reasoning model."""

    def __init__(
        self,
        optimization_engine: PortfolioOptimizationEngine | None = None,
        optimizer: Callable[
            [OptimizationInput],
            OptimizationResult,
        ]
        | None = None,
        llm_service: Callable[[list[dict[str, str]]], str] | None = None,
    ):
        self.optimization_engine = (
            optimization_engine
            or PortfolioOptimizationEngine()
        )
        self.optimizer = optimizer or self.optimization_engine.optimize
        self.llm_service = llm_service or LLMService(model="portfolio")

    @property
    def name(self) -> str:
        return "portfolio_optimization"

    def run(
        self,
        optimization_input: OptimizationInput,
    ) -> AgentResult:
        """Optimize a portfolio, then explain the result using the reasoning model."""

        try:
            result = self.optimizer(optimization_input)
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

        if self.llm_service is None:
            self.llm_service = LLMService(model="portfolio")

        messages = self._build_explanation_messages(
            optimization_input=optimization_input,
            result=result,
        )

        try:
            response = self.llm_service(messages)
        except LLMError:
            raise

        if not isinstance(response, str) or not response.strip():
            return AgentResult(
                response=(
                    "Unable to explain the portfolio optimization result: "
                    "the reasoning model returned an empty response."
                ),
                tools_used=["portfolio_optimization"],
            )

        return AgentResult(
            response=response.strip(),
            tools_used=["portfolio_optimization"],
        )

    def _build_explanation_messages(
        self,
        optimization_input: OptimizationInput,
        result: OptimizationResult,
    ) -> list[dict[str, str]]:
        system_prompt = (
            "You are the portfolio optimization explanation specialist for FinPilot AI. "
            "The optimizer output in this prompt is authoritative. Do not modify, recompute, or reinterpret the numerical values. "
            "Use the supplied optimization result and constraints to explain the outcome in plain language. "
            "Describe the allocation, diversification, concentration, and risk-adjusted trade-off using only the supplied optimizer values. "
            "Explain how the min/max bounds may shape the final allocation when relevant. "
            "Call out historical-data limitations, dependency on the supplied constraints, and the fact that a high Sharpe ratio in sample data does not guarantee future performance. "
            "Do not invent values that are absent. Do not calculate replacement weights or alternative metrics. "
            "Do not guarantee future returns. Do not provide an unconditional buy/sell recommendation. Distinguish objective optimizer output from explanatory interpretation."
        )

        context = {
            "OPTIMIZATION INPUT": {
                "tickers": optimization_input.tickers,
                "risk_free_rate": optimization_input.risk_free_rate,
                "min_weight": optimization_input.min_weight,
                "max_weight": optimization_input.max_weight,
                "historical_data_summary": {
                    ticker: {
                        "observations": len(prices),
                        "first_price": prices[0],
                        "last_price": prices[-1],
                        "min_price": min(prices),
                        "max_price": max(prices),
                    }
                    for ticker, prices in optimization_input.historical_prices.items()
                },
            },
            "OPTIMIZATION RESULT": {
                "success": result.success,
                "message": result.message,
                "optimized_weights": result.optimized_weights,
                "expected_return": result.expected_return,
                "volatility": result.volatility,
                "sharpe_ratio": result.sharpe_ratio,
                "total_weight": result.total_weight,
            },
            "CONSTRAINTS": {
                "min_weight": optimization_input.min_weight,
                "max_weight": optimization_input.max_weight,
                "total_weight_target": 1.0,
            },
            "INSTRUCTIONS": [
                "Numerical values from OPTIMIZATION RESULT are authoritative.",
                "Do not change or reinterpret optimizer values.",
                "Do not invent missing values or recompute metrics.",
                "Do not claim certainty about future performance.",
                "Do not give an unconditional buy or sell recommendation.",
                "Explain the allocation and risk-adjusted trade-off only using the supplied optimization output.",
            ],
        }

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    context,
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ]

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