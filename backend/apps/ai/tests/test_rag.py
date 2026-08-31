from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.ai.rag.chunker import DocumentChunker
from apps.ai.rag.embeddings import DeterministicEmbeddingProvider
from apps.ai.rag.pipeline import RAGPipeline
from apps.ai.rag.retriever import Retriever
from apps.ai.rag.schemas import DocumentChunk, RetrievalResult
from apps.ai.rag.vector_store import InMemoryVectorStore
from apps.ai.services.rag_tools import search_financial_documents


class RAGFoundationTestCase(SimpleTestCase):

    def test_valid_document_chunk(self):
        chunk = DocumentChunk(
            document_id="annual-report",
            chunk_id="annual-report:0",
            text="Revenue increased during the period.",
            metadata={"year": 2026},
        )

        self.assertEqual(chunk.document_id, "annual-report")

    def test_empty_document_chunk_fields_are_rejected(self):
        for field in ("document_id", "chunk_id", "text"):
            values = {
                "document_id": "document",
                "chunk_id": "document:0",
                "text": "content",
                "metadata": {},
            }
            values[field] = " "

            with self.assertRaises(ValidationError):
                DocumentChunk(**values)

    def test_chunking_is_deterministic_and_creates_multiple_chunks(self):
        chunker = DocumentChunker(chunk_size=5, overlap=2)

        first = chunker.chunk("doc", "abcdefghij")
        second = chunker.chunk("doc", "abcdefghij")

        self.assertEqual(first, second)
        self.assertEqual([chunk.text for chunk in first], ["abcde", "defgh", "ghij"])
        self.assertEqual([chunk.chunk_id for chunk in first], ["doc:0", "doc:1", "doc:2"])

    def test_chunker_preserves_overlap_metadata_and_original_text(self):
        chunks = DocumentChunker(chunk_size=5, overlap=2).chunk(
            "doc",
            "abcdefghij",
            {"source": "report"},
        )

        self.assertEqual(chunks[0].text[-2:], chunks[1].text[:2])
        self.assertEqual(chunks[0].metadata, {"source": "report"})
        self.assertEqual(
            chunks[0].text + chunks[1].text[2:] + chunks[2].text[2:],
            "abcdefghij",
        )
        self.assertTrue(all(chunk.text for chunk in chunks))

    def test_chunker_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            DocumentChunker(chunk_size=0)
        with self.assertRaises(ValueError):
            DocumentChunker(chunk_size=5, overlap=-1)
        with self.assertRaises(ValueError):
            DocumentChunker(chunk_size=5, overlap=5)

    def test_embedding_provider_is_deterministic_fixed_size_and_local(self):
        provider = DeterministicEmbeddingProvider(dimension=16)

        embeddings = provider.embed(["Revenue growth", "Revenue growth", "Profit"])

        self.assertEqual(len(embeddings), 3)
        self.assertEqual(len(embeddings[0]), 16)
        self.assertEqual(embeddings[0], embeddings[1])
        self.assertNotEqual(embeddings[0], embeddings[2])

    def test_vector_store_add_search_top_k_and_stable_ties(self):
        store = InMemoryVectorStore()
        chunks = [
            DocumentChunk(document_id="doc", chunk_id="doc:0", text="one", metadata={}),
            DocumentChunk(document_id="doc", chunk_id="doc:1", text="two", metadata={}),
            DocumentChunk(document_id="doc", chunk_id="doc:2", text="three", metadata={}),
        ]
        store.add(chunks, [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])

        results = store.search([1.0, 0.0], top_k=2)

        self.assertEqual([result.chunk.chunk_id for result in results], ["doc:0", "doc:1"])
        self.assertEqual(len(results), 2)

    def test_vector_store_empty_and_dimension_mismatch(self):
        store = InMemoryVectorStore()
        self.assertEqual(store.search([1.0, 0.0], top_k=1), [])

        chunk = DocumentChunk(document_id="doc", chunk_id="doc:0", text="text", metadata={})
        store.add([chunk], [[1.0, 0.0]])

        with self.assertRaises(ValueError):
            store.add([chunk], [[1.0, 0.0, 0.0]])
        with self.assertRaises(ValueError):
            store.search([1.0, 0.0, 0.0], top_k=1)

    def test_retriever_embeds_query_and_validates_inputs(self):
        provider = DeterministicEmbeddingProvider()
        store = InMemoryVectorStore()
        chunk = DocumentChunk(document_id="doc", chunk_id="doc:0", text="revenue", metadata={})
        store.add([chunk], provider.embed([chunk.text]))
        retriever = Retriever(provider, store)

        results = retriever.retrieve("revenue", top_k=1)

        self.assertEqual(results[0].chunk.chunk_id, "doc:0")
        with self.assertRaises(ValueError):
            retriever.retrieve(" ")
        with self.assertRaises(ValueError):
            retriever.retrieve("revenue", top_k=0)

    def test_pipeline_ingest_retrieve_and_deterministic_behavior(self):
        pipeline = self._pipeline()

        chunks = pipeline.ingest(
            "report",
            "Revenue improved. Profit margin expanded.",
            {"type": "annual-report"},
        )
        first = pipeline.retrieve("profit", top_k=1)
        second = pipeline.retrieve("profit", top_k=1)

        self.assertTrue(chunks)
        self.assertEqual(first, second)
        self.assertEqual(first[0].chunk.metadata, {"type": "annual-report"})

    def test_pipeline_empty_retrieval_and_no_external_api_or_llm_calls(self):
        pipeline = self._pipeline()

        self.assertEqual(pipeline.retrieve("revenue"), [])

    @patch("apps.ai.services.rag_tools.build_rag_pipeline")
    def test_search_financial_documents_valid_retrieval(self, mock_build_pipeline):
        pipeline = MagicMock()
        pipeline.retrieve.return_value = [
            RetrievalResult(
                chunk=DocumentChunk(
                    document_id="doc-1",
                    chunk_id="doc-1:0",
                    text="Revenue grew 12% in FY2024.",
                    metadata={
                        "ticker": "RELIANCE",
                        "market": "IN",
                        "document_type": "annual_report",
                        "fiscal_year": 2024,
                    },
                ),
                score=0.91,
            )
        ]
        mock_build_pipeline.return_value = pipeline

        result = search_financial_documents(
            query="revenue growth",
            ticker="RELIANCE",
            market="IN",
            document_type="annual_report",
            fiscal_year=2024,
            top_k=3,
        )

        self.assertEqual(result["documents"][0]["text"], "Revenue grew 12% in FY2024.")
        self.assertEqual(result["documents"][0]["score"], 0.91)
        self.assertEqual(result["documents"][0]["document_id"], "doc-1")
        self.assertEqual(result["documents"][0]["chunk_id"], "doc-1:0")
        self.assertEqual(
            result["documents"][0]["metadata"],
            {
                "ticker": "RELIANCE",
                "market": "IN",
                "document_type": "annual_report",
                "fiscal_year": 2024,
            },
        )
        pipeline.retrieve.assert_called_once_with(
            query="revenue growth",
            top_k=3,
            filters={
                "ticker": "RELIANCE",
                "market": "IN",
                "document_type": "annual_report",
                "fiscal_year": 2024,
            },
        )

    @patch("apps.ai.services.rag_tools.build_rag_pipeline")
    def test_search_financial_documents_applies_ticker_filter(self, mock_build_pipeline):
        pipeline = MagicMock()
        pipeline.retrieve.return_value = []
        mock_build_pipeline.return_value = pipeline

        search_financial_documents(query="revenue", ticker="tcs")

        pipeline.retrieve.assert_called_once_with(
            query="revenue",
            top_k=5,
            filters={"ticker": "TCS"},
        )

    @patch("apps.ai.services.rag_tools.build_rag_pipeline")
    def test_search_financial_documents_applies_document_type_filter(self, mock_build_pipeline):
        pipeline = MagicMock()
        pipeline.retrieve.return_value = []
        mock_build_pipeline.return_value = pipeline

        search_financial_documents(query="revenue", document_type="annual_report")

        pipeline.retrieve.assert_called_once_with(
            query="revenue",
            top_k=5,
            filters={"document_type": "annual_report"},
        )

    @patch("apps.ai.services.rag_tools.build_rag_pipeline")
    def test_search_financial_documents_applies_fiscal_year_filter(self, mock_build_pipeline):
        pipeline = MagicMock()
        pipeline.retrieve.return_value = []
        mock_build_pipeline.return_value = pipeline

        search_financial_documents(query="revenue", fiscal_year=2024)

        pipeline.retrieve.assert_called_once_with(
            query="revenue",
            top_k=5,
            filters={"fiscal_year": 2024},
        )

    @patch("apps.ai.services.rag_tools.build_rag_pipeline")
    def test_search_financial_documents_rejects_invalid_top_k(self, mock_build_pipeline):
        with self.assertRaises(ValueError):
            search_financial_documents(query="revenue", top_k=0)

        with self.assertRaises(ValueError):
            search_financial_documents(query="revenue", top_k=11)

        mock_build_pipeline.assert_not_called()

    @patch("apps.ai.services.rag_tools.build_rag_pipeline")
    def test_search_financial_documents_rejects_empty_query(self, mock_build_pipeline):
        with self.assertRaises(ValueError):
            search_financial_documents(query="   ")

        mock_build_pipeline.assert_not_called()

    @staticmethod
    def _pipeline() -> RAGPipeline:
        provider = DeterministicEmbeddingProvider(dimension=32)
        store = InMemoryVectorStore()
        return RAGPipeline(
            chunker=DocumentChunker(chunk_size=20, overlap=5),
            embedding_provider=provider,
            vector_store=store,
        )
