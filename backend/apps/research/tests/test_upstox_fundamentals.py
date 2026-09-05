from unittest.mock import patch
from django.test import TestCase

from apps.research.services.providers.upstox import UpstoxProvider
from apps.research.services.symbols import Market


class UpstoxFundamentalsTestCase(TestCase):

    def setUp(self):
        self.provider = UpstoxProvider.__new__(UpstoxProvider)
        self.provider.access_token = "mock_token"

    @patch("apps.research.services.providers.upstox.UpstoxProvider._get")
    def test_get_company_profile(self, mock_get):
        mock_get.return_value = {
            "status": "success",
            "data": {
                "company_name": "Larsen & Toubro Ltd",
                "exchange": "NSE",
                "sector": "Engineering",
                "industry": "Engineering & Construction",
                "company_profile": "Leading Indian multinational engaged in EPC projects.",
                "symbol": "LT",
            },
        }

        profile = self.provider.get_company_profile("LT", Market.INDIA)

        self.assertEqual(profile.ticker, "LT")
        self.assertEqual(profile.name, "Larsen & Toubro Ltd")
        self.assertEqual(profile.isin, "INE018A01030")
        self.assertEqual(profile.sector, "Engineering")
        self.assertEqual(profile.industry, "Engineering & Construction")
        mock_get.assert_called_once_with("fundamentals/INE018A01030/profile", {}, base_url="https://api.upstox.com/v2")

    @patch("apps.research.services.providers.upstox.UpstoxProvider._get")
    def test_get_financials_statements(self, mock_get):
        def side_effect(endpoint, params, base_url=None):
            if "income-statement" in endpoint:
                return {
                    "status": "success",
                    "data": {
                        "type": "consolidated",
                        "time_period": "yearly",
                        "income_statement": [
                            {
                                "category": "revenue",
                                "history": [
                                    {"value": 291635.04, "period": "Mar 2026"},
                                ],
                            },
                            {
                                "category": "net_profit",
                                "history": [
                                    {"value": 19159.4, "period": "Mar 2026"},
                                ],
                            },
                        ],
                    },
                }
            if "balance-sheet" in endpoint:
                return {
                    "status": "success",
                    "data": {
                        "type": "consolidated",
                        "time_period": "yearly",
                        "history": [
                            {"total_asset": 452549.88, "total_liability": 324019.42, "period": "Mar 2026"},
                        ],
                    },
                }
            if "cash-flow" in endpoint:
                return {
                    "status": "success",
                    "data": {
                        "type": "consolidated",
                        "time_period": "yearly",
                        "cash_flow": [
                            {
                                "category": "operating",
                                "history": [
                                    {"value": 16741.0, "period": "Mar 2026"},
                                ],
                            }
                        ],
                    },
                }
            return {"status": "error", "data": None}

        mock_get.side_effect = side_effect

        statements = self.provider.get_financials("LT", Market.INDIA)

        self.assertEqual(len(statements), 3)

        inc_stmt = next(s for s in statements if s.statement_type == "INC")
        bal_stmt = next(s for s in statements if s.statement_type == "BAL")
        cas_stmt = next(s for s in statements if s.statement_type == "CAS")

        self.assertEqual(inc_stmt.fiscal_year, "2026")
        self.assertEqual(len(inc_stmt.metrics), 2)
        rev_metric = next(m for m in inc_stmt.metrics if m.key == "revenue")
        self.assertEqual(rev_metric.name, "Revenue")
        self.assertEqual(rev_metric.value, 291635.04)

        self.assertEqual(bal_stmt.fiscal_year, "2026")
        asset_metric = next(m for m in bal_stmt.metrics if m.key == "total_asset")
        self.assertEqual(asset_metric.value, 452549.88)

        self.assertEqual(cas_stmt.fiscal_year, "2026")
        op_metric = next(m for m in cas_stmt.metrics if m.key == "operating_cash_flow")
        self.assertEqual(op_metric.value, 16741.0)

    @patch("apps.research.services.providers.upstox.UpstoxProvider._get")
    def test_get_key_metrics_ratios(self, mock_get):
        mock_get.return_value = {
            "status": "success",
            "data": [
                {"name": "P/E", "company_value": "27.8", "sector_value": "18.3"},
                {"name": "P/B", "company_value": "4.99", "sector_value": "1.97"},
                {"name": "ROE", "company_value": "14.72%", "sector_value": "7.26%"},
                {"name": "ROCE", "company_value": "15.13%", "sector_value": "29.98%"},
            ],
        }

        result = self.provider.get_key_metrics("LT", Market.INDIA)

        self.assertEqual(result.ticker, "LT")
        self.assertEqual(len(result.metrics), 4)

        pe_metric = next(m for m in result.metrics if m.name == "P/E")
        self.assertEqual(pe_metric.category, "valuation")
        self.assertEqual(pe_metric.value, 27.8)

        roe_metric = next(m for m in result.metrics if m.name == "ROE")
        self.assertEqual(roe_metric.category, "profitability")
        self.assertEqual(roe_metric.value, 14.72)

    @patch("apps.research.services.providers.upstox.UpstoxProvider._get")
    def test_null_empty_payload_handling(self, mock_get):
        mock_get.return_value = {"status": "success", "data": None}

        statements = self.provider.get_financials("LT", Market.INDIA)
        self.assertEqual(statements, [])

        metrics_res = self.provider.get_key_metrics("LT", Market.INDIA)
        self.assertEqual(metrics_res.metrics, [])

        profile = self.provider.get_company_profile("LT", Market.INDIA)
        self.assertEqual(profile.ticker, "LT")
        self.assertEqual(profile.isin, "INE018A01030")

    def test_resolve_isin(self):
        isin = self.provider._resolve_isin("LT", Market.INDIA)
        self.assertEqual(isin, "INE018A01030")
