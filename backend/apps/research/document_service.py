"""Document ingestion and lifecycle service for financial documents."""

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.ai.rag.factory import build_rag_pipeline
from apps.research.models import FinancialDocument
from apps.research.parsers import parse_financial_document

logger = logging.getLogger("finpilot")

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/csv": ".txt",
}
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".text"}


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and invalid characters."""
    base_name = os.path.basename(filename).strip()
    clean_name = re.sub(r"[^\w\-.]", "_", base_name)
    clean_name = re.sub(r"_+", "_", clean_name)
    if not clean_name or clean_name in (".", ".."):
        clean_name = f"document_{uuid.uuid4().hex[:8]}.txt"
    return clean_name


class DocumentIngestionService:
    """Handles end-to-end ingestion, validation, vectorization, and deletion of user documents."""

    @staticmethod
    def validate_file(file: UploadedFile) -> tuple[str, str]:
        """Validate uploaded file size, content-type, and extension."""
        if not file or file.size == 0:
            raise ValueError("Uploaded file is empty.")

        if file.size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File exceeds maximum allowed size of 10 MB (size: {file.size} bytes).")

        raw_filename = file.name or "document"
        clean_name = sanitize_filename(raw_filename)
        ext = Path(clean_name).suffix.lower()

        content_type = (getattr(file, "content_type", None) or "").lower()

        if ext not in ALLOWED_EXTENSIONS and content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"Unsupported file format '{ext or content_type}'. Only PDF and TXT files are supported.")

        if not content_type or content_type == "application/octet-stream":
            if ext == ".pdf":
                content_type = "application/pdf"
            else:
                content_type = "text/plain"

        return clean_name, content_type

    @classmethod
    def ingest_document(
        cls,
        user: Any,
        file: UploadedFile,
        ticker: str | None = None,
        market: str | None = None,
    ) -> FinancialDocument:
        """Ingest, store, parse, and vectorize a user document."""
        clean_filename, content_type = cls.validate_file(file)

        doc_id = uuid.uuid4()
        clean_ticker = str(ticker).strip().upper() if ticker else None
        clean_market = str(market).strip().upper() if market else None

        # Build local storage path under MEDIA_ROOT
        media_root = Path(settings.MEDIA_ROOT)
        user_doc_dir = media_root / "documents" / str(user.id)
        user_doc_dir.mkdir(parents=True, exist_ok=True)

        target_file_path = user_doc_dir / f"{doc_id}_{clean_filename}"

        # Write uploaded file safely
        try:
            with open(target_file_path, "wb+") as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
        except Exception as exc:
            logger.error("Failed to write document file to disk: %s", exc)
            raise IOError(f"Could not save document to disk: {exc}") from exc

        # Create initial PostgreSQL record
        doc = FinancialDocument.objects.create(
            id=doc_id,
            user=user,
            filename=clean_filename,
            content_type=content_type,
            file_size=file.size,
            file_path=str(target_file_path),
            ticker=clean_ticker,
            market=clean_market,
            ingestion_status=FinancialDocument.STATUS_PROCESSING,
            chunk_count=0,
            ingestion_error=None,
        )

        try:
            # Parse text
            parsed_doc = parse_financial_document(
                source=target_file_path,
                content_type=content_type,
                filename=clean_filename,
            )

            # Build metadata for Qdrant chunks
            doc_type = "pdf" if clean_filename.lower().endswith(".pdf") else "txt"
            chunk_metadata: dict[str, Any] = {
                "user_id": str(user.id),
                "document_id": str(doc.id),
                "filename": doc.filename,
                "document_name": doc.filename,
                "document_type": doc_type,
                "ticker": doc.ticker or "",
                "market": doc.market or "",
                "page_start": 1,
                "page_count": parsed_doc.page_count,
            }

            # Ingest through RAGPipeline
            pipeline = build_rag_pipeline()
            chunks = pipeline.ingest(
                document_id=str(doc.id),
                text=parsed_doc.text,
                metadata=chunk_metadata,
            )

            doc.ingestion_status = FinancialDocument.STATUS_COMPLETED
            doc.chunk_count = len(chunks)
            doc.ingestion_error = None
            doc.save(update_fields=["ingestion_status", "chunk_count", "ingestion_error"])
            logger.info("Successfully ingested document %s (%d chunks)", doc.id, len(chunks))
            return doc

        except Exception as exc:
            logger.exception("Ingestion failed for document %s: %s", doc.id, exc)
            doc.ingestion_status = FinancialDocument.STATUS_FAILED
            doc.ingestion_error = str(exc)
            doc.save(update_fields=["ingestion_status", "ingestion_error"])
            raise

    @classmethod
    def delete_document(cls, user: Any, document_id: uuid.UUID | str) -> bool:
        """Delete document from vector store, disk, and database with strict ownership check."""
        try:
            doc = FinancialDocument.objects.get(id=document_id, user=user)
        except FinancialDocument.DoesNotExist:
            return False

        # 1. Delete chunks from Vector Store
        try:
            pipeline = build_rag_pipeline()
            pipeline.delete_document(document_id=str(doc.id), user_id=str(user.id))
        except Exception as exc:
            logger.warning("Failed to delete vector chunks for document %s: %s", doc.id, exc)

        # 2. Delete source file from filesystem
        try:
            if doc.file_path and os.path.exists(doc.file_path):
                os.remove(doc.file_path)
        except Exception as exc:
            logger.warning("Failed to delete file from disk for document %s: %s", doc.id, exc)

        # 3. Delete PostgreSQL record
        doc.delete()
        return True
