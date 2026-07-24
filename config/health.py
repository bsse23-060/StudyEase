from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse, HttpResponse
from django.db.migrations.executor import MigrationExecutor
from django.core.files.storage import default_storage
from rest_framework.permissions import IsAdminUser
from rest_framework import serializers
from rest_framework.views import APIView
from .worker_health import bounded_redis_ping, worker_status

def live(_request): return JsonResponse({"status": "ok", "service": "api"})

def ready(_request):
    checks, ok = {}, True
    try:
        with connection.cursor() as cursor: cursor.execute("SELECT 1"); cursor.fetchone()
        checks["database"] = "ok"
        pending = MigrationExecutor(connection).migration_plan(MigrationExecutor(connection).loader.graph.leaf_nodes())
        checks["migrations"] = "pending" if pending else "ok"; ok = ok and not pending
    except Exception:
        checks["database"] = "unavailable"; ok = False
    if settings.HEALTH_REQUIRE_REDIS:
        try: checks["redis"] = "ok" if bounded_redis_ping() else "unavailable"
        except Exception: checks["redis"] = "unavailable"
        ok = ok and checks["redis"] == "ok"
    try:
        default_storage.exists("healthchecks/nonexistent"); checks["storage"] = "ok"
    except Exception: checks["storage"] = "unavailable"; ok = False
    return JsonResponse({"status": "ok" if ok else "not_ready", "checks": checks}, status=200 if ok else 503)

class AdministrativeHealthSerializer(serializers.Serializer):
    status = serializers.CharField(); providers = serializers.DictField(); vector = serializers.DictField(); workers = serializers.DictField()

class DetailedHealthView(APIView):
    permission_classes = (IsAdminUser,)
    serializer_class = AdministrativeHealthSerializer
    def get(self, request):
        try: workers = worker_status()
        except Exception: workers = {"status": "unavailable", "healthy_workers": 0, "observed_workers": 0, "workers": []}
        payload = {"status": "ok" if workers["status"] == "ok" else "degraded", "providers": {"embedding": settings.RAG_EMBEDDING_PROVIDER, "language_model": settings.RAG_LANGUAGE_MODEL_PROVIDER, "malware_scanner": settings.MALWARE_SCANNER}, "vector": {"backend": settings.RAG_VECTOR_BACKEND, "dimensions": settings.RAG_VECTOR_DIMENSIONS}, "workers": workers}
        return JsonResponse(payload)

def metrics(request):
    token = settings.METRICS_TOKEN
    if not token or request.headers.get("Authorization") != f"Bearer {token}": return HttpResponse(status=404)
    from django_prometheus.exports import ExportToDjangoView
    return ExportToDjangoView(request)
