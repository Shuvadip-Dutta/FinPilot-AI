"""Document ingestion and retrieval pipeline for the local RAG foundation."""

from apps.ai.rag.chunker import DocumentChunker
from apps.ai.rag.embeddings import EmbeddingProvider
from apps.ai.rag.retriever import Retriever
from apps.ai.rag.schemas import DocumentChunk, RetrievalResult
from apps.ai.rag.vector_store import VectorStore
from apps.ai.exceptions import RAGError


class RAGPipeline:
    """Ingest unstructured document text and retrieve its relevant chunks."""

    def __init__(
        self,
        chunker: DocumentChunker,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        retriever: Retriever | None = None,
    ):
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.retriever = retriever or Retriever(embedding_provider, vector_store)

    def ingest(
        self,
        document_id: str,
        text: str,
        metadata: dict[str, object] | None = None,
    ) -> list[DocumentChunk]:
        chunks = self.chunker.chunk(document_id, text, metadata)

        try:
            embeddings = self.embedding_provider.embed(
                [chunk.text for chunk in chunks]
            )
            self.vector_store.add(chunks, embeddings)
        except (ValueError, TypeError) as exc:
            raise RAGError(f"Unable to ingest RAG document: {exc}") from exc

        return chunks

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, object] | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        return self.retriever.retrieve(
            query=query,
            top_k=top_k,
            filters=filters,
            score_threshold=score_threshold,
        )

    def delete_document(
        self,
        document_id: str,
        user_id: str | None = None,
    ) -> None:
        if hasattr(self.vector_store, "delete_document"):
            self.vector_store.delete_document(document_id, user_id)

