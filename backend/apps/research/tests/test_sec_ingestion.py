"""Tests for Module 13 Phase 3 — SEC Filing Model Migration & Ingestion Pipeline."""

import io
import os
import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ai.rag.chunker import DocumentChunker
from apps.ai.rag.embeddings import DeterministicEmbeddingProvider
from apps.ai.rag.pipeline import RAGPipeline
from apps.ai.rag.vector_store import InMemoryVectorStore
from apps.research.document_service import DocumentIngestionService
from apps.research.models import FinancialDocument
from apps.research.services.sec_service import (
    SecEdgarClient,
    SecFilingMetadata,
    SecNetworkError,
    SecNotFoundError,
    SecResponseError,
    SecSubmissionsResult,
)

User = get_user_model()


class SecIngestionTestSuite(TestCase):
    """Test suite covering SEC filing ingestion, lifecycle tracking, idempotency, retry, and cleanup."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="user_a@finpilot.test",
            email="user_a@finpilot.test",
            password="TestPassword123!",
        )
        self.user_b = User.objects.create_user(
            username="user_b@finpilot.test",
            email="user_b@finpilot.test",
            password="TestPassword123!",
        )

        # In-memory test pipeline fixtures
        self.vector_store = InMemoryVectorStore()
        self.embedding_provider = DeterministicEmbeddingProvider(dimension=8)
        self.chunker = DocumentChunker(chunk_size=150, overlap=20)
        self.rag_pipeline = RAGPipeline(
            chunker=self.chunker,
            embedding_provider=self.embedding_provider,
            vector_store=self.vector_store,
        )

        self.mock_sec_client = MagicMock(spec=SecEdgarClient)
        self.mock_sec_client.ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
        self.mock_sec_client.resolve_cik.return_value = "0000320193"

        self.sample_html = b"""
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Apple Inc. Form 10-K</h1>
            <p>Annual Report for the fiscal year ended September 28, 2024.</p>
            <table>
                <tr><th>Metric</th><th>2024</th></tr>
                <tr><td>Total Net Sales</td><td>$391,035</td></tr>
            </table>
        </body>
        </html>
        """

    # -------------------------------------------------------------------------
    # 1. Model Extension & Upload Defaults
    # -------------------------------------------------------------------------
    def test_existing_user_upload_preserves_defaults(self):
        """Verify uploaded documents default to source_type=UPLOAD and nullable SEC fields."""
        doc = FinancialDocument.objects.create(
            user=self.user_a,
            filename="sample_report.pdf",
            content_type="application/pdf",
            file_size=1024,
            file_path="/tmp/sample_report.pdf",
            ticker="AAPL",
            market="US",
        )
        self.assertEqual(doc.source_type, FinancialDocument.SOURCE_UPLOAD)
        self.assertIsNone(doc.sec_accession_number)
        self.assertIsNone(doc.sec_form)
        self.assertIsNone(doc.sec_cik)
        self.assertIsNone(doc.sec_filing_date)

    # -------------------------------------------------------------------------
    # 2. Successful SEC Filing Ingestion
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_ingest_sec_filing_success(self, mock_build_pipeline):
        """Test successful SEC filing download, parsing, chunking, and vector indexing."""
        mock_build_pipeline.return_value = self.rag_pipeline
        self.mock_sec_client.download_filing_content.return_value = self.sample_html

        doc = DocumentIngestionService.ingest_sec_filing(
            user=self.user_a,
            ticker="AAPL",
            accession_number="0000320193-24-000106",
            form="10-K",
            filing_date="2024-11-01",
            report_date="2024-09-28",
            primary_document="aapl-20240928.htm",
            description="Form 10-K Annual Report",
            sec_client=self.mock_sec_client,
        )

        self.assertIsNotNone(doc)
        self.assertEqual(doc.ingestion_status, FinancialDocument.STATUS_COMPLETED)
        self.assertEqual(doc.source_type, FinancialDocument.SOURCE_SEC_EDGAR)
        self.assertEqual(doc.sec_form, "10-K")
        self.assertEqual(doc.sec_accession_number, "0000320193-24-000106")
        self.assertEqual(doc.sec_cik, "0000320193")
        self.assertEqual(str(doc.sec_filing_date), "2024-11-01")
        self.assertEqual(str(doc.sec_report_date), "2024-09-28")
        self.assertGreater(doc.chunk_count, 0)
        self.assertIsNone(doc.ingestion_error)

        # Verify chunks in vector store
        results = self.rag_pipeline.retrieve(
            query="Apple Total Net Sales",
            filters={"user_id": str(self.user_a.id)},
            top_k=3,
        )
        self.assertGreater(len(results), 0)
        top_chunk = results[0].chunk
        self.assertEqual(top_chunk.metadata.get("source_type"), "SEC_EDGAR")
        self.assertEqual(top_chunk.metadata.get("sec_form"), "10-K")
        self.assertEqual(top_chunk.metadata.get("sec_accession_number"), "0000320193-24-000106")
        self.assertEqual(top_chunk.metadata.get("sec_cik"), "0000320193")
        self.assertEqual(top_chunk.metadata.get("user_id"), str(self.user_a.id))

    # -------------------------------------------------------------------------
    # 3. Automatic Metadata Resolution from Submissions API
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_ingest_sec_filing_auto_resolves_metadata(self, mock_build_pipeline):
        """Test that missing filing metadata is auto-resolved from SEC submissions."""
        mock_build_pipeline.return_value = self.rag_pipeline
        self.mock_sec_client.download_filing_content.return_value = self.sample_html
        self.mock_sec_client.get_company_submissions.return_value = SecSubmissionsResult(
            cik="0000320193",
            ticker="AAPL",
            company_name="Apple Inc.",
            filings=[
                SecFilingMetadata(
                    accession_number="0000320193-24-000106",
                    form="10-K",
                    filing_date="2024-11-01",
                    report_date="2024-09-28",
                    primary_document="aapl-20240928.htm",
                    description="Annual Report",
                    document_url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000106/aapl-20240928.htm",
                    interactive_data_url="",
                )
            ],
        )

        doc = DocumentIngestionService.ingest_sec_filing(
            user=self.user_a,
            ticker="AAPL",
            accession_number="0000320193-24-000106",
            sec_client=self.mock_sec_client,
        )

        self.assertEqual(doc.sec_form, "10-K")
        self.assertEqual(str(doc.sec_filing_date), "2024-11-01")
        self.assertEqual(doc.ingestion_status, FinancialDocument.STATUS_COMPLETED)

    # -------------------------------------------------------------------------
    # 4. Completed-Document Idempotency
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_ingest_sec_filing_idempotency(self, mock_build_pipeline):
        """Repeated ingestion of the same accession number returns existing document without duplicate chunks."""
        mock_build_pipeline.return_value = self.rag_pipeline
        self.mock_sec_client.download_filing_content.return_value = self.sample_html

        doc1 = DocumentIngestionService.ingest_sec_filing(
            user=self.user_a,
            ticker="AAPL",
            accession_number="0000320193-24-000106",
            form="10-K",
            filing_date="2024-11-01",
            primary_document="aapl-20240928.htm",
            sec_client=self.mock_sec_client,
        )

        initial_count = len(self.vector_store._entries)

        doc2 = DocumentIngestionService.ingest_sec_filing(
            user=self.user_a,
            ticker="AAPL",
            accession_number="0000320193-24-000106",
            form="10-K",
            filing_date="2024-11-01",
            primary_document="aapl-20240928.htm",
            sec_client=self.mock_sec_client,
        )

        self.assertEqual(doc1.id, doc2.id)
        # Vector store chunk count must not double
        self.assertEqual(len(self.vector_store._entries), initial_count)

    # -------------------------------------------------------------------------
    # 5. Same Accession Number for Different Users (User Isolation)
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_user_isolation_for_same_filing(self, mock_build_pipeline):
        """User A and User B can each ingest the same SEC filing into their own workspace without cross-contamination."""
        mock_build_pipeline.return_value = self.rag_pipeline
        self.mock_sec_client.download_filing_content.return_value = self.sample_html

        doc_a = DocumentIngestionService.ingest_sec_filing(
            user=self.user_a,
            ticker="AAPL",
            accession_number="0000320193-24-000106",
            form="10-K",
            filing_date="2024-11-01",
            primary_document="aapl-20240928.htm",
            sec_client=self.mock_sec_client,
        )

        doc_b = DocumentIngestionService.ingest_sec_filing(
            user=self.user_b,
            ticker="AAPL",
            accession_number="0000320193-24-000106",
            form="10-K",
            filing_date="2024-11-01",
            primary_document="aapl-20240928.htm",
            sec_client=self.mock_sec_client,
        )

        self.assertNotEqual(doc_a.id, doc_b.id)
        self.assertEqual(doc_a.user, self.user_a)
        self.assertEqual(doc_b.user, self.user_b)

        # Retrieval for User A must return only User A chunks
        results_a = self.rag_pipeline.retrieve(
            query="Apple Net Sales",
            filters={"user_id": str(self.user_a.id)},
        )
        for res in results_a:
            self.assertEqual(res.chunk.metadata["user_id"], str(self.user_a.id))

        # Retrieval for User B must return only User B chunks
        results_b = self.rag_pipeline.retrieve(
            query="Apple Net Sales",
            filters={"user_id": str(self.user_b.id)},
        )
        for res in results_b:
            self.assertEqual(res.chunk.metadata["user_id"], str(self.user_b.id))

    # -------------------------------------------------------------------------
    # 6. SEC Download Failure Creates FAILED Document Record
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_sec_download_failure_marks_document_failed(self, mock_build_pipeline):
        """Verify network/HTTP errors during download create a document marked as FAILED with accurate error."""
        mock_build_pipeline.return_value = self.rag_pipeline
        self.mock_sec_client.download_filing_content.side_effect = SecNetworkError("Connection reset by peer.")

        with self.assertRaises(SecNetworkError):
            DocumentIngestionService.ingest_sec_filing(
                user=self.user_a,
                ticker="AAPL",
                accession_number="0000320193-24-000106",
                form="10-K",
                filing_date="2024-11-01",
                primary_document="aapl-20240928.htm",
                sec_client=self.mock_sec_client,
            )

        doc = FinancialDocument.objects.get(
            user=self.user_a,
            sec_accession_number="0000320193-24-000106",
        )
        self.assertEqual(doc.ingestion_status, FinancialDocument.STATUS_FAILED)
        self.assertIn("Connection reset by peer", doc.ingestion_error)

    # -------------------------------------------------------------------------
    # 7. Parsing Failure Marks Document as FAILED
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_parsing_failure_marks_document_failed(self, mock_build_pipeline):
        """Verify parsing errors mark the document as FAILED and clean up."""
        mock_build_pipeline.return_value = self.rag_pipeline
        self.mock_sec_client.download_filing_content.return_value = self.sample_html

        with patch("apps.research.document_service.parse_financial_document") as mock_parse:
            mock_parse.side_effect = ValueError("Corrupt HTML structure cannot be parsed.")
            with self.assertRaises(ValueError):
                DocumentIngestionService.ingest_sec_filing(
                    user=self.user_a,
                    ticker="AAPL",
                    accession_number="0000320193-24-000106",
                    form="10-K",
                    filing_date="2024-11-01",
                    primary_document="aapl-20240928.htm",
                    sec_client=self.mock_sec_client,
                )

        doc = FinancialDocument.objects.get(
            user=self.user_a,
            sec_accession_number="0000320193-24-000106",
        )
        self.assertEqual(doc.ingestion_status, FinancialDocument.STATUS_FAILED)
        self.assertIn("Corrupt HTML structure", doc.ingestion_error)

    # -------------------------------------------------------------------------
    # 8. Embedding / Vector Store Failure Triggers Rollback
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_embedding_or_vector_store_failure_marks_failed(self, mock_build_pipeline):
        """Verify pipeline ingestion errors mark the document as FAILED and trigger rollback."""
        mock_pipeline = MagicMock()
        mock_pipeline.ingest.side_effect = RuntimeError("Embedding service unavailable.")
        mock_build_pipeline.return_value = mock_pipeline
        self.mock_sec_client.download_filing_content.return_value = self.sample_html

        with self.assertRaises(RuntimeError):
            DocumentIngestionService.ingest_sec_filing(
                user=self.user_a,
                ticker="AAPL",
                accession_number="0000320193-24-000106",
                form="10-K",
                filing_date="2024-11-01",
                primary_document="aapl-20240928.htm",
                sec_client=self.mock_sec_client,
            )

        doc = FinancialDocument.objects.get(
            user=self.user_a,
            sec_accession_number="0000320193-24-000106",
        )
        self.assertEqual(doc.ingestion_status, FinancialDocument.STATUS_FAILED)
        self.assertIn("Embedding service unavailable", doc.ingestion_error)
        # Verify rollback call
        mock_pipeline.delete_document.assert_called_once_with(
            document_id=str(doc.id),
            user_id=str(self.user_a.id),
        )

    # -------------------------------------------------------------------------
    # 9. Failed-Document Retry Succeeds Without Duplicates
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_failed_document_retry_succeeds_without_duplicates(self, mock_build_pipeline):
        """Verify that retrying a failed document reuses the existing row, transitions to COMPLETED, and produces 1 doc."""
        mock_build_pipeline.return_value = self.rag_pipeline

        # First attempt: simulate transient failure
        self.mock_sec_client.download_filing_content.side_effect = SecNetworkError("Transient 503 error.")
        with self.assertRaises(SecNetworkError):
            DocumentIngestionService.ingest_sec_filing(
                user=self.user_a,
                ticker="AAPL",
                accession_number="0000320193-24-000106",
                form="10-K",
                filing_date="2024-11-01",
                primary_document="aapl-20240928.htm",
                sec_client=self.mock_sec_client,
            )

        failed_doc = FinancialDocument.objects.get(
            user=self.user_a,
            sec_accession_number="0000320193-24-000106",
        )
        self.assertEqual(failed_doc.ingestion_status, FinancialDocument.STATUS_FAILED)

        # Second attempt (retry): simulate success
        self.mock_sec_client.download_filing_content.side_effect = None
        self.mock_sec_client.download_filing_content.return_value = self.sample_html

        retried_doc = DocumentIngestionService.ingest_sec_filing(
            user=self.user_a,
            ticker="AAPL",
            accession_number="0000320193-24-000106",
            form="10-K",
            filing_date="2024-11-01",
            primary_document="aapl-20240928.htm",
            sec_client=self.mock_sec_client,
        )

        # Ensure same document ID was reused and total doc count is 1
        self.assertEqual(failed_doc.id, retried_doc.id)
        self.assertEqual(retried_doc.ingestion_status, FinancialDocument.STATUS_COMPLETED)
        self.assertIsNone(retried_doc.ingestion_error)
        self.assertEqual(
            FinancialDocument.objects.filter(user=self.user_a, sec_accession_number="0000320193-24-000106").count(),
            1,
        )
