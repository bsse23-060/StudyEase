from django.db import migrations
from pgvector.django import HnswIndex, VectorExtension, VectorField

def create_hnsw(_apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("CREATE INDEX chunk_embedding_hnsw ON study_tools_documentchunk USING hnsw (embedding_vector vector_cosine_ops) WITH (m = 16, ef_construction = 64)")

def drop_hnsw(_apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql": schema_editor.execute("DROP INDEX IF EXISTS chunk_embedding_hnsw")

class Migration(migrations.Migration):
    dependencies = [("study_tools", "0006_document_quarantine_reason_document_scan_provider_and_more")]
    operations = [
        VectorExtension(),
        migrations.AddField(model_name="documentchunk", name="embedding_vector", field=VectorField(blank=True, dimensions=1536, null=True)),
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(create_hnsw, drop_hnsw)],
            state_operations=[migrations.AddIndex(model_name="documentchunk", index=HnswIndex(name="chunk_embedding_hnsw", fields=["embedding_vector"], m=16, ef_construction=64, opclasses=["vector_cosine_ops"]))],
        ),
    ]
