# Performance validation

Local load tests use `load/locustfile.py`, the seeded demo account, the reverse proxy at `http://proxy:8080`, and deterministic fake AI providers. Results are workstation stability measurements, not production capacity.

## Profiles

Smoke: 5 users, spawn rate 1/s, 30 seconds. Moderate: 20 users, spawn rate 2/s, 60 seconds. Both exercise authenticated login plus course catalogue, conversation history and document-status polling. Token refresh, course detail, quiz submission and RAG require stable seeded entity identifiers and should be added to a staging-only fixture before calling those paths representative.

```powershell
docker run --rm --network studyease_default -v "${PWD}/load:/mnt/locust" locustio/locust -f /mnt/locust/locustfile.py --host http://proxy:8080 --headless -u 5 -r 1 -t 30s --csv /mnt/locust/results/smoke
docker run --rm --network studyease_default -v "${PWD}/load:/mnt/locust" locustio/locust -f /mnt/locust/locustfile.py --host http://proxy:8080 --headless -u 20 -r 2 -t 60s --csv /mnt/locust/results/moderate
docker stats --no-stream
docker compose exec redis redis-cli LLEN documents
```

Record requests, failures, RPS, median, p90/p95/p99, queue depth, task durations, CPU/memory and database connections. Stop if the host swaps, containers are OOM-killed, failure rate exceeds 5%, or p95 remains above 2 seconds for ordinary reads. Suggested staging gates: zero authentication/data-isolation errors, under 1% non-induced failures, ordinary-read p95 under 750 ms, fake-RAG p95 under 3 s, and no growing Celery queue after load stops.

The seeded pgvector dataset has only two chunks; PostgreSQL used the document/version relational index and an in-memory distance sort rather than HNSW. Benchmark HNSW only with a non-sensitive staging corpus large enough for planner statistics and compare `EXPLAIN (ANALYZE, BUFFERS)` with realistic authorization filters.

## 2026-07-21 measurements

The 5-user/20-second smoke run completed 48 requests with zero failures at 2.46 RPS. Aggregate median was 39 ms, p95 490 ms and p99 560 ms; login dominated the tail.

The 20-user/30-second moderate run made 265 requests at 9.04 RPS with median 32 ms, p90 49 ms, p95 430 ms and p99 540 ms, but failed the stability gate: 7 of 20 logins were throttled with HTTP 429 and their unauthenticated follow-on requests produced 42 total failures (15.85%). This is a fixture/IP-throttling interaction and must not be “fixed” by weakening production authentication throttles. Staging load should use pre-issued sessions or distinct source identities when testing authenticated read capacity, while retaining a separate throttle test.

Afterward the `documents` queue length was zero. Idle post-test memory was approximately API 288 MiB, worker 224 MiB, frontend 51 MiB, proxy 12 MiB, PostgreSQL 68 MiB, Redis 13 MiB, MinIO 238 MiB and ClamAV 1.0 GiB. CPU was below 0.5% when sampled after the run; this is not peak CPU telemetry.

## Corrected authentication fixture

`generate_load_tokens` creates distinct synthetic load users and emits access/refresh tokens. `scripts/prepare_load_tokens.ps1` writes the ignored `load/results/tokens.json`; each Locust user receives a different token. Refresh traffic is opt-in with `LOAD_ENABLE_REFRESH=1`, so ordinary reads are not mislabeled when a shared-IP login throttle behaves correctly. `locustfile_abuse.py` is the separate intentional login-abuse profile.

The final normal authenticated run used 20 users for 20 seconds: 135 requests, zero failures, 6.88 RPS, median 25 ms, p95 29 ms and p99 34 ms. No refresh occurred because refresh was disabled for this short normal profile; the document queue ended at zero.

The final abuse run used 5 users for 10 seconds: 171 login attempts, 161 expected HTTP 429 responses and 10 HTTP 401 responses, with zero unexpected Locust failures. The expected 429 rate was 94.2%. These local results validate fixture behavior and throttling, not production capacity.
