from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.ai.services.providers.groq import GroqProvider
from apps.ai.services.token_budget import LLMUsage


class GroqProviderTestCase(SimpleTestCase):

    @patch("apps.ai.services.providers.groq.Groq")
    def test_generate_qwen36_preserves_visible_reasoning(self, mock_groq):
        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "<think>Reasoning content</think>\nFinal answer."
        )
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 25
        mock_response.usage.total_tokens = 40

        mock_client.chat.completions.create.return_value = mock_response

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
            "<think>Reasoning content</think>\nFinal answer.",
        )

        request_kwargs = mock_client.chat.completions.create.call_args.kwargs

        self.assertEqual(request_kwargs["model"], "qwen/qwen3.8-27b")
        self.assertNotIn("reasoning_format", request_kwargs)

        self.assertEqual(
            provider.last_usage,
            LLMUsage(
                prompt_tokens=15,
                completion_tokens=25,
                total_tokens=40,
                model="qwen/qwen3.6-27b",
            ),
        )

    @override_settings(REASONING_MAX_COMPLETION_TOKENS=4096)
    @patch("apps.ai.services.providers.groq.Groq")
    def test_qwen38_uses_hidden_reasoning_configuration(
        self, mock_groq
    ):
        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "Configured answer"

        provider = GroqProvider(model="qwen/qwen3.8-27b")

        provider.generate(
            [{"role": "user", "content": "Explain."}]
        )

        request_kwargs = mock_client.chat.completions.create.call_args.kwargs

        self.assertEqual(
            request_kwargs["reasoning_format"],
            "hidden",
        )
        self.assertEqual(
            request_kwargs["max_completion_tokens"],
            4096,
        )
    @patch("apps.ai.services.providers.groq.Groq")
    def test_generate_forwards_explicit_max_completion_tokens(self, mock_groq):
        mock_client = MagicMock()
        mock_groq.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "Answer"

        provider = GroqProvider(model="llama-3.1-8b-instant")
        provider.generate(
            [{"role": "user", "content": "Query"}],
            max_completion_tokens=2048,
        )

        request_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(request_kwargs["max_completion_tokens"], 2048)

    @patch("apps.ai.services.providers.groq.Groq")
    def test_generate_handles_missing_usage(self, mock_groq):
        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Answer without usage"
        mock_response.usage = None
        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider(model="qwen/qwen3.6-27b")
        result = provider.generate([{"role": "user", "content": "Hi"}])

        self.assertEqual(result, "Answer without usage")
        self.assertIsNone(provider.last_usage)

    @patch("apps.ai.services.providers.groq.Groq")
    def test_fast_generation_keeps_normal_request_shape(self, mock_groq):
        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Fast answer"
        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider(model="llama-3.1-8b-instant")
        result = provider.generate(
            [{"role": "user", "content": "Quick answer."}]
        )

        self.assertEqual(result, "Fast answer")
        self.assertNotIn(
            "reasoning_format",
            mock_client.chat.completions.create.call_args.kwargs,
        )
        self.assertNotIn(
            "max_completion_tokens",
            mock_client.chat.completions.create.call_args.kwargs,
        )

    @patch("apps.ai.services.providers.groq.Groq")
    def test_generate_with_tools_uses_tool_call_request_without_reasoning_format(
        self, mock_groq
    ):
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
        self.assertEqual(
            mock_client.chat.completions.create.call_args.kwargs[
                "tool_choice"
            ],
            "auto",
        )
        self.assertNotIn(
            "reasoning_format",
            mock_client.chat.completions.create.call_args.kwargs,
        )

    @patch("apps.ai.services.providers.groq.Groq")
    def test_generate_with_tools_forwards_max_completion_tokens_and_captures_usage(
        self, mock_groq
    ):
        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_response = MagicMock()
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 150
        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider(model="qwen/qwen3.6-27b")
        result = provider.generate_with_tools(
            messages=[{"role": "user", "content": "Test"}],
            tools=[],
            max_completion_tokens=1024,
        )

        self.assertIs(result, mock_response)
        self.assertEqual(
            mock_client.chat.completions.create.call_args.kwargs[
                "max_completion_tokens"
            ],
            1024,
        )
        self.assertEqual(
            provider.last_usage,
            LLMUsage(
                prompt_tokens=50,
                completion_tokens=100,
                total_tokens=150,
                model="qwen/qwen3.6-27b",
            ),
        )

    @override_settings(
        GROQ_API_KEY=None,
        GROQ_MODEL="qwen/qwen3.8-27b",
    )
    def test_missing_api_key(self):
        with self.assertRaises(ValueError) as context:
            GroqProvider(model="qwen/qwen3.8-27b")

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
            
            
    def test_reasoning_model_classification(self):
        self.assertFalse(
            GroqProvider(model="qwen/qwen3.6-27b")._is_reasoning_model()
        )
        self.assertTrue(
            GroqProvider(model="qwen/qwen3.8-27b")._is_reasoning_model()
        )

    def test_provider_model_resolution_and_compatibility(self):
        # 1. qwen/qwen3.6-27b resolves to qwen/qwen3.8-27b on Groq
        p36 = GroqProvider(model="qwen/qwen3.6-27b")
        self.assertEqual(p36.model, "qwen/qwen3.6-27b")
        self.assertEqual(p36.get_effective_model(), "qwen/qwen3.8-27b")
        self.assertFalse(p36._is_reasoning_model())

        # 2. qwen/qwen3.8-27b resolves to itself
        p38 = GroqProvider(model="qwen/qwen3.8-27b")
        self.assertEqual(p38.model, "qwen/qwen3.8-27b")
        self.assertEqual(p38.get_effective_model(), "qwen/qwen3.8-27b")
        self.assertTrue(p38._is_reasoning_model())

        # 3. Unmapped models resolve to themselves
        p_llama = GroqProvider(model="llama-3.1-8b-instant")
        self.assertEqual(p_llama.model, "llama-3.1-8b-instant")
        self.assertEqual(p_llama.get_effective_model(), "llama-3.1-8b-instant")
        self.assertFalse(p_llama._is_reasoning_model())