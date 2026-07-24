# Staging deployment plan

## Recommendation

Use Render for the first human-approved staging environment. It directly supports Docker services, pre-deploy commands, HTTP health checks, private services, Celery background workers, managed PostgreSQL with pgvector, and Redis-compatible Key Value on a regional private network. Those features are documented by [Render Docker](https://render.com/docs/docker), [Postgres](https://render.com/docs/postgresql), [background workers](https://render.com/docs/background-workers), [private networking](https://render.com/docs/private-network), and [health checks](https://render.com/docs/health-checks). Capabilities and prices must be rechecked immediately before provisioning.

| Platform | Fit and principal limitation |
|---|---|
| Render | Best operational fit: managed pgvector/Postgres, Key Value, Docker web/worker/private services. Run ClamAV privately; use external S3-compatible object storage because service filesystems are ephemeral unless a paid disk is attached. |
| Railway | Simple Docker and private networking; validate current managed pgvector, backup guarantees, and private malware-scanner persistence before selection. |
| Fly.io | Strong Machines/private networking and managed Postgres includes pgvector; persistent volumes are single-host resources unless deliberately replicated, increasing MinIO/ClamAV operations. |
| DigitalOcean | App Platform workers plus managed databases and Spaces are attractive, but confirm pgvector version and feasibility of a long-running private ClamAV service. |
| AWS | ECS/Fargate, RDS pgvector, ElastiCache and S3 provide the strongest component choice; IAM/VPC/load-balancer/observability complexity is disproportionate for first staging. |

## Topology and order

Provision one region: managed Postgres, Key Value, private ClamAV Docker service, Django Docker web service, Celery Docker background worker, and Next.js Docker web service. Prefer the platform TLS ingress over an extra Nginx service. Use a private S3-compatible bucket (AWS S3 is simplest) with CORS disabled unless a documented direct-download design needs it.

1. Create secret group and datastores; enable `vector` through migrations.
2. Create the private scanner and verify its TCP health.
3. Create API with Dockerfile `Dockerfile`, pre-deploy `python manage.py migrate --noinput`, start command from the image, and health path `/api/v1/health/ready/`.
4. Create worker from the same image: `celery -A config worker -l INFO -Q default,documents --concurrency=2`.
5. Create frontend from `frontend/Dockerfile`, health path `/api/health`.
6. Configure the frontend domain/TLS and API/BFF private address; then run smoke tests.

Required secrets/settings include `DJANGO_ENV=production`, a generated `DJANGO_SECRET_KEY`, allowed hosts, CSRF origins, internal `DATABASE_URL`, broker/result URLs, S3 bucket/region/endpoint and scoped credentials, ClamAV host, AI provider selection/keys, metrics token, secure-cookie settings and error-reporting DSN. Never copy local Compose credentials. Store them in platform secret management and restrict staff access.

Back up PostgreSQL with managed PITR plus periodic portable custom dumps; enable object versioning/lifecycle separately. Deployment rollback means restore the previous immutable image, run only backward-compatible migrations, and restore data only through an approved recovery event. Smoke login, refresh/revocation, catalogue, quiz, upload/scan, async RAG/citation, signed access and horizontal denial after every release. Manual approvals: budget/region, domains, secrets, bucket/IAM, retention, data-processing terms, backup restore drill and go/no-go.

Known limitations: Compose is not a cloud orchestrator; ClamAV memory/signature updates need monitoring; object storage is restored separately; worker health needs platform-level queue/heartbeat monitoring; already-issued signed URLs remain usable until their short expiry; correlation IDs do not currently propagate into every third-party or Celery log.

