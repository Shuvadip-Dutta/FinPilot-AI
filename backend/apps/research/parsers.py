"""Document parsers for extracting text and provenance from financial files."""

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO
import pypdf


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
    """Extract UTF-8 text from a plain text file."""
    if isinstance(source, (str, Path)):
        with open(source, "rb") as f:
            raw_bytes = f.read()
    elif isinstance(source, bytes):
        raw_bytes = source
    else:
        raw_bytes = source.read()

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"File is not valid UTF-8 text: {exc}") from exc

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
    elif norm_content_type in ("text/plain", "text/csv") or norm_filename.endswith((".txt", ".text")):
        return extract_text_from_txt(source)
    else:
        raise ValueError(f"Unsupported document format: {content_type or filename}. Only PDF and TXT files are supported.")
