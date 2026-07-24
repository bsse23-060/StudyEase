import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from celery import bootsteps, signals
from django.conf import settings
from redis import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry
from prometheus_client import Gauge

WORKER_AVAILABLE = Gauge("studyease_document_worker_available", "Whether at least one document worker heartbeat is fresh")
WORKER_HEARTBEAT_AGE = Gauge("studyease_document_worker_heartbeat_age_seconds", "Age of the freshest document worker heartbeat")
_health_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="redis-health")
_health_future = None


def health_redis():
    return Redis.from_url(
        settings.CELERY_BROKER_URL,
        socket_connect_timeout=settings.HEALTH_REDIS_TIMEOUT_SECONDS,
        socket_timeout=settings.HEALTH_REDIS_TIMEOUT_SECONDS,
        retry_on_timeout=False,
        retry=Retry(NoBackoff(), 0),
        health_check_interval=0,
        decode_responses=True,
    )


def bounded_redis_ping():
    """Bound readiness even when Docker/service DNS resolution itself is slow."""
    global _health_future
    if _health_future is None or _health_future.done():
        _health_future = _health_executor.submit(lambda: bool(health_redis().ping()))
    try:
        return _health_future.result(timeout=settings.HEALTH_REDIS_TIMEOUT_SECONDS)
    except FutureTimeout:
        return False


def record_worker_heartbeat(hostname):
    if not hostname:
        return
    now = time.time()
    client = health_redis()
    key = f"studyease:worker-heartbeat:{hostname}"
    client.set(key, json.dumps({"last_seen": now, "queues": ["documents"]}), ex=settings.WORKER_HEARTBEAT_TTL_SECONDS)


def worker_status():
    now = time.time()
    workers = []
    client = health_redis()
    for key in client.scan_iter("studyease:worker-heartbeat:*", count=20):
        raw = client.get(key)
        if not raw:
            continue
        try:
            value = json.loads(raw)
            age = max(0.0, now - float(value["last_seen"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        workers.append({"age_seconds": round(age, 1), "queues": value.get("queues", [])})
    healthy = [worker for worker in workers if worker["age_seconds"] <= settings.WORKER_HEARTBEAT_STALE_SECONDS]
    WORKER_AVAILABLE.set(1 if healthy else 0)
    WORKER_HEARTBEAT_AGE.set(min((worker["age_seconds"] for worker in workers), default=float(settings.WORKER_HEARTBEAT_TTL_SECONDS)))
    return {"status": "ok" if healthy else "unavailable", "healthy_workers": len(healthy), "observed_workers": len(workers), "workers": workers}


@signals.heartbeat_sent.connect
def on_worker_heartbeat(sender=None, **_kwargs):
    try:
        record_worker_heartbeat(getattr(sender, "hostname", None))
    except Exception:
        # Monitoring must not terminate a worker when Redis is temporarily unavailable.
        return


class WorkerHeartbeatStep(bootsteps.StartStopStep):
    requires = {"celery.worker.components:Timer"}

    def start(self, worker):
        record_worker_heartbeat(worker.hostname)
        interval = max(2, min(10, settings.WORKER_HEARTBEAT_STALE_SECONDS // 3))
        self.timer = worker.timer.call_repeatedly(interval, record_worker_heartbeat, (worker.hostname,))

    def stop(self, _worker):
        if getattr(self, "timer", None):
            self.timer.cancel()
