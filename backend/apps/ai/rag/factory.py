from django.conf import settings

from apps.ai.rag.chunker import DocumentChunker
from apps.ai.rag.embeddings import HuggingFaceEmbeddingProvider
from apps.ai.rag.pipeline import RAGPipeline
from apps.ai.rag.retriever import Retriever
from apps.ai.rag.vector_store import QdrantVectorStore


def build_rag_pipeline() -> RAGPipeline:

    embedding_provider = HuggingFaceEmbeddingProvider(
        model_name=settings.RAG_EMBEDDING_MODEL,
        device=settings.RAG_EMBEDDING_DEVICE,
    )

    vector_size = (
        384
        if "bge-small" in settings.RAG_EMBEDDING_MODEL
        else 1024
    )

    vector_store = QdrantVectorStore(
        url=settings.QDRANT_URL,
        collection_name=settings.QDRANT_COLLECTION,
        vector_size=vector_size,
    )

    retriever = Retriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    return RAGPipeline(
        chunker=DocumentChunker(),
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        retriever=retriever,
    )