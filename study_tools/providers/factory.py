from django.conf import settings
from .base import ProviderConfigurationError
from .embeddings.fake import DeterministicEmbeddingProvider
from .embeddings.openai import OpenAIEmbeddingProvider
from .language_models.fake import DeterministicLanguageModelProvider
from .language_models.openai import OpenAILanguageModelProvider

def get_embedding_provider():
    if settings.RAG_EMBEDDING_PROVIDER == "fake": return DeterministicEmbeddingProvider(settings.RAG_VECTOR_DIMENSIONS)
    if settings.RAG_EMBEDDING_PROVIDER == "openai": return OpenAIEmbeddingProvider(settings.OPENAI_API_KEY, settings.RAG_EMBEDDING_MODEL, settings.RAG_VECTOR_DIMENSIONS)
    raise ProviderConfigurationError(f"Unsupported embedding provider: {settings.RAG_EMBEDDING_PROVIDER}")

def get_language_model_provider():
    if settings.RAG_LANGUAGE_MODEL_PROVIDER == "fake": return DeterministicLanguageModelProvider()
    if settings.RAG_LANGUAGE_MODEL_PROVIDER == "openai": return OpenAILanguageModelProvider(settings.OPENAI_API_KEY, settings.RAG_LANGUAGE_MODEL)
    raise ProviderConfigurationError(f"Unsupported language-model provider: {settings.RAG_LANGUAGE_MODEL_PROVIDER}")
