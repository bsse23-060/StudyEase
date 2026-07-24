import math
from django.conf import settings
from django.db import connection
from pgvector.django import CosineDistance
from study_tools.models import DocumentChunk

class VectorBackendConfigurationError(RuntimeError): pass

def cosine_similarity(left, right):
    if len(left) != len(right): return -1.0
    denominator = math.sqrt(sum(x*x for x in left)) * math.sqrt(sum(x*x for x in right))
    return sum(x*y for x, y in zip(left, right)) / denominator if denominator else 0.0

class DatabaseVectorBackend:
    name = "database"
    def search(self, queryset, query_vector, limit):
        scored = [(chunk, cosine_similarity(query_vector, chunk.embedding)) for chunk in queryset.iterator() if chunk.embedding and chunk.embedding_dimensions == len(query_vector)]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]

class PgvectorBackend:
    name = "pgvector"
    def search(self, queryset, query_vector, limit):
        if connection.vendor != "postgresql": raise VectorBackendConfigurationError("The pgvector backend requires PostgreSQL and the vector extension.")
        if len(query_vector) != 1536: raise VectorBackendConfigurationError("The production pgvector index requires 1536-dimensional embeddings.")
        rows = list(queryset.filter(embedding_vector__isnull=False).annotate(distance=CosineDistance("embedding_vector", query_vector)).order_by("distance")[:limit])
        return [(chunk, 1.0 - float(chunk.distance)) for chunk in rows]

def get_vector_backend():
    if settings.RAG_VECTOR_BACKEND == "database": return DatabaseVectorBackend()
    if settings.RAG_VECTOR_BACKEND == "pgvector": return PgvectorBackend()
    raise VectorBackendConfigurationError(f"Unsupported vector backend: {settings.RAG_VECTOR_BACKEND}")
