from django.conf import settings
from django.db import transaction
from django.utils import timezone
from study_tools.models import Document, DocumentChunk
from .chunking import chunk_blocks
from .document_extraction import extract_document
from .embeddings import embed_chunks

def process_document(document_id: int, *, force=False):
    with transaction.atomic():
        document = Document.objects.select_for_update().select_related("owner").get(pk=document_id)
        if document.deleted_at: return document
        if document.file and document.scan_status != Document.ScanStatus.CLEAN: raise PermissionError("Document processing requires a clean malware scan.")
        if document.status == Document.Status.READY and not force: return document
        if document.status == Document.Status.PROCESSING and not force: return document
        document.status = Document.Status.PROCESSING; document.processing_error = ""; document.processing_started_at = timezone.now()
        if force: document.processing_version += 1
        document.save(update_fields=("status", "processing_error", "processing_started_at", "processing_version", "updated_at"))
        expected_version = document.processing_version
    try:
        blocks = extract_document(document)
        chunks = chunk_blocks(blocks, settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP, settings.RAG_MIN_CHUNK_SIZE)
        provider, vectors = embed_chunks(chunks, document.owner)
        with transaction.atomic():
            locked = Document.objects.select_for_update().get(pk=document_id)
            if locked.deleted_at: return locked
            if locked.processing_version != expected_version: return locked
            DocumentChunk.objects.filter(document=locked, is_active=True).update(is_active=False)
            DocumentChunk.objects.bulk_create([DocumentChunk(document=locked, text=data.text, position=data.position, page=data.page, section_title=data.section_title, start_position=data.start_position, end_position=data.end_position, character_count=data.character_count, token_count=data.token_count, content_checksum=data.content_checksum, metadata=data.metadata, embedding=vector, embedding_vector=vector if len(vector) == 1536 else None, embedding_model=provider.model, embedding_dimensions=provider.dimensions, processing_version=locked.processing_version) for data, vector in zip(chunks, vectors)])
            locked.status = Document.Status.READY; locked.processed_at = timezone.now(); locked.processing_error = ""; locked.chunk_count = len(chunks); locked.embedding_provider = provider.name; locked.embedding_model = provider.model; locked.embedding_dimensions = provider.dimensions
            locked.save(update_fields=("status", "processed_at", "processing_error", "chunk_count", "embedding_provider", "embedding_model", "embedding_dimensions", "updated_at"))
            return locked
    except Exception as exc:
        Document.objects.filter(pk=document_id, deleted_at__isnull=True, processing_version=expected_version).update(status=Document.Status.FAILED, processing_error=str(exc)[:2000])
        raise
