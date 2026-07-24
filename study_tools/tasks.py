from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import Document
from accounts.models import AuditEvent
from .services.malware import get_scanner
from .services.locking import document_lock
from .providers.base import ProviderRequestError
from .services.document_processing import process_document

@shared_task(bind=True, autoretry_for=(ConnectionError, TimeoutError, ProviderRequestError), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 3}, expires=1800)
def process_document_task(self, document_id: int, force=False, expected_version=None):
    document = Document.objects.filter(pk=document_id).first()
    if not document or document.deleted_at: return None
    expected_version = document.processing_version if expected_version is None else int(expected_version)
    if document.processing_version != expected_version: return document_id
    lock_key = f"document-processing:{document_id}:{expected_version}"
    with document_lock(lock_key, self.request.id or "eager", settings.DOCUMENT_LOCK_TIMEOUT) as acquired:
        if not acquired: return document_id
        document.refresh_from_db()
        if document.deleted_at or document.processing_version != expected_version: return document_id
        return process_document(document_id, force=force).pk

@shared_task(bind=True, autoretry_for=(ConnectionError, TimeoutError, OSError), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 4}, expires=1800)
def scan_document_task(self, document_id: int, expected_version=None):
    document = Document.objects.filter(pk=document_id, deleted_at__isnull=True).first()
    if not document or document.scan_status == Document.ScanStatus.CLEAN: return document_id if document else None
    expected_version = document.processing_version if expected_version is None else int(expected_version)
    if document.processing_version != expected_version: return document_id
    lock_key = f"document-scan:{document_id}:{expected_version}"
    with document_lock(lock_key, self.request.id or "eager", settings.DOCUMENT_LOCK_TIMEOUT) as acquired:
        if not acquired: return document_id
        document.refresh_from_db()
        if document.deleted_at or document.scan_status == Document.ScanStatus.CLEAN: return document_id
        Document.objects.filter(pk=document_id).update(scan_status=Document.ScanStatus.SCANNING)
        try:
            with document.file.open("rb") as uploaded: result = get_scanner().scan(uploaded)
        except Exception as exc:
            Document.objects.filter(pk=document_id, deleted_at__isnull=True).update(scan_status=Document.ScanStatus.UNAVAILABLE, scan_result="Scanner temporarily unavailable")
            AuditEvent.objects.create(actor=document.owner, action="document.scan_unavailable", target_type="document", target_id=str(document_id), metadata={"error_type": type(exc).__name__})
            raise
        updates = {"scan_status": result.status, "scan_provider": result.provider, "scanned_at": timezone.now(), "scan_result": result.detail}
        if result.status != Document.ScanStatus.CLEAN:
            updates.update(status=Document.Status.FAILED, quarantine_reason=result.detail)
        updated = Document.objects.filter(pk=document_id, deleted_at__isnull=True, processing_version=document.processing_version).update(**updates)
        if not updated: return document_id
        if result.status == Document.ScanStatus.CLEAN:
            process_document_task.delay(document_id, False, expected_version)
        else:
            AuditEvent.objects.create(actor=document.owner, action="document.quarantine", target_type="document", target_id=str(document_id), metadata={"scan_status": result.status, "provider": result.provider})
    return document_id
