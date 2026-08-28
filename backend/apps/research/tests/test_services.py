from unittest.mock import patch

from django.test import SimpleTestCase

from apps.research.services.research_service import ResearchService
from apps.research.services.schemas import (
    HistoricalCandle,
    HistoricalMarketData,
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