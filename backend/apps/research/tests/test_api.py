from unittest.mock import patch

from django.urls import reverse
import requests
from rest_framework import status
from rest_framework.test import APITestCase

from apps.research.services.schemas import (
    CompanyProfile,
    ExchangeQuote,
    MarketQuote,
    FinancialStatement,
    FinancialMetric,
    KeyMetricsResearch,
    KeyMetric,
)


class CompanyResearchAPITestCase(APITestCase):

    @patch(
        "apps.research.views.ResearchService.get_company_profile"
    )
    @patch(
        "apps.research.views.ResearchService.get_market_data"
    )
    def test_us_company_research(
        self,
        mock_market_data,
        mock_profile,
    ):
        mock_profile.return_value = CompanyProfile(
            ticker="AAPL",
            name="Apple Inc",
            exchange="NASDAQ",
            country="US",
            industry="Technology",
        )

        mock_market_data.return_value = MarketQuote(
            ticker="AAPL",
            price=310.12,
            change=-3.33,
            percent_change=-1.0624,
            high=312.035,
            low=309.4001,
            open=311.0125,
            previous_close=313.45,
        )

        response = self.client.get(
            "/api/research/company/",
            {
                "ticker": "AAPL",
                "market": "US",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["ticker"],
            "AAPL",
        )

        self.assertEqual(
            response.data["company"]["name"],
            "Apple Inc",
        )

        self.assertEqual(
            response.data["market_data"]["price"],
            310.12,
        )

    @patch(
        "apps.research.views.ResearchService.get_company_profile"
    )
    @patch(
        "apps.research.views.ResearchService.get_market_data"
    )
    def test_indian_company_research(
        self,
        mock_market_data,
        mock_profile,
    ):
        mock_profile.return_value = CompanyProfile(
            ticker="RELIANCE",
            name="Reliance Industries",
            exchange="NSE/BSE",
            country="India",
            industry="Oil & Gas Operations",
            isin="INE002A01018",
            nse_symbol="RELIANCE",
            bse_code="500325",
        )

        mock_market_data.return_value = [
            ExchangeQuote(
                exchange="NSE",
                price=1317.0,
                percent_change=0.39,
                year_high=1611.2,
                year_low=1250.55,
            ),
            ExchangeQuote(
                exchange="BSE",
                price=1312.6,
                percent_change=0.39,
                year_high=1611.2,
                year_low=1250.55,
            ),
        ]

        response = self.client.get(
            "/api/research/company/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["company"]["name"],
            "Reliance Industries",
        )

        self.assertEqual(
            response.data["company"]["isin"],
            "INE002A01018",
        )

        self.assertEqual(
            len(response.data["market_data"]),
            2,
        )

    def test_missing_ticker(self):
        response = self.client.get(
            "/api/research/company/",
            {
                "market": "US",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_invalid_market(self):
        response = self.client.get(
            "/api/research/company/",
            {
                "ticker": "AAPL",
                "market": "UK",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_empty_ticker(self):
        response = self.client.get(
            "/api/research/company/",
            {
                "ticker": "",
                "market": "US",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch(
    "apps.research.views.ResearchService.get_market_data"
    )
    @patch(
        "apps.research.views.ResearchService.get_company_profile"
    )
    def test_company_not_found(
        self,
        mock_profile,
        mock_market_data,
    ):
        mock_profile.side_effect = ValueError(
            "Company not found for ticker: XYZNOTAREALSTOCK"
        )

        response = self.client.get(
            "/api/research/company/",
            {
                "ticker": "XYZNOTAREALSTOCK",
                "market": "US",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["error"],
            "Company not found for ticker: XYZNOTAREALSTOCK",
        )

        mock_market_data.assert_not_called()
        
    @patch(
    "apps.research.views.ResearchService.get_company_profile"
    )
    def test_provider_unavailable(
        self,
        mock_profile,
    ):
        mock_profile.side_effect = requests.RequestException(
            "Provider unavailable"
        )

        response = self.client.get(
            "/api/research/company/",
            {
                "ticker": "AAPL",
                "market": "US",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_502_BAD_GATEWAY,
        )

        self.assertEqual(
            response.data["error"],
            "External market data provider is unavailable.",
        )
        
    @patch("apps.research.views.ResearchService.get_financials")
    def test_indian_financials(self, mock_financials):

        mock_financials.return_value = [
            FinancialStatement(
                statement_type="INC",
                fiscal_year="2026",
                end_date="2026-03-31",
                period_type="Months",
                period_length=12,
                metrics=[
                    FinancialMetric(
                        name="Revenue",
                        key="Revenue",
                        value=1075675.0,
                    ),
                    FinancialMetric(
                        name="Net Income",
                        key="NetIncome",
                        value=80775.0,
                    ),
                ],
            )
        ]

        response = self.client.get(
            "/api/research/financials/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["ticker"],
            "RELIANCE",
        )

        self.assertEqual(
            response.data["market"],
            "IN",
        )

        self.assertEqual(
            len(response.data["financials"]),
            1,
        )

        self.assertEqual(
            response.data["financials"][0]["statement_type"],
            "INC",
        )

        self.assertEqual(
            response.data["financials"][0]["metrics"][0]["value"],
            1075675.0,
        )

        mock_financials.assert_called_once()    
        
    def test_financials_missing_ticker(self):

        response = self.client.get(
            "/api/research/financials/",
            {
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    def test_financials_invalid_market(self):

        response = self.client.get(
            "/api/research/financials/",
            {
                "ticker": "RELIANCE",
                "market": "UK",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    def test_financials_empty_ticker(self):

        response = self.client.get(
            "/api/research/financials/",
            {
                "ticker": "",
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        
    @patch(
        "apps.research.views.ResearchService.get_financials"
    )
    def test_financials_not_found(self, mock_financials):

        mock_financials.side_effect = ValueError(
            "Financials not found for ticker: XYZNOTAREALSTOCK"
        )

        response = self.client.get(
            "/api/research/financials/",
            {
                "ticker": "XYZNOTAREALSTOCK",
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["error"],
            "Financials not found for ticker: XYZNOTAREALSTOCK",
        )
        
    @patch(
    "apps.research.views.ResearchService.get_key_metrics"
    )
    def test_indian_key_metrics(self, mock_key_metrics):

        mock_key_metrics.return_value = KeyMetricsResearch(
            ticker="RELIANCE",
            metrics=[
                KeyMetric(
                    category="mgmtEffectiveness",
                    name="Return on average equity - 5 year average",
                    key="returnOnAverageEquity5YearAverage",
                    value=8.78,
                    raw_value="8.78",
                ),
                KeyMetric(
                    category="valuation",
                    name="Peg Ratio",
                    key="pegRatio",
                    value=3.48,
                    raw_value="3.48",
                ),
            ],
        )

        response = self.client.get(
            "/api/research/metrics/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["ticker"],
            "RELIANCE",
        )

        self.assertEqual(
            len(response.data["metrics"]),
            2,
        )

        self.assertEqual(
            response.data["metrics"][0]["value"],
            8.78,
        )

        self.assertEqual(
            response.data["metrics"][0]["raw_value"],
            "8.78",
        )

        mock_key_metrics.assert_called_once()
        
    def test_metrics_missing_ticker(self):

        response = self.client.get(
            "/api/research/metrics/",
            {
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        
    def test_metrics_invalid_market(self):

        response = self.client.get(
            "/api/research/metrics/",
            {
                "ticker": "RELIANCE",
                "market": "UK",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        
    def test_metrics_empty_ticker(self):

        response = self.client.get(
            "/api/research/metrics/",
            {
                "ticker": "",
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        
    @patch(
        "apps.research.views.ResearchService.get_key_metrics"
    )
    def test_metrics_not_found(self, mock_key_metrics):

        mock_key_metrics.side_effect = ValueError(
            "Key metrics not found for ticker: XYZNOTAREALSTOCK"
        )

        response = self.client.get(
            "/api/research/metrics/",
            {
                "ticker": "XYZNOTAREALSTOCK",
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["error"],
            "Key metrics not found for ticker: XYZNOTAREALSTOCK",
        )
        
    @patch(
    "apps.research.views.ResearchService.get_key_metrics"
    )
    def test_metrics_provider_error(self, mock_key_metrics):

        mock_key_metrics.side_effect = requests.RequestException(
            "Indian API unavailable"
        )

        response = self.client.get(
            "/api/research/metrics/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_502_BAD_GATEWAY,
        )

        self.assertEqual(
            response.data["error"],
            "Indian API unavailable",
        )