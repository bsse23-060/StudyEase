# Celery concurrency validation

Validated locally on 2026-07-21 with Redis, PostgreSQL/pgvector, MinIO, ClamAV, deterministic fake AI providers, two Celery containers, and concurrency 2 per container.

| Scenario | Result | Evidence |
|---|---|---|
| Duplicate forced processing | Initially failed: version advanced 1→3 and two usage side effects occurred. Fixed by carrying `expected_version`; rerun advanced 3→4 once, retained one active chunk, and added one usage record. | Two task IDs received by different workers; final SQL `4|ready|1|1|1`. |
| Duplicate live scan | Initially exposed per-process `LocMemCache`. Integration now uses Redis DB 2. Rerun produced clean/ready, one chunk and one usage record. | Two workers received scan tasks; final SQL `clean|ready|1|1|1|1`. |
| Two workers/heartbeat | Passed. | Two distinct heartbeat keys and administrative status reported two healthy workers. |
| Active lock ownership | Passed in automated tests: a second owner cannot steal or delete a live lock. | `study_tools.test_release_gates.LockOwnershipTests`. |
| Stale lock | Passed in automated tests: expired lock can be reacquired. | Same test module. Production timeout is bounded by `DOCUMENT_LOCK_TIMEOUT`. |
| Version race | Passed structurally and through stale expected-version rejection. Task checks expected version before and after lock; service checks it again inside the final transaction. |
| Deletion race | Service and task recheck `deleted_at`; final writes and scan updates filter deleted rows, and deletion deactivates chunks. Covered by existing unit tests, not a deliberately slowed live extraction. |
| Retry exhaustion | Live ClamAV DNS outage exhausted five attempts, ended unavailable, and did not become ready. |
| Abrupt worker loss during extraction | Blocked: deterministic processing completed in under 0.4 seconds, so no reliable live kill window was produced without adding an artificial production hook. `acks_late` and `task_reject_on_worker_lost` are configured, but this exact crash path is not claimed as exercised. |
| Older task finishing after N+1 | The three version guards prevent overwrite and stale tasks return without side effects. A deliberately delayed live N task was not produced; automated stale-version tests are the remaining recommended addition. |

The critical defects discovered by this matrix were fixed rather than accepted: version-less forced dispatch and non-distributed integration locks. Worker failures remain visible in Celery logs without document content; provider/database writes are transaction-bounded and unique constraints provide a final duplicate barrier.
