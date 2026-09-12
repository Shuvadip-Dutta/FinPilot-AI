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

    def test_search_financial_documents_sec_schema(self):
        tool = next(
            tool
            for tool in RESEARCH_TOOLS
            if tool["function"]["name"] == "search_financial_documents"
        )
        props = tool["function"]["parameters"]["properties"]

        # Ensure all Phase 4 SEC filters are declared
        self.assertIn("source_type", props)
        self.assertIn("sec_form", props)
        self.assertIn("sec_cik", props)
        self.assertIn("sec_accession_number", props)
        self.assertIn("document_id", props)
        self.assertIn("filing_date_from", props)
        self.assertIn("filing_date_to", props)
        self.assertIn("report_date_from", props)
        self.assertIn("report_date_to", props)

        # Ensure user_id is NOT exposed to LLM function calling schema
        self.assertNotIn("user_id", props)
        self.assertFalse(tool["function"]["parameters"]["additionalProperties"])
