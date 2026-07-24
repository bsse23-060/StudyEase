# Release candidate checklist

Legend: `[x]` automated pass, `[M]` manual pass required, `[B]` blocked/not fully validated, `[N/A]` not applicable.

- [B] Git status clean (release-gate changes intentionally remain unstaged and uncommitted)
- [x] Generated files and ignore behavior reviewed (`docs/generated_file_deletion_review.md` and JSON report)
- [x] Full history (4 commits, 460.4 MB) and a clean tracked/untracked current-tree copy scanned with zero findings after 15 generated-Next false positives were narrowly allowlisted in `.gitleaks.toml`
- [x] Python/Node dependency audits
- [x] Backend, frontend and custom unprivileged proxy have zero fixed HIGH/CRITICAL Trivy findings
- [x] Backend tests, coverage gate, Django checks and migration drift
- [x] Frontend tests, 80% coverage gates, typecheck, lint, format and build
- [x] Integration/API/RAG smoke tests
- [x] Automated accessibility tests; [M] manual accessibility plan
- [x] Backend/frontend Docker builds and non-root users
- [x] Clean Compose startup and service health
- [x] PostgreSQL/pgvector migration, dimension, index and retrieval checks
- [x] Duplicate dispatch, two-worker distributed locks and stale-lock behavior; [B] abrupt worker-kill and deliberately delayed N/N+1 live races (`docs/celery_concurrency_validation.md`)
- [x] Private MinIO expiry, authorization, deletion and reprocessing matrix; [B] archived-course fixture absent
- [x] Live ClamAV clean, EICAR, unavailable/restart/retry exhaustion; [B] live accepting-but-hanging socket and delete-while-waiting were not exercised
- [x] Timestamped PostgreSQL backup
- [x] Isolated PostgreSQL restore and representative row checks
- [x] Reverse-proxy smoke walkthroughs
- [x] Normal token-fixture load passed with zero failures; separate abuse profile produced 94.2% expected 429 responses
- [x] Redis readiness failure bounded below one second in the observed stopped-Redis run; recovered normally
- [x] Two-worker heartbeat, stale/missing/multiple-worker status and Prometheus metrics
- [x] Restored-database API startup, login, reads, pgvector retrieval, citations and isolated write; [B] no archived-course row existed
- [x] PostgreSQL and MinIO backup/isolated restore verified separately; [B] combined restored DB plus restored-bucket application flow was not exercised
- [x] Production-like Playwright: 7/7 journeys passed
- [B] `actionlint` image unavailable due transient Docker registry DNS; YAML parsing/local job-equivalent commands passed
- [B] GitHub-hosted Actions have not run
- [M] Documentation, environment and privacy review
- [x] Migration and rollback procedure reviewed
- [M] Staging budget, region, credentials, storage and deployment approval

The project remains a conditional staging candidate. It becomes unconditional only after the unresolved live race/crash cases are exercised or formally accepted, final security/tool reruns and GitHub-hosted CI pass from a clean branch, and a human reviews the proposed commits.
