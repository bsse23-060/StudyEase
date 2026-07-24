# Storage and ClamAV release-gate validation

## MinIO

- Bucket policy is private and object keys are UUID-derived rather than direct filenames.
- Owner download succeeded; cross-user, unauthenticated, quarantined and deleted-document requests were denied by the API/queryset.
- A five-second URL succeeded before expiry and returned 403 after seven seconds.
- An issued URL succeeded before deletion; document deletion removed the object, new link generation returned 404, and the issued URL then returned object-store 404.
- Reprocessing read the private source object and changed processing version without returning a public URL.
- Missing objects fail at storage access and are never converted to public paths.
- Three objects were mirrored with preserved metadata, SHA-256 verified, restored 3-for-3 into a separate private bucket, and inventoried successfully.

An already-issued URL normally remains usable until its short expiry. Object deletion invalidated it immediately in this implementation. Restoring the same key before expiry could make it usable again, which is why restores must target an isolated bucket before cutover.

## ClamAV

- Clean text and document processing passed live.
- The harmless EICAR antivirus test pattern was marked infected, quarantined, never chunked, audited, and denied download.
- With the scanner stopped, Docker DNS failure was exercised live. Five bounded Celery attempts ended `scan_status=unavailable`; the file remained uploaded/unprocessed and five safe `document.scan_unavailable` audit records contained only exception types.
- After scanner health recovered, explicit retry progressed the same document to clean/ready with one chunk.
- Socket timeout, malformed response, and unexpected close are automated in `study_tools/test_release_gates.py`; malformed/empty responses become suspicious and never clean.
- The socket connect/read timeout is configurable through `CLAMAV_TIMEOUT_SECONDS`.
- Deletion filters prevent a waiting scan from updating or processing a deleted document.

Connection-refused and DNS-unavailable outcomes share the bounded retry path. A separate live fake TCP server that accepts and never responds was not run; the protocol-level timeout test covers that branch without real malware or paid calls.
