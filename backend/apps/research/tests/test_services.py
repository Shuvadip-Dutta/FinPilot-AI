from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.research.services.exceptions import ProviderResponseError
from apps.research.services.research_service import ResearchService
from apps.research.services.schemas import (
    CompanyProfile,
    FinancialMetric,
    FinancialStatement,
    HistoricalCandle,
    HistoricalMarketData,
    KeyMetric,
    KeyMetricsResearch,
)
from apps.research.services.symbols import Market


class ResearchServiceTestCase(SimpleTestCase):

    @patch(
        "apps.research.services.research_service.UpstoxProvider.get_historical"
    )
    def test_get_historical_data(
        self,
        mock_get_historical,
    ):
        mock_get_historical.return_value = HistoricalMarketData(
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

        service = ResearchService()

        result = service.get_historical_data(
            "RELIANCE",
            to_date="2026-08-28",
            from_date="2026-08-25",
            market=Market.INDIA,
        )

        mock_get_historical.assert_called_once_with(
            "RELIANCE",
            "2026-08-28",
            "2026-08-25",
            Market.INDIA,
        )

        self.assertEqual(
            result.ticker,
            "RELIANCE",
        )

        self.assertEqual(
            len(result.candles),
            1,
        )

    def test_get_historical_data_unsupported_market(self):

        service = ResearchService()

        with self.assertRaises(ValueError) as context:
            service.get_historical_data(
                "AAPL",
                to_date="2026-08-28",
                market=Market.US,
            )

        self.assertEqual(
            str(context.exception),
            "Historical data is not yet supported for market: US",
        )

    @patch("apps.research.services.research_service.IndianAPIProvider.get_financials")
    @patch("apps.research.services.research_service.UpstoxProvider.get_financials")
    def test_financials_primary_success(self, mock_upstox, mock_indian_api):
        mock_stmt = FinancialStatement(
            statement_type="INC",
            fiscal_year="2026",
            end_date="2026-03-31",
            period_type="Annual",
            period_length=12,
            metrics=[FinancialMetric(name="Revenue", key="Revenue", value=100.0)],
        )
        mock_upstox.return_value = [mock_stmt]

        service = ResearchService()
        result = service.get_financials("LT", Market.INDIA)

        self.assertEqual(result, [mock_stmt])
        mock_upstox.assert_called_once_with("LT", Market.INDIA)
        mock_indian_api.assert_not_called()

    @patch("apps.research.services.research_service.IndianAPIProvider.get_financials")
    @patch("apps.research.services.research_service.UpstoxProvider.get_financials")
    def test_financials_empty_data_fallback(self, mock_upstox, mock_indian_api):
        mock_upstox.return_value = []
        mock_stmt = FinancialStatement(
            statement_type="INC",
            fiscal_year="2026",
            end_date="2026-03-31",
            period_type="Annual",
            period_length=12,
            metrics=[],
        )
        mock_indian_api.return_value = [mock_stmt]

        service = ResearchService()
        result = service.get_financials("LT", Market.INDIA)

        self.assertEqual(result, [mock_stmt])
        mock_upstox.assert_called_once_with("LT", Market.INDIA)
        mock_indian_api.assert_called_once_with("LT", Market.INDIA)

    @patch("apps.research.services.research_service.IndianAPIProvider.get_financials")
    @patch("apps.research.services.research_service.UpstoxProvider.get_financials")
    def test_financials_exception_fallback(self, mock_upstox, mock_indian_api):
        mock_upstox.side_effect = ProviderResponseError("Upstox error")
        mock_stmt = FinancialStatement(
            statement_type="INC",
            fiscal_year="2026",
            end_date="2026-03-31",
            period_type="Annual",
            period_length=12,
            metrics=[],
        )
        mock_indian_api.return_value = [mock_stmt]

        service = ResearchService()
        result = service.get_financials("LT", Market.INDIA)

        self.assertEqual(result, [mock_stmt])
        mock_upstox.assert_called_once_with("LT", Market.INDIA)
        mock_indian_api.assert_called_once_with("LT", Market.INDIA)

    @patch("apps.research.services.research_service.IndianAPIProvider.get_financials")
    @patch("apps.research.services.research_service.UpstoxProvider.get_financials")
    def test_financials_both_provider_failure(self, mock_upstox, mock_indian_api):
        mock_upstox.side_effect = ProviderResponseError("Upstox error")
        mock_indian_api.return_value = []

        service = ResearchService()
        result = service.get_financials("LT", Market.INDIA)

        self.assertEqual(result, [])
        mock_upstox.assert_called_once_with("LT", Market.INDIA)
        mock_indian_api.assert_called_once_with("LT", Market.INDIA)

    @patch("apps.research.services.research_service.IndianAPIProvider.get_key_metrics")
    @patch("apps.research.services.research_service.UpstoxProvider.get_key_metrics")
    def test_key_metrics_primary_success(self, mock_upstox, mock_indian_api):
        mock_res = KeyMetricsResearch(
            ticker="LT",
            metrics=[KeyMetric(category="valuation", name="PE Ratio", key="pe", value=30.0)],
        )
        mock_upstox.return_value = mock_res

        service = ResearchService()
        result = service.get_key_metrics("LT", Market.INDIA)

        self.assertEqual(result, mock_res)
        mock_upstox.assert_called_once_with("LT", Market.INDIA)
        mock_indian_api.assert_not_called()

    @patch("apps.research.services.research_service.IndianAPIProvider.get_key_metrics")
    @patch("apps.research.services.research_service.UpstoxProvider.get_key_metrics")
    def test_key_metrics_empty_data_fallback(self, mock_upstox, mock_indian_api):
        mock_upstox.return_value = KeyMetricsResearch(ticker="LT", metrics=[])
        fallback_res = KeyMetricsResearch(
            ticker="LT",
            metrics=[KeyMetric(category="valuation", name="PE", key="pe", value=25.0)],
        )
        mock_indian_api.return_value = fallback_res

        service = ResearchService()
        result = service.get_key_metrics("LT", Market.INDIA)

        self.assertEqual(result, fallback_res)
        mock_upstox.assert_called_once_with("LT", Market.INDIA)
        mock_indian_api.assert_called_once_with("LT", Market.INDIA)

    @patch("apps.research.services.research_service.IndianAPIProvider.get_company_profile")
    @patch("apps.research.services.research_service.UpstoxProvider.get_company_profile")
    def test_company_profile_primary_success(self, mock_upstox, mock_indian_api):
        mock_profile = CompanyProfile(ticker="LT", name="Larsen & Toubro Ltd", exchange="NSE", country="India")
        mock_upstox.return_value = mock_profile

        service = ResearchService()
        result = service.get_company_profile("LT", Market.INDIA)

        self.assertEqual(result, mock_profile)
        self.assertIsNotNone(getattr(result, "_provenance", None))
        self.assertEqual(result._provenance.primary_provider, "upstox")
        self.assertEqual(result._provenance.source, "upstox")
        self.assertFalse(result._provenance.fallback_used)
        self.assertEqual(result._provenance.data_status, "complete")
        mock_upstox.assert_called_once_with("LT", Market.INDIA)
        mock_indian_api.assert_not_called()

    @patch("apps.research.services.research_service.IndianAPIProvider.get_company_profile")
    @patch("apps.research.services.research_service.UpstoxProvider.get_company_profile")
    def test_company_profile_exception_fallback(self, mock_upstox, mock_indian_api):
        mock_upstox.side_effect = Exception("Upstox error")
        fallback_profile = CompanyProfile(ticker="LT", name="Larsen & Toubro Ltd", exchange="NSE", country="India")
        mock_indian_api.return_value = fallback_profile

        service = ResearchService()
        result = service.get_company_profile("LT", Market.INDIA)

        self.assertEqual(result, fallback_profile)
        self.assertIsNotNone(getattr(result, "_provenance", None))
        self.assertEqual(result._provenance.primary_provider, "upstox")
        self.assertEqual(result._provenance.source, "indian_api")
        self.assertTrue(result._provenance.fallback_used)
        self.assertEqual(result._provenance.fallback_reason, "upstox_exception: Exception")
        mock_upstox.assert_called_once_with("LT", Market.INDIA)
        mock_indian_api.assert_called_once_with("LT", Market.INDIA)

    @patch("apps.research.services.research_service.IndianAPIProvider.get_financials")
    @patch("apps.research.services.research_service.UpstoxProvider.get_financials")
    def test_financials_provenance_list_and_partial_data(self, mock_upstox, mock_indian_api):
        mock_stmt1 = FinancialStatement(
            statement_type="INC",
            fiscal_year="2026",
            end_date="2026-03-31",
            period_type="Annual",
            period_length=12,
            metrics=[FinancialMetric(name="Revenue", key="Revenue", value=100.0)],
        )
        mock_upstox.return_value = [mock_stmt1]

        service = ResearchService()
        result = service.get_financials("LT", Market.INDIA)

        self.assertEqual(len(result), 1)
        self.assertIsNotNone(getattr(result, "_provenance", None))
        self.assertEqual(result._provenance.primary_provider, "upstox")
        self.assertEqual(result._provenance.source, "upstox")
        self.assertFalse(result._provenance.fallback_used)
        self.assertEqual(result._provenance.data_status, "partial")
        self.assertIsNotNone(getattr(result[0], "_provenance", None))
        self.assertEqual(result[0]._provenance.source, "upstox")

    @patch("apps.research.services.research_service.IndianAPIProvider.get_financials")
    @patch("apps.research.services.research_service.UpstoxProvider.get_financials")
    def test_financials_empty_data_fallback_provenance(self, mock_upstox, mock_indian_api):
        mock_upstox.return_value = []
        mock_stmt = FinancialStatement(
            statement_type="INC",
            fiscal_year="2026",
            end_date="2026-03-31",
            period_type="Annual",
            period_length=12,
            metrics=[],
        )
        mock_indian_api.return_value = [mock_stmt]

        service = ResearchService()
        result = service.get_financials("LT", Market.INDIA)

        self.assertEqual(len(result), 1)
        self.assertIsNotNone(getattr(result, "_provenance", None))
        self.assertEqual(result._provenance.primary_provider, "upstox")
        self.assertEqual(result._provenance.source, "indian_api")
        self.assertTrue(result._provenance.fallback_used)
        self.assertEqual(result._provenance.fallback_reason, "upstox_empty_data")


class MarketNormalizeTestCase(SimpleTestCase):

    def test_market_normalize_known_values(self):
        self.assertEqual(Market.normalize("IN"), "IN")
        self.assertEqual(Market.normalize("in"), "IN")
        self.assertEqual(Market.normalize("INDIA"), "IN")
        self.assertEqual(Market.normalize("india"), "IN")
        self.assertEqual(Market.normalize("US"), "US")
        self.assertEqual(Market.normalize("us"), "US")
        self.assertEqual(Market.normalize("USA"), "US")
        self.assertEqual(Market.normalize("UNITED STATES"), "US")
        self.assertIsNone(Market.normalize(None))