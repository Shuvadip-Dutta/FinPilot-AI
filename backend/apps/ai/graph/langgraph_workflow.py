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
from apps.ai.graph.persistence import LangGraphPersistence
from apps.ai.observability import AIObserver
from langgraph.checkpoint.base import BaseCheckpointSaver


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
        checkpointer: BaseCheckpointSaver | None = None,
        persistence: LangGraphPersistence | None = None,
    ):
        self.router = router
        self.financial_agent = financial_agent
        self.market_agent = market_agent
        self.news_agent = news_agent
        self.synthesis_agent = synthesis_agent
        self.risk_agent = risk_agent
        self.portfolio_intelligence = portfolio_intelligence
        self.portfolio_optimization_agent = portfolio_optimization_agent
        self.observer = AIObserver()

        self._checkpointer = checkpointer
        if self._checkpointer is None:
            self.persistence = LangGraphPersistence()
            self._checkpointer = self.persistence.start()
        else:
            self.persistence = None
        self._graph = self._build_graph()

    def run(
        self,
        user_message: str,
        ticker: str | None = None,
        market: str | None = None,
        portfolio_input: PortfolioWorkflowInput | None = None,
        thread_id: str = "default",
    ) -> AgentState:
        """Execute the compiled graph for a user request."""
        route = self.router.route(user_message)
        initial_state = {
            "user_message": user_message,
            "ticker": ticker,
            "market": market,
            "portfolio_input": portfolio_input,
            "thread_id": thread_id,
            "route": route,
            "results": {},
            "errors": [],
        }
        self.observer.graph_started(thread_id=thread_id, route=route)
        try:
            result = self._graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": thread_id}},
            )
            state = self._to_agent_state(result)
            self.observer.graph_completed(
                thread_id=thread_id,
                route=route,
                result_count=len(state.results),
                error_count=len(state.errors),
            )
            return state
        except Exception as exc:
            self.observer.graph_failed(
                thread_id=thread_id,
                route=route,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise

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

        return graph.compile(
            checkpointer=self._checkpointer,
        )
        
    def close(self) -> None:
        if self.persistence is not None:
            self.persistence.close()

    def _route_node(self, state: dict[str, Any]) -> dict[str, Any]:
        thread_id = state.get("thread_id")
        route = state.get("route")
        self.observer.node_started(
            thread_id=thread_id,
            node="router",
            route=route,
        )
        resolved_route = self.router.route(state.get("user_message", ""))
        value = {"route": resolved_route}
        self.observer.node_completed(
            thread_id=thread_id,
            node="router",
            route=resolved_route,
        )
        return value

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
            thread_id = state.get("thread_id")
            route = state.get("route")
            self.observer.node_started(
                thread_id=thread_id,
                node=key,
                route=route,
            )
            try:
                agent = {
                    "financial": self.financial_agent,
                    "market": self.market_agent,
                    "news": self.news_agent,
                }[key]
                result = agent.run(state["user_message"])
                payload = {"results": {key: result.model_dump()}}
                self.observer.node_completed(
                    thread_id=thread_id,
                    node=key,
                    route=route,
                    result_count=len(payload.get("results", {})),
                )
                return payload
            except (AIError, ValueError, TypeError) as exc:
                message = f"{key}: {exc}"
                self.observer.node_failed(
                    thread_id=thread_id,
                    node=key,
                    route=route,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                return {
                    "errors": [
                        message
                    ]
                }

        return _node

    def _execute_synthesis_node(self, state: dict[str, Any]) -> dict[str, Any]:
        thread_id = state.get("thread_id")
        route = state.get("route")
        self.observer.node_started(
            thread_id=thread_id,
            node="synthesis",
            route=route,
        )
        if self.synthesis_agent is None:
            self.observer.node_completed(
                thread_id=thread_id,
                node="synthesis",
                route=route,
            )
            return {}

        try:
            final_state = self._to_agent_state(state)
            result = self.synthesis_agent.run(final_state)
            payload = {
                "results": {
                    "synthesis": result,
                }
            }
            self.observer.node_completed(
                thread_id=thread_id,
                node="synthesis",
                route=route,
                result_count=len(payload.get("results", {})),
            )
            return payload

        except (AIError, ValueError, TypeError) as exc:
            message = f"synthesis: {exc}"
            self.observer.node_failed(
                thread_id=thread_id,
                node="synthesis",
                route=route,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return {
                "errors": [
                    message
                ]
            }
            
    def _execute_risk_node(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        thread_id = state.get("thread_id")
        route = state.get("route")
        self.observer.node_started(
            thread_id=thread_id,
            node="risk",
            route=route,
        )
        if self.risk_agent is None:
            self.observer.node_completed(
                thread_id=thread_id,
                node="risk",
                route=route,
            )
            return {}

        try:
            final_state = self._to_agent_state(state)

            result = self.risk_agent.run(
                final_state
            )
            payload = {
                "results": {
                    "risk": result,
                }
            }
            self.observer.node_completed(
                thread_id=thread_id,
                node="risk",
                route=route,
                result_count=len(payload.get("results", {})),
            )
            return payload

        except (AIError, ValueError, TypeError) as exc:
            message = f"risk: {exc}"
            self.observer.node_failed(
                thread_id=thread_id,
                node="risk",
                route=route,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return {
                "errors": [
                    message
                ]
            }
            
    def _execute_portfolio_node(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        thread_id = state.get("thread_id")
        route = state.get("route")
        self.observer.node_started(
            thread_id=thread_id,
            node="portfolio",
            route=route,
        )
        if self.portfolio_intelligence is None:
            message = "portfolio: Portfolio intelligence service is not configured."
            self.observer.node_failed(
                thread_id=thread_id,
                node="portfolio",
                route=route,
                error_type="ConfigurationError",
                error_message=message,
            )
            return {
                "errors": [
                    message
                ]
            }

        portfolio_input = state.get(
            "portfolio_input"
        )

        if portfolio_input is None:
            message = "portfolio: Portfolio input is required."
            self.observer.node_failed(
                thread_id=thread_id,
                node="portfolio",
                route=route,
                error_type="ValueError",
                error_message=message,
            )
            return {
                "errors": [
                    message
                ]
            }

        try:
            result = self.portfolio_intelligence.analyze(
                portfolio_input.portfolio
            )
            payload = {
                "results": {
                    "portfolio": result,
                }
            }
            self.observer.node_completed(
                thread_id=thread_id,
                node="portfolio",
                route=route,
                result_count=len(payload.get("results", {})),
            )
            return payload

        except (AIError, ValueError, TypeError) as exc:
            message = f"portfolio: {exc}"
            self.observer.node_failed(
                thread_id=thread_id,
                node="portfolio",
                route=route,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return {
                "errors": [
                    message
                ]
            }
            
            
    def _execute_portfolio_optimization_node(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        thread_id = state.get("thread_id")
        route = state.get("route")
        self.observer.node_started(
            thread_id=thread_id,
            node="portfolio_optimization",
            route=route,
        )
        if self.portfolio_optimization_agent is None:
            message = "portfolio_optimization: Agent is not configured."
            self.observer.node_failed(
                thread_id=thread_id,
                node="portfolio_optimization",
                route=route,
                error_type="ConfigurationError",
                error_message=message,
            )
            return {
                "errors": [
                    message
                ]
            }

        portfolio_input = state.get(
            "portfolio_input"
        )

        if (
            portfolio_input is None
            or portfolio_input.optimization_input is None
        ):
            message = "portfolio_optimization: Optimization input is required."
            self.observer.node_failed(
                thread_id=thread_id,
                node="portfolio_optimization",
                route=route,
                error_type="ValueError",
                error_message=message,
            )
            return {
                "errors": [
                    message
                ]
            }

        try:
            result = self.portfolio_optimization_agent.run(
                portfolio_input.optimization_input
            )
            payload = {
                "results": {
                    "portfolio_optimization": result,
                }
            }
            self.observer.node_completed(
                thread_id=thread_id,
                node="portfolio_optimization",
                route=route,
                result_count=len(payload.get("results", {})),
            )
            return payload

        except (AIError, ValueError, TypeError) as exc:
            message = f"portfolio_optimization: {exc}"
            self.observer.node_failed(
                thread_id=thread_id,
                node="portfolio_optimization",
                route=route,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return {
                "errors": [
                    message
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

