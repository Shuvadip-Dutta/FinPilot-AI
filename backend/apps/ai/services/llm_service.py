from apps.ai.services.providers.groq import GroqProvider


class LLMService:

    def __init__(self):
        self.provider = GroqProvider()

    def generate(
        self,
        messages: list[dict[str, str]],
    ) -> str:

        return self.provider.generate(messages)