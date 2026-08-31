"""LangGraph orchestration for the FinPilot AI research workflow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from apps.ai.agents.base import BaseAgent
from apps.ai.exceptions import AIError
from apps.ai.graph.router import WorkflowRouter, WorkflowRoute
from apps.ai.graph.state import AgentState
from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput


def _merge_graph_state(current: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    for key, value in update.items():
        if key == "results" and isinstance(merged.get("results"), dict) and isinstance(value, dict):
            merged["results"] = {**merged["results"], **value}
        elif key == "errors" and isinstance(merged.get("errors"), list) and isinstance(value, list):
            merged["errors"] = [*merged["errors"], *value]
        else:
            merged[key] = value
    return merged


class GraphState(TypedDict):
    """Root state that allows independent branch updates to merge safely."""

    __root__: Annotated[dict[str, Any], _merge_graph_state]


class LangGraphResearchWorkflow:
    """Execute the research workflow using a compiled LangGraph graph."""

    def __init__(
        self,
        router: WorkflowRouter,
        financial_agent: BaseAgent,
        market_agent: BaseAgent,
        news_agent: BaseAgent,
        synthesis_agent: BaseAgent | None = None,
        risk_agent: BaseAgent | None = None,
        portfolio_intelligence=None,
        portfolio_optimization_agent: BaseAgent | None = None,
    ):
        self.router = router
        self.financial_agent = financial_agent
        self.market_agent = market_agent
        self.news_agent = news_agent
        self.synthesis_agent = synthesis_agent
        self.risk_agent = risk_agent
        self.portfolio_intelligence = portfolio_intelligence
        self.portfolio_optimization_agent = portfolio_optimization_agent
        self._graph = self._build_graph()

    def run(
        self,
        user_message: str,
        ticker: str | None = None,
        market: str | None = None,
        portfolio_input: PortfolioWorkflowInput | None = None,
    ) -> AgentState:
        """Execute the compiled graph for a user request."""
        initial_state = {
            "user_message": user_message,
            "ticker": ticker,
            "market": market,
            "portfolio_input": portfolio_input,
            "route": self.router.route(user_message),
            "results": {},
            "errors": [],
        }
        result = self._graph.invoke(initial_state)
        return self._to_agent_state(result)

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_edge(START, "router")

        graph.add_node("router", self._route_node)
        graph.add_node("financial", self._execute_agent_node("financial"))
        graph.add_node("market", self._execute_agent_node("market"))
        graph.add_node("news", self._execute_agent_node("news"))
        graph.add_node("risk", self._execute_risk_node)
        graph.add_node("synthesis", self._execute_synthesis_node)
        graph.add_node("portfolio", self._execute_portfolio_node)
        graph.add_node("portfolio_optimization", self._execute_portfolio_optimization_node)

        graph.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "financial": "financial",
                "market": "market",
                "news": "news",
                "portfolio": "portfolio",
                "risk": "risk",
            },
        )

        graph.add_conditional_edges(
            "financial",
            self._research_decision,
            {
                "risk": "risk",
                "synthesis": "synthesis",
            },
        )
        graph.add_conditional_edges(
            "market",
            self._research_decision,
            {
                "risk": "risk",
                "synthesis": "synthesis",
            },
        )
        graph.add_conditional_edges(
            "news",
            self._research_decision,
            {
                "risk": "risk",
                "synthesis": "synthesis",
            },
        )

        graph.add_edge("portfolio", "risk")
        graph.add_conditional_edges(
            "risk",
            self._risk_decision,
            {
                "portfolio_optimization": "portfolio_optimization",
                "synthesis": "synthesis",
            },
        )
        graph.add_edge("portfolio_optimization", "synthesis")
        graph.add_edge("synthesis", END)

        return graph.compile()

    def _route_node(self, state: dict[str, Any]) -> dict[str, Any]:
        route = self.router.route(state.get("user_message", ""))
        return {"route": route}

    def _route_decision(self, state: dict[str, Any]) -> WorkflowRoute | list[str]:
        route = state.get("route") or self.router.route(state.get("user_message", ""))
        if route == "general":
            return ["financial", "market", "news"]
        return route

    def _research_decision(self, state: dict[str, Any]) -> str:
        route = state.get("route") or self.router.route(state.get("user_message", ""))
        return "risk" if route == "general" else "synthesis"

    def _risk_decision(self, state: dict[str, Any]) -> str:
        if state.get("route") == "portfolio":
            message = (state.get("user_message") or "").casefold()
            if "optimiz" in message:
                return "portfolio_optimization"
        return "synthesis"

    def _execute_agent_node(self, key: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def _node(state: dict[str, Any]) -> dict[str, Any]:
            try:
                agent = {
                    "financial": self.financial_agent,
                    "market": self.market_agent,
                    "news": self.news_agent,
                }[key]
                result = agent.run(state["user_message"])
                return {"results": {key: result}}
            except (AIError, ValueError, TypeError) as exc:
                return {
                    "errors": [
                        f"{key}: {exc}"
                    ]
                }

        return _node

    def _execute_synthesis_node(self, state: dict[str, Any]) -> dict[str, Any]:
        if self.synthesis_agent is None:
            return {}

        try:
            final_state = self._to_agent_state(state)
            result = self.synthesis_agent.run(final_state)

            return {
                "results": {
                    "synthesis": result,
                }
            }

        except (AIError, ValueError, TypeError) as exc:
            return {
                "errors": [
                    f"synthesis: {exc}"
                ]
            }
            
    def _execute_risk_node(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        if self.risk_agent is None:
            return {}

        try:
            final_state = self._to_agent_state(state)

            result = self.risk_agent.run(
                final_state
            )

            return {
                "results": {
                    "risk": result,
                }
            }

        except (AIError, ValueError, TypeError) as exc:
            return {
                "errors": [
                    f"risk: {exc}"
                ]
            }
            
    def _execute_portfolio_node(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        if self.portfolio_intelligence is None:
            return {
                "errors": [
                    "portfolio: Portfolio intelligence service is not configured."
                ]
            }

        portfolio_input = state.get(
            "portfolio_input"
        )

        if portfolio_input is None:
            return {
                "errors": [
                    "portfolio: Portfolio input is required."
                ]
            }

        try:
            result = self.portfolio_intelligence.analyze(
                portfolio_input.portfolio
            )

            return {
                "results": {
                    "portfolio": result,
                }
            }

        except (AIError, ValueError, TypeError) as exc:
            return {
                "errors": [
                    f"portfolio: {exc}"
                ]
            }
            
            
    def _execute_portfolio_optimization_node(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        if self.portfolio_optimization_agent is None:
            return {
                "errors": [
                    "portfolio_optimization: Agent is not configured."
                ]
            }

        portfolio_input = state.get(
            "portfolio_input"
        )

        if (
            portfolio_input is None
            or portfolio_input.optimization_input is None
        ):
            return {
                "errors": [
                    "portfolio_optimization: "
                    "Optimization input is required."
                ]
            }

        try:
            result = self.portfolio_optimization_agent.run(
                portfolio_input.optimization_input
            )

            return {
                "results": {
                    "portfolio_optimization": result,
                }
            }

        except (AIError, ValueError, TypeError) as exc:
            return {
                "errors": [
                    f"portfolio_optimization: {exc}"
                ]
            }
            
            
    def _optimization_decision(
        self,
        state: dict[str, Any],
    ) -> str:
        message = state.get(
            "user_message",
            "",
        ).casefold()

        if "optimiz" in message:
            return "portfolio_optimization"

        return "synthesis"

    def _to_agent_state(self, state: dict[str, Any]) -> AgentState:
        root = state.get("__root__", state)
        results = dict(root.get("results", {}))
        errors = list(root.get("errors", []))
        route = root.get("route")
        return AgentState(
            user_message=root.get("user_message", ""),
            ticker=root.get("ticker"),
            market=root.get("market"),
            route=route,
            results=results,
            errors=errors,
        )

