from unittest.mock import patch

from django.test import SimpleTestCase
from requests import RequestException

from apps.research.services.instrument_resolver import (
    UpstoxInstrumentResolver,
)


class UpstoxInstrumentResolverTestCase(SimpleTestCase):

    @patch(
        "apps.research.services.instrument_resolver.requests.get"
    )
    def test_resolve_nse_equity(self, mock_get):

        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "status": "success",
            "data": [
                {
                    "instrument_key": "NSE_EQ|INE002A01018",
                    "trading_symbol": "RELIANCE",
                    "segment": "NSE_EQ",
                    "instrument_type": "EQ",
                }
            ],
        }

        resolver = UpstoxInstrumentResolver()

        result = resolver.resolve_nse_equity(
            "RELIANCE"
        )

        self.assertEqual(
            result,
            "NSE_EQ|INE002A01018",
        )

        mock_get.assert_called_once()

    @patch(
        "apps.research.services.instrument_resolver.requests.get"
    )
    def test_resolve_unknown_symbol(self, mock_get):

        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "status": "success",
            "data": [],
        }

        resolver = UpstoxInstrumentResolver()

        with self.assertRaises(ValueError) as context:
            resolver.resolve_nse_equity(
                "UNKNOWN"
            )

        self.assertEqual(
            str(context.exception),
            "Unable to resolve NSE instrument for UNKNOWN.",
        )

    @patch(
        "apps.research.services.instrument_resolver.requests.get"
    )
    def test_api_failure(self, mock_get):

        mock_get.side_effect = RequestException(
            "Upstox unavailable"
        )

        resolver = UpstoxInstrumentResolver()

        with self.assertRaises(RequestException):
            resolver.resolve_nse_equity(
                "RELIANCE"
            )


class UpstoxBenchmarkResolutionTestCase(SimpleTestCase):
    """Focused tests for Upstox benchmark instrument-key resolution and provider URL generation."""

    def setUp(self):
        from apps.research.services.providers.upstox import UpstoxProvider
        self.provider = UpstoxProvider()

    def test_nifty_50_resolves_to_canonical_instrument_key(self):
        """A. Prove 'NIFTY 50' resolves exactly to 'NSE_INDEX|Nifty 50'."""
        key = self.provider._resolve_instrument_key("NIFTY 50")
        self.assertEqual(key, "NSE_INDEX|Nifty 50")
        self.assertNotEqual(key, "NSE_INDEX|NIFTY 50")

    def test_case_insensitive_user_alias_handling(self):
        """B. Prove case-insensitive user aliases ('nifty 50', 'NIFTY 50', 'NIFTY50', '^NSEI') resolve correctly."""
        aliases = ["nifty 50", "NIFTY 50", "NIFTY50", "nifty50", "^NSEI", "^nsei", "NIFTY", "nifty"]
        for alias in aliases:
            resolved = self.provider._resolve_instrument_key(alias)
            self.assertEqual(
                resolved,
                "NSE_INDEX|Nifty 50",
                f"Alias '{alias}' did not resolve to 'NSE_INDEX|Nifty 50', got '{resolved}'",
            )
            self.assertNotEqual(resolved, "NSE_INDEX|NIFTY 50")

    @patch("apps.research.services.providers.upstox.requests.get")
    def test_provider_receives_exact_canonical_instrument_key_not_uppercased(self, mock_get):
        """C. Prove the provider receives exact canonical instrument key and does NOT receive 'NSE_INDEX|NIFTY 50'."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "status": "success",
            "data": {
                "candles": [
                    ["2024-09-20T00:00:00+05:30", 25000.0, 25100.0, 24900.0, 25050.0, 100000, 0]
                ]
            },
        }

        # Test with canonical alias "NIFTY 50"
        self.provider.get_historical("NIFTY 50", to_date="2026-09-18", from_date="2024-09-20")
        call_url_1 = mock_get.call_args[0][0]
        self.assertIn("historical-candle/NSE_INDEX|Nifty 50/days/1/2026-09-18/2024-09-20", call_url_1)
        self.assertNotIn("NSE_INDEX|NIFTY 50", call_url_1)

        # Test with lowercase alias "nifty 50"
        mock_get.reset_mock()
        self.provider.get_historical("nifty 50", to_date="2026-09-18", from_date="2024-09-20")
        call_url_2 = mock_get.call_args[0][0]
        self.assertIn("historical-candle/NSE_INDEX|Nifty 50/days/1/2026-09-18/2024-09-20", call_url_2)
        self.assertNotIn("NSE_INDEX|NIFTY 50", call_url_2)

        # Test with complete Upstox instrument key "NSE_INDEX|Nifty 50"
        mock_get.reset_mock()
        self.provider.get_historical("NSE_INDEX|Nifty 50", to_date="2026-09-18", from_date="2024-09-20")
        call_url_3 = mock_get.call_args[0][0]
        self.assertIn("historical-candle/NSE_INDEX|Nifty 50/days/1/2026-09-18/2024-09-20", call_url_3)
        self.assertNotIn("NSE_INDEX|NIFTY 50", call_url_3)

    def test_existing_benchmark_mappings_continue_to_work(self):
        """D. Prove existing benchmark mappings continue to work."""
        expected_mappings = {
            "NIFTY 50": "NSE_INDEX|Nifty 50",
            "NIFTY50": "NSE_INDEX|Nifty 50",
            "nifty 50": "NSE_INDEX|Nifty 50",
            "NIFTY 500": "NSE_INDEX|Nifty 500",
            "nifty 500": "NSE_INDEX|Nifty 500",
            "NIFTY500": "NSE_INDEX|Nifty 500",
            "nifty500": "NSE_INDEX|Nifty 500",
            "BANKNIFTY": "NSE_INDEX|Nifty Bank",
            "banknifty": "NSE_INDEX|Nifty Bank",
            "NIFTY BANK": "NSE_INDEX|Nifty Bank",
            "nifty bank": "NSE_INDEX|Nifty Bank",
            "SENSEX": "BSE_INDEX|SENSEX",
            "sensex": "BSE_INDEX|SENSEX",
            "^BSESN": "BSE_INDEX|SENSEX",
            "^bsesn": "BSE_INDEX|SENSEX",
        }
        for alias, expected_key in expected_mappings.items():
            resolved = self.provider._resolve_instrument_key(alias)
            self.assertEqual(
                resolved,
                expected_key,
                f"Benchmark '{alias}' resolved to '{resolved}', expected '{expected_key}'",
            )