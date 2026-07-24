import logging
import time
import uuid

logger = logging.getLogger("studyease.request")

class RequestContextMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID", "")[:128] or str(uuid.uuid4())
        started = time.monotonic()
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        if response.status_code == 403 and getattr(getattr(request, "user", None), "is_authenticated", False) and request.path.startswith("/api/"):
            try:
                from accounts.models import AuditEvent
                AuditEvent.objects.create(actor=request.user, action="permission.denied", target_type="endpoint", target_id=request.path[:64], request_id=request.request_id, metadata={"method": request.method})
            except Exception:
                logger.exception("audit_event_write_failed", extra={"request_id": request.request_id})
        logger.info("request_complete method=%s path=%s status=%s duration_ms=%s user_id=%s", request.method, request.path, response.status_code, round((time.monotonic()-started)*1000), getattr(getattr(request, "user", None), "pk", None), extra={"request_id": request.request_id})
        return response
