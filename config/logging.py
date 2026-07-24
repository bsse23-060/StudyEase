import logging
import re
from django.conf import settings

SENSITIVE = re.compile(r"(authorization|cookie|password|secret|token|api[_-]?key)(\s*[=:]\s*)([^\s,;]+)", re.I)

def redact(value):
    return SENSITIVE.sub(r"\1\2[REDACTED]", str(value))

class SafeContextFilter(logging.Filter):
    def filter(self, record):
        record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(redact(v) for v in record.args) if isinstance(record.args, tuple) else record.args
        record.service = getattr(settings, "SERVICE_NAME", "studyease-api")
        record.environment = getattr(settings, "ENVIRONMENT", "development")
        record.request_id = getattr(record, "request_id", "-")
        return True
