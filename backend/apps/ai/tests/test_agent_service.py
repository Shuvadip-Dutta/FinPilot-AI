from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.services.agent_service import AgentService
from apps.ai.services.schemas import AgentResult


class AgentServiceTestCase(SimpleTestCase):

    @patch(
        "apps.ai.services.agent_service.GroqProvider"
    )
    def test_direct_response(
        self,
        mock_groq_provider,
    ):
        mock_service = (
            mock_groq_provider.return_value
        )

        mock_response = MagicMock()

        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].message.content = (
            "Hello from FinPilot AI."
        )

        mock_service.generate_with_tools.return_value = (
            mock_response
        )

        service = AgentService()

        result = service.run(
            "Say hello."
        )

        self.assertEqual(
            result.response,
            "Hello from FinPilot AI.",
        )

        self.assertEqual(
            result.tools_used,
            [],
        )

        mock_service.generate_with_tools.assert_called_once()

    @patch(
        "apps.ai.services.agent_service.research_tools.get_company_profile"
    )
    @patch(
        "apps.ai.services.agent_service.GroqProvider"
    )
    def test_single_tool_call(
        self,
        mock_groq_provider,
        mock_get_company_profile,
    ):

        mock_service = (
            mock_groq_provider.return_value
        )

        tool_call = SimpleNamespace(
            id="call_123",
            function=SimpleNamespace(
                name="get_company_profile",
                arguments=(
                    '{"ticker":"RELIANCE","market":"IN"}'
                ),
            ),
        )

        first_response = MagicMock()
        first_response.choices[0].message.tool_calls = [
            tool_call
        ]
        first_response.choices[0].message.content = None

        second_response = MagicMock()
        second_response.choices[0].message.tool_calls = None
        second_response.choices[0].message.content = (
            "Reliance Industries is a major Indian company."
        )

        mock_service.generate_with_tools.side_effect = [
            first_response,
            second_response,
        ]

        mock_get_company_profile.return_value = {
            "ticker": "RELIANCE",
            "name": "Reliance Industries Limited",
        }

        service = AgentService()

        result = service.run(
            "Tell me about Reliance."
        )

        self.assertEqual(
            result.response,
            "Reliance Industries is a major Indian company.",
        )

        self.assertEqual(
            result.tools_used,
            [
                "get_company_profile",
            ],
        )
        
        mock_get_company_profile.assert_called_once_with(
            ticker="RELIANCE",
            market="IN",
        )

        self.assertEqual(
            mock_service.generate_with_tools.call_count,
            2,
        )
        
    @patch(
        "apps.ai.services.agent_service.research_tools.get_news"
    )
    @patch(
        "apps.ai.services.agent_service.research_tools.get_market_data"
    )
    @patch(
        "apps.ai.services.agent_service.GroqProvider"
    )
    def test_multiple_tool_calls(
        self,
        mock_groq_provider,
        mock_get_market_data,
        mock_get_news,
    ):

        mock_service = (
            mock_groq_provider.return_value
        )

        first_tool_call = SimpleNamespace(
            id="call_market",
            function=SimpleNamespace(
                name="get_market_data",
                arguments=(
                    '{"ticker":"RELIANCE","market":"IN"}'
                ),
            ),
        )

        second_tool_call = SimpleNamespace(
            id="call_news",
            function=SimpleNamespace(
                name="get_news",
                arguments=(
                    '{"ticker":"RELIANCE","market":"IN","limit":5}'
                ),
            ),
        )

        first_response = MagicMock()

        first_response.choices[0].message.tool_calls = [
            first_tool_call,
            second_tool_call,
        ]

        first_response.choices[0].message.content = None

        second_response = MagicMock()

        second_response.choices[0].message.tool_calls = None

        second_response.choices[0].message.content = (
            "Reliance is currently trading at a strong level "
            "with several recent developments in the news."
        )

        mock_service.generate_with_tools.side_effect = [
            first_response,
            second_response,
        ]

        mock_get_market_data.return_value = {
            "ticker": "RELIANCE",
            "last_price": 1287.0,
        }

        mock_get_news.return_value = {
            "ticker": "RELIANCE",
            "articles": [
                {
                    "title": "Reliance market update",
                }
            ],
        }

        service = AgentService()

        result = service.run(
            "Give me an overview of Reliance."
        )

        self.assertEqual(
            result.response,
            (
                "Reliance is currently trading at a strong level "
                "with several recent developments in the news."
            ),
        )
        self.assertEqual(
            result.tools_used,
            [
                "get_market_data",
                "get_news",
            ],
        )
        mock_get_market_data.assert_called_once_with(
            ticker="RELIANCE",
            market="IN",
        )

        mock_get_news.assert_called_once_with(
            ticker="RELIANCE",
            market="IN",
            limit=5,
        )

        self.assertEqual(
            mock_service.generate_with_tools.call_count,
            2,
        )
        
    @patch(
        "apps.ai.services.agent_service.research_tools.get_market_data"
    )
    @patch(
        "apps.ai.services.agent_service.GroqProvider"
    )
    def test_tool_failure(
        self,
        mock_groq_provider,
        mock_get_market_data,
    ):

        mock_service = mock_groq_provider.return_value

        tool_call = SimpleNamespace(
            id="call_market",
            function=SimpleNamespace(
                name="get_market_data",
                arguments=(
                    '{"ticker":"RELIANCE","market":"IN"}'
                ),
            ),
        )

        first_response = MagicMock()
        first_response.choices[0].message.tool_calls = [
            tool_call
        ]
        first_response.choices[0].message.content = None

        second_response = MagicMock()
        second_response.choices[0].message.tool_calls = None
        second_response.choices[0].message.content = (
            "I could not retrieve the current market data "
            "for Reliance."
        )

        mock_service.generate_with_tools.side_effect = [
            first_response,
            second_response,
        ]

        mock_get_market_data.side_effect = ValueError(
            "Market data unavailable"
        )

        service = AgentService()

        result = service.run(
            "What is the current price of Reliance?"
        )

        self.assertEqual(
            result.response,
            "I could not retrieve the current market data "
            "for Reliance.",
        )
        
        self.assertEqual(
            result.tools_used,
            [
                "get_market_data",
            ],
        )

        self.assertEqual(
            mock_service.generate_with_tools.call_count,
            2,
        )
        
    @patch(
    "apps.ai.services.agent_service.GroqProvider"
    )
    def test_unknown_tool(
        self,
        mock_groq_provider,
    ):

        mock_service = mock_groq_provider.return_value

        tool_call = SimpleNamespace(
            id="call_unknown",
            function=SimpleNamespace(
                name="unknown_tool",
                arguments="{}",
            ),
        )

        response = MagicMock()
        response.choices[0].message.tool_calls = [
            tool_call
        ]
        response.choices[0].message.content = None

        mock_service.generate_with_tools.return_value = response

        service = AgentService()

        with self.assertRaises(ValueError) as context:
            service.run(
                "Use an unknown tool."
            )

        self.assertEqual(
            str(context.exception),
            "Unknown tool: unknown_tool",
        )
        
    @patch(
    "apps.ai.services.agent_service.GroqProvider"
    )
    def test_max_tool_rounds(
        self,
        mock_groq_provider,
    ):

        mock_service = mock_groq_provider.return_value

        tool_call = SimpleNamespace(
            id="call_loop",
            function=SimpleNamespace(
                name="get_market_data",
                arguments=(
                    '{"ticker":"RELIANCE","market":"IN"}'
                ),
            ),
        )

        response = MagicMock()
        response.choices[0].message.tool_calls = [
            tool_call
        ]
        response.choices[0].message.content = None

        mock_service.generate_with_tools.return_value = response

        service = AgentService()

        with patch.object(
            service,
            "tool_registry",
            {
                "get_market_data": lambda **kwargs: {
                    "ticker": "RELIANCE",
                    "market": "IN",
                    "data": "mocked",
                }
            },
        ):

            with self.assertRaises(ValueError) as context:
                service.run(
                    "Keep analyzing Reliance."
                )

        self.assertEqual(
            str(context.exception),
            "Maximum tool-call limit exceeded.",
        )
        
    def test_system_prompt_is_used(self):

        service = AgentService()

        messages = service._build_messages(
            "Hello."
        )

        self.assertEqual(
            messages[0]["role"],
            "system",
        )

        self.assertIn(
            "You are FinPilot AI",
            messages[0]["content"],
        )

        self.assertEqual(
            messages[1]["role"],
            "user",
        )

        self.assertEqual(
            messages[1]["content"],
            "Hello.",
        )
        
        
    def test_agent_result_schema(self):

        result = AgentResult(
            response="Test response",
            tools_used=[
                "get_news",
            ],
        )

        self.assertEqual(
            result.response,
            "Test response",
        )

        self.assertEqual(
            result.tools_used,
            ["get_news"],
        )    