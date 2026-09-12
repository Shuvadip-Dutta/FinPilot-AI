"""SEC EDGAR Client and CIK Resolution Service for US regulatory disclosures.

Provides bounded HTTP access to SEC EDGAR company tickers directory and company submissions endpoints.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
import requests
from django.conf import settings

logger = logging.getLogger("finpilot")


class SecError(Exception):
    """Base exception for SEC EDGAR operations."""


class SecNotFoundError(SecError):
    """Raised when a company, ticker, or filing cannot be resolved on SEC EDGAR."""


class SecRateLimitError(SecError):
    """Raised when SEC EDGAR HTTP 429 rate limit is exceeded after retries."""


class SecNetworkError(SecError):
    """Raised when a network timeout or connection error occurs communicating with SEC."""


class SecResponseError(SecError):
    """Raised when SEC EDGAR returns an invalid, malformed, or unparseable response."""


@dataclass
class SecCompanyMetadata:
    """Canonical SEC identity metadata for a registered entity."""

    cik: str  # 10-digit zero-padded string, e.g. "0000320193"
    ticker: str
    company_name: str
    sic: str | None = None
    sic_description: str | None = None
    fiscal_year_end: str | None = None
    state_of_incorporation: str | None = None


@dataclass
class SecFilingMetadata:
    """Metadata for an individual regulatory filing submission."""

    accession_number: str
    form: str  # e.g. "10-K", "10-Q", "8-K"
    filing_date: str  # ISO date string "YYYY-MM-DD"
    report_date: str | None  # ISO date string "YYYY-MM-DD" or None
    primary_document: str  # e.g. "aapl-20240928.htm"
    description: str | None
    document_url: str
    interactive_data_url: str
    size: int | None = None
    is_xbrl: bool = False


@dataclass
class SecSubmissionsResult:
    """Aggregated filings result for an SEC-registered company."""

    cik: str
    ticker: str
    company_name: str
    filings: list[SecFilingMetadata] = field(default_factory=list)


def _get_default_user_agent() -> str:
    try:
        from django.conf import settings
        if settings.configured:
            return getattr(
                settings,
                "SEC_EDGAR_USER_AGENT",
                "FinPilot-AI research-admin@finpilot.ai",
            )
    except Exception:
        pass
    return "FinPilot-AI research-admin@finpilot.ai"


class SecEdgarClient:
    """Client for SEC EDGAR public APIs with compliant User-Agent, retries, and caching."""

    DATA_BASE_URL = "https://data.sec.gov"
    WWW_BASE_URL = "https://www.sec.gov"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
    COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

    # Default TTL: 24 hours (in seconds)
    CACHE_TTL_SECONDS = 86400

    def __init__(
        self,
        user_agent: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        session: requests.Session | None = None,
    ):
        self.user_agent = user_agent or _get_default_user_agent()
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = session or requests.Session()

        # In-memory cache structures: { key: (data, expiry_timestamp) }
        self._cache: dict[str, tuple[Any, float]] = {}

    def _get_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov" if "data.sec.gov" in self.DATA_BASE_URL else "www.sec.gov",
            "Accept": "application/json, text/plain, */*",
        }

    def _cached_get(self, cache_key: str) -> Any | None:
        """Retrieve unexpired value from memory cache."""
        if cache_key in self._cache:
            data, expiry = self._cache[cache_key]
            if time.time() < expiry:
                return data
            del self._cache[cache_key]
        return None

    def _cached_set(self, cache_key: str, data: Any, ttl: float = CACHE_TTL_SECONDS) -> None:
        """Store value in memory cache with expiry."""
        self._cache[cache_key] = (data, time.time() + ttl)

    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def _request(self, url: str) -> dict[str, Any]:
        """Execute HTTP GET with compliant headers, bounded exponential retry, and typed error handling."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/plain, */*",
        }

        last_status_code = None
        last_error_msg = ""

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                )
                last_status_code = response.status_code

                if response.status_code == 200:
                    try:
                        return response.json()
                    except Exception as json_err:
                        raise SecResponseError(
                            f"Failed to parse JSON response from SEC EDGAR ({url}): {json_err}"
                        ) from json_err

                elif response.status_code == 404:
                    raise SecNotFoundError(f"SEC EDGAR resource not found: {url}")

                elif response.status_code == 403:
                    raise SecError(
                        "SEC EDGAR returned 403 Forbidden. Ensure a valid and descriptive User-Agent is configured."
                    )

                elif response.status_code == 429:
                    last_error_msg = "SEC rate limit exceeded (HTTP 429)."
                    logger.warning("SEC EDGAR 429 rate limit hit on %s (attempt %d/%d)", url, attempt, self.max_retries)

                elif response.status_code >= 500:
                    last_error_msg = f"SEC server error (HTTP {response.status_code})."
                    logger.warning("SEC EDGAR 5xx server error (%d) on %s (attempt %d/%d)", response.status_code, url, attempt, self.max_retries)

                else:
                    raise SecResponseError(f"Unexpected HTTP {response.status_code} from SEC EDGAR: {response.text[:200]}")

            except requests.Timeout as exc:
                last_error_msg = f"Timeout connecting to SEC EDGAR ({self.timeout}s)."
                logger.warning("SEC request timeout on %s (attempt %d/%d): %s", url, attempt, self.max_retries, exc)
            except requests.ConnectionError as exc:
                last_error_msg = f"Connection error connecting to SEC EDGAR: {exc}"
                logger.warning("SEC connection error on %s (attempt %d/%d): %s", url, attempt, self.max_retries, exc)

            if attempt < self.max_retries:
                sleep_duration = self.backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_duration)

        if last_status_code == 429:
            raise SecRateLimitError(
                f"SEC EDGAR request failed after {self.max_retries} attempts: {last_error_msg}"
            )

        raise SecNetworkError(
            f"SEC EDGAR request failed after {self.max_retries} attempts: {last_error_msg}"
        )

    def download_filing_content(self, url: str) -> bytes:
        """Download raw filing document (HTML/text/XML) from SEC Archives with compliant User-Agent and retries."""
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string.")

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
        }

        last_status_code = None
        last_error_msg = ""

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                )
                last_status_code = response.status_code

                if response.status_code == 200:
                    content = response.content
                    if not content or not content.strip():
                        raise SecResponseError(f"SEC filing document at {url} is empty.")
                    return content

                if response.status_code == 404:
                    raise SecNotFoundError(f"SEC EDGAR filing document not found: {url}")

                if response.status_code == 403:
                    raise SecError(
                        "SEC EDGAR returned 403 Forbidden. Ensure a valid and descriptive User-Agent is configured."
                    )

                if response.status_code == 429:
                    last_error_msg = "SEC rate limit exceeded (HTTP 429)."
                    logger.warning(
                        "SEC EDGAR 429 rate limit hit on %s (attempt %d/%d)",
                        url,
                        attempt,
                        self.max_retries,
                    )

                elif response.status_code >= 500:
                    last_error_msg = f"SEC server error (HTTP {response.status_code})."
                    logger.warning(
                        "SEC EDGAR 5xx server error (%d) on %s (attempt %d/%d)",
                        response.status_code,
                        url,
                        attempt,
                        self.max_retries,
                    )

                else:
                    raise SecResponseError(
                        f"Unexpected HTTP {response.status_code} from SEC EDGAR: {response.text[:200]}"
                    )

            except requests.Timeout as exc:
                last_error_msg = f"Timeout connecting to SEC EDGAR ({self.timeout}s)."
                logger.warning(
                    "SEC request timeout on %s (attempt %d/%d): %s",
                    url,
                    attempt,
                    self.max_retries,
                    exc,
                )
            except requests.ConnectionError as exc:
                last_error_msg = f"Connection error connecting to SEC EDGAR: {exc}"
                logger.warning(
                    "SEC connection error on %s (attempt %d/%d): %s",
                    url,
                    attempt,
                    self.max_retries,
                    exc,
                )

            if attempt < self.max_retries:
                sleep_duration = self.backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_duration)

        if last_status_code == 429:
            raise SecRateLimitError(
                f"SEC EDGAR document download failed after {self.max_retries} attempts: {last_error_msg}"
            )

        raise SecNetworkError(
            f"SEC EDGAR document download failed after {self.max_retries} attempts: {last_error_msg}"
        )

    def get_company_tickers_directory(self) -> dict[str, dict[str, Any]]:
        """Fetch and cache the full SEC company ticker directory mapping uppercase ticker to metadata."""
        cache_key = "sec:company_tickers_directory"
        cached = self._cached_get(cache_key)
        if cached is not None:
            return cached

        raw_data = self._request(self.COMPANY_TICKERS_URL)
        if not isinstance(raw_data, dict):
            raise SecResponseError("SEC company_tickers.json response is not a valid dictionary.")

        normalized_map: dict[str, dict[str, Any]] = {}
        for entry in raw_data.values():
            if isinstance(entry, dict) and "ticker" in entry and "cik_str" in entry:
                ticker_upper = str(entry["ticker"]).strip().upper()
                cik_int = entry["cik_str"]
                title = entry.get("title", "")
                normalized_map[ticker_upper] = {
                    "ticker": ticker_upper,
                    "cik_int": cik_int,
                    "cik_padded": str(cik_int).zfill(10),
                    "title": title,
                }

        self._cached_set(cache_key, normalized_map, ttl=self.CACHE_TTL_SECONDS)
        return normalized_map

    def resolve_cik(self, ticker: str) -> str:
        """Resolve a US stock ticker to a 10-digit zero-padded SEC CIK string.

        Example:
            'AAPL' -> '0000320193'
            'msft' -> '0000789019'
        """
        if not ticker or not isinstance(ticker, str):
            raise ValueError("Ticker must be a non-empty string.")

        clean_ticker = ticker.strip().upper()

        # 1. Attempt lookup in local Company database model if available
        try:
            from apps.research.models import Company

            company = Company.objects.filter(ticker__iexact=clean_ticker).first()
            if company and company.sec_cik:
                clean_cik = str(company.sec_cik).strip()
                if clean_cik:
                    return clean_cik.zfill(10)
        except Exception:
            # Fallback to SEC directory if database lookup fails
            pass

        # 2. Lookup in SEC company tickers directory
        directory = self.get_company_tickers_directory()
        if clean_ticker in directory:
            return directory[clean_ticker]["cik_padded"]

        raise SecNotFoundError(f"Could not resolve SEC CIK for ticker '{clean_ticker}'.")

    def get_company_submissions(
        self,
        cik_or_ticker: str,
        forms: list[str] | tuple[str, ...] | None = None,
        limit: int = 20,
    ) -> SecSubmissionsResult:
        """Retrieve company submission metadata and filings from SEC EDGAR.

        Args:
            cik_or_ticker: 10-digit CIK or stock ticker symbol.
            forms: Optional filter list of filing forms (e.g. ['10-K', '10-Q', '8-K']).
            limit: Maximum number of filing items to return.

        Returns:
            SecSubmissionsResult containing company metadata and parsed SecFilingMetadata list.
        """
        if not cik_or_ticker or not isinstance(cik_or_ticker, str):
            raise ValueError("cik_or_ticker must be a non-empty string.")

        clean_input = cik_or_ticker.strip()

        # Determine if input is a 10-digit CIK or ticker
        if clean_input.isdigit():
            cik_padded = clean_input.zfill(10)
            ticker_hint = ""
        else:
            ticker_hint = clean_input.upper()
            cik_padded = self.resolve_cik(ticker_hint)

        cache_key = f"sec:submissions:{cik_padded}"
        raw_json = self._cached_get(cache_key)

        if raw_json is None:
            url = f"{self.DATA_BASE_URL}/submissions/CIK{cik_padded}.json"
            raw_json = self._request(url)
            self._cached_set(cache_key, raw_json, ttl=self.CACHE_TTL_SECONDS)

        if not isinstance(raw_json, dict):
            raise SecResponseError(f"SEC submissions response for CIK {cik_padded} is not a valid dictionary.")

        cik_str = str(raw_json.get("cik") or cik_padded).zfill(10)
        company_name = str(raw_json.get("name") or "").strip()
        tickers_list = raw_json.get("tickers") or []
        resolved_ticker = (
            tickers_list[0].upper()
            if tickers_list
            else (ticker_hint or clean_input.upper())
        )

        filings_dict = raw_json.get("filings") or {}
        recent = filings_dict.get("recent") or {}

        # Columns in recent submissions
        accession_numbers = recent.get("accessionNumber") or []
        filing_dates = recent.get("filingDate") or []
        report_dates = recent.get("reportDate") or []
        forms_list = recent.get("form") or []
        primary_documents = recent.get("primaryDocument") or []
        primary_descriptions = recent.get("primaryDocDescription") or []
        sizes = recent.get("size") or []
        is_xbrl_list = recent.get("isXBRL") or []

        num_entries = len(accession_numbers)
        parsed_filings: list[SecFilingMetadata] = []

        cik_no_zeros = str(int(cik_str))

        filter_forms_upper = {f.upper().strip() for f in forms} if forms else None

        for idx in range(num_entries):
            form_val = str(forms_list[idx] if idx < len(forms_list) else "").strip()

            if filter_forms_upper and form_val.upper() not in filter_forms_upper:
                continue

            acc_num = str(accession_numbers[idx] if idx < len(accession_numbers) else "").strip()
            f_date = str(filing_dates[idx] if idx < len(filing_dates) else "").strip()
            r_date = str(report_dates[idx] if idx < len(report_dates) else "").strip() or None
            prim_doc = str(primary_documents[idx] if idx < len(primary_documents) else "").strip()
            desc = str(primary_descriptions[idx] if idx < len(primary_descriptions) else "").strip() or None
            size_val = sizes[idx] if idx < len(sizes) and isinstance(sizes[idx], int) else None
            is_xbrl = bool(is_xbrl_list[idx]) if idx < len(is_xbrl_list) else False

            acc_no_hyphens = acc_num.replace("-", "")

            # Canonical SEC Archives URL
            document_url = f"{self.ARCHIVES_URL}/{cik_no_zeros}/{acc_no_hyphens}/{prim_doc}"

            # Interactive data viewer URL for modern browsers
            interactive_url = f"https://www.sec.gov/ix?doc=/Archives/edgar/data/{cik_no_zeros}/{acc_no_hyphens}/{prim_doc}"

            parsed_filings.append(
                SecFilingMetadata(
                    accession_number=acc_num,
                    form=form_val,
                    filing_date=f_date,
                    report_date=r_date,
                    primary_document=prim_doc,
                    description=desc,
                    document_url=document_url,
                    interactive_data_url=interactive_url,
                    size=size_val,
                    is_xbrl=is_xbrl,
                )
            )

            if len(parsed_filings) >= limit:
                break

        return SecSubmissionsResult(
            cik=cik_str,
            ticker=resolved_ticker,
            company_name=company_name,
            filings=parsed_filings,
        )


# Global singleton instance for easy import across research apps
default_sec_client = SecEdgarClient()
