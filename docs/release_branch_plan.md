# Release branch and commit plan

Recommended branch: `release/staging-candidate-remediation`.

The three existing local `meow` commits should be reviewed by a human before publication. Commit `98e9f8f9` contains the 36,006-file generated-artifact cleanup; no history rewrite was performed. If reviewers require those existing commits to be reorganized, obtain explicit approval before an interactive rebase.

Proposed new commits:

1. `fix(frontend): preserve BFF authentication in production-like HTTP tests` — cookie configuration, BFF path normalization, login and E2E changes. Depends on no later commit; validate frontend and Playwright.
2. `fix(workers): make document processing idempotent and observable` — Celery expected-version guards, distributed cache, heartbeat/readiness and tests. Validate backend tests and two-worker matrix.
3. `fix(storage): bound malware scanning and verify private object lifecycle` — ClamAV service/task behavior and release-gate tests. Validate ClamAV and signed-URL matrices.
4. `feat(ops): add database and object-store recovery tooling` — MinIO scripts and recovery documentation. Validate isolated backup/restore checksums.
5. `test(load): separate authenticated load from throttle abuse` — token command, scripts, Locust profiles and measurements.
6. `chore(security): document generated cleanup and tune secret scan` — narrow Gitleaks config and deletion reports.
7. `docs(release): record final release-gate evidence` — checklist, concurrency, CI and validation reports.

PowerShell preparation commands (execute only after approval):

```powershell
git switch -c release/staging-candidate-remediation
git status --short
git add frontend/src/lib/auth/cookies.ts frontend/src/lib/api/client.ts frontend/src/lib/api/client.test.ts frontend/src/app/login/page.tsx frontend/e2e/journeys.spec.ts frontend/src/types/api.generated.ts schema.yml docker-compose.integration.yml
git diff --cached --stat
git diff --cached
git commit -m "fix(frontend): preserve BFF authentication in production-like tests"
git add config/celery.py config/health.py config/settings/base.py config/worker_health.py config/test_worker_health.py study_tools/tasks.py study_tools/views.py study_tools/test_release_gates.py
git diff --cached --stat
git diff --cached
git commit -m "fix(workers): make document processing idempotent and observable"
git add study_tools/services/malware.py docs/storage_and_clamav_validation.md docs/celery_concurrency_validation.md
git diff --cached
git commit -m "fix(storage): bound malware scanning and verify private object lifecycle"
git add scripts/backup_minio.ps1 scripts/restore_minio.ps1 docs/backup_and_recovery.md docs/object_storage_backup_and_recovery.md
git diff --cached
git commit -m "feat(ops): add database and object-store recovery tooling"
git add learning/management/commands/generate_load_tokens.py scripts/prepare_load_tokens.ps1 load/locustfile.py load/locustfile_abuse.py docs/performance_validation.md
git diff --cached
git commit -m "test(load): separate authenticated load from throttle abuse"
git add .gitleaks.toml docs/generated_file_deletion_review.md docs/generated_file_deletion_review.json
git diff --cached
git commit -m "chore(security): document generated cleanup and tune secret scan"
git add README.md frontend/README.md docs/release_candidate_checklist.md docs/github_actions_validation.md docs/release_branch_plan.md
git diff --cached
git commit -m "docs(release): record final release-gate evidence"
git status --short
git push -u origin release/staging-candidate-remediation
```

Use explicit file lists for each group; do not use `git add .`. Repeat the staged diff review before every commit. The final `git status --short` must be empty before push.
