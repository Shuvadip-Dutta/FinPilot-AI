import uuid

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
            url="http://localhost:6333",
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
            url="http://localhost:6333",
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