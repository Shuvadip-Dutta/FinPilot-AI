from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ai.services.llm_service import LLMService


class LLMServiceTestCase(SimpleTestCase):

    @patch(
        "apps.ai.services.llm_service.GroqProvider"
    )
    def test_generate(self, mock_groq_provider):

        mock_provider = mock_groq_provider.return_value

        mock_provider.generate.return_value = (
            "Reliance Industries is a major Indian company."
        )

        service = LLMService()

        result = service.generate(
            [
                {
                    "role": "user",
                    "content": "Tell me about Reliance.",
                }
            ]
        )

        self.assertEqual(
            result,
            "Reliance Industries is a major Indian company.",
        )

        mock_provider.generate.assert_called_once_with(
            [
                {
                    "role": "user",
                    "content": "Tell me about Reliance.",
                }
            ]
        )