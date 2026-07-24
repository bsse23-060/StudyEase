from dataclasses import dataclass
import time
from django.conf import settings
from study_tools.models import Document, DocumentChunk, ProviderUsage
from study_tools.providers import get_embedding_provider
from study_tools.providers.base import ContextChunk
from .access import authorised_documents
from .vector_store import get_vector_backend

@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[ContextChunk]
    query: str

def _near_duplicate(text, selected):
    words = set(text.casefold().split())
    return any(len(words & other) / max(1, len(words | other)) > .9 for other in selected)

def retrieve_chunks(user, query: str, *, course=None, lesson=None, document_ids=None, top_k=None, max_context_chars=None) -> RetrievalResult:
    top_k = min(top_k or settings.RAG_RETRIEVAL_TOP_K, settings.RAG_MAX_TOP_K)
    max_context_chars = max_context_chars or settings.RAG_MAX_CONTEXT_CHARACTERS
    documents = authorised_documents(user).filter(status=Document.Status.READY)
    if course: documents = documents.filter(course=course)
    if lesson: documents = documents.filter(lesson=lesson)
    if document_ids: documents = documents.filter(id__in=document_ids)
    provider = get_embedding_provider(); started = time.perf_counter()
    try: query_vector = provider.embed_query(query)
    except Exception as exc:
        ProviderUsage.objects.create(user=user, provider=provider.name, model=provider.model, operation=ProviderUsage.Operation.EMBEDDING, input_characters=len(query), success=False, latency_ms=int((time.perf_counter()-started)*1000), error_code=exc.__class__.__name__); raise
    ProviderUsage.objects.create(user=user, provider=provider.name, model=provider.model, operation=ProviderUsage.Operation.EMBEDDING, input_characters=len(query), success=True, latency_ms=int((time.perf_counter()-started)*1000))
    if len(query_vector) != provider.dimensions: raise ValueError("Query embedding has unexpected dimensions.")
    chunks = DocumentChunk.objects.filter(document__in=documents, is_active=True, embedding_model=provider.model, embedding_dimensions=provider.dimensions).select_related("document")
    ranked = get_vector_backend().search(chunks, query_vector, top_k * 3)
    selected = []; selected_word_sets = []; total = 0
    for chunk, score in ranked:
        if score < settings.RAG_MIN_SIMILARITY or _near_duplicate(chunk.text, selected_word_sets): continue
        if total + len(chunk.text) > max_context_chars: continue
        selected.append(ContextChunk(chunk.id, chunk.text, chunk.document.title, chunk.page, chunk.section_title, score)); selected_word_sets.append(set(chunk.text.casefold().split())); total += len(chunk.text)
        if len(selected) >= top_k: break
    return RetrievalResult(selected, query)
