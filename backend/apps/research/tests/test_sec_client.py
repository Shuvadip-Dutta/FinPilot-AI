"""Unit tests for SecEdgarClient and CIK resolution service."""

import unittest
from unittest.mock import MagicMock, patch
import requests

from apps.research.services.sec_service import (
    SecCompanyMetadata,
    SecEdgarClient,
    SecError,
    SecFilingMetadata,
    SecNetworkError,
    SecNotFoundError,
    SecRateLimitError,
    SecResponseError,
    SecSubmissionsResult,
)


class SecEdgarClientTestCase(unittest.TestCase):
    """Focused test suite for SecEdgarClient HTTP access, CIK resolution, and metadata parsing."""

    def setUp(self):
        self.mock_session = MagicMock(spec=requests.Session)
        self.client = SecEdgarClient(
            user_agent="FinPilot-AI-Test test-suite@finpilot.ai",
            timeout=5.0,
            max_retries=3,
            backoff_factor=0.01,  # Fast for unit tests
            session=self.mock_session,
        )

        # Mock sample company tickers directory response
        self.sample_tickers_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
            "2": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
            "3": {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
        }

        # Mock sample company submissions response
        self.sample_submissions_data = {
            "cik": "0000320193",
            "entityType": "operating",
            "sic": "3571",
            "sicDescription": "Electronic Computers",
            "name": "Apple Inc.",
            "tickers": ["AAPL"],
            "exchanges": ["Nasdaq"],
            "ein": "942404110",
            "filings": {
                "recent": {
                    "accessionNumber": [
                        "0000320193-24-000106",
                        "0000320193-24-000081",
                        "0000320193-24-000006",
                        "0000320193-24-000002",
                    ],
                    "filingDate": ["2024-11-01", "2024-08-02", "2024-05-03", "2024-02-02"],
                    "reportDate": ["2024-09-28", "2024-06-29", "2024-03-30", "2023-12-30"],
                    "acceptanceDateTime": [
                        "2024-11-01T18:02:44.000Z",
                        "2024-08-01T18:02:44.000Z",
                        "2024-05-02T18:02:44.000Z",
                        "2024-02-01T18:02:44.000Z",
                    ],
                    "act": ["34", "34", "34", "34"],
                    "form": ["10-K", "10-Q", "10-Q", "8-K"],
                    "fileNumber": ["001-36743", "001-36743", "001-36743", "001-36743"],
                    "filmNumber": ["241428765", "241165432", "24987654", "24123456"],
                    "items": ["", "", "", "5.02"],
                    "size": [15420100, 8420100, 7890100, 120500],
                    "isXBRL": [1, 1, 1, 0],
                    "isInlineXBRL": [1, 1, 1, 0],
                    "primaryDocument": [
                        "aapl-20240928.htm",
                        "aapl-20240629.htm",
                        "aapl-20240330.htm",
                        "aapl-20240201.htm",
                    ],
                    "primaryDocDescription": [
                        "10-K ANNUAL REPORT",
                        "10-Q QUARTERLY REPORT",
                        "10-Q QUARTERLY REPORT",
                        "CURRENT REPORT",
                    ],
                }
            },
        }

    def test_user_agent_header_present(self):
        """Test that every request sends the configured descriptive User-Agent."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.sample_tickers_data
        self.mock_session.get.return_value = mock_resp

        self.client.get_company_tickers_directory()

        self.mock_session.get.assert_called_once()
        _, kwargs = self.mock_session.get.call_args
        headers = kwargs.get("headers", {})
        self.assertIn("User-Agent", headers)
        self.assertEqual(headers["User-Agent"], "FinPilot-AI-Test test-suite@finpilot.ai")

    def test_resolve_cik_uppercase_and_padding(self):
        """Test resolving ticker to 10-digit zero-padded CIK."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.sample_tickers_data
        self.mock_session.get.return_value = mock_resp

        # Uppercase
        cik_aapl = self.client.resolve_cik("AAPL")
        self.assertEqual(cik_aapl, "0000320193")
        self.assertEqual(len(cik_aapl), 10)

        # Lowercase normalization
        cik_msft = self.client.resolve_cik("msft")
        self.assertEqual(cik_msft, "0000789019")
        self.assertEqual(len(cik_msft), 10)

        # Mixed-case & whitespace
        cik_nvda = self.client.resolve_cik("  nVdA  ")
        self.assertEqual(cik_nvda, "0001045810")
        self.assertEqual(len(cik_nvda), 10)

    def test_resolve_cik_unknown_ticker(self):
        """Test that an unknown ticker raises SecNotFoundError."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.sample_tickers_data
        self.mock_session.get.return_value = mock_resp

        with self.assertRaises(SecNotFoundError) as ctx:
            self.client.resolve_cik("NONEXISTENT_TICKER_XYZ")
        self.assertIn("Could not resolve SEC CIK", str(ctx.exception))

    def test_resolve_cik_invalid_input(self):
        """Test validation on empty or non-string ticker input."""
        with self.assertRaises(ValueError):
            self.client.resolve_cik("")
        with self.assertRaises(ValueError):
            self.client.resolve_cik(None)  # type: ignore

    def test_caching_tickers_directory(self):
        """Test that company_tickers.json is cached and not repeatedly requested."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.sample_tickers_data
        self.mock_session.get.return_value = mock_resp

        # 1st call executes HTTP request
        dir1 = self.client.get_company_tickers_directory()
        self.assertEqual(self.mock_session.get.call_count, 1)
        self.assertEqual(len(dir1), 4)

        # 2nd call uses in-memory cache without repeating HTTP call
        dir2 = self.client.get_company_tickers_directory()
        self.assertEqual(self.mock_session.get.call_count, 1)
        self.assertEqual(dir1, dir2)

    def test_submissions_metadata_parsing(self):
        """Test parsing company submissions JSON into typed SecSubmissionsResult and SecFilingMetadata."""
        mock_tickers_resp = MagicMock()
        mock_tickers_resp.status_code = 200
        mock_tickers_resp.json.return_value = self.sample_tickers_data

        mock_sub_resp = MagicMock()
        mock_sub_resp.status_code = 200
        mock_sub_resp.json.return_value = self.sample_submissions_data

        self.mock_session.get.side_effect = [mock_tickers_resp, mock_sub_resp]

        result = self.client.get_company_submissions("AAPL", limit=10)

        self.assertIsInstance(result, SecSubmissionsResult)
        self.assertEqual(result.cik, "0000320193")
        self.assertEqual(result.ticker, "AAPL")
        self.assertEqual(result.company_name, "Apple Inc.")
        self.assertEqual(len(result.filings), 4)

        # Check 10-K metadata item
        filing_10k = result.filings[0]
        self.assertIsInstance(filing_10k, SecFilingMetadata)
        self.assertEqual(filing_10k.accession_number, "0000320193-24-000106")
        self.assertEqual(filing_10k.form, "10-K")
        self.assertEqual(filing_10k.filing_date, "2024-11-01")
        self.assertEqual(filing_10k.report_date, "2024-09-28")
        self.assertEqual(filing_10k.primary_document, "aapl-20240928.htm")
        self.assertEqual(filing_10k.description, "10-K ANNUAL REPORT")
        self.assertEqual(
            filing_10k.document_url,
            "https://www.sec.gov/Archives/edgar/data/320193/000032019324000106/aapl-20240928.htm",
        )
        self.assertEqual(
            filing_10k.interactive_data_url,
            "https://www.sec.gov/ix?doc=/Archives/edgar/data/320193/000032019324000106/aapl-20240928.htm",
        )
        self.assertTrue(filing_10k.is_xbrl)
        self.assertEqual(filing_10k.size, 15420100)

    def test_submissions_form_filter(self):
        """Test filtering submissions by specific forms (e.g. only 10-K)."""
        mock_tickers_resp = MagicMock()
        mock_tickers_resp.status_code = 200
        mock_tickers_resp.json.return_value = self.sample_tickers_data

        mock_sub_resp = MagicMock()
        mock_sub_resp.status_code = 200
        mock_sub_resp.json.return_value = self.sample_submissions_data

        self.mock_session.get.side_effect = [mock_tickers_resp, mock_sub_resp]

        result_10k = self.client.get_company_submissions("AAPL", forms=["10-K"])
        self.assertEqual(len(result_10k.filings), 1)
        self.assertEqual(result_10k.filings[0].form, "10-K")

    def test_direct_cik_input_skips_ticker_lookup(self):
        """Test passing a numeric CIK directly avoids directory lookup."""
        mock_sub_resp = MagicMock()
        mock_sub_resp.status_code = 200
        mock_sub_resp.json.return_value = self.sample_submissions_data

        self.mock_session.get.return_value = mock_sub_resp

        result = self.client.get_company_submissions("0000320193")
        self.assertEqual(result.cik, "0000320193")
        self.assertEqual(self.mock_session.get.call_count, 1)

    def test_retry_on_429_rate_limit(self):
        """Test that HTTP 429 triggers bounded retry and eventually succeeds if resolved."""
        mock_429 = MagicMock()
        mock_429.status_code = 429

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = self.sample_tickers_data

        # 1st attempt 429, 2nd attempt 200 OK
        self.mock_session.get.side_effect = [mock_429, mock_200]

        data = self.client.get_company_tickers_directory()
        self.assertEqual(len(data), 4)
        self.assertEqual(self.mock_session.get.call_count, 2)

    def test_retry_on_5xx_server_error(self):
        """Test that 500/503 responses trigger retry up to max_retries."""
        mock_503 = MagicMock()
        mock_503.status_code = 503

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = self.sample_tickers_data

        # 1st and 2nd attempt 503, 3rd attempt 200 OK
        self.mock_session.get.side_effect = [mock_503, mock_503, mock_200]

        data = self.client.get_company_tickers_directory()
        self.assertEqual(len(data), 4)
        self.assertEqual(self.mock_session.get.call_count, 3)

    def test_rate_limit_exceeded_raises_sec_rate_limit_error(self):
        """Test that persistent 429 raises SecRateLimitError after max_retries."""
        mock_429 = MagicMock()
        mock_429.status_code = 429

        self.mock_session.get.return_value = mock_429

        with self.assertRaises(SecRateLimitError):
            self.client.get_company_tickers_directory()

        self.assertEqual(self.mock_session.get.call_count, 3)

    def test_timeout_triggers_retry_and_raises_sec_network_error(self):
        """Test that persistent timeouts raise SecNetworkError."""
        self.mock_session.get.side_effect = requests.Timeout("Connection timed out")

        with self.assertRaises(SecNetworkError):
            self.client.get_company_tickers_directory()

        self.assertEqual(self.mock_session.get.call_count, 3)

    def test_malformed_json_raises_sec_response_error(self):
        """Test that invalid JSON from SEC raises SecResponseError."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        self.mock_session.get.return_value = mock_resp

        with self.assertRaises(SecResponseError):
            self.client.get_company_tickers_directory()

    def test_403_forbidden_raises_sec_error(self):
        """Test that HTTP 403 (e.g. rejected User-Agent) raises SecError immediately."""
        mock_403 = MagicMock()
        mock_403.status_code = 403
        self.mock_session.get.return_value = mock_403

        with self.assertRaises(SecError) as ctx:
            self.client.get_company_tickers_directory()

        self.assertIn("User-Agent", str(ctx.exception))
        # 403 does not retry wastefully
        self.assertEqual(self.mock_session.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
