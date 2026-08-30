"""Deterministic risk analysis based on existing workflow results."""

from apps.ai.agents.base import BaseAgent
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult


class RiskAnalysisAgent(BaseAgent):
    """Analyze risk signals from previously collected research results."""

    @property
    def name(self) -> str:
        return "risk"

    def run(self, state: AgentState) -> AgentResult:
        risk_signals: list[str] = []

        financial_result = state.results.get("financial")
        market_result = state.results.get("market")
        news_result = state.results.get("news")

        if financial_result is None:
            risk_signals.append(
                "Financial research data is unavailable."
            )

        if market_result is None:
            risk_signals.append(
                "Current market data is unavailable."
            )

        if news_result is None:
            risk_signals.append(
                "News intelligence is unavailable."
            )

        if not risk_signals:
            risk_signals.append(
                "Financial, market, and news research are available "
                "for risk assessment."
            )

        response = (
            f"Risk analysis for "
            f"{state.ticker or 'the requested company'}: "
            + " ".join(risk_signals)
        )

        return AgentResult(
            response=response,
            tools_used=[],
        )