"""Controlled operational errors for FinPilot AI boundaries."""


class AIError(Exception):
    """Base application-level AI error."""


class LLMError(AIError):
    """LLM/provider operational failure."""


class ToolExecutionError(AIError):
    """Expected tool execution failure."""


class WorkflowError(AIError):
    """Workflow/orchestration failure."""


class RAGError(AIError):
    """RAG ingestion/retrieval failure."""
