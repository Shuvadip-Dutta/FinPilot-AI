"""Deterministic text chunking for unstructured documents."""

from apps.ai.rag.schemas import DocumentChunk


class DocumentChunker:
    """Split text into overlapping, character-preserving chunks."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")

        if overlap < 0:
            raise ValueError("overlap must not be negative.")

        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size.")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self,
        document_id: str,
        text: str,
        metadata: dict[str, object] | None = None,
    ) -> list[DocumentChunk]:
        """Return stable sequential chunks without modifying source text."""
        if not document_id.strip():
            raise ValueError("document_id must not be empty.")

        if not text.strip():
            raise ValueError("text must not be empty.")

        chunk_metadata = dict(metadata or {})
        step = self.chunk_size - self.overlap
        chunks: list[DocumentChunk] = []

        for index, start in enumerate(range(0, len(text), step)):
            chunk_text = text[start : start + self.chunk_size]

            if not chunk_text:
                continue

            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    chunk_id=f"{document_id}:{index}",
                    text=chunk_text,
                    metadata=dict(chunk_metadata),
                )
            )

            if start + self.chunk_size >= len(text):
                break

        return chunks
