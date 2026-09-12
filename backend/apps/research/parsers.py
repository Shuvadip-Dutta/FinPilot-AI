"""Document parsers for extracting text and provenance from financial files."""

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO
import pypdf
from bs4 import BeautifulSoup, NavigableString


@dataclass
class PageInfo:
    page_number: int
    text: str
    char_start: int
    char_end: int


@dataclass
class ParsedDocument:
    text: str
    page_count: int
    pages: list[PageInfo] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _format_html_table(table_tag) -> str:
    """Convert an HTML <table> into structured, delimited rows preserving columns."""
    rows: list[str] = []
    for tr in table_tag.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        row_values: list[str] = []
        for cell in cells:
            # Flatten cell contents and normalize internal whitespace
            cell_text = " ".join(cell.get_text(" ", strip=True).split())
            row_values.append(cell_text)

        # Only retain row if it contains at least one non-empty cell
        if any(row_values):
            rows.append(" | ".join(row_values))

    if not rows:
        return ""
    return "\n".join(rows)


def extract_text_from_html(source: str | Path | BinaryIO | bytes) -> ParsedDocument:
    """Extract clean, structured text from an SEC HTML / XHTML document with table preservation."""
    raw_html = ""
    if isinstance(source, (str, Path)):
        # Check if source is a file path on disk
        source_str = str(source)
        # Only treat as path if it looks like a path and doesn't look like raw HTML content
        is_html_content = "<html" in source_str.lower() or "<body" in source_str.lower() or "<table" in source_str.lower() or "<p" in source_str.lower()
        if not is_html_content and Path(source_str).is_file():
            with open(source_str, "rb") as f:
                raw_bytes = f.read()
            try:
                raw_html = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raw_html = raw_bytes.decode("latin-1", errors="replace")
        else:
            raw_html = source_str
    elif isinstance(source, bytes):
        try:
            raw_html = source.decode("utf-8")
        except UnicodeDecodeError:
            raw_html = source.decode("latin-1", errors="replace")
    else:
        read_data = source.read()
        if isinstance(read_data, bytes):
            try:
                raw_html = read_data.decode("utf-8")
            except UnicodeDecodeError:
                raw_html = read_data.decode("latin-1", errors="replace")
        else:
            raw_html = str(read_data)

    if not raw_html or not raw_html.strip():
        raise ValueError("HTML file contains no readable text or is empty.")

    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove dangerous and non-content tags
    for tag_name in [
        "script",
        "style",
        "head",
        "noscript",
        "meta",
        "link",
        "title",
        "svg",
        "iframe",
        "object",
        "embed",
        "applet",
    ]:
        for element in soup.find_all(tag_name):
            element.decompose()

    # Convert tables into structured text before general extraction to avoid duplication
    for table in soup.find_all("table"):
        table_text = _format_html_table(table)
        if table_text:
            table.replace_with(NavigableString(f"\n\n{table_text}\n\n"))
        else:
            table.decompose()

    # Extract text with newline separator for block structure
    extracted_text = soup.get_text("\n")

    # Clean up and normalize whitespace
    lines = [line.strip() for line in extracted_text.splitlines()]
    cleaned_lines: list[str] = []
    empty_streak = 0
    for line in lines:
        if line:
            # Normalize internal tabs / multiple spaces
            norm_line = re.sub(r"[ \t]+", " ", line)
            cleaned_lines.append(norm_line)
            empty_streak = 0
        else:
            if empty_streak == 0:
                cleaned_lines.append("")
            empty_streak += 1

    full_text = "\n".join(cleaned_lines).strip()

    # Fallback if meaningful text is extremely small (< 100 characters) or empty due to unparseable tags
    if len(full_text) < 100:
        # Strip dangerous blocks from raw HTML before fallback text extraction
        sanitized_raw = re.sub(
            r"<(script|style|head|noscript|svg|iframe|object|embed|applet)[^>]*>.*?</\1>",
            " ",
            raw_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        stripped = re.sub(r"<[^>]+>", " ", sanitized_raw)
        fallback_text = re.sub(r"\s+", " ", stripped).strip()
        if not full_text and fallback_text:
            full_text = fallback_text

    if not full_text:
        raise ValueError("HTML file contains no readable text or is empty.")

    return ParsedDocument(
        text=full_text,
        page_count=1,
        pages=[
            PageInfo(
                page_number=1,
                text=full_text,
                char_start=0,
                char_end=len(full_text),
            )
        ],
        metadata={"page_count": 1, "format": "html"},
    )


def extract_text_from_pdf(source: str | Path | BinaryIO | bytes) -> ParsedDocument:
    """Extract text page-by-page from a PDF file preserving page provenance."""
    if isinstance(source, (str, Path)):
        reader = pypdf.PdfReader(str(source))
    elif isinstance(source, bytes):
        reader = pypdf.PdfReader(io.BytesIO(source))
    else:
        reader = pypdf.PdfReader(source)

    total_pages = len(reader.pages)
    if total_pages == 0:
        raise ValueError("PDF file contains no pages.")

    pages: list[PageInfo] = []
    combined_texts: list[str] = []
    current_offset = 0

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        page_text = page.extract_text() or ""
        clean_text = page_text.strip()
        
        char_start = current_offset
        char_end = current_offset + len(page_text)
        current_offset = char_end + 1  # accounting for joined newline

        pages.append(
            PageInfo(
                page_number=page_num,
                text=page_text,
                char_start=char_start,
                char_end=char_end,
            )
        )
        combined_texts.append(page_text)

    full_text = "\n".join(combined_texts).strip()
    if not full_text:
        raise ValueError("PDF contains no readable text.")

    return ParsedDocument(
        text=full_text,
        page_count=total_pages,
        pages=pages,
        metadata={"page_count": total_pages},
    )


def extract_text_from_txt(source: str | Path | BinaryIO | bytes) -> ParsedDocument:
    """Extract UTF-8 text from a plain text file or string."""
    text = ""
    if isinstance(source, (str, Path)):
        source_str = str(source)
        if isinstance(source, Path) or ("\n" not in source_str and Path(source_str).is_file()):
            with open(source_str, "rb") as f:
                raw_bytes = f.read()
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"File is not valid UTF-8 text: {exc}") from exc
        else:
            text = source_str
    elif isinstance(source, bytes):
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"File is not valid UTF-8 text: {exc}") from exc
    else:
        read_data = source.read()
        if isinstance(read_data, bytes):
            try:
                text = read_data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"File is not valid UTF-8 text: {exc}") from exc
        else:
            text = str(read_data)

    clean_text = text.strip()
    if not clean_text:
        raise ValueError("TXT file contains no readable text or is empty.")

    return ParsedDocument(
        text=text,
        page_count=1,
        pages=[
            PageInfo(
                page_number=1,
                text=text,
                char_start=0,
                char_end=len(text),
            )
        ],
        metadata={"page_count": 1},
    )


def parse_financial_document(
    source: str | Path | BinaryIO | bytes,
    content_type: str = "",
    filename: str = "",
) -> ParsedDocument:
    """Parse a document source by content type or file extension."""
    norm_content_type = (content_type or "").lower().strip()
    norm_filename = (filename or "").lower().strip()

    if norm_content_type == "application/pdf" or norm_filename.endswith(".pdf"):
        return extract_text_from_pdf(source)
    elif norm_content_type in ("text/html", "application/xhtml+xml") or norm_filename.endswith((".html", ".htm", ".xhtml")):
        return extract_text_from_html(source)
    elif norm_content_type in ("text/plain", "text/csv") or norm_filename.endswith((".txt", ".text", ".csv")):
        return extract_text_from_txt(source)
    else:
        raise ValueError(f"Unsupported document format: {content_type or filename}. Only PDF, HTML, and TXT files are supported.")


