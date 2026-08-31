from asgiref.sync import async_to_sync
from django.test import SimpleTestCase

from apps.ai.mcp.server import mcp


class MCPServerTestCase(SimpleTestCase):

    def test_server_created(self):

        self.assertIsNotNone(mcp)

    def test_research_tools_registered(self):

        tools = async_to_sync(
            mcp.list_tools
        )()

        tool_names = {
            tool.name
            for tool in tools
        }

        expected_tools = {
            "get_company_profile",
            "get_market_data",
            "get_financials",
            "get_key_metrics",
            "get_historical_data",
            "get_news",
            "search_financial_documents",
        }

        self.assertEqual(
            tool_names,
            expected_tools,
        )