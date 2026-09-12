import datetime
import uuid

from apps.ai.rag.factory import build_rag_pipeline


def _normalize_sec_form(form: str) -> str:
    """Normalize SEC form variations into standard representations."""
    cleaned = form.strip().upper()
    if cleaned.startswith("FORM "):
        cleaned = cleaned[5:].strip()
    if cleaned == "10K":
        return "10-K"
    if cleaned == "10Q":
        return "10-Q"
    if cleaned == "8K":
        return "8-K"
    return cleaned


def _validate_iso_date(date_val: str | datetime.date, field_name: str) -> str:
    """Validate and format an ISO date string."""
    if isinstance(date_val, datetime.date):
        return date_val.isoformat()
    cleaned = str(date_val).strip()
    if not cleaned:
        return ""
    try:
        parsed = datetime.date.fromisoformat(cleaned)
        return parsed.isoformat()
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{field_name} must be a valid ISO date in YYYY-MM-DD format.") from exc


def _validate_uuid(val: str | uuid.UUID, field_name: str) -> str:
    """Validate a UUID string or instance."""
    if isinstance(val, uuid.UUID):
        return str(val)
    cleaned = str(val).strip()
    if not cleaned:
        return ""
    try:
        return str(uuid.UUID(cleaned))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be a valid UUID.") from exc


def _build_metadata_filters(
    ticker: str | None = None,
    market: str | None = None,
    document_type: str | None = None,
    fiscal_year: int | None = None,
    user_id: str | int | None = None,
    source_type: str | None = None,
    sec_form: str | None = None,
    sec_cik: str | None = None,
    sec_accession_number: str | None = None,
    document_id: str | uuid.UUID | None = None,
    filing_date_from: str | datetime.date | None = None,
    filing_date_to: str | datetime.date | None = None,
    report_date_from: str | datetime.date | None = None,
    report_date_to: str | datetime.date | None = None,
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

    if user_id is not None:
        cleaned_user_id = str(user_id).strip()
        if cleaned_user_id:
            filters["user_id"] = cleaned_user_id

    if source_type is not None:
        cleaned_source = str(source_type).strip().upper()
        if cleaned_source:
            filters["source_type"] = cleaned_source

    if sec_form is not None:
        cleaned_form = str(sec_form).strip()
        if cleaned_form:
            filters["sec_form"] = _normalize_sec_form(cleaned_form)

    if sec_cik is not None:
        cleaned_cik = str(sec_cik).strip()
        if cleaned_cik:
            if cleaned_cik.isdigit() and len(cleaned_cik) < 10:
                cleaned_cik = cleaned_cik.zfill(10)
            filters["sec_cik"] = cleaned_cik

    if sec_accession_number is not None:
        cleaned_acc = str(sec_accession_number).strip()
        if cleaned_acc:
            filters["sec_accession_number"] = cleaned_acc

    if document_id is not None:
        valid_doc_id = _validate_uuid(document_id, "document_id")
        if valid_doc_id:
            filters["document_id"] = valid_doc_id

    # Validate filing dates
    parsed_filing_from = _validate_iso_date(filing_date_from, "filing_date_from") if filing_date_from else None
    parsed_filing_to = _validate_iso_date(filing_date_to, "filing_date_to") if filing_date_to else None

    if parsed_filing_from and parsed_filing_to and parsed_filing_from > parsed_filing_to:
        raise ValueError("filing_date_from must be before or equal to filing_date_to.")

    if parsed_filing_from:
        filters["filing_date_from"] = parsed_filing_from
    if parsed_filing_to:
        filters["filing_date_to"] = parsed_filing_to

    # Validate report dates
    parsed_report_from = _validate_iso_date(report_date_from, "report_date_from") if report_date_from else None
    parsed_report_to = _validate_iso_date(report_date_to, "report_date_to") if report_date_to else None

    if parsed_report_from and parsed_report_to and parsed_report_from > parsed_report_to:
        raise ValueError("report_date_from must be before or equal to report_date_to.")

    if parsed_report_from:
        filters["report_date_from"] = parsed_report_from
    if parsed_report_to:
        filters["report_date_to"] = parsed_report_to

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
    user_id: str | int | None = None,
    source_type: str | None = None,
    sec_form: str | None = None,
    sec_cik: str | None = None,
    sec_accession_number: str | None = None,
    document_id: str | uuid.UUID | None = None,
    filing_date_from: str | datetime.date | None = None,
    filing_date_to: str | datetime.date | None = None,
    report_date_from: str | datetime.date | None = None,
    report_date_to: str | datetime.date | None = None,
) -> dict[str, object]:
    """Search the vectorized financial document corpus using the existing RAG pipeline."""

    if user_id is None or not str(user_id).strip():
        raise ValueError("user_id is required for document search.")

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
        user_id=user_id,
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

    results = pipeline.retrieve(
        query=query.strip(),
        top_k=top_k,
        filters=filters or None,
    )

    return {
        "documents": _serialize_results(results),
    }

