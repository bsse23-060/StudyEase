# GitHub Actions validation

The workflow YAML parses locally and its equivalent backend, frontend, PostgreSQL/pgvector, Redis/Celery, integration, Playwright, dependency-audit, schema-drift and container-build commands were exercised on 2026-07-21. Production-like Playwright passed all seven tests. The workflow uses read-only repository permissions, per-ref concurrency cancellation, pinned major action releases, service health checks, unconditional Compose log upload and cleanup, and a full-history checkout for Gitleaks.

`actionlint` could not be executed because its container image was not cached and Docker registry DNS failed. A GitHub-hosted runner, action download behavior, artifact upload, fork pull-request secret behavior and the complete job graph therefore remain unverified. GitHub Actions must not be marked passed until the release branch is pushed and every required job succeeds.

Recommended required checks are `backend`, `frontend`, `postgres`, `e2e`, and `security`. Protect `main` with required pull-request review, required up-to-date branches, conversation resolution, no force pushes/deletions, and those five checks.
