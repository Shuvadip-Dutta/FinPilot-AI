"""Final synthesis agent for combining multi-agent analysis."""

import json
from collections.abc import Callable

from apps.ai.agents.base import BaseAgent
from apps.ai.graph.state import AgentState
from apps.ai.services.llm_service import LLMService
from apps.ai.services.schemas import AgentResult


LLMGenerate = Callable[[list[dict[str, str]]], str]


class FinalSynthesisAgent(BaseAgent):
    """Combine agent outputs into one coherent user-facing response."""

    def __init__(
        self,
        llm_service: LLMGenerate | None = None,
    ):
        self.llm_service = (
            llm_service or LLMService().generate
        )

    @property
    def name(self) -> str:
        return "synthesis"

    def run(
        self,
        state: AgentState,
    ) -> AgentResult:
        """Synthesize the available workflow results."""

        context = self._build_context(state)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the final synthesis component of FinPilot AI. "
                    "Combine the supplied specialist analysis into one "
                    "clear, accurate response. Do not invent facts. "
                    "Use only the information provided in the context. "
                    "Clearly distinguish unavailable information. "
                    "Do not claim that an action was performed unless "
                    "the context explicitly says it was."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User request:\n{state.user_message}\n\n"
                    f"Research context:\n{context}\n\n"
                    "Produce a concise but useful final answer."
                ),
            },
        ]

        try:
            response = self.llm_service(messages)
        except (ValueError, TypeError) as exc:
            return AgentResult(
                response=(
                    "Unable to generate the final synthesis: "
                    f"{exc}"
                ),
                tools_used=[],
            )

        if not isinstance(response, str) or not response.strip():
            return AgentResult(
                response=(
                    "Unable to generate the final synthesis: "
                    "the language model returned an empty response."
                ),
                tools_used=[],
            )

        tools_used = self._collect_tools_used(state)

        return AgentResult(
            response=response.strip(),
            tools_used=tools_used,
        )

    @staticmethod
    def _build_context(
        state: AgentState,
    ) -> str:
        context: dict[str, object] = {}

        for key, value in state.results.items():
            if isinstance(value, AgentResult):
                context[key] = {
                    "response": value.response,
                    "tools_used": value.tools_used,
                }
            else:
                context[key] = value

        if state.errors:
            context["workflow_errors"] = state.errors

        return json.dumps(
            context,
            ensure_ascii=False,
            default=str,
        )

    @staticmethod
    def _collect_tools_used(
        state: AgentState,
    ) -> list[str]:
        tools: list[str] = []

        for value in state.results.values():
            if not isinstance(value, AgentResult):
                continue

            for tool in value.tools_used:
                if tool not in tools:
                    tools.append(tool)

        if "llm_synthesis" not in tools:
            tools.append("llm_synthesis")

        return tools