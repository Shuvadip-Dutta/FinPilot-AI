import requests

from django.conf import settings


class UpstoxInstrumentResolver:

    BASE_URL = "https://api.upstox.com/v2"

    def __init__(self):
        self.access_token = (
            settings.UPSTOX_ANALYTICS_ACCESS_TOKEN
        )

    def resolve_nse_equity(
        self,
        ticker: str,
    ) -> str:

        response = requests.get(
            f"{self.BASE_URL}/instruments/search",
            headers={
                "Accept": "application/json",
                "Authorization": (
                    f"Bearer {self.access_token}"
                ),
            },
            params={
                "query": ticker.upper(),
                "exchanges": "NSE",
                "segments": "EQ",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        instruments = data.get("data") or []

        for instrument in instruments:
            if (
                instrument.get("segment") == "NSE_EQ"
                and instrument.get("instrument_type") == "EQ"
                and instrument.get("trading_symbol", "").upper()
                == ticker.upper()
            ):
                return instrument["instrument_key"]

        raise ValueError(
            f"Unable to resolve NSE instrument for {ticker.upper()}."
        )