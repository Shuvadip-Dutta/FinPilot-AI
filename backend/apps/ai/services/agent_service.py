import json

from apps.ai.services.llm_service import LLMService
from apps.ai.services.tool_schemas import RESEARCH_TOOLS
from apps.ai.services import research_tools
from dataclasses import asdict, is_dataclass
from apps.ai.services.prompts import (
    FINPILOT_SYSTEM_PROMPT,
)
from apps.ai.services.schemas import AgentResult


class AgentService:
    MAX_TOOL_ROUNDS = 5

    def __init__(self):
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

        messages = self._build_messages(message)

        response = self.llm.generate_with_tools(
            messages=messages,
            tools=RESEARCH_TOOLS,
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

            if tool_rounds > self.MAX_TOOL_ROUNDS:
                raise ValueError(
                    "Maximum tool-call limit exceeded."
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
                    raise ValueError(
                        f"Unknown tool: {tool_name}"
                    )
                tools_used.append(tool_name)

                arguments = json.loads(
                    tool_call.function.arguments
                )

                tool_function = self.tool_registry[
                    tool_name
                ]

                try:
                    result = tool_function(
                        **arguments
                    )

                except (ValueError, TypeError) as exc:
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
                tools=RESEARCH_TOOLS,
            )