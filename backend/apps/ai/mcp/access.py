"""Controlled MCP tool access policies for FinPilot AI agents."""

from pydantic import BaseModel, Field


class AgentToolPolicy(BaseModel):
    """Defines which MCP tools an agent may use and its execution limits."""

    allowed_tools: set[str] = Field(
        default_factory=set,
    )

    max_tool_calls: int = Field(
        default=5,
        gt=0,
    )

    max_rounds: int = Field(
        default=3,
        gt=0,
    )


class AgentToolAccess:
    """Validate and enforce an agent's allowed MCP tool set."""

    def __init__(
        self,
        available_tools: set[str],
    ):
        self.available_tools = set(available_tools)

    def get_allowed_tools(
        self,
        policy: AgentToolPolicy,
    ) -> set[str]:
        """Return only tools that are both available and explicitly allowed."""

        unknown_tools = (
            policy.allowed_tools - self.available_tools
        )

        if unknown_tools:
            raise ValueError(
                "Unknown MCP tools requested: "
                + ", ".join(sorted(unknown_tools))
            )

        return set(policy.allowed_tools)

    def validate_tool(
        self,
        tool_name: str,
        policy: AgentToolPolicy,
    ) -> None:
        """Raise when a tool is not allowed by the policy."""

        if tool_name not in self.available_tools:
            raise ValueError(
                f"Unknown MCP tool: {tool_name}"
            )

        if tool_name not in policy.allowed_tools:
            raise ValueError(
                f"MCP tool not allowed for this agent: {tool_name}"
            )

    @staticmethod
    def validate_limits(
        tool_calls: int,
        rounds: int,
        policy: AgentToolPolicy,
    ) -> None:
        """Validate current tool execution counts against policy limits."""

        if tool_calls > policy.max_tool_calls:
            raise ValueError(
                "Maximum MCP tool-call limit exceeded."
            )

        if rounds > policy.max_rounds:
            raise ValueError(
                "Maximum MCP round limit exceeded."
            )