from typing import Any

from django.conf import settings
from groq import APIConnectionError, APIStatusError, APITimeoutError, Groq

from apps.ai.exceptions import LLMError
from apps.ai.services.token_budget import LLMUsage


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
        self.last_usage: LLMUsage | None = None

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

    def _extract_usage(self, response: Any) -> LLMUsage | None:
        usage_obj = getattr(response, "usage", None)
        if usage_obj is None:
            return None

        prompt_tokens = getattr(usage_obj, "prompt_tokens", None)
        completion_tokens = getattr(usage_obj, "completion_tokens", None)
        total_tokens = getattr(usage_obj, "total_tokens", None)

        if prompt_tokens is None or completion_tokens is None or total_tokens is None:
            return None

        try:
            return LLMUsage(
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=int(total_tokens),
                model=str(self.model),
            )
        except Exception:
            return None

    def generate(
        self,
        messages: list[dict[str, str]],
        max_completion_tokens: int | None = None,
    ) -> str:
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if self._is_reasoning_model():
            request_kwargs.update(self._reasoning_request_kwargs())

        if max_completion_tokens is not None:
            request_kwargs["max_completion_tokens"] = int(max_completion_tokens)

        try:
            response = self.client.chat.completions.create(**request_kwargs)
        except (APIConnectionError, APIStatusError, APITimeoutError) as exc:
            raise LLMError(f"Groq provider request failed: {exc}") from exc

        self.last_usage = self._extract_usage(response)

        content = response.choices[0].message.content
        if content is None:
            return ""
        return str(content)

    def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        max_completion_tokens: int | None = None,
    ):
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }
        if max_completion_tokens is not None:
            request_kwargs["max_completion_tokens"] = int(max_completion_tokens)

        try:
            response = self.client.chat.completions.create(**request_kwargs)
        except (APIConnectionError, APIStatusError, APITimeoutError) as exc:
            raise LLMError(f"Groq provider request failed: {exc}") from exc

        self.last_usage = self._extract_usage(response)
        return response
