import os
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403

DEBUG = False
required = [name for name in ("DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "DATABASE_URL", "DJANGO_CSRF_TRUSTED_ORIGINS", "AWS_STORAGE_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY") if not os.environ.get(name)]
if required:
    raise ImproperlyConfigured("Missing required production settings: " + ", ".join(required))
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("dev-"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be a random value of at least 50 characters.")
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production DATABASE_URL must use PostgreSQL.")
if RAG_EMBEDDING_PROVIDER != "fake" and not OPENAI_API_KEY:
    raise ImproperlyConfigured("OPENAI_API_KEY is required for the configured production embedding provider.")
if RAG_VECTOR_BACKEND == "pgvector" and RAG_VECTOR_DIMENSIONS != 1536:
    raise ImproperlyConfigured("The pgvector HNSW index requires RAG_VECTOR_DIMENSIONS=1536.")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True; SESSION_COOKIE_SECURE = True; CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True; SESSION_COOKIE_SAMESITE = "Lax"; CSRF_COOKIE_HTTPONLY = True; CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "3600")); SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False); SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True; SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"; X_FRAME_OPTIONS = "DENY"
USE_X_FORWARDED_HOST = True
CELERY_TASK_ALWAYS_EAGER = False
CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": os.environ.get("CACHE_URL", CELERY_BROKER_URL), "TIMEOUT": 300}}
HEALTH_REQUIRE_REDIS = True
LOGGING["handlers"]["console"]["formatter"] = "json"
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN, environment=ENVIRONMENT, send_default_pii=False, traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.05")))
if os.environ.get("AWS_STORAGE_BUCKET_NAME"):
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage", "OPTIONS": {"bucket_name": os.environ["AWS_STORAGE_BUCKET_NAME"], "default_acl": None, "querystring_auth": True, "querystring_expire": int(os.environ.get("AWS_QUERYSTRING_EXPIRE", "300")), "file_overwrite": False}}
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL") or None
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")
AWS_S3_ADDRESSING_STYLE = os.environ.get("AWS_S3_ADDRESSING_STYLE", "path" if AWS_S3_ENDPOINT_URL else "auto")
