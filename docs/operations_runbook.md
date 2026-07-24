# Operations runbook

- Start/stop: `docker compose up -d --wait`; `docker compose down` (never add `-v` unless intentionally destroying local data).
- Health/logs: check `/health/live/`, `/health/ready/`, then restricted admin health; use `docker compose logs --since 15m api worker` and request IDs. Never paste secrets/private payloads.
- Workers/backlog: inspect Celery workers/queue length, stop intake if growing, scale `worker`, identify provider/scanner latency, and retry only idempotent failed documents. Restart gracefully with `docker compose restart worker`.
- Migrations: stop rollout, inspect DB locks and `showmigrations`, restore from verified backup only if forward repair cannot be made. Never let every web replica migrate.
- Restore/rotation: follow backup guide in isolation. Rotate one credential at a time, restart consumers, verify readiness, then revoke old credentials.
- Dependency outage: DB → maintenance mode/read-only edge; Redis → pause uploads/async actions; storage → disable uploads and retain metadata; scanner → disable uploads or leave pending, never bypass; AI → keep learning content available and return controlled provider-unavailable responses.
- Maintenance: route the edge to a static maintenance page while retaining internal health access. Disable uploads at proxy/application feature flag (provider deployment must add the flag) and drain workers before invasive work.
