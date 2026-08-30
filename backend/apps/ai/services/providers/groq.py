from django.conf import settings
from groq import APIConnectionError, APIStatusError, APITimeoutError, Groq

from apps.ai.exceptions import LLMError


class GroqProvider:

    def __init__(self):

        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not configured."
            )

        if not settings.GROQ_MODEL:
            raise ValueError(
                "GROQ_MODEL is not configured."
            )

        self.client = Groq(
            api_key=settings.GROQ_API_KEY,
        )

        self.model = settings.GROQ_MODEL

    def generate(
        self,
        messages: list[dict[str, str]],
    ) -> str:

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
        except (APIConnectionError, APIStatusError, APITimeoutError) as exc:
            raise LLMError(f"Groq provider request failed: {exc}") from exc

        return response.choices[0].message.content
    
    def generate_with_tools(
    self,
    messages: list[dict],
    tools: list[dict],
    ):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
        except (APIConnectionError, APIStatusError, APITimeoutError) as exc:
            raise LLMError(f"Groq provider request failed: {exc}") from exc

        return response
