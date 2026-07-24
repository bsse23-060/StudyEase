# Production checklist

- [ ] Approved provider architecture, budgets, data residency, TLS/DNS, private networking, and secret manager
- [ ] Strong unique secrets; no secrets in images/client bundles/repository; forwarding trust restricted
- [ ] PostgreSQL extension/migrations reviewed against real table sizes; verified restore and PITR drill
- [ ] Private versioned bucket, lifecycle, signed access, and cross-system checksum reconciliation tested
- [ ] ClamAV signatures/update/alerts tested; infected, unavailable, retry, and quarantine paths verified
- [ ] Redis persistence expectation, queue alerts, worker concurrency/timeouts, and lock expiry load-tested
- [ ] API/frontend images scanned, non-root verified, SBOM/license review complete
- [ ] Backend/frontend/integration/Playwright/accessibility/security CI green with no schema drift
- [ ] Readiness, metrics, logs, error reporting, alert routing, and incident on-call privately configured
- [ ] Cookie/JWT logout/rotation/replay, CSRF/CORS/CSP, rate limits, upload limits, and horizontal denial tested
- [ ] Staging smoke/load/backup/restore and rollback rehearsal complete with results recorded
- [ ] Manual accessibility, privacy/retention, regulatory, and threat-model reviews signed off

Automated checks alone do not establish full production, security, privacy, accessibility, or regulatory readiness.
