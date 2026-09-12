from django.conf import settings

from apps.ai.mcp.server import mcp

from apps.ai.services.rag_tools import search_financial_documents as search_financial_documents_tool
from apps.ai.services.research_tools import (
    get_company_profile as get_company_profile_tool,
    get_market_data as get_market_data_tool,
    get_financials as get_financials_tool,
    get_key_metrics as get_key_metrics_tool,
    get_historical_data as get_historical_data_tool,
    get_news as get_news_tool,
)


def _resolve_trusted_mcp_user_id() -> str | int:
    """Resolve trusted tenant identity from configuration or context.

    Raises PermissionError if no trusted tenant context is configured.
    """
    configured_id = getattr(settings, "MCP_TENANT_USER_ID", None)
    if configured_id is not None and str(configured_id).strip():
        return str(configured_id).strip()
    raise PermissionError(
        "No trusted tenant context available for MCP document search. "
        "Tenant context must be established via authenticated session or configuration."
    )


@mcp.tool()
def get_company_profile(
    ticker: str,
    market: str,
) -> dict:
    """
    Get a company's profile and basic information.

    Args:
        ticker: Stock ticker symbol.
        market: Market code. Use IN for India or US for United States.
    """

    return get_company_profile_tool(
        ticker=ticker,
        market=market,
    )


@mcp.tool()
def get_market_data(
    ticker: str,
    market: str,
) -> dict:
    """
    Get current market data for a company.

    Args:
        ticker: Stock ticker symbol.
        market: Market code. Use IN for India or US for United States.
    """

    return get_market_data_tool(
        ticker=ticker,
        market=market,
    )


@mcp.tool()
def get_financials(
    ticker: str,
    market: str,
) -> dict:
    """
    Get financial statements for a company.

    Args:
        ticker: Stock ticker symbol.
        market: Market code. Currently supports IN.
    """

    return get_financials_tool(
        ticker=ticker,
        market=market,
    )


@mcp.tool()
def get_key_metrics(
    ticker: str,
    market: str,
) -> dict:
    """
    Get key financial metrics for a company.

    Args:
        ticker: Stock ticker symbol.
        market: Market code. Currently supports IN.
    """

    return get_key_metrics_tool(
        ticker=ticker,
        market=market,
    )


@mcp.tool()
def get_historical_data(
    ticker: str,
    to_date: str,
    from_date: str | None = None,
    market: str = "IN",
) -> dict:
    """
    Get historical daily market data for a company.

    Args:
        ticker: Stock ticker symbol.
        to_date: End date in YYYY-MM-DD format.
        from_date: Optional start date in YYYY-MM-DD format.
        market: Market code. Currently supports IN.
    """

    return get_historical_data_tool(
        ticker=ticker,
        to_date=to_date,
        from_date=from_date,
        market=market,
    )


@mcp.tool()
def get_news(
    ticker: str,
    market: str = "IN",
    limit: int = 10,
) -> dict:
    """
    Get recent news for a company.

    Args:
        ticker: Stock ticker symbol.
        market: Market code. Currently supports IN.
        limit: Maximum number of articles to return.
    """

    return get_news_tool(
        ticker=ticker,
        market=market,
        limit=limit,
    )


@mcp.tool()
def search_financial_documents(
    query: str,
    ticker: str | None = None,
    market: str | None = None,
    document_type: str | None = None,
    fiscal_year: int | None = None,
    top_k: int = 5,
    source_type: str | None = None,
    sec_form: str | None = None,
    sec_cik: str | None = None,
    sec_accession_number: str | None = None,
    document_id: str | None = None,
    filing_date_from: str | None = None,
    filing_date_to: str | None = None,
    report_date_from: str | None = None,
    report_date_to: str | None = None,
) -> dict:
    """
    Search indexed financial documents for the most relevant text chunks.

    Args:
        query: User search text.
        ticker: Optional ticker symbol filter.
        market: Optional market code filter.
        document_type: Optional document category filter.
        fiscal_year: Optional fiscal year filter.
        top_k: Maximum number of relevant chunks to return.
        source_type: Optional document source type ('UPLOAD' or 'SEC_EDGAR').
        sec_form: Optional SEC form type (e.g. '10-K', '10-Q', '8-K').
        sec_cik: Optional SEC CIK filter.
        sec_accession_number: Optional SEC accession number filter.
        document_id: Optional document UUID filter.
        filing_date_from: Optional filing date range start (YYYY-MM-DD).
        filing_date_to: Optional filing date range end (YYYY-MM-DD).
        report_date_from: Optional report period date range start (YYYY-MM-DD).
        report_date_to: Optional report period date range end (YYYY-MM-DD).
    """
    trusted_user_id = _resolve_trusted_mcp_user_id()

    return search_financial_documents_tool(
        query=query,
        ticker=ticker,
        market=market,
        document_type=document_type,
        fiscal_year=fiscal_year,
        top_k=top_k,
        user_id=trusted_user_id,
        source_type=source_type,
        sec_form=sec_form,
        sec_cik=sec_cik,
        sec_accession_number=sec_accession_number,
        document_id=document_id,
        filing_date_from=filing_date_from,
        filing_date_to=filing_date_to,
        report_date_from=report_date_from,
        report_date_to=report_date_to,
    )
