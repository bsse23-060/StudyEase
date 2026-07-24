import time
from study_tools.models import ProviderUsage
from study_tools.providers import get_embedding_provider

class EmbeddingDimensionError(ValueError): pass

def embed_chunks(chunks, user):
    provider = get_embedding_provider(); texts = [chunk.text for chunk in chunks]; started = time.perf_counter()
    try:
        vectors = provider.embed_texts(texts)
        if len(vectors) != len(texts) or any(len(vector) != provider.dimensions for vector in vectors): raise EmbeddingDimensionError(f"Expected {provider.dimensions}-dimensional embeddings.")
    except Exception as exc:
        ProviderUsage.objects.create(user=user, provider=provider.name, model=provider.model, operation=ProviderUsage.Operation.EMBEDDING, input_characters=sum(map(len, texts)), success=False, latency_ms=int((time.perf_counter()-started)*1000), error_code=exc.__class__.__name__)
        raise
    ProviderUsage.objects.create(user=user, provider=provider.name, model=provider.model, operation=ProviderUsage.Operation.EMBEDDING, input_characters=sum(map(len, texts)), success=True, latency_ms=int((time.perf_counter()-started)*1000))
    return provider, vectors
