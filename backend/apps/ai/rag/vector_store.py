"""In-memory vector storage with deterministic cosine-similarity ranking."""

import math
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5
from apps.ai.rag.schemas import DocumentChunk, RetrievalResult
from qdrant_client import QdrantClient
from qdrant_client.http import models


class VectorStore(Protocol):
    """Storage interface used by retrievers and ingestion pipelines."""

    def add(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        """Add chunks paired with their embeddings."""

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, object] | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        """Return the highest-scoring chunks for a query embedding."""


class InMemoryVectorStore:
    """A deterministic in-memory store intended for development and tests."""

    def __init__(self):
        self._entries: list[tuple[DocumentChunk, list[float]]] = []
        self._dimension: int | None = None

    def add(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must have exactly one embedding.")

        for embedding in embeddings:
            self._validate_embedding(embedding)

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self._entries.append((chunk, list(embedding)))

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, object] | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if score_threshold is not None and not math.isfinite(
            score_threshold
        ):
            raise ValueError(
                "score_threshold must be finite."
            )

        if not self._entries:
            return []

        self._validate_embedding(query_embedding)

        candidates = []

        for index, (chunk, embedding) in enumerate(
            self._entries
        ):
            if filters:
                if any(
                    chunk.metadata.get(key) != value
                    for key, value in filters.items()
                ):
                    continue

            score = self._cosine_similarity(
                query_embedding,
                embedding,
            )

            if (
                score_threshold is not None
                and score < score_threshold
            ):
                continue

            candidates.append(
                (
                    index,
                    chunk,
                    score,
                )
            )

        candidates.sort(
            key=lambda entry: (
                -entry[2],
                entry[0],
            )
        )

        return [
            RetrievalResult(
                chunk=chunk,
                score=score,
            )
            for _, chunk, score in candidates[:top_k]
        ]

    def delete_document(
        self,
        document_id: str,
        user_id: str | None = None,
    ) -> int:
        initial_len = len(self._entries)
        self._entries = [
            (chunk, emb)
            for chunk, emb in self._entries
            if not (
                chunk.document_id == document_id
                and (
                    user_id is None
                    or str(chunk.metadata.get("user_id")) == str(user_id)
                )
            )
        ]
        return initial_len - len(self._entries)

    def _validate_embedding(self, embedding: list[float]) -> None:

        if not embedding:
            raise ValueError("Embeddings must not be empty.")

        if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in embedding):
            raise ValueError("Embeddings must contain finite numeric values.")

        if self._dimension is None:
            self._dimension = len(embedding)
        elif len(embedding) != self._dimension:
            raise ValueError("Embedding dimensions must match.")

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(
            sum(value * value for value in right)
        )

        if not denominator:
            return 0.0

        return sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True)) / denominator

class QdrantVectorStore:
    """Persistent Qdrant-backed vector store."""

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection_name: str = "finpilot_documents",
        vector_size: int = 384,
    ):
        if not url.strip():
            raise ValueError("Qdrant URL must not be empty.")

        if not collection_name.strip():
            raise ValueError(
                "Collection name must not be empty."
            )

        if vector_size <= 0:
            raise ValueError(
                "Vector size must be greater than zero."
            )

        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.vector_size = vector_size

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if not self.client.collection_exists(
            self.collection_name
        ):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

    def add(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError(
                "Each chunk must have exactly one embedding."
            )

        points = []

        for chunk, embedding in zip(
            chunks,
            embeddings,
            strict=True,
        ):
            if len(embedding) != self.vector_size:
                raise ValueError(
                    "Embedding dimensions must match "
                    "the configured vector size."
                )

            point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{chunk.document_id}:{chunk.chunk_id}",
                )
            )

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "document_id": chunk.document_id,
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "metadata": chunk.metadata,
                    },
                )
            )

        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, object] | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if len(query_embedding) != self.vector_size:
            raise ValueError(
                "Query embedding dimensions must match "
                "the configured vector size."
            )

        query_filter = self._build_filter(
            filters
        )

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            query_filter=query_filter,
            score_threshold=score_threshold,
            with_payload=True,
            limit=top_k,
        ).points

        return [
            RetrievalResult(
                chunk=DocumentChunk(
                    document_id=result.payload["document_id"],
                    chunk_id=result.payload["chunk_id"],
                    text=result.payload["text"],
                    metadata=result.payload.get(
                        "metadata",
                        {},
                    ),
                ),
                score=float(result.score),
            )
            for result in results
        ]

    @staticmethod
    def _build_filter(
        filters: dict[str, object] | None,
    ) -> models.Filter | None:

        if not filters:
            return None

        conditions = []

        for key, value in filters.items():
            conditions.append(
                models.FieldCondition(
                    key=f"metadata.{key}",
                    match=models.MatchValue(
                        value=value,
                    ),
                )
            )

        return models.Filter(
            must=conditions,
        )

    def delete_document(
        self,
        document_id: str,
        user_id: str | None = None,
    ) -> None:
        conditions = [
            models.FieldCondition(
                key="metadata.document_id",
                match=models.MatchValue(value=document_id),
            )
        ]
        if user_id is not None:
            conditions.append(
                models.FieldCondition(
                    key="metadata.user_id",
                    match=models.MatchValue(value=str(user_id)),
                )
            )

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=conditions)
            ),
        )