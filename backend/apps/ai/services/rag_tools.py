"""RAG-backed document retrieval tools for MCP and agent orchestration."""

from apps.ai.rag.factory import build_rag_pipeline


def _build_metadata_filters(
    ticker: str | None = None,
    market: str | None = None,
    document_type: str | None = None,
    fiscal_year: int | None = None,
) -> dict[str, object]:
    filters: dict[str, object] = {}

    if ticker is not None:
        cleaned_ticker = str(ticker).strip()
        if cleaned_ticker:
            filters["ticker"] = cleaned_ticker.upper()

    if market is not None:
        cleaned_market = str(market).strip()
        if cleaned_market:
            filters["market"] = cleaned_market.upper()

    if document_type is not None:
        cleaned_document_type = str(document_type).strip()
        if cleaned_document_type:
            filters["document_type"] = cleaned_document_type.lower()

    if fiscal_year is not None:
        if isinstance(fiscal_year, bool):
            raise ValueError("fiscal_year must be an integer or null.")
        if not isinstance(fiscal_year, int):
            raise TypeError("fiscal_year must be an integer or null.")
        filters["fiscal_year"] = fiscal_year

    return filters


def _serialize_results(results: list) -> list[dict[str, object]]:
    return [
        {
            "text": item.chunk.text,
            "score": float(item.score),
            "document_id": item.chunk.document_id,
            "chunk_id": item.chunk.chunk_id,
            "metadata": item.chunk.metadata,
        }
        for item in results
    ]


def search_financial_documents(
    query: str,
    ticker: str | None = None,
    market: str | None = None,
    document_type: str | None = None,
    fiscal_year: int | None = None,
    top_k: int = 5,
) -> dict[str, object]:
    """Search the vectorized financial document corpus using the existing RAG pipeline."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must not be empty.")

    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise TypeError("top_k must be an integer.")

    if top_k < 1 or top_k > 10:
        raise ValueError("top_k must be between 1 and 10.")

    pipeline = build_rag_pipeline()
    filters = _build_metadata_filters(
        ticker=ticker,
        market=market,
        document_type=document_type,
        fiscal_year=fiscal_year,
    )

    results = pipeline.retrieve(
        query=query.strip(),
        top_k=top_k,
        filters=filters or None,
    )

    return {
        "documents": _serialize_results(results),
    }
