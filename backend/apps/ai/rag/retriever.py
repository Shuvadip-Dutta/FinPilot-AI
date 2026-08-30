"""Query-to-vector-store retrieval orchestration."""

from apps.ai.rag.embeddings import EmbeddingProvider
from apps.ai.rag.schemas import RetrievalResult
from apps.ai.rag.vector_store import VectorStore


class Retriever:
    """Embed a query and retrieve its nearest document chunks."""

    def __init__(self, embedding_provider: EmbeddingProvider, vector_store: VectorStore):
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        if not query.strip():
            raise ValueError("query must not be empty.")

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        embeddings = self.embedding_provider.embed([query])

        if len(embeddings) != 1:
            raise ValueError("Embedding provider must return one query embedding.")

        return self.vector_store.search(embeddings[0], top_k)
