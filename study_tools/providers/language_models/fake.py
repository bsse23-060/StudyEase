import re
from collections.abc import Sequence
from ..base import CitationResult, ContextChunk, GenerationResult, LanguageModelProvider

class DeterministicLanguageModelProvider(LanguageModelProvider):
    name = "fake"
    model = "deterministic-grounded-v1"
    def generate_answer(self, question: str, context_chunks: Sequence[ContextChunk], conversation_history: Sequence[dict[str, str]]) -> GenerationResult:
        terms = {word for word in re.findall(r"\w+", question.casefold()) if len(word) > 2}
        supported = [chunk for chunk in context_chunks if terms & set(re.findall(r"\w+", chunk.text.casefold()))]
        if not supported:
            return GenerationResult(answer="I could not find enough information in the authorised sources to answer that question.", has_sufficient_context=False)
        chunk = supported[0]; excerpt = chunk.text[:240]
        return GenerationResult(answer=f"Based on the supplied source: {excerpt}", citations=[CitationResult(chunk.id, excerpt)], has_sufficient_context=True, input_tokens=sum(len(c.text.split()) for c in context_chunks), output_tokens=len(excerpt.split()))
