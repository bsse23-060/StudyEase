FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt requirements.lock ./
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip && /opt/venv/bin/pip install --require-hashes -r requirements.lock

FROM python:3.12-slim AS runtime
ENV PATH=/opt/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_ENV=production
RUN groupadd --system studyease && useradd --system --gid studyease --home /app studyease
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=studyease:studyease . .
RUN mkdir -p /app/staticfiles /app/media && chown -R studyease:studyease /app/staticfiles /app/media
USER studyease
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live/', timeout=3)"]
ENTRYPOINT ["sh", "/app/scripts/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind=0.0.0.0:8000", "--workers=3", "--threads=2", "--timeout=120", "--graceful-timeout=30", "--access-logfile=-", "--error-logfile=-"]
