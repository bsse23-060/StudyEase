# Repository hygiene

The Git index previously contained 3,136 `frontend/.next` files, 32,868 `frontend/node_modules` files, `.coverage`, and `frontend/tsconfig.tsbuildinfo`. They were removed from the index with `git rm --cached`; local copies were not treated as source and Git history was not rewritten. A subsequent production build leaves `.next` ignored and zero files under `.next` or `node_modules` tracked.

The root and frontend ignore files now cover Python caches/coverage, virtual environments, local environment files (while retaining documented examples), SQLite, uploads, collected static, logs, backups, local service data, Playwright output, frontend coverage, `.next`, `node_modules`, and TypeScript build metadata. Docker contexts exclude the same runtime/build material plus Git metadata and secrets.

Intentionally retained reproducible artifacts include migrations, `requirements.lock`, `package-lock.json`, `schema.yml`, generated OpenAPI TypeScript types, example environment files, Dockerfiles, Compose manifests and operational scripts.

Before a PR:

```powershell
git status --short
git ls-files frontend/.next frontend/node_modules
git check-ignore -v frontend/.next frontend/node_modules .coverage
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file schema.check.yml --validate
Set-Location frontend; npm run api:types; git diff --exit-code src/types/api.generated.ts
```

Runtime data belongs in named Docker volumes. Backups belong in `backups/` and require separate protected retention. Never commit `.env`, uploads, database/Redis/MinIO/ClamAV data, scan reports, traces, logs or generated build directories.

