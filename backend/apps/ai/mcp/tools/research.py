from apps.ai.mcp.server import mcp

from apps.ai.services.research_tools import (
    get_company_profile as get_company_profile_tool,
    get_market_data as get_market_data_tool,
    get_financials as get_financials_tool,
    get_key_metrics as get_key_metrics_tool,
    get_historical_data as get_historical_data_tool,
    get_news as get_news_tool,
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