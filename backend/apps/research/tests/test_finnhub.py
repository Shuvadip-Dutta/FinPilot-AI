from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from requests.exceptions import RequestException

from apps.research.services.providers.finnhub import FinnhubProvider
from apps.research.services.schemas import (
    ExchangeQuote,
    FinancialStatement,
    KeyMetricsResearch,
    MarketQuote,
)
from apps.research.services.symbols import Market


class FinnhubProviderTestCase(SimpleTestCase):

    def setUp(self):
        self.provider = FinnhubProvider()

    @patch.object(FinnhubProvider, "_get")
    def test_get_key_metrics_mapping(self, mock_get):
        mock_get.return_value = {
            "metric": {
                "peTTM": 27.7724,
                "forwardPE": 18.10034,
                "evEbitdaTTM": 26.6854,
                "pb": 23.3934,
                "marketCapitalization": 3000000.0,
                "enterpriseValue": 2950000.0,
                "epsTTM": 2.50,
                "bookValuePerShareQuarterly": 5.20,
                "52WeekHigh": 140.50,
                "52WeekLow": 80.25,
                "roeTTM": 45.2,
                "roaTTM": 22.1,
                "netProfitMarginTTM": 55.4,
                "operatingMarginTTM": 62.1,
                "grossMarginTTM": 75.0,
                "revenueGrowthQuarterlyYoy": 122.0,
            }
        }

        result = self.provider.get_key_metrics("NVDA", Market.US)

        self.assertIsInstance(result, KeyMetricsResearch)
        self.assertEqual(result.ticker, "NVDA")

        metric_dict = {m.key: m for m in result.metrics}

        self.assertIn("pe_ttm", metric_dict)
        self.assertEqual(metric_dict["pe_ttm"].name, "Trailing P/E")
        self.assertEqual(metric_dict["pe_ttm"].category, "valuation")
        self.assertAlmostEqual(metric_dict["pe_ttm"].value, 27.7724)

        self.assertIn("forward_pe", metric_dict)
        self.assertEqual(metric_dict["forward_pe"].name, "Forward P/E")
        self.assertEqual(metric_dict["forward_pe"].category, "valuation")
        self.assertAlmostEqual(metric_dict["forward_pe"].value, 18.10034)

        self.assertIn("ev_ebitda_ttm", metric_dict)
        self.assertEqual(metric_dict["ev_ebitda_ttm"].name, "EV/EBITDA")
        self.assertAlmostEqual(metric_dict["ev_ebitda_ttm"].value, 26.6854)

        self.assertIn("pb", metric_dict)
        self.assertEqual(metric_dict["pb"].name, "Price/Book")
        self.assertAlmostEqual(metric_dict["pb"].value, 23.3934)

        self.assertIn("market_capitalization", metric_dict)
        self.assertIn("52_week_high", metric_dict)
        self.assertEqual(metric_dict["52_week_high"].value, 140.50)
        self.assertEqual(metric_dict["52_week_low"].value, 80.25)

    @patch.object(FinnhubProvider, "_get")
    def test_get_key_metrics_missing_and_null_values(self, mock_get):
        mock_get.return_value = {
            "metric": {
                "peTTM": 25.0,
                "forwardPE": None,
                "pb": None,
                # evEbitdaTTM is completely absent from the dict
            }
        }

        result = self.provider.get_key_metrics("NVDA", Market.US)
        metric_dict = {m.key: m for m in result.metrics}

        # forward_pe was explicitly null
        self.assertIn("forward_pe", metric_dict)
        self.assertIsNone(metric_dict["forward_pe"].value)
        self.assertNotEqual(metric_dict["forward_pe"].value, 0)

        # ev_ebitda_ttm was absent
        self.assertIn("ev_ebitda_ttm", metric_dict)
        self.assertIsNone(metric_dict["ev_ebitda_ttm"].value)
        self.assertNotEqual(metric_dict["ev_ebitda_ttm"].value, 0)

        # pb was null
        self.assertIn("pb", metric_dict)
        self.assertIsNone(metric_dict["pb"].value)

        # pe_ttm had value
        self.assertEqual(metric_dict["pe_ttm"].value, 25.0)

    @patch.object(FinnhubProvider, "_get")
    def test_get_financials_mapping(self, mock_get):
        mock_get.return_value = {
            "symbol": "NVDA",
            "data": [
                {
                    "year": 2026,
                    "endDate": "2026-01-26",
                    "period": "FY",
                    "report": {
                        "bs": [
                            {"concept": "Assets", "label": "Total Assets", "value": 65728000000},
                            {"concept": "Liabilities", "label": "Total Liabilities", "value": 22750000000},
                        ],
                        "ic": [
                            {"concept": "Revenues", "label": "Revenue", "value": 60922000000},
                            {"concept": "NetIncomeLoss", "label": "Net Income", "value": 29760000000},
                        ],
                        "cf": [
                            {"concept": "NetCashProvidedByUsedInOperatingActivities", "label": "Operating Cash Flow", "value": 28090000000},
                        ],
                    },
                }
            ],
        }

        result = self.provider.get_financials("NVDA", Market.US)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)

        by_type = {s.statement_type: s for s in result}
        self.assertIn("BAL", by_type)
        self.assertIn("INC", by_type)
        self.assertIn("CAS", by_type)

        bal = by_type["BAL"]
        self.assertEqual(bal.fiscal_year, "2026")
        self.assertEqual(bal.end_date, "2026-01-26")
        self.assertEqual(bal.period_type, "Annual")
        self.assertEqual(bal.period_length, 12)
        self.assertEqual(len(bal.metrics), 2)
        self.assertEqual(bal.metrics[0].name, "Total Assets")
        self.assertEqual(bal.metrics[0].value, 65728000000.0)

        inc = by_type["INC"]
        self.assertEqual(inc.metrics[0].name, "Revenue")
        self.assertEqual(inc.metrics[0].value, 60922000000.0)

        cas = by_type["CAS"]
        self.assertEqual(cas.metrics[0].name, "Operating Cash Flow")
        self.assertEqual(cas.metrics[0].value, 28090000000.0)

    @patch.object(FinnhubProvider, "_get")
    def test_get_financials_empty_and_error(self, mock_get):
        mock_get.return_value = {"data": []}
        res = self.provider.get_financials("NVDA", Market.US)
        self.assertEqual(res, [])

        mock_get.return_value = None
        res = self.provider.get_financials("NVDA", Market.US)
        self.assertEqual(res, [])

    @patch.object(FinnhubProvider, "_get")
    def test_get_quotes_normalized_contract(self, mock_get):
        def side_effect(endpoint, params):
            if endpoint == "quote":
                return {
                    "c": 125.5,
                    "d": 2.5,
                    "dp": 2.03,
                    "h": 126.0,
                    "l": 122.0,
                    "o": 123.0,
                    "pc": 123.0,
                }
            if endpoint == "stock/metric":
                return {
                    "metric": {
                        "52WeekHigh": 140.76,
                        "52WeekLow": 75.60,
                    }
                }
            return {}

        mock_get.side_effect = side_effect

        quotes = self.provider.get_quotes("NVDA", Market.US)

        self.assertIsInstance(quotes, list)
        self.assertEqual(len(quotes), 1)
        q = quotes[0]
        self.assertIsInstance(q, ExchangeQuote)
        self.assertEqual(q.exchange, "US")
        self.assertEqual(q.price, 125.5)
        self.assertEqual(q.percent_change, 2.03)
        self.assertEqual(q.year_high, 140.76)
        self.assertEqual(q.year_low, 75.60)
