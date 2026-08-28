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