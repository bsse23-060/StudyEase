# Security model

Production fails closed without a strong secret, PostgreSQL URL, hosts, and CSRF origins. TLS redirect, secure/HttpOnly/SameSite cookies, content sniffing protection, referrer policy, clickjacking denial, rotating/blacklisted refresh tokens, password validators, private storage, malware gating, per-scope throttles, request limits, JSON redaction, and a restrictive frontend CSP are configured. Only a known private reverse proxy may supply forwarding headers; strip client-supplied forwarding headers at the edge.

Do not expose `/internal/metrics/`, admin health, Django admin, database, Redis, MinIO console, or ClamAV publicly. Storage objects are private; signed URLs expire in five minutes by default. Rotate secrets after suspected exposure and deploy a new Django secret only with an explicit JWT/session invalidation plan. Registration email verification should be introduced before unrestricted public registration. Multi-device session inventory and per-device revocation remain a documented limitation.

Run pip/npm audits, Gitleaks, Trivy, and CI weekly. Review—not blindly merge—major upgrades; test migration, API schema, BFF cookies, RAG, and Playwright paths. License review remains a human release gate.
