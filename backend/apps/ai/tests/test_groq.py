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

        provider = GroqProvider(model="qwen/qwen3.6-27b")

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
        self.assertEqual(
            mock_client.chat.completions.create.call_args.kwargs["reasoning_format"],
            "hidden",
        )
        self.assertEqual(
            mock_client.chat.completions.create.call_args.kwargs[
                "max_completion_tokens"
            ],
            4096,
        )

    @override_settings(REASONING_MAX_COMPLETION_TOKENS=4096)
    @patch("apps.ai.services.providers.groq.Groq")
    def test_reasoning_generation_uses_configured_completion_limit(self, mock_groq):
        mock_client = MagicMock()
        mock_groq.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices[0].message.content = (
            "Configured answer"
        )

        with override_settings(REASONING_MODEL="configured-reasoning-model"):
            provider = GroqProvider(model="configured-reasoning-model")
            provider.generate([{"role": "user", "content": "Explain."}])

        request_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(request_kwargs["reasoning_format"], "hidden")
        self.assertEqual(request_kwargs["max_completion_tokens"], 4096)

    @patch(
        "apps.ai.services.providers.groq.Groq"
    )
    def test_fast_generation_keeps_normal_request_shape(self, mock_groq):
        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Fast answer"
        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider(model="llama-3.1-8b-instant")
        result = provider.generate([
            {"role": "user", "content": "Quick answer."}
        ])

        self.assertEqual(result, "Fast answer")
        self.assertNotIn("reasoning_format", mock_client.chat.completions.create.call_args.kwargs)
        self.assertNotIn("max_completion_tokens", mock_client.chat.completions.create.call_args.kwargs)

    @patch(
        "apps.ai.services.providers.groq.Groq"
    )
    def test_generate_with_tools_uses_tool_call_request_without_reasoning_format(self, mock_groq):
        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.tool_calls = []
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider(model="qwen/qwen3.6-27b")
        result = provider.generate_with_tools(
            messages=[{"role": "user", "content": "Analyze Reliance."}],
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

        self.assertIs(result, mock_response)
        self.assertEqual(mock_client.chat.completions.create.call_args.kwargs["tool_choice"], "auto")
        self.assertNotIn("reasoning_format", mock_client.chat.completions.create.call_args.kwargs)

    @override_settings(
        GROQ_API_KEY=None,
        GROQ_MODEL="qwen/qwen3.6-27b",
    )
    def test_missing_api_key(self):

        with self.assertRaises(ValueError) as context:
            GroqProvider(model="qwen/qwen3.6-27b")

        self.assertEqual(
            str(context.exception),
            "GROQ_API_KEY is not configured.",
        )

    @override_settings(
        GROQ_API_KEY="test-key",
        GROQ_MODEL=None,
        REASONING_MODEL=None,
        FAST_MODEL=None,
        EVALUATION_MODEL=None,
    )
    def test_missing_model(self):

        with self.assertRaises(ValueError) as context:
            GroqProvider()

        self.assertEqual(
            str(context.exception),
            "GROQ_MODEL is not configured.",
        )

    @override_settings(
        GROQ_API_KEY="test-key",
        GROQ_MODEL="legacy-model",
        REASONING_MODEL="reasoning-model",
        FAST_MODEL="fast-model",
        EVALUATION_MODEL="evaluation-model",
    )
    def test_provider_uses_concrete_model_id(self):
        with patch("apps.ai.services.providers.groq.Groq"):
            provider = GroqProvider(model="qwen/custom-model")
            self.assertEqual(provider.model, "qwen/custom-model")

        with patch("apps.ai.services.providers.groq.Groq"):
            provider = GroqProvider()
            self.assertEqual(provider.model, "reasoning-model")

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

        provider = GroqProvider(model="qwen/qwen3.6-27b")

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