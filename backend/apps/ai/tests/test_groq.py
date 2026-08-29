from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.ai.services.providers.groq import GroqProvider



class GroqProviderTestCase(SimpleTestCase):

    @patch(
        "apps.ai.services.providers.groq.Groq"
    )
    def test_generate(self, mock_groq):

        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "Reliance Industries is a major Indian company."
        )

        mock_client.chat.completions.create.return_value = (
            mock_response
        )

        provider = GroqProvider()

        result = provider.generate(
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
        
    @override_settings(
    GROQ_API_KEY=None,
    GROQ_MODEL="qwen/qwen3.6-27b",
    )
    def test_missing_api_key(self):

        with self.assertRaises(ValueError) as context:
            GroqProvider()

        self.assertEqual(
            str(context.exception),
            "GROQ_API_KEY is not configured.",
        )
        
    @override_settings(
    GROQ_API_KEY="test-key",
    GROQ_MODEL=None,
    )
    def test_missing_model(self):

        with self.assertRaises(ValueError) as context:
            GroqProvider()

        self.assertEqual(
            str(context.exception),
            "GROQ_MODEL is not configured.",
        )
        
    @patch(
    "apps.ai.services.providers.groq.Groq"
    )
    def test_generate_with_tools(self, mock_groq):

        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_response = MagicMock()

        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "get_company_profile"
        mock_tool_call.function.arguments = (
            '{"ticker":"RELIANCE","market":"IN"}'
        )

        mock_response.choices[0].message.tool_calls = [
            mock_tool_call
        ]
        mock_response.choices[0].message.content = None

        mock_client.chat.completions.create.return_value = (
            mock_response
        )

        provider = GroqProvider()

        result = provider.generate_with_tools(
            messages=[
                {
                    "role": "user",
                    "content": "Analyze Reliance.",
                }
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_company_profile",
                        "description": "Get company profile.",
                        "parameters": {},
                    },
                }
            ],
        )

        self.assertIs(
            result,
            mock_response,
        )

        mock_client.chat.completions.create.assert_called_once()