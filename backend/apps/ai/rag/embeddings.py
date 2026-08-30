"""Local embedding abstractions for the RAG foundation.

``DeterministicEmbeddingProvider`` is a development/test hash embedding.  It
is not a semantic embedding model and must not be treated as one.
"""

import hashlib
import math
import re
from typing import Protocol


class EmbeddingProvider(Protocol):
    """Convert a batch of texts into equally sized numeric vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed the supplied texts."""


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
