from apps.ai.services.providers.groq import GroqProvider


class LLMService:

    def __init__(self):
        self.provider = GroqProvider()

    def generate(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        return self.provider.generate(messages)

    def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ):
        return self.provider.generate_with_tools(
            messages=messages,
            tools=tools,
        )