"""Coordinator for deterministic specialized research workflows."""

from collections.abc import Iterable

from apps.ai.agents.base import BaseAgent
from apps.ai.exceptions import AIError
from apps.ai.graph.router import WorkflowRouter, WorkflowRoute
from apps.ai.graph.state import AgentState


from apps.ai.graph.langgraph_workflow import (
    _extract_research_context_from_result,
    _merge_research_context,
)


class ResearchWorkflow:
    """Route a request and collect results from specialized research agents.

    Agent execution is intentionally kept behind ``_execute_agents`` so the
    public ``run`` interface can remain unchanged when concurrency is added.
    """

    def __init__(
        self,
        router: WorkflowRouter,
        financial_agent: BaseAgent,
        market_agent: BaseAgent,
        news_agent: BaseAgent,
        synthesis_agent: BaseAgent | None = None,
    ):
        self.router = router
        self.synthesis_agent = synthesis_agent
        self.agents = {
            "financial": financial_agent,
            "market": market_agent,
            "news": news_agent,
        }

    def run(
        self,
        user_message: str,
        ticker: str | None = None,
        market: str | None = None,
    ) -> AgentState:
        """Return the routed research state for a user message."""
        route = self.router.route(user_message)
        state = AgentState(
            user_message=user_message,
            ticker=ticker,
            market=market,
            route=route,
        )

        agent_keys = self._agent_keys_for(route, user_message)

        self._execute_agents(
            state=state,
            agent_keys=agent_keys,
        )

        if self._is_overview(route, user_message):
            self._execute_synthesis(state)

        return state

    def execute(
        self,
        user_message: str,
        ticker: str | None = None,
        market: str | None = None,
    ) -> AgentState:
        """Alias for integrations that use execution-oriented naming."""
        return self.run(
            user_message=user_message,
            ticker=ticker,
            market=market,
        )

    def _agent_keys_for(
        self,
        route: WorkflowRoute,
        user_message: str,
    ) -> tuple[str, ...]:
        if route in self.agents:
            return (route,)

        if "overview" in user_message.casefold():
            return ("financial", "market", "news")

        return ()

    @staticmethod
    def _is_overview(route: WorkflowRoute, user_message: str) -> bool:
        return route == "general" and "overview" in user_message.casefold()

    def _execute_agents(
        self,
        state: AgentState,
        agent_keys: Iterable[str],
    ) -> None:
        for key in agent_keys:
            try:
                result = self.agents[key].run(state.user_message)
                state.results[key] = result
                ctx_patch = _extract_research_context_from_result(
                    ticker=state.ticker or "",
                    market=state.market or "IN",
                    result=result,
                )
                if ctx_patch is not None:
                    state.research_context = _merge_research_context(state.research_context, ctx_patch)
            except (AIError, ValueError, TypeError) as exc:
                state.errors.append(f"{key}: {exc}")

    def _execute_synthesis(self, state: AgentState) -> None:
        if self.synthesis_agent is None:
            return

        try:
            state.results["synthesis"] = self.synthesis_agent.run(state)
        except (AIError, ValueError, TypeError) as exc:
            state.errors.append(f"synthesis: {exc}")
