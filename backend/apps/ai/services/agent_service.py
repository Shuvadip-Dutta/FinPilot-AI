import json

from dataclasses import asdict, is_dataclass

from apps.ai.exceptions import ToolExecutionError
from apps.ai.mcp.access import AgentToolAccess, AgentToolPolicy
from apps.ai.services import research_tools
from apps.ai.services.llm_service import LLMService
from apps.ai.services.prompts import (
    FINPILOT_SYSTEM_PROMPT,
)
from apps.ai.services.schemas import AgentResult
from apps.ai.services.tool_schemas import RESEARCH_TOOLS


class AgentService:
    MAX_TOOL_ROUNDS = 5

    def __init__(self, policy: AgentToolPolicy | None = None):
        self.llm = LLMService()

        self.tool_registry = {
            "get_company_profile": (
                research_tools.get_company_profile
            ),
            "get_market_data": (
                research_tools.get_market_data
            ),
            "get_financials": (
                research_tools.get_financials
            ),
            "get_key_metrics": (
                research_tools.get_key_metrics
            ),
            "get_historical_data": (
                research_tools.get_historical_data
            ),
            "get_news": (
                research_tools.get_news
            ),
        }

        self.access = AgentToolAccess(
            available_tools=set(self.tool_registry.keys())
        )

        if policy is None:
            policy = AgentToolPolicy(
                allowed_tools=set(self.tool_registry.keys()),
                max_tool_calls=5,
                max_rounds=self.MAX_TOOL_ROUNDS,
            )

        self.policy = policy
        self.max_rounds = self.policy.max_rounds
        self.allowed_tools = self.access.get_allowed_tools(self.policy)

    def _get_allowed_tool_schemas(self):
        allowed = self.access.get_allowed_tools(self.policy)
        return [
            tool
            for tool in RESEARCH_TOOLS
            if tool["function"]["name"] in allowed
        ]


    def _serialize_tool_result(
    self,
    result,
    ):
        if is_dataclass(result):
            return asdict(result)

        if isinstance(result, list):
            return [
                self._serialize_tool_result(item)
                for item in result
            ]

        if isinstance(result, dict):
            return {
                key: self._serialize_tool_result(value)
                for key, value in result.items()
            }

        return result
    
    def _build_messages(
    self,
    message: str,
    ) -> list[dict]:
        return [
            {
                "role": "system",
                "content": FINPILOT_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": message,
            },
        ]
            
    def run(
        self,
        message: str,
    ) -> AgentResult:
        tools_used: list[str] = []
        tool_rounds = 0
        tool_calls = 0

        messages = self._build_messages(message)

        response = self.llm.generate_with_tools(
            messages=messages,
            tools=self._get_allowed_tool_schemas(),
        )

        while True:

            assistant_message = response.choices[0].message

            if not assistant_message.tool_calls:
                return AgentResult(
                    response=(
                        assistant_message.content
                        or ""
                    ),
                    tools_used=tools_used,
                )

            tool_rounds += 1
            self.access.validate_limits(
                tool_calls=tool_calls,
                rounds=tool_rounds,
                policy=self.policy,
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": (
                                    tool_call.function.name
                                ),
                                "arguments": (
                                    tool_call.function.arguments
                                ),
                            },
                        }
                        for tool_call in assistant_message.tool_calls
                    ],
                }
            )

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name

                if tool_name not in self.tool_registry:
                    raise ToolExecutionError(
                        f"Unknown tool: {tool_name}"
                    )

                try:
                    self.access.validate_tool(
                        tool_name,
                        self.policy,
                    )
                except ValueError as exc:
                    raise ToolExecutionError(str(exc)) from exc

                self.access.validate_limits(
                    tool_calls=tool_calls + 1,
                    rounds=tool_rounds,
                    policy=self.policy,
                )

                tool_calls += 1
                tools_used.append(tool_name)

                try:
                    arguments = json.loads(
                        tool_call.function.arguments
                    )
                except json.JSONDecodeError as exc:
                    raise ToolExecutionError(
                        f"Malformed arguments for tool {tool_name}."
                    ) from exc

                if not isinstance(arguments, dict):
                    raise ToolExecutionError(
                        f"Arguments for tool {tool_name} must be a JSON object."
                    )

                tool_function = self.tool_registry[
                    tool_name
                ]

                try:
                    result = tool_function(
                        **arguments
                    )

                except (ToolExecutionError, ValueError, TypeError) as exc:
                    result = {
                        "error": str(exc),
                    }

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            self._serialize_tool_result(result)
                        ),
                    }
                )

            response = self.llm.generate_with_tools(
                messages=messages,
                tools=self._get_allowed_tool_schemas(),
            )
