from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence

class ProviderConfigurationError(RuntimeError): pass
class ProviderRequestError(RuntimeError): pass

@dataclass(frozen=True)
class ContextChunk:
    id: int
    text: str
    document_title: str
    page: int | None = None
    section_title: str = ""
    score: float = 0.0

@dataclass(frozen=True)
class CitationResult:
    chunk_id: int
    supporting_text: str

@dataclass(frozen=True)
class GenerationResult:
    answer: str
    citations: list[CitationResult] = field(default_factory=list)
    has_sufficient_context: bool = False
    input_tokens: int = 0
    output_tokens: int = 0

class EmbeddingProvider(ABC):
    name: str
    model: str
    dimensions: int
    @abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: raise NotImplementedError
    def embed_query(self, text: str) -> list[float]: return self.embed_texts([text])[0]

class LanguageModelProvider(ABC):
    name: str
    model: str
    @abstractmethod
    def generate_answer(self, question: str, context_chunks: Sequence[ContextChunk], conversation_history: Sequence[dict[str, str]]) -> GenerationResult: raise NotImplementedError
