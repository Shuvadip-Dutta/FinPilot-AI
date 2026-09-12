"""Comprehensive tests for Module 11 — RAG Financial Document Intelligence."""

import datetime
import io
import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.ai.agents.financial import FinancialAnalysisAgent
from apps.ai.rag.chunker import DocumentChunker
from apps.ai.rag.embeddings import DeterministicEmbeddingProvider
from apps.ai.rag.pipeline import RAGPipeline
from apps.ai.rag.schemas import DocumentChunk
from apps.ai.rag.vector_store import InMemoryVectorStore
from apps.ai.services.rag_tools import search_financial_documents
from apps.research.models import FinancialDocument
from apps.research.parsers import ParsedDocument, parse_financial_document

User = get_user_model()


class RAGDocumentsTestSuite(TestCase):
    """Test suite covering Document Ingestion, Retrieval, User Isolation, and Agent Integration."""

    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(
            username="usera@finpilot.test",
            email="usera@finpilot.test",
            password="TestPassword123!",
        )
        self.user_b = User.objects.create_user(
            username="userb@finpilot.test",
            email="userb@finpilot.test",
            password="TestPassword123!",
        )

        # Set up in-memory RAG pipeline fixture
        self.vector_store = InMemoryVectorStore()
        self.embedding_provider = DeterministicEmbeddingProvider(dimension=8)
        self.chunker = DocumentChunker(chunk_size=200, overlap=20)
        self.rag_pipeline = RAGPipeline(
            chunker=self.chunker,
            embedding_provider=self.embedding_provider,
            vector_store=self.vector_store,
        )

    # -------------------------------------------------------------------------
    # 1. Unauthenticated Upload -> 401
    # -------------------------------------------------------------------------
    def test_unauthenticated_upload_returns_401(self):
        payload = {
            "file": SimpleUploadedFile("sample.txt", b"Sample content", content_type="text/plain"),
        }
        response = self.client.post("/api/v1/research/documents/", payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -------------------------------------------------------------------------
    # 2. PDF Upload Success
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    @patch("apps.research.document_service.parse_financial_document")
    def test_pdf_upload_success(self, mock_parse, mock_build_pipeline):
        mock_build_pipeline.return_value = self.rag_pipeline
        mock_parse.return_value = ParsedDocument(
            text="Reliance Industries reported consolidated quarterly revenue of INR 2,40,000 crore.",
            page_count=3,
            metadata={"page_count": 3},
        )

        self.client.force_authenticate(user=self.user_a)
        pdf_content = b"%PDF-1.4 dummy pdf content"
        uploaded_file = SimpleUploadedFile("reliance_q3.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(
            "/api/v1/research/documents/",
            {"file": uploaded_file, "ticker": "RELIANCE", "market": "IN"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["filename"], "reliance_q3.pdf")
        self.assertEqual(data["ticker"], "RELIANCE")
        self.assertEqual(data["market"], "IN")
        self.assertEqual(data["ingestion_status"], "COMPLETED")
        self.assertGreater(data["chunk_count"], 0)

        # Verify DB
        doc = FinancialDocument.objects.get(id=data["id"])
        self.assertEqual(doc.user, self.user_a)
        self.assertEqual(doc.ingestion_status, FinancialDocument.STATUS_COMPLETED)

    # -------------------------------------------------------------------------
    # 3. TXT Upload Success
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_txt_upload_success(self, mock_build_pipeline):
        mock_build_pipeline.return_value = self.rag_pipeline

        self.client.force_authenticate(user=self.user_a)
        txt_content = (
            "Infosys announced Q4 revenue growth of 4.5% year over year. "
            "Operating margin expanded by 60 basis points."
        ).encode("utf-8")
        uploaded_file = SimpleUploadedFile("infy_notes.txt", txt_content, content_type="text/plain")

        response = self.client.post(
            "/api/v1/research/documents/",
            {"file": uploaded_file, "ticker": "INFY", "market": "IN"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["filename"], "infy_notes.txt")
        self.assertEqual(data["ingestion_status"], "COMPLETED")
        self.assertGreater(data["chunk_count"], 0)

    # -------------------------------------------------------------------------
    # 4. Invalid Type -> 400
    # -------------------------------------------------------------------------
    def test_invalid_file_type_returns_400(self):
        self.client.force_authenticate(user=self.user_a)
        uploaded_file = SimpleUploadedFile(
            "malicious.exe",
            b"MZ executable binary",
            content_type="application/x-msdownload",
        )

        response = self.client.post(
            "/api/v1/research/documents/",
            {"file": uploaded_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # 5. Oversized File -> 400
    # -------------------------------------------------------------------------
    def test_oversized_file_returns_400(self):
        self.client.force_authenticate(user=self.user_a)
        # Create genuinely oversized file > 10 MB
        oversized = SimpleUploadedFile(
            "huge.txt",
            b"x" * (10 * 1024 * 1024 + 1024),
            content_type="text/plain",
        )

        response = self.client.post(
            "/api/v1/research/documents/",
            {"file": oversized},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    # -------------------------------------------------------------------------
    # 6. Empty File -> 400
    # -------------------------------------------------------------------------
    def test_empty_file_returns_400(self):
        self.client.force_authenticate(user=self.user_a)
        empty_file = SimpleUploadedFile("empty.txt", b"", content_type="text/plain")

        response = self.client.post(
            "/api/v1/research/documents/",
            {"file": empty_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # 7. Ticker/Market Metadata Stored Correctly
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_ticker_market_metadata(self, mock_build_pipeline):
        mock_build_pipeline.return_value = self.rag_pipeline
        self.client.force_authenticate(user=self.user_a)

        uploaded_file = SimpleUploadedFile("aapl.txt", b"Apple 10-K report text", content_type="text/plain")
        response = self.client.post(
            "/api/v1/research/documents/",
            {"file": uploaded_file, "ticker": "aapl", "market": "us"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["ticker"], "AAPL")
        self.assertEqual(data["market"], "US")

    # -------------------------------------------------------------------------
    # 8. Listing Only Own Documents
    # -------------------------------------------------------------------------
    def test_listing_only_own_documents(self):
        doc_a = FinancialDocument.objects.create(
            user=self.user_a,
            filename="user_a_doc.pdf",
            content_type="application/pdf",
            file_size=1024,
            file_path="/tmp/user_a_doc.pdf",
            ingestion_status=FinancialDocument.STATUS_COMPLETED,
        )
        doc_b = FinancialDocument.objects.create(
            user=self.user_b,
            filename="user_b_doc.pdf",
            content_type="application/pdf",
            file_size=2048,
            file_path="/tmp/user_b_doc.pdf",
            ingestion_status=FinancialDocument.STATUS_COMPLETED,
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.get("/api/v1/research/documents/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(doc_a.id))
        self.assertEqual(data[0]["filename"], "user_a_doc.pdf")

    # -------------------------------------------------------------------------
    # 9. Empty Listing
    # -------------------------------------------------------------------------
    def test_empty_listing(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get("/api/v1/research/documents/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    # -------------------------------------------------------------------------
    # 10. Relevant Search
    # -------------------------------------------------------------------------
    @patch("apps.ai.services.rag_tools.build_rag_pipeline")
    def test_relevant_search(self, mock_build_pipeline):
        mock_build_pipeline.return_value = self.rag_pipeline

        # Ingest document into in-memory store
        doc_id = str(uuid.uuid4())
        self.rag_pipeline.ingest(
            document_id=doc_id,
            text="Tata Motors witnessed significant EV market share growth in FY24.",
            metadata={
                "user_id": str(self.user_a.id),
                "document_id": doc_id,
                "document_name": "tata_motors.pdf",
                "ticker": "TATAMOTORS",
                "market": "IN",
                "page_start": 2,
            },
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            "/api/v1/research/documents/search/",
            {"query": "Tata Motors EV market growth", "top_k": 5},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        res = data["results"][0]
        self.assertIn("EV market share", res["text"])
        self.assertEqual(res["ticker"], "TATAMOTORS")
        self.assertEqual(res["page_start"], 2)

    # -------------------------------------------------------------------------
    # 11. User ID Isolation (Cross-User Search is Blocked)
    # -------------------------------------------------------------------------
    @patch("apps.ai.services.rag_tools.build_rag_pipeline")
    def test_user_id_isolation_in_search(self, mock_build_pipeline):
        mock_build_pipeline.return_value = self.rag_pipeline

        # User B ingests private document
        doc_id_b = str(uuid.uuid4())
        self.rag_pipeline.ingest(
            document_id=doc_id_b,
            text="Confidential merger discussion between Alpha Corp and Beta Inc.",
            metadata={
                "user_id": str(self.user_b.id),
                "document_id": doc_id_b,
                "document_name": "confidential_mna.txt",
            },
        )

        # User A searches for the same text
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            "/api/v1/research/documents/search/",
            {"query": "Confidential merger Alpha Corp"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    # -------------------------------------------------------------------------
    # 12. Ticker Filter in Search
    # -------------------------------------------------------------------------
    @patch("apps.ai.services.rag_tools.build_rag_pipeline")
    def test_ticker_filter_in_search(self, mock_build_pipeline):
        mock_build_pipeline.return_value = self.rag_pipeline

        # Ingest document for TCS
        tcs_doc_id = str(uuid.uuid4())
        self.rag_pipeline.ingest(
            document_id=tcs_doc_id,
            text="TCS margins improved by 120 bps.",
            metadata={
                "user_id": str(self.user_a.id),
                "ticker": "TCS",
                "document_name": "tcs.txt",
            },
        )

        # Ingest document for Wipro
        wipro_doc_id = str(uuid.uuid4())
        self.rag_pipeline.ingest(
            document_id=wipro_doc_id,
            text="Wipro margins improved by 80 bps.",
            metadata={
                "user_id": str(self.user_a.id),
                "ticker": "WIPRO",
                "document_name": "wipro.txt",
            },
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            "/api/v1/research/documents/search/",
            {"query": "margins improved", "ticker": "TCS"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["ticker"], "TCS")

    # -------------------------------------------------------------------------
    # 13. Blank Query -> 400
    # -------------------------------------------------------------------------
    def test_blank_query_returns_400(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            "/api/v1/research/documents/search/",
            {"query": "   "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # 14. No Results
    # -------------------------------------------------------------------------
    @patch("apps.ai.services.rag_tools.build_rag_pipeline")
    def test_no_results_search(self, mock_build_pipeline):
        mock_build_pipeline.return_value = self.rag_pipeline
        self.client.force_authenticate(user=self.user_a)

        response = self.client.post(
            "/api/v1/research/documents/search/",
            {"query": "unrelated quantum mechanics string theory"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    # -------------------------------------------------------------------------
    # 15. Own Document Deletion
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    def test_own_document_deletion(self, mock_build_pipeline):
        mock_build_pipeline.return_value = self.rag_pipeline

        doc = FinancialDocument.objects.create(
            user=self.user_a,
            filename="to_delete.txt",
            content_type="text/plain",
            file_size=100,
            file_path="/tmp/to_delete.txt",
            ingestion_status=FinancialDocument.STATUS_COMPLETED,
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.delete(f"/api/v1/research/documents/{doc.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FinancialDocument.objects.filter(id=doc.id).exists())

    # -------------------------------------------------------------------------
    # 16. Cross-User Delete is Forbidden / 404
    # -------------------------------------------------------------------------
    def test_cross_user_deletion_fails(self):
        doc_b = FinancialDocument.objects.create(
            user=self.user_b,
            filename="user_b_private.txt",
            content_type="text/plain",
            file_size=100,
            file_path="/tmp/user_b_private.txt",
            ingestion_status=FinancialDocument.STATUS_COMPLETED,
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.delete(f"/api/v1/research/documents/{doc_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(FinancialDocument.objects.filter(id=doc_b.id).exists())

    # -------------------------------------------------------------------------
    # 17. Ingestion Failure Preserves FAILED Record
    # -------------------------------------------------------------------------
    @patch("apps.research.document_service.build_rag_pipeline")
    @patch("apps.research.document_service.parse_financial_document")
    def test_ingestion_failure_preserves_failed_record(self, mock_parse, mock_build_pipeline):
        mock_parse.side_effect = ValueError("Corrupt PDF streams cannot be decoded.")

        self.client.force_authenticate(user=self.user_a)
        uploaded_file = SimpleUploadedFile("corrupt.pdf", b"garbage", content_type="application/pdf")

        response = self.client.post(
            "/api/v1/research/documents/",
            {"file": uploaded_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        failed_doc = FinancialDocument.objects.filter(user=self.user_a, filename="corrupt.pdf").first()
        self.assertIsNotNone(failed_doc)
        self.assertEqual(failed_doc.ingestion_status, FinancialDocument.STATUS_FAILED)
        self.assertIn("Corrupt PDF streams", failed_doc.ingestion_error)

    # -------------------------------------------------------------------------
    # 18. FinancialAnalysisAgent Uses RAG Evidence
    # -------------------------------------------------------------------------
    def test_financial_agent_uses_rag_evidence(self):
        mock_financials_tool = MagicMock(return_value={"statements": []})
        mock_key_metrics_tool = MagicMock(return_value={"metrics": []})
        mock_rag_tool = MagicMock(
            return_value={
                "documents": [
                    {
                        "text": "Management expects cloud segment revenue to grow by 25% in FY25.",
                        "score": 0.88,
                        "document_id": "doc-123",
                        "chunk_id": "doc-123:0",
                        "metadata": {
                            "document_name": "FY24_Annual_Report.pdf",
                            "page_start": 14,
                        },
                    }
                ]
            }
        )
        mock_llm_service = MagicMock(return_value="Financial analysis considering management 25% cloud guidance.")

        agent = FinancialAnalysisAgent(
            financials_tool=mock_financials_tool,
            key_metrics_tool=mock_key_metrics_tool,
            rag_search_tool=mock_rag_tool,
            ticker="INFY",
            llm_service=mock_llm_service,
        )

        result = agent.run("Analyze INFY financial outlook.")

        self.assertIn("search_financial_documents", result.tools_used)
        mock_rag_tool.assert_called_once()
        mock_llm_service.assert_called_once()

        prompt_messages = mock_llm_service.call_args[0][0]
        self.assertIn("document_evidence", prompt_messages[1]["content"])
        self.assertIn("FY24_Annual_Report.pdf", prompt_messages[1]["content"])

    # -------------------------------------------------------------------------
    # 19. Existing Financial Tools Still Work
    # -------------------------------------------------------------------------
    def test_existing_financial_tools_still_work(self):
        mock_financials_tool = MagicMock(return_value={"statements": []})
        mock_key_metrics_tool = MagicMock(return_value={"metrics": []})
        # RAG tool returns empty or fails gracefully
        mock_rag_tool = MagicMock(side_effect=RuntimeError("Qdrant offline"))
        mock_llm_service = MagicMock(return_value="Standard financial analysis without RAG.")

        agent = FinancialAnalysisAgent(
            financials_tool=mock_financials_tool,
            key_metrics_tool=mock_key_metrics_tool,
            rag_search_tool=mock_rag_tool,
            ticker="TCS",
            llm_service=mock_llm_service,
        )

        result = agent.run("Analyze TCS financials.")

        self.assertEqual(result.response, "Standard financial analysis without RAG.")
        self.assertEqual(result.tools_used, ["get_financials", "get_key_metrics"])

    # -------------------------------------------------------------------------
    # 20. SEC Filing Metadata Filtering & Normalization
    # -------------------------------------------------------------------------
    def test_sec_metadata_search_and_normalization(self):
        doc_uuid = uuid.uuid4()
        chunk_sec = DocumentChunk(
            document_id=str(doc_uuid),
            chunk_id="sec-chunk-1",
            text="Apple Inc. reports record iPhone revenue of $65 billion in FY23 Q4.",
            metadata={
                "user_id": str(self.user_a.id),
                "document_id": str(doc_uuid),
                "source_type": "SEC_EDGAR",
                "ticker": "AAPL",
                "market": "US",
                "sec_form": "10-K",
                "sec_cik": "0000320193",
                "sec_accession_number": "0000320193-23-000106",
                "sec_filing_date": "2023-11-03",
                "sec_report_date": "2023-09-30",
            },
        )
        chunk_upload = DocumentChunk(
            document_id=str(uuid.uuid4()),
            chunk_id="up-chunk-1",
            text="Apple broker research note on iPad growth.",
            metadata={
                "user_id": str(self.user_a.id),
                "source_type": "UPLOAD",
                "ticker": "AAPL",
                "market": "US",
            },
        )
        self.vector_store.add(
            [chunk_sec, chunk_upload],
            [self.embedding_provider.embed(["Apple revenue"])[0], self.embedding_provider.embed(["Apple research note"])[0]],
        )

        with patch("apps.ai.services.rag_tools.build_rag_pipeline", return_value=self.rag_pipeline):
            # Form normalization: "10k" -> "10-K"
            res1 = search_financial_documents(
                query="iPhone revenue",
                ticker="aapl",
                sec_form="10k",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res1["documents"]), 1)
            self.assertEqual(res1["documents"][0]["metadata"]["sec_form"], "10-K")

            # Form normalization: "FORM 10-K" -> "10-K"
            res2 = search_financial_documents(
                query="iPhone revenue",
                sec_form="FORM 10-K",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res2["documents"]), 1)

            # Filter by source_type="SEC_EDGAR"
            res3 = search_financial_documents(
                query="Apple",
                source_type="SEC_EDGAR",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res3["documents"]), 1)
            self.assertEqual(res3["documents"][0]["metadata"]["source_type"], "SEC_EDGAR")

            # Filter by source_type="UPLOAD"
            res4 = search_financial_documents(
                query="Apple",
                source_type="UPLOAD",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res4["documents"]), 1)
            self.assertEqual(res4["documents"][0]["metadata"]["source_type"], "UPLOAD")

            # Filter by sec_accession_number
            res5 = search_financial_documents(
                query="revenue",
                sec_accession_number="0000320193-23-000106",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res5["documents"]), 1)

            # Filter by sec_cik
            res6 = search_financial_documents(
                query="revenue",
                sec_cik="0000320193",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res6["documents"]), 1)

            # Filter by document_id
            res7 = search_financial_documents(
                query="revenue",
                document_id=str(doc_uuid),
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res7["documents"]), 1)

    # -------------------------------------------------------------------------
    # 21. Date Range and Exact Date Filtering
    # -------------------------------------------------------------------------
    def test_sec_date_range_filtering(self):
        chunk_sec1 = DocumentChunk(
            document_id="doc-2023",
            chunk_id="chunk-1",
            text="2023 10-K text.",
            metadata={
                "user_id": str(self.user_a.id),
                "ticker": "AAPL",
                "sec_form": "10-K",
                "sec_filing_date": "2023-11-03",
                "sec_report_date": "2023-09-30",
            },
        )
        chunk_sec2 = DocumentChunk(
            document_id="doc-2024",
            chunk_id="chunk-1",
            text="2024 10-K text.",
            metadata={
                "user_id": str(self.user_a.id),
                "ticker": "AAPL",
                "sec_form": "10-K",
                "sec_filing_date": "2024-11-01",
                "sec_report_date": "2024-09-28",
            },
        )
        self.vector_store.add(
            [chunk_sec1, chunk_sec2],
            [self.embedding_provider.embed(["2023 10-K text"])[0], self.embedding_provider.embed(["2024 10-K text"])[0]],
        )

        with patch("apps.ai.services.rag_tools.build_rag_pipeline", return_value=self.rag_pipeline):
            # Filing date range matching only 2023
            res_2023 = search_financial_documents(
                query="10-K text",
                filing_date_from="2023-01-01",
                filing_date_to="2023-12-31",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res_2023["documents"]), 1)
            self.assertEqual(res_2023["documents"][0]["document_id"], "doc-2023")

            # Exact filing date matching 2024 (from == to)
            res_exact = search_financial_documents(
                query="10-K text",
                filing_date_from="2024-11-01",
                filing_date_to="2024-11-01",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res_exact["documents"]), 1)
            self.assertEqual(res_exact["documents"][0]["document_id"], "doc-2024")

            # Report date range matching both
            res_both = search_financial_documents(
                query="10-K text",
                report_date_from="2023-01-01",
                report_date_to="2024-12-31",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res_both["documents"]), 2)

            # Combined filing and report date filters
            res_comb = search_financial_documents(
                query="10-K text",
                filing_date_from="2024-01-01",
                report_date_from="2024-01-01",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res_comb["documents"]), 1)
            self.assertEqual(res_comb["documents"][0]["document_id"], "doc-2024")

    # -------------------------------------------------------------------------
    # 22. Date Validation & Range Error Handling
    # -------------------------------------------------------------------------
    def test_date_validation_errors(self):
        with patch("apps.ai.services.rag_tools.build_rag_pipeline", return_value=self.rag_pipeline):
            # Invalid date format
            with self.assertRaises(ValueError) as ctx:
                search_financial_documents(
                    query="revenue",
                    filing_date_from="11/03/2023",
                    user_id=self.user_a.id,
                )
            self.assertIn("must be a valid ISO date", str(ctx.exception))

            # Invalid range from > to
            with self.assertRaises(ValueError) as ctx:
                search_financial_documents(
                    query="revenue",
                    filing_date_from="2024-12-31",
                    filing_date_to="2024-01-01",
                    user_id=self.user_a.id,
                )
            self.assertIn("must be before or equal to", str(ctx.exception))

            with self.assertRaises(ValueError) as ctx:
                search_financial_documents(
                    query="revenue",
                    report_date_from="2024-12-31",
                    report_date_to="2024-01-01",
                    user_id=self.user_a.id,
                )
            self.assertIn("must be before or equal to", str(ctx.exception))

            # Invalid UUID
            with self.assertRaises(ValueError) as ctx:
                search_financial_documents(
                    query="revenue",
                    document_id="not-a-valid-uuid",
                    user_id=self.user_a.id,
                )
            self.assertIn("must be a valid UUID", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 23. Cross-User Isolation for SEC Filings
    # -------------------------------------------------------------------------
    def test_cross_user_isolation_sec_filings(self):
        chunk_user_a = DocumentChunk(
            document_id="sec-a",
            chunk_id="chunk-1",
            text="User A confidential SEC note on AAPL.",
            metadata={
                "user_id": str(self.user_a.id),
                "ticker": "AAPL",
                "sec_form": "10-K",
                "sec_accession_number": "0000320193-23-000106",
            },
        )
        chunk_user_b = DocumentChunk(
            document_id="sec-b",
            chunk_id="chunk-1",
            text="User B confidential SEC note on AAPL.",
            metadata={
                "user_id": str(self.user_b.id),
                "ticker": "AAPL",
                "sec_form": "10-K",
                "sec_accession_number": "0000320193-23-000106",
            },
        )
        self.vector_store.add(
            [chunk_user_a, chunk_user_b],
            [self.embedding_provider.embed(["User A note"])[0], self.embedding_provider.embed(["User B note"])[0]],
        )

        with patch("apps.ai.services.rag_tools.build_rag_pipeline", return_value=self.rag_pipeline):
            # User A searching must only get User A documents
            res_a = search_financial_documents(
                query="confidential note",
                ticker="AAPL",
                sec_form="10-K",
                user_id=self.user_a.id,
            )
            self.assertEqual(len(res_a["documents"]), 1)
            self.assertEqual(res_a["documents"][0]["document_id"], "sec-a")

            # User B searching must only get User B documents
            res_b = search_financial_documents(
                query="confidential note",
                ticker="AAPL",
                sec_form="10-K",
                user_id=self.user_b.id,
            )
            self.assertEqual(len(res_b["documents"]), 1)
            self.assertEqual(res_b["documents"][0]["document_id"], "sec-b")

    # -------------------------------------------------------------------------
    # 24. REST Search View Forwards SEC Metadata
    # -------------------------------------------------------------------------
    def test_search_api_forwards_sec_filters(self):
        self.client.force_authenticate(user=self.user_a)

        with patch("apps.research.document_views.search_financial_documents") as mock_search:
            mock_search.return_value = {
                "documents": [
                    {
                        "text": "SEC filing sample snippet",
                        "score": 0.95,
                        "document_id": "doc-sec-1",
                        "chunk_id": "chunk-1",
                        "metadata": {
                            "document_name": "AAPL 10-K (2023-11-03)",
                            "ticker": "AAPL",
                            "sec_form": "10-K",
                            "page_start": 1,
                            "page_count": 50,
                        },
                    }
                ]
            }

            payload = {
                "query": "operating margin expansion",
                "ticker": "AAPL",
                "market": "US",
                "source_type": "SEC_EDGAR",
                "sec_form": "10-K",
                "sec_cik": "0000320193",
                "sec_accession_number": "0000320193-23-000106",
                "filing_date_from": "2023-01-01",
                "filing_date_to": "2023-12-31",
                "report_date_from": "2023-01-01",
                "report_date_to": "2023-12-31",
                "top_k": 3,
            }

            response = self.client.post("/api/v1/research/documents/search/", payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["document_name"], "AAPL 10-K (2023-11-03)")

            mock_search.assert_called_once()
            call_kwargs = mock_search.call_args[1]
            self.assertEqual(call_kwargs["user_id"], self.user_a.id)
            self.assertEqual(call_kwargs["ticker"], "AAPL")
            self.assertEqual(call_kwargs["source_type"], "SEC_EDGAR")
            self.assertEqual(call_kwargs["sec_form"], "10-K")
            self.assertEqual(call_kwargs["sec_accession_number"], "0000320193-23-000106")
            self.assertEqual(call_kwargs["filing_date_from"], datetime.date(2023, 1, 1))
            self.assertEqual(call_kwargs["filing_date_to"], datetime.date(2023, 12, 31))

    # -------------------------------------------------------------------------
    # 25. Tenant ID Requirement & CIK Normalization
    # -------------------------------------------------------------------------
    def test_search_financial_documents_requires_valid_user_id(self):
        with self.assertRaises(ValueError) as ctx:
            search_financial_documents(query="revenue", user_id=None)
        self.assertIn("user_id is required", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            search_financial_documents(query="revenue", user_id="")
        self.assertIn("user_id is required", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            search_financial_documents(query="revenue", user_id="   ")
        self.assertIn("user_id is required", str(ctx.exception))

    def test_sec_cik_zero_padding_normalization(self):
        with patch("apps.ai.services.rag_tools.build_rag_pipeline") as mock_build_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.retrieve.return_value = []
            mock_build_pipeline.return_value = mock_pipeline

            # 6-digit unpadded CIK -> normalized to 10-digit
            search_financial_documents(
                query="revenue",
                sec_cik="320193",
                user_id=self.user_a.id,
            )
            mock_pipeline.retrieve.assert_called_once()
            filters = mock_pipeline.retrieve.call_args[1]["filters"]
            self.assertEqual(filters["sec_cik"], "0000320193")

            mock_pipeline.reset_mock()

            # Already 10-digit CIK -> kept as is
            search_financial_documents(
                query="revenue",
                sec_cik="0000320193",
                user_id=self.user_a.id,
            )
            filters = mock_pipeline.retrieve.call_args[1]["filters"]
            self.assertEqual(filters["sec_cik"], "0000320193")
