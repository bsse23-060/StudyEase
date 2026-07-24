from collections.abc import Sequence
from openai import OpenAI
from ..base import EmbeddingProvider, ProviderConfigurationError, ProviderRequestError

class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"
    def __init__(self, api_key: str, model: str, dimensions: int):
        if not api_key: raise ProviderConfigurationError("OPENAI_API_KEY is required for the OpenAI embedding provider.")
        self.model = model; self.dimensions = dimensions; self.client = OpenAI(api_key=api_key)
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            response = self.client.embeddings.create(model=self.model, input=list(texts), dimensions=self.dimensions)
            vectors = [item.embedding for item in response.data]
        except Exception as exc: raise ProviderRequestError("Embedding provider request failed.") from exc
        if len(vectors) != len(texts) or any(len(vector) != self.dimensions for vector in vectors): raise ProviderRequestError("Embedding provider returned unexpected dimensions.")
        return vectors
