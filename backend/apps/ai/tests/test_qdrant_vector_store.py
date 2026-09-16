import uuid
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from apps.ai.rag.schemas import DocumentChunk
from apps.ai.rag.vector_store import QdrantVectorStore


class QdrantVectorStoreTestCase(SimpleTestCase):
    def setUp(cls):
        super().setUpClass()

        cls.collection_name = (
            f"finpilot_test_{uuid.uuid4().hex}"
        )

        cls.store = QdrantVectorStore(
            url=settings.QDRANT_URL,
            collection_name=cls.collection_name,
            vector_size=3,
        )
        
    def tearDown(cls):
        try:
            cls.store.client.delete_collection(
                cls.collection_name
            )
        finally:
            super().tearDownClass()

    def test_collection_is_created(self):
        exists = self.store.client.collection_exists(
            self.collection_name
        )

        self.assertTrue(exists)

    def test_add_and_search(self):
        chunks = [
            DocumentChunk(
                document_id="doc-1",
                chunk_id="chunk-1",
                text="Reliance revenue increased.",
                metadata={
                    "ticker": "RELIANCE",
                    "document_type": "annual_report",
                },
            ),
            DocumentChunk(
                document_id="doc-2",
                chunk_id="chunk-1",
                text="TCS revenue increased.",
                metadata={
                    "ticker": "TCS",
                    "document_type": "annual_report",
                },
            ),
        ]

        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]

        self.store.add(
            chunks,
            embeddings,
        )

        results = self.store.search(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=1,
        )

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0].chunk.document_id,
            "doc-1",
        )

    def test_metadata_filtering(self):
        chunks = [
            DocumentChunk(
                document_id="reliance-annual",
                chunk_id="chunk-1",
                text="Reliance annual report.",
                metadata={
                    "ticker": "RELIANCE",
                    "document_type": "annual_report",
                },
            ),
            DocumentChunk(
                document_id="reliance-news",
                chunk_id="chunk-1",
                text="Reliance news article.",
                metadata={
                    "ticker": "RELIANCE",
                    "document_type": "news",
                },
            ),
            DocumentChunk(
                document_id="tcs-annual",
                chunk_id="chunk-1",
                text="TCS annual report.",
                metadata={
                    "ticker": "TCS",
                    "document_type": "annual_report",
                },
            ),
        ]

        embeddings = [
            [1.0, 0.0, 0.0],
            [0.99, 0.01, 0.0],
            [0.98, 0.02, 0.0],
        ]

        self.store.add(
            chunks,
            embeddings,
        )

        results = self.store.search(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=10,
            filters={
                "ticker": "RELIANCE",
                "document_type": "annual_report",
            },
        )

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0].chunk.document_id,
            "reliance-annual",
        )

    def test_score_threshold(self):
        chunks = [
            DocumentChunk(
                document_id="high",
                chunk_id="chunk-1",
                text="High similarity.",
                metadata={},
            ),
            DocumentChunk(
                document_id="low",
                chunk_id="chunk-1",
                text="Low similarity.",
                metadata={},
            ),
        ]

        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]

        self.store.add(
            chunks,
            embeddings,
        )

        results = self.store.search(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=10,
            score_threshold=0.8,
        )

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0].chunk.document_id,
            "high",
        )

    def test_same_chunk_id_is_idempotent(self):
        chunk = DocumentChunk(
            document_id="idempotent-doc",
            chunk_id="chunk-1",
            text="Same chunk.",
            metadata={},
        )

        embedding = [
            [1.0, 0.0, 0.0],
        ]

        self.store.add(
            [chunk],
            embedding,
        )

        self.store.add(
            [chunk],
            embedding,
        )

        results = self.store.search(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=10,
        )

        matching = [
            result
            for result in results
            if result.chunk.document_id
            == "idempotent-doc"
        ]

        self.assertEqual(
            len(matching),
            1,
        )

    def test_embedding_dimension_mismatch_is_rejected(self):
        chunk = DocumentChunk(
            document_id="doc-dimension",
            chunk_id="chunk-1",
            text="Dimension test.",
            metadata={},
        )

        with self.assertRaises(ValueError):
            self.store.add(
                [chunk],
                [[1.0, 0.0]],
            )

    def test_query_dimension_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.search(
                query_embedding=[1.0, 0.0],
                top_k=1,
            )

    def test_empty_store_returns_empty_results(self):
        collection_name = (
            f"finpilot_empty_{uuid.uuid4().hex}"
        )

        store = QdrantVectorStore(
            url=settings.QDRANT_URL,
            collection_name=collection_name,
            vector_size=3,
        )

        try:
            results = store.search(
                query_embedding=[1.0, 0.0, 0.0],
                top_k=5,
            )

            self.assertEqual(
                results,
                [],
            )
        finally:
            store.client.delete_collection(
                collection_name
            )

    def test_sec_metadata_and_date_range_filtering(self):
        chunks = [
            DocumentChunk(
                document_id="sec-doc-1",
                chunk_id="chunk-1",
                text="Apple 10-K filing text with strong revenue.",
                metadata={
                    "user_id": "1",
                    "source_type": "SEC_EDGAR",
                    "ticker": "AAPL",
                    "market": "US",
                    "sec_form": "10-K",
                    "sec_cik": "0000320193",
                    "sec_accession_number": "0000320193-23-000106",
                    "sec_filing_date": "2023-11-03",
                    "sec_report_date": "2023-09-30",
                },
            ),
            DocumentChunk(
                document_id="sec-doc-2",
                chunk_id="chunk-1",
                text="Apple 10-Q filing text for Q2.",
                metadata={
                    "user_id": "1",
                    "source_type": "SEC_EDGAR",
                    "ticker": "AAPL",
                    "market": "US",
                    "sec_form": "10-Q",
                    "sec_cik": "0000320193",
                    "sec_accession_number": "0000320193-23-000070",
                    "sec_filing_date": "2023-05-05",
                    "sec_report_date": "2023-04-01",
                },
            ),
            DocumentChunk(
                document_id="upload-doc-1",
                chunk_id="chunk-1",
                text="Uploaded PDF on Apple.",
                metadata={
                    "user_id": "1",
                    "source_type": "UPLOAD",
                    "ticker": "AAPL",
                    "market": "US",
                },
            ),
        ]

        embeddings = [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.8, 0.2, 0.0],
        ]

        self.store.add(chunks, embeddings)

        # 1. Filter by source_type and sec_form
        res = self.store.search(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=10,
            filters={"source_type": "SEC_EDGAR", "sec_form": "10-K"},
        )
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].chunk.document_id, "sec-doc-1")

        # 2. Filter by accession number
        res_acc = self.store.search(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=10,
            filters={"sec_accession_number": "0000320193-23-000070"},
        )
        self.assertEqual(len(res_acc), 1)
        self.assertEqual(res_acc[0].chunk.document_id, "sec-doc-2")

        # 3. Filter by filing date range
        res_date = self.store.search(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=10,
            filters={
                "filing_date_from": "2023-06-01",
                "filing_date_to": "2023-12-31",
            },
        )
        self.assertEqual(len(res_date), 1)
        self.assertEqual(res_date[0].chunk.document_id, "sec-doc-1")

        # 4. Filter by exact filing date
        res_exact = self.store.search(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=10,
            filters={
                "filing_date_from": "2023-11-03",
                "filing_date_to": "2023-11-03",
            },
        )
        self.assertEqual(len(res_exact), 1)
        self.assertEqual(res_exact[0].chunk.document_id, "sec-doc-1")

    def test_payload_indexes_created_and_idempotent(self):
        col_info = self.store.client.get_collection(self.collection_name)
        schema = col_info.payload_schema

        expected_indexes = {
            "metadata.user_id": "keyword",
            "metadata.document_id": "keyword",
            "metadata.source_type": "keyword",
            "metadata.ticker": "keyword",
            "metadata.market": "keyword",
            "metadata.sec_form": "keyword",
            "metadata.sec_cik": "keyword",
            "metadata.sec_accession_number": "keyword",
            "metadata.sec_filing_date": "datetime",
            "metadata.sec_report_date": "datetime",
        }

        for field_path, expected_type in expected_indexes.items():
            self.assertIn(field_path, schema, f"Missing payload index for {field_path}")
            actual_type = str(schema[field_path].data_type).lower()
            self.assertIn(expected_type, actual_type)

        # Idempotent call: re-running _ensure_payload_indexes must not raise
        self.store._ensure_payload_indexes()

    def test_payload_index_failure_is_logged(self):
        with patch.object(
            self.store.client,
            "create_payload_index",
            side_effect=RuntimeError("Simulated index connection failure"),
        ):
            with self.assertLogs("apps.ai.rag.vector_store", level="WARNING") as cm:
                self.store._ensure_payload_indexes()

            self.assertTrue(
                any("Could not ensure payload index" in msg for msg in cm.output),
                f"Expected warning log in output: {cm.output}",
            )
