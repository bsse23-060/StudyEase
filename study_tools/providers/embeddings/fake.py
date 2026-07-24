import hashlib
import math
import re
from collections.abc import Sequence
from ..base import EmbeddingProvider

class DeterministicEmbeddingProvider(EmbeddingProvider):
    name = "fake"
    model = "deterministic-hash-v1"
    def __init__(self, dimensions: int = 64): self.dimensions = dimensions
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]
    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[\w'-]+", text.casefold()):
            digest = hashlib.sha256(token.encode()).digest(); index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += -1.0 if digest[4] & 1 else 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
