"""Local embedding abstractions for the RAG foundation.

``DeterministicEmbeddingProvider`` is a development/test hash embedding.  It
is not a semantic embedding model and must not be treated as one.
"""

import hashlib
import math
import re
from typing import Protocol

from sentence_transformers import SentenceTransformer


class EmbeddingProvider(Protocol):

    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        ...


class HuggingFaceEmbeddingProvider:
    """Sentence-Transformers embedding provider with lazy model loading."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.device = device
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )

        return self._model

    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
        )

        return embeddings.tolist()

class DeterministicEmbeddingProvider:
    """A fixed-size, local hash/token embedding for development and tests."""

    def __init__(self, dimension: int = 64):
        if dimension <= 0:
            raise ValueError("dimension must be greater than zero.")

        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension

        for token in re.findall(r"\w+", text.casefold()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            direction = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += direction

        magnitude = math.sqrt(sum(value * value for value in vector))

        if magnitude:
            return [value / magnitude for value in vector]

        return vector
