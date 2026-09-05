"""LangGraph orchestration for the FinPilot AI research workflow."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from apps.ai.agents.base import AgentResult, BaseAgent
from apps.ai.exceptions import AIError
from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
from apps.ai.graph.router import WorkflowRouter, WorkflowRoute
from apps.ai.graph.state import AgentState
from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.graph.persistence import LangGraphPersistence
from apps.ai.observability import AIObserver
from apps.research.services.schemas import (
    CompanyProfile,
    FinancialStatement,
    HistoricalMarketData,
    KeyMetricsResearch,
    NewsResearch,
)
from apps.research.services.session_service import ResearchSessionService
from apps.research.services.symbols import Market
from langgraph.checkpoint.base import BaseCheckpointSaver


def _merge_research_context(
    base: ResearchContext | dict[str, Any] | None,
    patch: ResearchContext | dict[str, Any] | None,
) -> ResearchContext | None:
    if base is None and patch is None:
        return None

    def _to_rc(val: Any) -> ResearchContext | None:
        if isinstance(val, ResearchContext):
            return val
        if isinstance(val, dict):
            try:
                return ResearchContext.model_validate(val)
            except Exception:
                return None
        return None

    base_rc = _to_rc(base)
    patch_rc = _to_rc(patch)

    if base_rc is None:
        return patch_rc
    if patch_rc is None:
        return base_rc

    ticker = patch_rc.ticker or base_rc.ticker
    market = patch_rc.market or base_rc.market
    company_profile = patch_rc.company_profile or base_rc.company_profile
    financials = patch_rc.financials or base_rc.financials
    key_metrics = patch_rc.key_metrics or base_rc.key_metrics
    market_data = patch_rc.market_data or base_rc.market_data
    news = patch_rc.news or base_rc.news

    merged_prov = dict(base_rc.provenance)
    merged_prov.update(patch_rc.provenance)

    return ResearchContext(
        ticker=ticker,
        market=market,
        company_profile=company_profile,
        financials=financials,
        key_metrics=key_metrics,
        market_data=market_data,
        news=news,
        provenance=merged_prov,
    )


def _extract_research_context_from_result(
    ticker: str,
    market: str,
    result: Any,
) -> ResearchContext | None:
    if not hasattr(result, "data") or not isinstance(result.data, dict):
        if isinstance(result, dict) and "provenance" in result:
            data = result
        else:
            return None
    else:
        data = result.data

    provenance_dict: dict[str, ProviderProvenance] = {}
    p_data = data.get("provenance")
    if isinstance(p_data, dict):
        for sec_name, prov_val in p_data.items():
            if isinstance(prov_val, ProviderProvenance):
                provenance_dict[sec_name] = prov_val
            elif isinstance(prov_val, dict):
                status_val = str(prov_val.get("data_status") or "complete")
                provenance_dict[sec_name] = ProviderProvenance(
                    primary_provider=str(prov_val.get("primary_provider") or prov_val.get("source") or "upstox"),
                    source=str(prov_val.get("source") or prov_val.get("provider_used") or "upstox"),
                    fallback_used=bool(prov_val.get("fallback_used", False)),
                    data_status=status_val if status_val in ("complete", "partial", "empty", "failed") else "complete",
                    fallback_reason=str(prov_val.get("fallback_reason")) if prov_val.get("fallback_reason") else None,
                )

    company_profile = data.get("company_profile") if isinstance(data.get("company_profile"), CompanyProfile) else None
    financials = data.get("financials") if isinstance(data.get("financials"), list) else None
    key_metrics = data.get("key_metrics") if isinstance(data.get("key_metrics"), KeyMetricsResearch) else None
    market_data = data.get("market_data") if isinstance(data.get("market_data"), HistoricalMarketData) else None
    news = data.get("news") if isinstance(data.get("news"), NewsResearch) else None

    if not provenance_dict and not any([company_profile, financials, key_metrics, market_data, news]):
        return None

    return ResearchContext(
        ticker=ticker,
        market=market,
        company_profile=company_profile,
        financials=financials,
        key_metrics=key_metrics,
        market_data=market_data,
        news=news,
        provenance=provenance_dict,
    )


def _merge_graph_state(current: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    for key, value in update.items():
        if key == "results" and isinstance(merged.get("results"), dict) and isinstance(value, dict):
            merged["results"] = {**merged["results"], **value}
        elif key == "errors" and isinstance(merged.get("errors"), list) and isinstance(value, list):
            merged["errors"] = [*merged["errors"], *value]
        elif key == "research_context":
            merged["research_context"] = _merge_research_context(merged.get("research_context"), value)
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
        user: object = None,
        ticker: str | None = None,
        market: str | None = None,
        portfolio_input: PortfolioWorkflowInput | None = None,
        thread_id: str = "default",
    ) -> AgentState:
        """Execute the compiled graph for a user request."""
        start_time = time.perf_counter()
        route = self.router.route(user_message)
        market = Market.normalize(market) or market

        session = None
        try:
            session = ResearchSessionService.create_session(
                user_message=user_message,
                user=user,
                ticker=ticker,
                market=market,
                route=route,
                thread_id=thread_id,
            )
            session.status = "RUNNING"
            session.save(update_fields=["status"])
        except Exception:
            session = None

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

            if session is not None:
                try:
                    latency_ms = (time.perf_counter() - start_time) * 1000.0
                    ResearchSessionService.save_workflow_result(
                        session.id,
                        state,
                        latency_ms=latency_ms,
                        status="COMPLETED",
                    )
                except Exception:
                    try:
                        session.status = "FAILED"
                        session.save(update_fields=["status"])
                    except Exception:
                        pass
                    raise

            return state
        except Exception as exc:
            if session is not None:
                try:
                    session.status = "FAILED"
                    session.save(update_fields=["status"])
                except Exception:
                    pass
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
                agent_state = self._to_agent_state(state)
                result = agent.run(agent_state)
                payload: dict[str, Any] = {
                    "results": {
                        key: result.model_dump() if hasattr(result, "model_dump") else result
                    }
                }
                rc_patch = _extract_research_context_from_result(
                    ticker=agent_state.ticker or "",
                    market=agent_state.market or "IN",
                    result=result,
                )
                if rc_patch is not None:
                    payload["research_context"] = rc_patch

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
            payload: dict[str, Any] = {
                "results": {
                    "risk": result,
                }
            }
            rc_patch = _extract_research_context_from_result(
                ticker=final_state.ticker or "",
                market=final_state.market or "IN",
                result=result,
            )
            if rc_patch is not None:
                payload["research_context"] = rc_patch

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
        rc_val = root.get("research_context")
        rc: ResearchContext | None = None
        if isinstance(rc_val, ResearchContext):
            rc = rc_val
        elif isinstance(rc_val, dict):
            try:
                rc = ResearchContext.model_validate(rc_val)
            except Exception:
                rc = None

        return AgentState(
            user_message=root.get("user_message", ""),
            ticker=root.get("ticker"),
            market=root.get("market"),
            route=route,
            research_context=rc,
            results=results,
            errors=errors,
        )
