from contextlib import contextmanager
from django.core.cache import cache

@contextmanager
def document_lock(key, owner, timeout):
    backend = getattr(cache, "_cache", None)
    if hasattr(backend, "get_client"):
        lock = backend.get_client(write=True).lock(key, timeout=timeout, blocking=False, thread_local=False)
        acquired = lock.acquire(blocking=False)
        try: yield acquired
        finally:
            if acquired:
                try: lock.release()
                except Exception: pass  # Expired/not-owned locks must never delete a newer owner's lock.
        return
    acquired = cache.add(key, owner, timeout=timeout)
    try: yield acquired
    finally:
        if acquired and cache.get(key) == owner: cache.delete(key)
