"""Typed RAG document and retrieval contracts."""

from pydantic import BaseModel, field_validator


class DocumentChunk(BaseModel):
    """A stable portion of an unstructured source document."""

    document_id: str
    chunk_id: str
    text: str
    metadata: dict[str, object]

    @field_validator("document_id", "chunk_id", "text")
    @classmethod
    def value_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be empty.")

        return value


class RetrievalResult(BaseModel):
    """A chunk returned by similarity search and its cosine score."""

    chunk: DocumentChunk
    score: float
