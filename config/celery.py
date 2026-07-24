import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("studyease")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
from config.worker_health import WorkerHeartbeatStep  # noqa: E402
app.steps["worker"].add(WorkerHeartbeatStep)
