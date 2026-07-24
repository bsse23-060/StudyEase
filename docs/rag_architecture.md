# RAG architecture

Conversation collections no longer embed histories. Detail is capped at 30 recent messages and `/conversations/{id}/history/` paginates older messages while preserving chronological presentation and authorised citation joins.

## Existing schema audit and changes

The audited `Document`, `DocumentChunk`, `Conversation`, `Message`, and relational `Citation` models were retained. The citation relationship was already suitable because every answer citation points to an exact chunk. Missing pieces were lifecycle metadata, safe upload facts, structural chunk metadata, embeddings/model versions, lesson scope, soft deletion/archive state, usage telemetry, server-owned processing, and retrieval-time authorization.

`study_tools/models.py` now gives `Document` the `uploaded -> queued -> processing -> ready|failed` lifecycle; visibility; course/lesson scope; original filename, detected MIME, byte size and SHA-256; error/timing/chunk/model/version fields; and `deleted_at`. `DocumentChunk` adds page/section/offset/count/checksum metadata, portable JSON embeddings, model/dimension/version, and `is_active`. Reprocessing creates a new active version and retains inactive cited chunks, so historical citations never break. `Conversation` adds lesson scope and archive state; messages have a soft deletion marker. `ProviderUsage` stores provider-neutral operation, tokens/characters, outcome, latency, and timestamp for monitoring or later quotas/billing. Migration `0003_providerusage_and_more.py` maps legacy statuses and preserves old rows.

Uploaded storage still uses Django's configured storage API. Local `MEDIA_ROOT` is appropriate only for development; production must use private object storage, encryption, malware scanning, signed downloads, retention policy, and backups.

## Service boundaries

- `services/document_extraction.py` accepts a stored document and returns `ExtractedBlock` values with text, page, heading, paragraph position, and filename. It raises `ExtractionError` for corrupt, unsupported, remote, or textless input. PDF uses pypdf and removes only repeated first/last lines; DOCX uses paragraph styles; text/Markdown requires UTF-8. OCR is deliberately not automatic.
- `services/chunking.py` accepts extracted blocks and configurable size/overlap/minimum values. It uses paragraph/sentence structure, avoids duplicate checksums, and returns offsets/counts/source metadata. The 1,200-character default is large enough for local meaning but small enough for focused retrieval; 150-character overlap reduces boundary loss at the cost of storage and near-duplicates.
- `services/embeddings.py` batches chunk text, validates exact dimensions, and records usage. It raises provider or dimension errors; it never writes model data itself.
- `services/vector_store.py` defines portable in-process cosine search for SQLite/tests and a PostgreSQL pgvector SQL backend. Portable JSON is intentionally less efficient; production uses PostgreSQL's `vector` extension and should add an expression HNSW index matching `RAG_VECTOR_DIMENSIONS`.
- `services/access.py` is the shared authorization query. Owners see private sources; enrolled students see ready published-course sources; instructors see their course sources; admins see all. This query is reused inside retrieval, not merely API lists.
- `services/retrieval.py` embeds the query, filters authorised/ready/active/model-compatible chunks first, ranks, removes near duplicates, enforces `top_k`, similarity, and a maximum context size, then returns scores and source metadata.
- `services/generation.py` calls the language-model abstraction, records usage, bounds output/excerpts, rejects fabricated chunk IDs, removes duplicate citations, and replaces non-verbatim excerpts with a safe server excerpt.
- `services/rag_pipeline.py` validates conversation ownership, limits ordered history, retrieves scoped context, generates, and transactionally persists user/assistant messages plus citations. Provider work is intentionally outside the database transaction.
- `tasks.py::process_document_task` delegates to `document_processing.py`, retries transient connection/provider failures with backoff, and is idempotent. The processor locks status transitions, versions reprocessing, replaces active chunks atomically, and records failures without leaving partial active data.

This separation makes extraction, providers, retrieval, and persistence independently testable. Putting them in a view would couple HTTP behavior to parsing/network/database work, make Celery reuse difficult, and hold request workers open.

## Provider abstraction

`providers/base.py` defines abstract `EmbeddingProvider` and `LanguageModelProvider` contracts plus structured context/citation/result dataclasses. Deterministic hash embeddings and a grounded fake language model make tests repeatable without network or paid calls. OpenAI implementations are the real configurable providers because its embeddings and structured JSON chat APIs are widely supported; keys/models come only from environment settings. Selecting OpenAI without `OPENAI_API_KEY` raises a clear configuration error.

The OpenAI system prompt says context is untrusted reference data, not instructions; answers must be context-grounded, disclose insufficient context, and cite IDs. XML-like source boundaries and JSON payload separation reduce accidental instruction mixing. Prompt injection cannot be fully solved: production should add content classification, human review for sensitive corpora, output policy checks, and provider-side safety controls.

Model changes require reprocessing because retrieval filters both embedding model and dimensions. Mixing incompatible vector spaces would yield meaningless similarity. `POST /documents/{id}/reprocess/` creates a new version while preserving citations to earlier versions.

## API and permissions

Document POST validates magic/container/text encoding rather than trusting extensions, maximum size, non-empty content, duplicate checksum, course/lesson consistency, and ownership. Supported types are extractable PDF, UTF-8 text/Markdown, and DOCX. Remote URL records remain compatible but are not fetched because unrestricted fetching creates SSRF risk.

Document actions are processing status, failed retry, reprocess, and instructor/admin retrieval preview. DELETE soft-deletes the database record, disables chunks, and removes the stored file. Chunks are read-only and visible only to owners, course instructors, and admins. Enrolled students use them only through retrieval.

Conversation actions include ordinary user messages, grounded `ask`, and archive. Question text is bounded/nonblank, optional document IDs must be authorised and match conversation scope, history is capped, and clients cannot create assistant messages/citations. RAG question and processing actions use per-user DRF throttles.

## Failure handling and asynchronous operation

Uploads become queued after save and dispatch only on transaction commit. Workers mark processing, then ready or failed with a bounded error. Invalid/corrupt/textless documents are permanent failures; transient provider/connectivity errors are retried three times. Duplicate ready tasks return without adding chunks. Force reprocessing increments a version.

Tests/local development use Celery eager mode and the fake providers. Production sets eager false and runs Redis plus Celery. Do not log API keys, JWTs, full documents, or complete prompts; `ProviderUsage` stores counts and error class names, not sensitive content.

## PostgreSQL/pgvector production note

Enable the extension and create an index whose dimension matches configuration, for example:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE INDEX chunk_embedding_hnsw ON study_tools_documentchunk
USING hnsw (((embedding::text)::vector(64)) vector_cosine_ops)
WHERE is_active = true AND embedding_dimensions = 64;
```

The database fallback performs Python cosine scans and is deliberately limited to development/small corpora. A future migration to a native `VectorField` is preferable once one embedding dimension is fixed organization-wide.

## Test coverage and limitations

`study_tools/test_rag.py` covers upload types/limits/duplicates, text/DOCX/PDF extraction behavior, corrupted files, chunk metadata/deduplication, dimension validation, idempotence/versioning, retries, retrieval isolation, failed/deleted exclusion, citations, fabricated IDs, insufficient context, injection-like source text, ownership, provider configuration, throttling, lifecycle actions, and schema rendering. Tests never call a real provider.

Remaining limitations: no OCR, antivirus, recursive archive extraction, URL ingestion, hybrid keyword ranking, reranker, distributed task lock, native pgvector model field, provider streaming, semantic cache, or automated sensitive-data redaction.
