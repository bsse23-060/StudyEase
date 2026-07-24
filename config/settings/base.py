from datetime import timedelta
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parents[2]

def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}

def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me-use-at-least-32-bytes-in-production")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")

INSTALLED_APPS = [
    "django_prometheus", "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "rest_framework_simplejwt.token_blacklist", "django_filters", "drf_spectacular",
    "corsheaders", "accounts", "courses", "learning", "study_tools",
]
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware", "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", "corsheaders.middleware.CorsMiddleware",
    "config.middleware.RequestContextMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware", "django_prometheus.middleware.PrometheusAfterMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=int(os.environ.get("DATABASE_CONN_MAX_AGE", "0")), conn_health_checks=True)}
CACHE_URL = os.environ.get("CACHE_URL", "")
if CACHE_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": CACHE_URL, "TIMEOUT": 300}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE, TIME_ZONE, USE_I18N, USE_TZ = "en-us", "UTC", True, True
STATIC_URL, STATIC_ROOT = "/static/", BASE_DIR / "staticfiles"
STORAGES = {"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}, "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}}
MEDIA_ROOT, MEDIA_URL = BASE_DIR / "media", "/media/"
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL") or None
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")
AWS_S3_ADDRESSING_STYLE = os.environ.get("AWS_S3_ADDRESSING_STYLE", "path" if AWS_S3_ENDPOINT_URL else "auto")
AWS_QUERYSTRING_EXPIRE = int(os.environ.get("AWS_QUERYSTRING_EXPIRE", "300"))
if AWS_STORAGE_BUCKET_NAME:
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage", "OPTIONS": {"bucket_name": AWS_STORAGE_BUCKET_NAME, "default_acl": None, "querystring_auth": True, "querystring_expire": AWS_QUERYSTRING_EXPIRE, "file_overwrite": False}}
DEFAULT_AUTO_FIELD, AUTH_USER_MODEL = "django.db.models.BigAutoField", "accounts.User"
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get("DATA_UPLOAD_MAX_MEMORY_SIZE", str(12 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get("FILE_UPLOAD_MAX_MEMORY_SIZE", str(2 * 1024 * 1024)))
CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend", "rest_framework.filters.SearchFilter", "rest_framework.filters.OrderingFilter"),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination", "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "auth": os.environ.get("AUTH_RATE", "10/minute"), "registration": os.environ.get("REGISTRATION_RATE", "5/hour"),
        "rag_question": os.environ.get("RAG_QUESTION_RATE", "20/hour"), "rag_processing": os.environ.get("RAG_PROCESSING_RATE", "30/hour"),
        "upload": os.environ.get("UPLOAD_RATE", "20/hour"), "quiz_submission": os.environ.get("QUIZ_SUBMISSION_RATE", "60/hour"),
    },
}
SIMPLE_JWT = {"ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "15"))), "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", "7"))), "ROTATE_REFRESH_TOKENS": True, "BLACKLIST_AFTER_ROTATION": True, "UPDATE_LAST_LOGIN": True}
SPECTACULAR_SETTINGS = {"TITLE": "studyEase API", "VERSION": "1.0.0"}

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost"); EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", ""); EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS"); DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "studyEase <noreply@localhost>")

RAG_EMBEDDING_PROVIDER = os.environ.get("RAG_EMBEDDING_PROVIDER", "fake").lower(); RAG_LANGUAGE_MODEL_PROVIDER = os.environ.get("RAG_LANGUAGE_MODEL_PROVIDER", "fake").lower()
RAG_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "text-embedding-3-small"); RAG_LANGUAGE_MODEL = os.environ.get("RAG_LANGUAGE_MODEL", "gpt-4.1-mini")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", ""); RAG_VECTOR_BACKEND = os.environ.get("RAG_VECTOR_BACKEND", "database").lower()
RAG_VECTOR_DIMENSIONS = int(os.environ.get("RAG_VECTOR_DIMENSIONS", "64")); RAG_CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "1200")); RAG_CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "150")); RAG_MIN_CHUNK_SIZE = int(os.environ.get("RAG_MIN_CHUNK_SIZE", "80"))
RAG_RETRIEVAL_TOP_K = int(os.environ.get("RAG_RETRIEVAL_TOP_K", "5")); RAG_MAX_TOP_K = int(os.environ.get("RAG_MAX_TOP_K", "10")); RAG_MAX_CONTEXT_CHARACTERS = int(os.environ.get("RAG_MAX_CONTEXT_CHARACTERS", "12000")); RAG_MIN_SIMILARITY = float(os.environ.get("RAG_MIN_SIMILARITY", "-1")); RAG_HISTORY_MESSAGE_LIMIT = int(os.environ.get("RAG_HISTORY_MESSAGE_LIMIT", "12")); RAG_MAX_DOCUMENT_BYTES = int(os.environ.get("RAG_MAX_DOCUMENT_BYTES", str(10 * 1024 * 1024)))
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0"); CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", True); CELERY_TASK_EAGER_PROPAGATES = False; CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ACKS_LATE = True; CELERY_TASK_REJECT_ON_WORKER_LOST = True; CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "840")); CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "900"))
CELERY_TASK_ROUTES = {"study_tools.tasks.scan_document_task": {"queue": "documents"}, "study_tools.tasks.process_document_task": {"queue": "documents"}}
CELERY_TASK_DEFAULT_QUEUE = "default"; CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
DOCUMENT_LOCK_TIMEOUT = int(os.environ.get("DOCUMENT_LOCK_TIMEOUT", "1200")); MALWARE_SCANNER = os.environ.get("MALWARE_SCANNER", "fake")
CLAMAV_HOST = os.environ.get("CLAMAV_HOST", "clamav"); CLAMAV_PORT = int(os.environ.get("CLAMAV_PORT", "3310"))
CLAMAV_TIMEOUT_SECONDS = float(os.environ.get("CLAMAV_TIMEOUT_SECONDS", "10"))
HEALTH_REQUIRE_REDIS = env_bool("HEALTH_REQUIRE_REDIS", False); METRICS_TOKEN = os.environ.get("METRICS_TOKEN", "")
HEALTH_REDIS_TIMEOUT_SECONDS = float(os.environ.get("HEALTH_REDIS_TIMEOUT_SECONDS", "0.5"))
WORKER_HEARTBEAT_STALE_SECONDS = int(os.environ.get("WORKER_HEARTBEAT_STALE_SECONDS", "15"))
WORKER_HEARTBEAT_TTL_SECONDS = int(os.environ.get("WORKER_HEARTBEAT_TTL_SECONDS", "45"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO"); SERVICE_NAME = os.environ.get("SERVICE_NAME", "studyease-api"); ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
LOGGING = {"version": 1, "disable_existing_loggers": False, "filters": {"context": {"()": "config.logging.SafeContextFilter"}}, "formatters": {"json": {"()": "pythonjsonlogger.json.JsonFormatter", "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(service)s %(environment)s %(request_id)s"}, "plain": {"format": "%(levelname)s %(name)s %(message)s"}}, "handlers": {"console": {"class": "logging.StreamHandler", "filters": ["context"], "formatter": "plain"}}, "root": {"handlers": ["console"], "level": LOG_LEVEL}}
