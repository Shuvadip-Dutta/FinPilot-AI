from django.conf import settings
from groq import Groq


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

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )

        return response.choices[0].message.content
    
    def generate_with_tools(
    self,
    messages: list[dict],
    tools: list[dict],
    ):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        return response