import time
from study_tools.models import ProviderUsage
from study_tools.providers import get_language_model_provider
from study_tools.providers.base import CitationResult, GenerationResult

class InvalidGenerationError(ValueError): pass

def generate_grounded_answer(user, question, context_chunks, history):
    provider = get_language_model_provider(); started = time.perf_counter()
    try:
        result = provider.generate_answer(question, context_chunks, history)
        if not result.answer.strip(): result = GenerationResult("I could not produce a safe grounded answer from the available context.", [], False)
        allowed = {chunk.id: chunk for chunk in context_chunks}; citations = []; seen = set()
        for citation in result.citations:
            if citation.chunk_id not in allowed: raise InvalidGenerationError("The model cited a chunk that was not supplied as context.")
            if citation.chunk_id in seen: continue
            excerpt = citation.supporting_text.strip()[:300]
            if excerpt and excerpt not in allowed[citation.chunk_id].text: excerpt = allowed[citation.chunk_id].text[:240]
            citations.append(CitationResult(citation.chunk_id, excerpt)); seen.add(citation.chunk_id)
        result = GenerationResult(result.answer[:12000], citations, result.has_sufficient_context, result.input_tokens, result.output_tokens)
    except Exception as exc:
        ProviderUsage.objects.create(user=user, provider=provider.name, model=provider.model, operation=ProviderUsage.Operation.GENERATION, success=False, latency_ms=int((time.perf_counter()-started)*1000), error_code=exc.__class__.__name__)
        raise
    ProviderUsage.objects.create(user=user, provider=provider.name, model=provider.model, operation=ProviderUsage.Operation.GENERATION, input_tokens=result.input_tokens, output_tokens=result.output_tokens, input_characters=len(question)+sum(len(c.text) for c in context_chunks), success=True, latency_ms=int((time.perf_counter()-started)*1000))
    return result
