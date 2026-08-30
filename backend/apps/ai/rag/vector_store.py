"""In-memory vector storage with deterministic cosine-similarity ranking."""

import math
from typing import Protocol

from apps.ai.rag.schemas import DocumentChunk, RetrievalResult


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
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        if not self._entries:
            return []

        self._validate_embedding(query_embedding)
        ranked_entries = sorted(
            enumerate(self._entries),
            key=lambda entry: (
                -self._cosine_similarity(query_embedding, entry[1][1]),
                entry[0],
            ),
        )

        return [
            RetrievalResult(
                chunk=chunk,
                score=self._cosine_similarity(query_embedding, embedding),
            )
            for _, (chunk, embedding) in ranked_entries[:top_k]
        ]

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
