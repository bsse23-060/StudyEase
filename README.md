# studyEase

studyEase is a Django REST Framework learning-management platform with a Next.js frontend. It combines structured course delivery and adaptive learner state from Aurex with studyBuddy's documents, cited conversations, flashcards, and routines. It includes asynchronous extraction, structural chunking, provider-neutral embeddings, authorised retrieval, grounded answer generation, and a responsive role-aware learning interface.

## Architecture

The API is split into four domain apps:

- `accounts`: email login, learner preferences, roles, JWT authentication, and user visibility.
- `courses`: courses, ordered modules and lessons, reusable concepts/prerequisites, and quiz questions.
- `learning`: enrollments, learning profiles, mastery, attempts, roadmaps, and engagement events.
- `study_tools`: source documents/chunks, cited conversations, SM-2 flashcards, and routines.

RAG internals are split into providers, focused services, and a Celery task. See [rag_architecture.md](docs/rag_architecture.md).

SQLite is used locally. Production should use PostgreSQL, object storage, background document processing, HTTPS, and external secret management. See [architecture.md](docs/architecture.md), [backend_walkthrough.md](docs/backend_walkthrough.md), and [audit_report.md](docs/audit_report.md).

## Windows PowerShell setup

```powershell
cd "<path-to-your-clone>\StudyEase"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Development defaults use deterministic fake AI providers and eager tasks, so Redis and paid APIs are unnecessary. After seeding and starting Django, exercise the complete flow with:

```powershell
.\scripts\rag_walkthrough.ps1
```

The interactive API documentation is at `http://127.0.0.1:8000/api/docs/`; raw OpenAPI is at `/api/schema/`.

Start the frontend in a second PowerShell window:

```powershell
cd frontend
Copy-Item .env.local.example .env.local
npm.cmd install
npm.cmd run api:types
npm.cmd run dev
```

Open `http://127.0.0.1:3000`. See [frontend/README.md](frontend/README.md), [frontend_architecture.md](docs/frontend_architecture.md), and [frontend_walkthrough.md](docs/frontend_walkthrough.md).

## Development demo accounts

These credentials are created only by `python manage.py seed_demo`. Never use them in production. The command refuses to run when `DJANGO_DEBUG=false` and is idempotent.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@studyease.local` | `StudyEaseDemo123!` |
| Instructor 1 | `instructor1@studyease.local` | `StudyEaseDemo123!` |
| Instructor 2 | `instructor2@studyease.local` | `StudyEaseDemo123!` |
| Student 1 | `student1@studyease.local` | `StudyEaseDemo123!` |
| Student 2 | `student2@studyease.local` | `StudyEaseDemo123!` |

## Authentication examples

Obtain access and refresh tokens:

```powershell
$body = @{ email = "student1@studyease.local"; password = "StudyEaseDemo123!" } | ConvertTo-Json
$tokens = curl.exe -sS -X POST -H "Content-Type: application/json" --data-binary $body http://127.0.0.1:8000/api/v1/auth/token/ | ConvertFrom-Json
$access = $tokens.access
curl.exe -sS -H "Authorization: Bearer $access" http://127.0.0.1:8000/api/v1/auth/me/
```

Refresh an access token:

```powershell
$refreshBody = @{ refresh = $tokens.refresh } | ConvertTo-Json
curl.exe -sS -X POST -H "Content-Type: application/json" --data-binary $refreshBody http://127.0.0.1:8000/api/v1/auth/token/refresh/
```

Run the complete student/instructor walkthrough after starting the server:

```powershell
.\scripts\api_walkthrough.ps1
```

## Tests and validation

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test -v 2
python manage.py spectacular --file schema.yml --validate
```

## Environment variables

| Variable | Purpose | Development default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Signing key for Django and JWT | Insecure development value |
| `DJANGO_DEBUG` | Enables debug mode and `seed_demo` | `true` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated HTTP hosts | `localhost,127.0.0.1,testserver` |
| `DJANGO_SECURE_HSTS_SECONDS` | Production HSTS duration | `31536000` outside debug |
| `RAG_EMBEDDING_PROVIDER` / `RAG_LANGUAGE_MODEL_PROVIDER` | `fake` or `openai` | `fake` |
| `OPENAI_API_KEY` | Required only when an OpenAI provider is selected | Empty |
| `RAG_EMBEDDING_MODEL` / `RAG_LANGUAGE_MODEL` | Provider model names | See `.env.example` |
| `RAG_VECTOR_BACKEND` / `RAG_VECTOR_DIMENSIONS` | `database` or `pgvector`, and exact dimensions | `database` / `64` |
| `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` | Structural chunk targets | `1200` / `150` |
| `RAG_RETRIEVAL_TOP_K` / `RAG_MAX_CONTEXT_CHARACTERS` | Retrieval/context caps | `5` / `12000` |
| `RAG_MAX_DOCUMENT_BYTES` | Upload limit | `10485760` |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis endpoints | Local Redis DB 0/1 |
| `CELERY_TASK_ALWAYS_EAGER` | Run tasks synchronously | `true` in debug |

Set production values before deployment:

```powershell
$env:DJANGO_SECRET_KEY = "generate-a-long-random-secret"
$env:DJANGO_DEBUG = "false"
$env:DJANGO_ALLOWED_HOSTS = "api.example.com"
```

For production-style async processing on Windows, use separate PowerShell windows:

```powershell
docker run --name studyease-redis -p 6379:6379 redis:7-alpine
$env:CELERY_TASK_ALWAYS_EAGER = "false"
python manage.py runserver
python -m celery -A config worker --pool=solo --loglevel=INFO
python -m celery -A config inspect registered
```

`--pool=solo` avoids Windows multiprocessing incompatibilities. Production Redis/Celery processes must be supervised; Linux workers normally use prefork.

## Project structure

```text
StudyEase/
|-- accounts/             identity, roles, authentication permissions
|-- courses/              authored curriculum and assessments
|-- learning/             enrollment and learner state
|-- study_tools/          documents, citations, flashcards, routines
|-- config/               Django settings and router registration
|-- docs/                 architecture, audit, and learning walkthrough
|-- frontend/             Next.js App Router application and browser tests
|-- scripts/              PowerShell API walkthrough
|-- manage.py
|-- requirements.txt
`-- schema.yml
```

## Production preparation

The repository now includes split environment settings, PostgreSQL/pgvector HNSW retrieval, Redis/Celery locking, private S3-compatible storage configuration, malware scan gating, archival courses, overlap diagnostics, JWT blacklisting, structured logs, health/metrics endpoints, containers, CI/CD preparation, backups, and runbooks. Start with [production_architecture.md](docs/production_architecture.md), [deployment.md](docs/deployment.md), [security.md](docs/security.md), and [production_checklist.md](docs/production_checklist.md).

External staging validation, real PostgreSQL/Redis/S3/ClamAV failure drills, restore verification, load results, manual accessibility testing, provider threat/safety review, and formal privacy/regulatory review are still required. Automated checks do not constitute production, accessibility, privacy, security, or regulatory sign-off.
