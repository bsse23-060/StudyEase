from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings

from study_tools.models import Document, DocumentChunk
from study_tools.services.vector_store import PgvectorBackend


@override_settings(RAG_VECTOR_BACKEND="pgvector", RAG_VECTOR_DIMENSIONS=1536)
class PgvectorIntegrationTests(TestCase):
    def test_pgvector_orders_1536_dimension_embeddings(self):
        if connection.vendor != "postgresql":
            self.skipTest("The pgvector integration requires PostgreSQL.")

        user = get_user_model().objects.create_user(
            email="pgvector@test.local",
            password="LongPassword123!",
            full_name="Pgvector Test",
        )
        document = Document.objects.create(owner=user, title="Vector fixture")
        first = [0.0] * 1536
        first[0] = 1.0
        second = [0.0] * 1536
        second[1] = 1.0
        expected = DocumentChunk.objects.create(
            document=document,
            text="Closest",
            position=0,
            embedding=first,
            embedding_vector=first,
            embedding_dimensions=1536,
        )
        DocumentChunk.objects.create(
            document=document,
            text="Farther",
            position=1,
            embedding=second,
            embedding_vector=second,
            embedding_dimensions=1536,
        )

        results = PgvectorBackend().search(
            DocumentChunk.objects.filter(document=document),
            first,
            2,
        )

        self.assertEqual(results[0][0].pk, expected.pk)
        self.assertGreater(results[0][1], results[1][1])
