from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.research.services.exceptions import ProviderResponseError
from apps.research.services.research_service import ResearchService
from apps.research.services.schemas import (
    CompanyProfile,
    ExchangeQuote,
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

    @patch("apps.research.services.research_service.FinnhubProvider.get_quotes")
    def test_us_get_market_data(self, mock_get_quotes):
        mock_get_quotes.return_value = [
            ExchangeQuote(
                exchange="US",
                price=125.5,
                percent_change=2.03,
                year_high=140.76,
                year_low=75.60,
            )
        ]

        service = ResearchService()
        result = service.get_market_data("NVDA", Market.US)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        q = result[0]
        self.assertIsInstance(q, ExchangeQuote)
        self.assertEqual(q.exchange, "US")
        self.assertEqual(q.price, 125.5)
        self.assertEqual(q.percent_change, 2.03)
        self.assertEqual(q.year_high, 140.76)
        self.assertEqual(q.year_low, 75.60)

        self.assertIsNotNone(getattr(result, "_provenance", None))
        self.assertEqual(result._provenance.primary_provider, "finnhub")
        self.assertEqual(result._provenance.source, "finnhub")
        self.assertFalse(result._provenance.fallback_used)
        self.assertEqual(result._provenance.data_status, "complete")

    @patch("apps.research.services.research_service.FinnhubProvider.get_key_metrics")
    def test_us_get_key_metrics_complete(self, mock_get_metrics):
        mock_get_metrics.return_value = KeyMetricsResearch(
            ticker="NVDA",
            metrics=[
                KeyMetric(category="valuation", name="Trailing P/E", key="pe_ttm", value=27.77),
                KeyMetric(category="valuation", name="Forward P/E", key="forward_pe", value=18.10),
                KeyMetric(category="valuation", name="EV/EBITDA", key="ev_ebitda_ttm", value=26.68),
                KeyMetric(category="valuation", name="Price/Book", key="pb", value=23.39),
            ],
        )

        service = ResearchService()
        result = service.get_key_metrics("NVDA", Market.US)

        self.assertIsInstance(result, KeyMetricsResearch)
        self.assertEqual(result.ticker, "NVDA")
        metric_names = [m.name for m in result.metrics]
        self.assertIn("Trailing P/E", metric_names)
        self.assertIn("Forward P/E", metric_names)
        self.assertIn("EV/EBITDA", metric_names)
        self.assertIn("Price/Book", metric_names)

        self.assertIsNotNone(getattr(result, "_provenance", None))
        self.assertEqual(result._provenance.primary_provider, "finnhub")
        self.assertEqual(result._provenance.source, "finnhub")
        self.assertFalse(result._provenance.fallback_used)
        self.assertEqual(result._provenance.data_status, "complete")

    @patch("apps.research.services.research_service.FinnhubProvider.get_key_metrics")
    def test_us_get_key_metrics_partial(self, mock_get_metrics):
        # Missing forward_pe
        mock_get_metrics.return_value = KeyMetricsResearch(
            ticker="NVDA",
            metrics=[
                KeyMetric(category="valuation", name="Trailing P/E", key="pe_ttm", value=27.77),
                KeyMetric(category="valuation", name="Forward P/E", key="forward_pe", value=None),
                KeyMetric(category="valuation", name="EV/EBITDA", key="ev_ebitda_ttm", value=26.68),
                KeyMetric(category="valuation", name="Price/Book", key="pb", value=23.39),
            ],
        )

        service = ResearchService()
        result = service.get_key_metrics("NVDA", Market.US)

        self.assertIsNotNone(getattr(result, "_provenance", None))
        self.assertEqual(result._provenance.data_status, "partial")

    @patch("apps.research.services.research_service.FinnhubProvider.get_financials")
    def test_us_get_financials_complete(self, mock_get_financials):
        mock_get_financials.return_value = [
            FinancialStatement(
                statement_type="INC",
                fiscal_year="2026",
                end_date="2026-01-26",
                period_type="Annual",
                period_length=12,
                metrics=[FinancialMetric(name="Revenue", key="Revenue", value=60922000000.0)],
            ),
            FinancialStatement(
                statement_type="BAL",
                fiscal_year="2026",
                end_date="2026-01-26",
                period_type="Annual",
                period_length=12,
                metrics=[FinancialMetric(name="Total Assets", key="Assets", value=65728000000.0)],
            ),
            FinancialStatement(
                statement_type="CAS",
                fiscal_year="2026",
                end_date="2026-01-26",
                period_type="Annual",
                period_length=12,
                metrics=[FinancialMetric(name="Operating Cash Flow", key="OCF", value=28090000000.0)],
            ),
        ]

        service = ResearchService()
        result = service.get_financials("NVDA", Market.US)

        self.assertEqual(len(result), 3)
        self.assertIsNotNone(getattr(result, "_provenance", None))
        self.assertEqual(result._provenance.primary_provider, "finnhub")
        self.assertEqual(result._provenance.source, "finnhub")
        self.assertFalse(result._provenance.fallback_used)
        self.assertEqual(result._provenance.data_status, "complete")


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