from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ai.mcp.tools.research import (
    get_company_profile,
    get_market_data,
    get_financials,
    get_key_metrics,
    get_historical_data,
    get_news,
    
)
from apps.research.services.schemas import (
    FinancialMetric,
    FinancialStatement,
    KeyMetric,
    KeyMetricsResearch,
    HistoricalCandle,
    HistoricalMarketData,
    NewsArticle,
    NewsResearch,
)
from asgiref.sync import async_to_sync

from apps.ai.mcp.server import mcp
import json


class MCPResearchToolsTestCase(SimpleTestCase):

    @patch(
        "apps.ai.services.research_tools.ResearchService"
    )
    def test_get_company_profile(
        self,
        mock_research_service,
    ):

        mock_service = (
            mock_research_service.return_value
        )

        mock_service.get_company_profile.return_value = {
            "ticker": "RELIANCE",
            "name": "Reliance Industries Limited",
            "market": "IN",
        }

        result = get_company_profile(
            ticker="RELIANCE",
            market="IN",
        )

        self.assertEqual(
            result["ticker"],
            "RELIANCE",
        )

        self.assertEqual(
            result["name"],
            "Reliance Industries Limited",
        )

        mock_service.get_company_profile.assert_called_once()
        
        
    @patch(
    "apps.ai.services.research_tools.ResearchService"
    )
    def test_mcp_call_company_profile(
        self,
        mock_research_service,
    ):

        mock_service = (
            mock_research_service.return_value
        )

        mock_service.get_company_profile.return_value = {
            "ticker": "RELIANCE",
            "name": "Reliance Industries Limited",
            "market": "IN",
        }

        result = async_to_sync(
            mcp.call_tool
        )(
            "get_company_profile",
            {
                "ticker": "RELIANCE",
                "market": "IN",
            },
        )

        # print("RESULT:", result)
        # print("CONTENT:", result.content)
        # print("STRUCTURED:", result.structured_content)
        # print("IS ERROR:", result.is_error)

        self.assertFalse(result.is_error)
        payload = json.loads(
            result.content[0].text
        )

        self.assertEqual(
            payload["ticker"],
            "RELIANCE",
        )

        self.assertEqual(
            payload["name"],
            "Reliance Industries Limited",
        )

        self.assertEqual(
            payload["market"],
            "IN",
        )

        mock_service.get_company_profile.assert_called_once()
        
        
    @patch(
    "apps.ai.services.research_tools.ResearchService"
    )
    def test_get_market_data(
        self,
        mock_research_service,
    ):

        mock_service = (
            mock_research_service.return_value
        )

        mock_service.get_market_data.return_value = {
            "ticker": "RELIANCE",
            "last_price": 1287.0,
            "volume": 6830228,
        }

        result = get_market_data(
            ticker="RELIANCE",
            market="IN",
        )

        self.assertEqual(
            result["ticker"],
            "RELIANCE",
        )

        self.assertEqual(
            result["last_price"],
            1287.0,
        )

        mock_service.get_market_data.assert_called_once()
        
        
    @patch(
    "apps.ai.services.research_tools.ResearchService"
    )
    def test_get_financials(
        self,
        mock_research_service,
    ):

        mock_service = (
            mock_research_service.return_value
        )

        mock_service.get_financials.return_value = [
            FinancialStatement(
                statement_type="INC",
                fiscal_year="2026",
                end_date="2026-03-31",
                period_type="annual",
                period_length=12,
                metrics=[
                    FinancialMetric(
                        name="Revenue",
                        key="revenue",
                        value=100000.0,
                    )
                ],
            )
        ]

        result = get_financials(
            ticker="RELIANCE",
            market="IN",
        )

        self.assertEqual(
            result["ticker"],
            "RELIANCE",
        )

        self.assertEqual(
            result["market"],
            "IN",
        )

        self.assertEqual(
            len(result["financials"]),
            1,
        )

        self.assertEqual(
            result["financials"][0]["statement_type"],
            "INC",
        )

        self.assertEqual(
            result["financials"][0]["metrics"][0]["key"],
            "revenue",
        )

        self.assertEqual(
            result["financials"][0]["metrics"][0]["value"],
            100000.0,
        )

        mock_service.get_financials.assert_called_once()
        
        
    @patch(
    "apps.ai.services.research_tools.ResearchService"
    )
    def test_get_key_metrics(
        self,
        mock_research_service,
    ):

        mock_service = (
            mock_research_service.return_value
        )

        mock_service.get_key_metrics.return_value = (
            KeyMetricsResearch(
                ticker="RELIANCE",
                metrics=[
                    KeyMetric(
                        category="valuation",
                        name="P/E Ratio",
                        key="pe_ratio",
                        value=24.5,
                        raw_value="24.5x",
                    )
                ],
            )
        )

        result = get_key_metrics(
            ticker="RELIANCE",
            market="IN",
        )

        self.assertEqual(
            result["ticker"],
            "RELIANCE",
        )

        self.assertEqual(
            result["market"],
            "IN",
        )

        self.assertEqual(
            len(result["metrics"]),
            1,
        )

        self.assertEqual(
            result["metrics"][0]["key"],
            "pe_ratio",
        )

        self.assertEqual(
            result["metrics"][0]["value"],
            24.5,
        )

        self.assertEqual(
            result["metrics"][0]["raw_value"],
            "24.5x",
        )

        mock_service.get_key_metrics.assert_called_once()
        
        
    @patch(
    "apps.ai.services.research_tools.ResearchService"
    )
    def test_get_historical_data(
        self,
        mock_research_service,
    ):

        mock_service = (
            mock_research_service.return_value
        )

        mock_service.get_historical_data.return_value = (
            HistoricalMarketData(
                ticker="RELIANCE",
                candles=[
                    HistoricalCandle(
                        timestamp="2026-08-27T00:00:00+05:30",
                        open=1305.0,
                        high=1308.4,
                        low=1282.2,
                        close=1282.2,
                        volume=11271497,
                        open_interest=0,
                    )
                ],
            )
        )

        result = get_historical_data(
            ticker="RELIANCE",
            to_date="2026-08-28",
            from_date="2026-08-25",
            market="IN",
        )

        self.assertEqual(
            result["ticker"],
            "RELIANCE",
        )

        self.assertEqual(
            result["market"],
            "IN",
        )

        self.assertEqual(
            len(result["candles"]),
            1,
        )

        self.assertEqual(
            result["candles"][0]["close"],
            1282.2,
        )

        self.assertEqual(
            result["candles"][0]["volume"],
            11271497,
        )

        mock_service.get_historical_data.assert_called_once()
        
        
    @patch(
    "apps.ai.services.research_tools.ResearchService"
    )
    def test_get_news(
        self,
        mock_research_service,
    ):

        mock_service = (
            mock_research_service.return_value
        )

        mock_service.get_news.return_value = NewsResearch(
            ticker="RELIANCE",
            articles=[
                NewsArticle(
                    title="Reliance market update",
                    summary="Recent market developments.",
                    url="https://example.com/reliance",
                    source="example.com",
                    published_at="2026-08-28T10:00:00Z",
                )
            ],
        )

        result = get_news(
            ticker="RELIANCE",
            market="IN",
            limit=3,
        )

        self.assertEqual(
            result["ticker"],
            "RELIANCE",
        )

        self.assertEqual(
            result["market"],
            "IN",
        )

        self.assertEqual(
            len(result["articles"]),
            1,
        )

        self.assertEqual(
            result["articles"][0]["title"],
            "Reliance market update",
        )

        self.assertEqual(
            result["articles"][0]["source"],
            "example.com",
        )

        mock_service.get_news.assert_called_once()