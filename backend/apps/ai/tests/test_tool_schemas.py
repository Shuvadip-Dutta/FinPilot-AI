from django.test import SimpleTestCase

from apps.ai.services.tool_schemas import RESEARCH_TOOLS


class ToolSchemaTestCase(SimpleTestCase):

    def test_all_research_tools_exist(self):

        names = {
            tool["function"]["name"]
            for tool in RESEARCH_TOOLS
        }

        expected = {
            "get_company_profile",
            "get_market_data",
            "get_financials",
            "get_key_metrics",
            "get_historical_data",
            "get_news",
            "search_financial_documents",
        }

        self.assertEqual(
            names,
            expected,
        )

    def test_all_tools_have_required_structure(self):

        for tool in RESEARCH_TOOLS:

            self.assertEqual(
                tool["type"],
                "function",
            )

            self.assertIn(
                "name",
                tool["function"],
            )

            self.assertIn(
                "description",
                tool["function"],
            )

            self.assertIn(
                "parameters",
                tool["function"],
            )

    def test_financials_is_india_only(self):

        tool = next(
            tool
            for tool in RESEARCH_TOOLS
            if tool["function"]["name"] == "get_financials"
        )

        market_schema = (
            tool["function"]["parameters"]
            ["properties"]["market"]
        )

        self.assertEqual(
            market_schema["enum"],
            ["IN"],
        )

    def test_news_limit_is_bounded(self):

        tool = next(
            tool
            for tool in RESEARCH_TOOLS
            if tool["function"]["name"] == "get_news"
        )

        limit_schema = (
            tool["function"]["parameters"]
            ["properties"]["limit"]
        )

        self.assertEqual(
            limit_schema["minimum"],
            1,
        )

        self.assertEqual(
            limit_schema["maximum"],
            20,
        )