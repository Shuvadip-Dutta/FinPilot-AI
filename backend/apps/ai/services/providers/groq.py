from django.conf import settings
from groq import APIConnectionError, APIStatusError, APITimeoutError, Groq

from apps.ai.exceptions import LLMError


class GroqProvider:

    REASONING_MODELS = ("qwen3", "qwen/qwen3")

    def __init__(self, model: str | None = None):

        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not configured."
            )

        self.model = model or getattr(
            settings,
            "REASONING_MODEL",
            None,
        ) or getattr(settings, "GROQ_MODEL", None)

        if not self.model:
            raise ValueError(
                "GROQ_MODEL is not configured."
            )

        self.client = Groq(
            api_key=settings.GROQ_API_KEY,
        )

    def _is_reasoning_model(self) -> bool:
        normalized = str(self.model).lower()
        configured_model = str(
            getattr(settings, "REASONING_MODEL", "")
        ).lower()
        return normalized == configured_model or any(
            marker in normalized for marker in self.REASONING_MODELS
        )

    def _reasoning_request_kwargs(self) -> dict[str, object]:
        return {
            "reasoning_format": "hidden",
            "max_completion_tokens": int(
                getattr(settings, "REASONING_MAX_COMPLETION_TOKENS", 4096)
            ),
        }

    def generate(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        request_kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if self._is_reasoning_model():
            request_kwargs.update(self._reasoning_request_kwargs())

        try:
            response = self.client.chat.completions.create(**request_kwargs)
        except (APIConnectionError, APIStatusError, APITimeoutError) as exc:
            raise LLMError(f"Groq provider request failed: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            return ""
        return str(content)

    def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ):
        request_kwargs = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }

        try:
            response = self.client.chat.completions.create(**request_kwargs)
        except (APIConnectionError, APIStatusError, APITimeoutError) as exc:
            raise LLMError(f"Groq provider request failed: {exc}") from exc

        return response
