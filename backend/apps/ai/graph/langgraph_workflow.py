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
        portfolio_backtest_engine=None,
        portfolio_backtest_evaluator=None,
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
        self.portfolio_backtest_engine = portfolio_backtest_engine
        self.portfolio_backtest_evaluator = portfolio_backtest_evaluator
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
        route = "portfolio" if portfolio_input is not None else self.router.route(user_message)
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
        graph.add_node("portfolio_risk", self._execute_portfolio_risk_node)
        graph.add_node("portfolio_backtest", self._execute_portfolio_backtest_node)

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

        graph.add_conditional_edges(
            "portfolio",
            self._portfolio_decision,
            {
                "portfolio_optimization": "portfolio_optimization",
                "portfolio_risk": "portfolio_risk",
            },
        )
        graph.add_conditional_edges(
            "risk",
            self._risk_decision,
            {
                "portfolio_optimization": "portfolio_optimization",
                "synthesis": "synthesis",
            },
        )
        graph.add_edge("portfolio_optimization", "portfolio_risk")
        # portfolio_risk routes to portfolio_backtest when include_backtest is True,
        # otherwise directly to synthesis.
        graph.add_conditional_edges(
            "portfolio_risk",
            self._portfolio_risk_decision,
            {
                "portfolio_backtest": "portfolio_backtest",
                "synthesis": "synthesis",
            },
        )
        graph.add_edge("portfolio_backtest", "synthesis")
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
        if state.get("portfolio_input") is not None or route == "portfolio":
            resolved_route = "portfolio"
        else:
            resolved_route = route or self.router.route(state.get("user_message", ""))
        value = {"route": resolved_route}
        self.observer.node_completed(
            thread_id=thread_id,
            node="router",
            route=resolved_route,
        )
        return value

    def _route_decision(self, state: dict[str, Any]) -> WorkflowRoute | list[str]:
        if state.get("portfolio_input") is not None or state.get("route") == "portfolio":
            return "portfolio"
        route = state.get("route") or self.router.route(state.get("user_message", ""))
        if route == "general":
            return ["financial", "market", "news"]
        return route

    def _research_decision(self, state: dict[str, Any]) -> str:
        route = state.get("route") or self.router.route(state.get("user_message", ""))
        return "risk" if route == "general" else "synthesis"

    def _portfolio_decision(self, state: dict[str, Any]) -> str:
        message = (state.get("user_message") or "").casefold()
        portfolio_input = state.get("portfolio_input")
        if "optimiz" in message or (portfolio_input and getattr(portfolio_input, "optimization_input", None) is not None):
            return "portfolio_optimization"
        return "portfolio_risk"

    def _portfolio_risk_decision(self, state: dict[str, Any]) -> str:
        """Route to portfolio_backtest when include_backtest is True, otherwise to synthesis."""
        portfolio_input = state.get("portfolio_input")
        if portfolio_input is not None and getattr(portfolio_input, "include_backtest", False):
            return "portfolio_backtest"
        return "synthesis"

    def _risk_decision(self, state: dict[str, Any]) -> str:
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

    def _execute_portfolio_risk_node(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        thread_id = state.get("thread_id")
        route = state.get("route")
        self.observer.node_started(
            thread_id=thread_id,
            node="portfolio_risk",
            route=route,
        )

        portfolio_input = state.get("portfolio_input")
        if portfolio_input is None:
            message = "portfolio_risk: Portfolio input is required."
            self.observer.node_failed(
                thread_id=thread_id,
                node="portfolio_risk",
                route=route,
                error_type="ValueError",
                error_message=message,
            )
            return {"errors": [message]}

        try:
            from apps.ai.portfolio.risk import PortfolioRiskEngine, calculate_current_weights

            # 1. Read historical prices
            historical_prices = getattr(portfolio_input, "historical_prices", None)
            if not historical_prices and portfolio_input.optimization_input:
                historical_prices = portfolio_input.optimization_input.historical_prices

            if not historical_prices:
                raise ValueError("portfolio_risk: Historical prices are missing from portfolio input.")

            # 2. Calculate current portfolio weights
            if self.portfolio_intelligence is None:
                raise ValueError("portfolio_risk: Portfolio intelligence service is not configured.")

            last_prices = self.portfolio_intelligence.get_last_prices(portfolio_input.portfolio)
            current_weights = calculate_current_weights(portfolio_input.portfolio, last_prices)

            # 3. Call PortfolioRiskEngine for current portfolio risk
            risk_engine = PortfolioRiskEngine()
            current_risk = risk_engine.calculate(historical_prices, current_weights)

            # 4. If OptimizationResult exists and is successful:
            optimized_risk = None
            root = state.get("__root__", state)
            results = root.get("results", {}) if isinstance(root, dict) else {}
            opt_result = results.get("portfolio_optimization")

            if opt_result is not None:
                success = getattr(opt_result, "success", False)
                if isinstance(opt_result, dict):
                    success = opt_result.get("success", False)

                if success:
                    optimized_weights = getattr(opt_result, "optimized_weights", None)
                    if isinstance(opt_result, dict):
                        optimized_weights = opt_result.get("optimized_weights")

                    if optimized_weights:
                        optimized_risk = risk_engine.calculate(historical_prices, optimized_weights)

            # 5. Store in state.results["portfolio_risk"]
            payload = {
                "results": {
                    "portfolio_risk": {
                        "current_risk": current_risk,
                        "optimized_risk": optimized_risk,
                    }
                }
            }
            self.observer.node_completed(
                thread_id=thread_id,
                node="portfolio_risk",
                route=route,
                result_count=len(payload.get("results", {})),
            )
            return payload

        except Exception as exc:
            message = f"portfolio_risk: {exc}"
            self.observer.node_failed(
                thread_id=thread_id,
                node="portfolio_risk",
                route=route,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return {"errors": [message]}

    def _execute_portfolio_backtest_node(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Deterministic backtest node — orchestrates Builder → Engine → Evaluator.

        LangGraph is the orchestrator only.  No financial calculations happen here.
        All numeric work is delegated to the existing deterministic services.
        """
        thread_id = state.get("thread_id")
        route = state.get("route")
        self.observer.node_started(
            thread_id=thread_id,
            node="portfolio_backtest",
            route=route,
        )

        portfolio_input = state.get("portfolio_input")
        if portfolio_input is None:
            message = "portfolio_backtest: Portfolio input is required."
            self.observer.node_failed(
                thread_id=thread_id,
                node="portfolio_backtest",
                route=route,
                error_type="ValueError",
                error_message=message,
            )
            return {"errors": [message]}

        if not getattr(portfolio_input, "include_backtest", False):
            # Guard: this node should not be reached when include_backtest is False,
            # but be defensive in case the graph topology changes in future.
            self.observer.node_completed(
                thread_id=thread_id,
                node="portfolio_backtest",
                route=route,
            )
            return {}

        try:
            from apps.ai.portfolio.backtest import (
                PortfolioBacktestEngine,
                PortfolioBacktestResult,
            )
            from apps.ai.portfolio.backtest_evaluator import PortfolioBacktestEvaluator
            from apps.portfolio.backtest_builder import PortfolioBacktestInputBuilder

            # -----------------------------------------------------------------
            # Resolve the Django Portfolio ORM instance
            # -----------------------------------------------------------------
            portfolio_id = getattr(portfolio_input, "django_portfolio_id", None)
            if portfolio_id is None:
                raise ValueError(
                    "portfolio_backtest: 'django_portfolio_id' is required in PortfolioWorkflowInput "
                    "to resolve the persisted portfolio for backtesting."
                )

            from apps.portfolio.models import Portfolio as DjangoPortfolio

            django_portfolio = DjangoPortfolio.objects.get(pk=portfolio_id)


            # -----------------------------------------------------------------
            # Build PortfolioBacktestInput via the existing deterministic builder
            # -----------------------------------------------------------------
            builder = PortfolioBacktestInputBuilder()
            backtest_input = builder.build_backtest_input(
                portfolio=django_portfolio,
                from_date=getattr(portfolio_input, "backtest_from_date", None),
                to_date=getattr(portfolio_input, "backtest_to_date", None),
                benchmark_ticker=getattr(portfolio_input, "backtest_benchmark_ticker", None),
                initial_capital=getattr(portfolio_input, "backtest_initial_capital", 100_000.0),
                rebalance_frequency=getattr(portfolio_input, "backtest_rebalance_frequency", "monthly"),
                in_sample_window_days=getattr(portfolio_input, "backtest_in_sample_window_days", 252),
                out_of_sample_step_days=getattr(portfolio_input, "backtest_out_of_sample_step_days", 21),
                transaction_cost_bps=getattr(portfolio_input, "backtest_transaction_cost_bps", 10.0),
                risk_free_rate=getattr(portfolio_input, "backtest_risk_free_rate", 0.0),
                min_weight=getattr(portfolio_input, "backtest_min_weight", 0.0),
                max_weight=getattr(portfolio_input, "backtest_max_weight", 1.0),
            )


            # -----------------------------------------------------------------
            # Run the deterministic backtest engine
            # -----------------------------------------------------------------
            engine = self.portfolio_backtest_engine or PortfolioBacktestEngine()
            raw_result: PortfolioBacktestResult = engine.run(backtest_input)

            # -----------------------------------------------------------------
            # Evaluate (add risk metrics, relative metrics, buy-and-hold)
            # -----------------------------------------------------------------
            evaluator = self.portfolio_backtest_evaluator or PortfolioBacktestEvaluator()
            evaluated_result: PortfolioBacktestResult = evaluator.evaluate(
                input_data=backtest_input,
                backtest_result=raw_result,
            )

            # -----------------------------------------------------------------
            # Serialise to a plain dict for the synthesis agent
            # -----------------------------------------------------------------
            result_payload = self._serialise_backtest_result(evaluated_result, backtest_input)

            payload = {
                "results": {
                    "portfolio_backtest": result_payload,
                }
            }
            self.observer.node_completed(
                thread_id=thread_id,
                node="portfolio_backtest",
                route=route,
                result_count=1,
            )
            return payload

        except Exception as exc:
            message = f"portfolio_backtest: {exc}"
            self.observer.node_failed(
                thread_id=thread_id,
                node="portfolio_backtest",
                route=route,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            # Non-fatal: backtest failure must not block synthesis for the rest
            # of the portfolio workflow.  Store the error in errors list and
            # return a minimal failure payload so synthesis can report it.
            return {
                "errors": [message],
                "results": {
                    "portfolio_backtest": {
                        "success": False,
                        "error": str(exc),
                    }
                },
            }

    @staticmethod
    def _serialise_backtest_result(
        result: Any,
        input_data: Any,
    ) -> dict[str, Any]:
        """Convert PortfolioBacktestResult into a clean dict for the synthesis context."""
        def _safe_dump(obj: Any) -> Any:
            if obj is None:
                return None
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if hasattr(obj, "dict"):
                return obj.dict()
            return obj

        strategy = _safe_dump(getattr(result, "strategy_metrics", None))
        buy_and_hold = _safe_dump(getattr(result, "buy_and_hold_metrics", None))
        benchmark = _safe_dump(getattr(result, "benchmark_metrics", None))
        relative = _safe_dump(getattr(result, "relative_metrics", None))

        rebalance_events_raw = getattr(result, "rebalance_events", None) or []
        rebalance_summary = [
            {
                "date": getattr(ev, "date", None),
                "portfolio_value_before": getattr(ev, "portfolio_value_before", None),
                "portfolio_value_after": getattr(ev, "portfolio_value_after", None),
                "target_weights": getattr(ev, "target_weights", None),
                "turnover": getattr(ev, "turnover", None),
                "transaction_cost": getattr(ev, "transaction_cost", None),
            }
            for ev in rebalance_events_raw
        ]

        equity_curve = getattr(result, "equity_curve", None) or []
        # Limit equity curve points sent to synthesis to avoid blowing the context window.
        # First + last 5 + every ~20th point gives the LLM enough shape without flooding it.
        if len(equity_curve) > 30:
            sampled: list[Any] = [equity_curve[0]]
            step = max(1, len(equity_curve) // 20)
            sampled += equity_curve[1:-1:step]
            sampled.append(equity_curve[-1])
            equity_curve_summary = sampled
        else:
            equity_curve_summary = equity_curve

        return {
            "success": getattr(result, "success", False),
            "message": getattr(result, "message", ""),
            "tickers": getattr(input_data, "tickers", []),
            "from_date": getattr(input_data, "backtest_from_date", None)
                if hasattr(input_data, "backtest_from_date")
                else None,
            "to_date": getattr(input_data, "backtest_to_date", None)
                if hasattr(input_data, "backtest_to_date")
                else None,
            "benchmark_ticker": getattr(result, "benchmark_ticker", None),
            "initial_capital": getattr(input_data, "initial_capital", None),
            "final_portfolio_value": getattr(result, "final_portfolio_value", None),
            "total_transaction_costs": getattr(result, "total_transaction_costs", None),
            "rebalance_count": len(rebalance_summary),
            "rebalance_events_summary": rebalance_summary,
            "equity_curve_sample": equity_curve_summary,
            "strategy_metrics": strategy,
            "buy_and_hold_metrics": buy_and_hold,
            "benchmark_metrics": benchmark,
            "relative_metrics": relative,
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
