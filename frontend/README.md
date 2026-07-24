# studyEase frontend

The frontend is a Next.js 16 App Router application written in strict TypeScript. It connects to the existing DRF API through a same-origin backend-for-frontend (BFF), so JWT access and refresh tokens stay in `HttpOnly`, `SameSite=Lax` cookies and are never readable by React code.

## Why these dependencies

- **Next.js / React** provide route-level splitting, server route handlers, error/loading boundaries, and the BFF.
- **TanStack Query** owns remote cache, request state, bounded retries, polling, and targeted invalidation. Form and navigation state stay local.
- **React Hook Form + Zod** provide accessible forms with fast client feedback; DRF validation remains authoritative.
- **Tailwind CSS** provides a small responsive visual system without a runtime component framework.
- **openapi-typescript** generates `src/types/api.generated.ts` from the source-of-truth schema. Hand-reviewed ergonomic domain types live in `src/lib/api/types.ts` because generated JSON fields are necessarily broad.
- **Vitest / Testing Library** cover units and components. **Playwright / axe-core** cover seeded browser journeys and automated accessibility checks.

## Local setup (PowerShell)

```powershell
cd "<path-to-your-clone>\StudyEase\frontend"
Copy-Item .env.local.example .env.local
npm.cmd install
npm.cmd run api:types
npm.cmd run dev
```

Open `http://127.0.0.1:3000`. `DJANGO_API_BASE_URL` is server-only and defaults to `http://127.0.0.1:8000/api/v1`. There are no frontend secrets and no `NEXT_PUBLIC_` API credential.

## Backend and workers

From the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py seed_demo
$env:CELERY_TASK_ALWAYS_EAGER = "true"
python manage.py runserver
```

Fake embedding/language providers plus eager Celery need no Redis and make no paid calls. For production-style async processing:

```powershell
docker run --name studyease-redis -p 6379:6379 redis:7-alpine
$env:CELERY_TASK_ALWAYS_EAGER = "false"
python -m celery -A config worker --pool=solo --loglevel=INFO
```

## Verification

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run format
npm.cmd test
npm.cmd run test:coverage
npm.cmd run build
npm.cmd run test:e2e
```

Playwright expects the seeded Django backend on port 8000 and starts/reuses Next.js on port 3000. It covers a student learning journey, documents/RAG, instructor authoring, horizontal access denial, and axe checks.

## Security and failure behavior

The proxy retries an upstream request once after a 401 by rotating the refresh token. A second 401 clears both cookies; the application returns to login with a safe relative return URL. Route navigation is role-filtered, but DRF remains authoritative. Content and AI answers render as plain text; no `dangerouslySetInnerHTML` is used. File validation is duplicated for usability, never as a substitute for backend checks. Query caches clear on logout.

The browser and Django do not communicate cross-origin, so development does not need CORS. CSRF exposure is reduced by `SameSite=Lax`; production should add an explicit anti-CSRF token to mutation routes if the frontend and untrusted sibling applications share a registrable domain.

## Current product boundaries

- Scheduling supports one-time and weekly recurrence; arbitrary recurrence exceptions and overlap diagnostics remain future work.
- Quiz lifecycle and atomic submission are complete; legacy per-question attempts remain for compatibility.
- Course-scoped curriculum, prerequisite, quiz, document, and student sections are implemented; richer option reordering remains future work.
- Upload transfer progress is measurable; extraction and embedding correctly remain stage-based rather than fake percentages.
- Conversation history loads in 30-message pages; client virtualization is unnecessary at this page size.
- Dark mode was intentionally deferred to keep focus and contrast treatment consistent.
