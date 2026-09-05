from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
import requests
from rest_framework import status
from rest_framework.test import APITestCase

from apps.research.models import ResearchEvidence, ResearchSession
from apps.research.services.session_service import ResearchSessionService
from apps.research.services.schemas import (
    CompanyProfile,
    ExchangeQuote,
    MarketQuote,
    FinancialStatement,
    FinancialMetric,
    KeyMetricsResearch,
    KeyMetric,
    NewsArticle,
    NewsResearch,
    HistoricalCandle,
    HistoricalMarketData,
)


class CompanyResearchAPITestCase(APITestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="testresearcher",
            email="researcher@example.com",
            password="password123",
        )
        self.client.force_authenticate(user=self.user)

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
            "/api/v1/research/company/",
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
            "/api/v1/research/company/",
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
            "/api/v1/research/company/",
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
            "/api/v1/research/company/",
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
            "/api/v1/research/company/",
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
            "/api/v1/research/company/",
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
            "/api/v1/research/company/",
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
            "/api/v1/research/financials/",
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
            "/api/v1/research/financials/",
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
            "/api/v1/research/financials/",
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
            "/api/v1/research/financials/",
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
            "/api/v1/research/financials/",
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
            "/api/v1/research/metrics/",
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
            "/api/v1/research/metrics/",
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
            "/api/v1/research/metrics/",
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
            "/api/v1/research/metrics/",
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
            "/api/v1/research/metrics/",
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
            "/api/v1/research/metrics/",
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
        
    @patch(
        "apps.research.views.ResearchService.get_news"
    )
    def test_news_success(
        self,
        mock_get_news,
    ):
        mock_get_news.return_value = NewsResearch(
            ticker="RELIANCE",
            articles=[
                NewsArticle(
                    title="Reliance announces new investment",
                    summary="Reliance plans a major investment.",
                    url="https://example.com/reliance",
                    source="example.com",
                    published_at="2026-08-28T10:00:00Z",
                    image_url=None,
                    relevance_score=90.0,
                    entities=[],
                )
            ],
        )

        response = self.client.get(
            "/api/v1/research/news/",
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
            len(response.data["articles"]),
            1,
        )

        self.assertEqual(
            response.data["articles"][0]["title"],
            "Reliance announces new investment",
        )    

    @patch(
        "apps.research.views.ResearchService.get_news"
    )
    def test_news_provider_unavailable(
        self,
        mock_get_news,
    ):
        mock_get_news.side_effect = requests.RequestException(
            "Marketaux unavailable"
        )

        response = self.client.get(
            "/api/v1/research/news/",
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
            "External market data provider is unavailable.",
        )
        
    @patch(
        "apps.research.views.ResearchService.get_news"
    )
    def test_news_empty_result(
        self,
        mock_get_news,
    ):
        mock_get_news.return_value = NewsResearch(
            ticker="RELIANCE",
            articles=[],
        )

        response = self.client.get(
            "/api/v1/research/news/",
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
            response.data["articles"],
            [],
        )
        
    @patch(
        "apps.research.views.ResearchService.get_historical_data"
    )
    def test_historical_success(
        self,
        mock_historical,
    ):
        mock_historical.return_value = HistoricalMarketData(
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

        response = self.client.get(
            "/api/v1/research/historical/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
                "to_date": "2026-08-28",
                "from_date": "2026-08-25",
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
            len(response.data["candles"]),
            1,
        )

        self.assertEqual(
            response.data["candles"][0]["close"],
            1282.2,
        )
        
    def test_historical_missing_to_date(self):

        response = self.client.get(
            "/api/v1/research/historical/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "to_date",
            response.data,
        )
    def test_historical_invalid_to_date(self):
        response = self.client.get(
            "/api/v1/research/historical/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
                "to_date": "2026-99-99",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "to_date",
            response.data,
        )
        
    def test_historical_invalid_from_date(self):
        response = self.client.get(
            "/api/v1/research/historical/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
                "to_date": "2026-08-28",
                "from_date": "invalid-date",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "from_date",
            response.data,
        )
        
    def test_historical_reversed_date_range(self):
        response = self.client.get(
            "/api/v1/research/historical/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
                "to_date": "2026-08-25",
                "from_date": "2026-08-28",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "from_date",
            response.data,
        )    
        
    def test_historical_future_to_date(self):
        response = self.client.get(
            "/api/v1/research/historical/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
                "to_date": "2099-01-01",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "to_date",
            response.data,
        )
        
    @patch(
        "apps.research.views.ResearchService.get_historical_data"
    )
    def test_historical_provider_unavailable(
        self,
        mock_historical,
    ):
        mock_historical.side_effect = requests.RequestException(
            "Upstox unavailable"
        )

        response = self.client.get(
            "/api/v1/research/historical/",
            {
                "ticker": "RELIANCE",
                "market": "IN",
                "to_date": "2026-08-28",
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
        
    @patch(
        "apps.research.views.ResearchService.get_historical_data"
    )
    def test_historical_invalid_ticker(
        self,
        mock_historical,
    ):
        mock_historical.side_effect = ValueError(
            "Unsupported Upstox ticker: UNKNOWN"
        )

        response = self.client.get(
            "/api/v1/research/historical/",
            {
                "ticker": "UNKNOWN",
                "market": "IN",
                "to_date": "2026-08-28",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["error"],
            "Unsupported Upstox ticker: UNKNOWN",
        )


class ResearchSessionAPITestCase(APITestCase):

    def setUp(self):
        super().setUp()
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="password123",
        )
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="password123",
        )

    def test_authenticated_user_can_list_own_sessions(self):
        s1 = ResearchSessionService.create_session(
            user_message="Analyze RELIANCE",
            user=self.user1,
            ticker="RELIANCE",
            market="IN",
            route="financial",
        )
        s2 = ResearchSessionService.create_session(
            user_message="Analyze TCS",
            user=self.user1,
            ticker="TCS",
            market="IN",
            route="market",
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/research/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        session_ids = [item["id"] for item in response.data]
        self.assertIn(str(s1.id), session_ids)
        self.assertIn(str(s2.id), session_ids)

    def test_another_users_sessions_are_absent(self):
        s1 = ResearchSessionService.create_session(
            user_message="User 1 session",
            user=self.user1,
            ticker="RELIANCE",
        )
        s2 = ResearchSessionService.create_session(
            user_message="User 2 session",
            user=self.user2,
            ticker="INFY",
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/research/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(s1.id))
        self.assertNotIn(str(s2.id), [item["id"] for item in response.data])

    def test_authenticated_user_can_retrieve_own_session(self):
        s1 = ResearchSessionService.create_session(
            user_message="Detailed research on AAPL",
            user=self.user1,
            ticker="AAPL",
            market="US",
            route="financial",
        )
        ResearchEvidence.objects.create(
            session=s1,
            agent_name="financial",
            response="Financial metrics collected",
            tools_used=["get_financial_metrics"],
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/api/v1/research/sessions/{s1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(s1.id))
        self.assertEqual(response.data["user_message"], "Detailed research on AAPL")
        self.assertEqual(len(response.data["evidence_items"]), 1)
        self.assertEqual(response.data["evidence_items"][0]["agent_name"], "financial")

    def test_another_users_session_returns_404(self):
        s2 = ResearchSessionService.create_session(
            user_message="Private session of user2",
            user=self.user2,
            ticker="TCS",
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/api/v1/research/sessions/{s2.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_evidence_is_returned_only_for_owned_session(self):
        s1 = ResearchSessionService.create_session(
            user_message="User 1 prompt",
            user=self.user1,
            ticker="AAPL",
        )
        ev1 = ResearchEvidence.objects.create(
            session=s1,
            agent_name="market",
            response="Market evidence for user 1",
        )

        s2 = ResearchSessionService.create_session(
            user_message="User 2 prompt",
            user=self.user2,
            ticker="MSFT",
        )
        ev2 = ResearchEvidence.objects.create(
            session=s2,
            agent_name="market",
            response="Market evidence for user 2",
        )

        self.client.force_authenticate(user=self.user1)
        res1 = self.client.get(f"/api/v1/research/sessions/{s1.id}/")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res1.data["evidence_items"]), 1)
        self.assertEqual(res1.data["evidence_items"][0]["response"], "Market evidence for user 1")

        res2 = self.client.get(f"/api/v1/research/sessions/{s2.id}/")
        self.assertEqual(res2.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_requests_return_401(self):
        s1 = ResearchSessionService.create_session(
            user_message="Public test",
            user=self.user1,
        )
        self.client.force_authenticate(user=None)

        res_list = self.client.get("/api/v1/research/sessions/")
        self.assertEqual(res_list.status_code, status.HTTP_401_UNAUTHORIZED)

        res_detail = self.client.get(f"/api/v1/research/sessions/{s1.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_newest_first_ordering_works(self):
        import time
        s1 = ResearchSessionService.create_session(
            user_message="First session",
            user=self.user1,
            ticker="RELIANCE",
        )
        time.sleep(0.01)
        s2 = ResearchSessionService.create_session(
            user_message="Second session",
            user=self.user1,
            ticker="TCS",
        )
        time.sleep(0.01)
        s3 = ResearchSessionService.create_session(
            user_message="Third session",
            user=self.user1,
            ticker="INFY",
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/research/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data]
        self.assertEqual(ids, [str(s3.id), str(s2.id), str(s1.id)])

    def test_completed_and_failed_sessions_represented_correctly(self):
        s_completed = ResearchSessionService.create_session(
            user_message="Successful run",
            user=self.user1,
            ticker="RELIANCE",
        )
        s_failed = ResearchSessionService.create_session(
            user_message="Failed run",
            user=self.user1,
            ticker="TCS",
        )
        s_failed.status = "FAILED"
        s_failed.save()

        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/research/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = {item["id"]: item["status"] for item in response.data}
        self.assertEqual(statuses[str(s_completed.id)], "COMPLETED")
        self.assertEqual(statuses[str(s_failed.id)], "FAILED")

    def test_response_does_not_expose_secrets(self):
        s1 = ResearchSessionService.create_session(
            user_message="Secret check",
            user=self.user1,
            ticker="RELIANCE",
        )
        ResearchEvidence.objects.create(
            session=s1,
            agent_name="risk",
            response="Risk assessment data",
        )

        self.client.force_authenticate(user=self.user1)

        res_list = self.client.get("/api/v1/research/sessions/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        session_data = res_list.data[0]
        self.assertNotIn("password", session_data)
        self.assertNotIn("user", session_data)
        self.assertNotIn("secret", session_data)

        res_detail = self.client.get(f"/api/v1/research/sessions/{s1.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        detail_data = res_detail.data
        self.assertNotIn("password", detail_data)
        self.assertNotIn("user", detail_data)
        self.assertNotIn("secret", detail_data)

        
        
