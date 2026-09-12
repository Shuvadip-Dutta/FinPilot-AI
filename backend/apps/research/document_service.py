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
    def ingest_sec_filing(
        cls,
        user: Any,
        ticker: str,
        accession_number: str,
        form: str | None = None,
        filing_date: str | None = None,
        report_date: str | None = None,
        primary_document: str | None = None,
        description: str | None = None,
        sec_client: Any | None = None,
    ) -> FinancialDocument:
        """Download, parse, chunk, and index an SEC EDGAR filing document into RAG."""
        from django.db import IntegrityError
        from apps.research.services.sec_service import (
            SecEdgarClient,
            default_sec_client,
            SecNotFoundError,
        )

        client: SecEdgarClient = sec_client or default_sec_client
        clean_ticker = str(ticker).strip().upper()
        clean_acc_num = str(accession_number).strip()

        # 1. Idempotency Check: User + SEC Accession Number
        existing_doc = FinancialDocument.objects.filter(
            user=user,
            sec_accession_number=clean_acc_num,
        ).first()

        if existing_doc and existing_doc.ingestion_status == FinancialDocument.STATUS_COMPLETED:
            logger.info(
                "SEC filing %s for user %s already completed (id: %s). Returning existing document.",
                clean_acc_num,
                user.id,
                existing_doc.id,
            )
            return existing_doc

        # 2. Initialize / Reuse Record in PROCESSING state before download/processing
        initial_filename = f"{clean_ticker}_{clean_acc_num}_filing.htm"
        if existing_doc:
            doc = existing_doc
            doc.ingestion_status = FinancialDocument.STATUS_PROCESSING
            doc.ingestion_error = None
            doc.ticker = clean_ticker
            if form:
                doc.sec_form = form
            if filing_date:
                doc.sec_filing_date = filing_date
            if report_date:
                doc.sec_report_date = report_date
            doc.save(update_fields=["ingestion_status", "ingestion_error", "ticker", "sec_form", "sec_filing_date", "sec_report_date"])
        else:
            try:
                doc = FinancialDocument.objects.create(
                    id=uuid.uuid4(),
                    user=user,
                    source_type=FinancialDocument.SOURCE_SEC_EDGAR,
                    filename=initial_filename,
                    content_type="text/html",
                    file_size=0,
                    file_path="",
                    ticker=clean_ticker,
                    market="US",
                    sec_form=form,
                    sec_accession_number=clean_acc_num,
                    sec_filing_date=filing_date or None,
                    sec_report_date=report_date or None,
                    ingestion_status=FinancialDocument.STATUS_PROCESSING,
                    chunk_count=0,
                    ingestion_error=None,
                )
            except IntegrityError:
                # Concurrent creation race: fetch the created record
                doc = FinancialDocument.objects.get(
                    user=user,
                    sec_accession_number=clean_acc_num,
                )
                if doc.ingestion_status == FinancialDocument.STATUS_COMPLETED:
                    return doc
                doc.ingestion_status = FinancialDocument.STATUS_PROCESSING
                doc.ingestion_error = None
                doc.save(update_fields=["ingestion_status", "ingestion_error"])

        target_file_path: Path | None = None

        # 3. Execute Resolution, Download, Parsing, and Vector Ingestion
        try:
            # Resolve CIK
            cik = client.resolve_cik(clean_ticker)

            # Resolve Filing Submission Metadata if not fully specified
            resolved_form = form
            resolved_filing_date = filing_date
            resolved_report_date = report_date
            resolved_primary_doc = primary_document
            resolved_description = description
            resolved_document_url = None

            if not (resolved_form and resolved_primary_doc and resolved_filing_date):
                submissions = client.get_company_submissions(clean_ticker)
                matched_filing = None
                for f in submissions.filings:
                    if f.accession_number == clean_acc_num:
                        matched_filing = f
                        break

                if matched_filing:
                    resolved_form = resolved_form or matched_filing.form
                    resolved_filing_date = resolved_filing_date or matched_filing.filing_date
                    resolved_report_date = resolved_report_date or matched_filing.report_date
                    resolved_primary_doc = resolved_primary_doc or matched_filing.primary_document
                    resolved_description = resolved_description or matched_filing.description
                    resolved_document_url = matched_filing.document_url
                else:
                    if not resolved_primary_doc:
                        raise SecNotFoundError(
                            f"Filing accession number '{clean_acc_num}' not found in submissions for {clean_ticker}."
                        )

            if not resolved_document_url:
                cik_no_zeros = str(int(cik))
                acc_no_hyphens = clean_acc_num.replace("-", "")
                resolved_document_url = f"{client.ARCHIVES_URL}/{cik_no_zeros}/{acc_no_hyphens}/{resolved_primary_doc}"

            # Download raw filing content
            raw_bytes = client.download_filing_content(resolved_document_url)

            # Write document to user storage
            clean_primary_doc = sanitize_filename(resolved_primary_doc or "filing.htm")
            clean_filename = f"{clean_ticker}_{clean_acc_num}_{clean_primary_doc}"
            ext = Path(clean_filename).suffix.lower()
            content_type = "text/html" if ext in (".htm", ".html", ".xhtml") else "text/plain"

            media_root = Path(settings.MEDIA_ROOT)
            user_doc_dir = media_root / "documents" / str(user.id) / "sec"
            user_doc_dir.mkdir(parents=True, exist_ok=True)

            target_file_path = user_doc_dir / f"{doc.id}_{clean_filename}"
            with open(target_file_path, "wb+") as destination:
                destination.write(raw_bytes)

            # Update document attributes with downloaded metadata
            doc.filename = clean_filename
            doc.content_type = content_type
            doc.file_size = len(raw_bytes)
            doc.file_path = str(target_file_path)
            doc.sec_form = resolved_form
            doc.sec_filing_date = resolved_filing_date or None
            doc.sec_report_date = resolved_report_date or None
            doc.sec_cik = cik
            doc.source_url = resolved_document_url
            doc.primary_doc_description = resolved_description
            doc.save(update_fields=[
                "filename", "content_type", "file_size", "file_path",
                "sec_form", "sec_filing_date", "sec_report_date", "sec_cik",
                "source_url", "primary_doc_description",
            ])

            # Parse document text and tables
            parsed_doc = parse_financial_document(
                source=target_file_path,
                content_type=content_type,
                filename=clean_filename,
            )

            chunk_metadata: dict[str, Any] = {
                "user_id": str(user.id),
                "document_id": str(doc.id),
                "source_type": FinancialDocument.SOURCE_SEC_EDGAR,
                "filename": doc.filename,
                "document_name": f"{clean_ticker} {resolved_form or 'Filing'} ({resolved_filing_date or 'SEC'})",
                "document_type": "sec_filing",
                "ticker": clean_ticker,
                "market": "US",
                "sec_cik": cik,
                "sec_form": resolved_form or "",
                "sec_accession_number": clean_acc_num,
                "sec_filing_date": str(resolved_filing_date or ""),
                "sec_report_date": str(resolved_report_date or ""),
                "source_url": resolved_document_url,
                "page_start": 1,
                "page_count": parsed_doc.page_count,
            }

            # Vectorize & Index chunks into RAG
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
            logger.info("Successfully ingested SEC filing %s (%d chunks)", doc.id, len(chunks))
            return doc

        except Exception as exc:
            logger.exception("SEC filing ingestion failed for document %s: %s", doc.id, exc)
            doc.ingestion_status = FinancialDocument.STATUS_FAILED
            doc.ingestion_error = str(exc)
            doc.save(update_fields=["ingestion_status", "ingestion_error"])

            # Rollback any partially vectorized chunks
            try:
                pipeline = build_rag_pipeline()
                pipeline.delete_document(document_id=str(doc.id), user_id=str(user.id))
            except Exception as cleanup_err:
                logger.warning("Failed to clean up partial vector chunks for %s: %s", doc.id, cleanup_err)

            # Clean up incomplete file on disk if it was created
            if target_file_path and target_file_path.exists():
                try:
                    target_file_path.unlink()
                except Exception as file_cleanup_err:
                    logger.warning("Failed to delete incomplete file %s: %s", target_file_path, file_cleanup_err)

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

