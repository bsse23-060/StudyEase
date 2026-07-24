# Technical audit report

## Source Analysis Corrections

- The supplied folder is named `studyBuddy`, not `studdyBuddy`. The audit used the actual folder and did not alter either source project.
- Aurex was correctly identified as FastAPI, SQLAlchemy, Pydantic, bcrypt, and custom bearer JWT. Its 14 ORM models and mounted auth, course/admin, onboarding, student, tutor/voice, graph/career/twin, instructor, and admin analytics routes match the earlier inventory.
- Aurex's `ReviewQueue` is described in its docstring as “FSRS-lite”, although the scheduling implementation is a simplified algorithm rather than the complete modern FSRS model. The unified documentation now avoids claiming full FSRS compatibility.
- studyBuddy was correctly identified as Angular plus a Cloudflare Hono worker with browser IndexedDB domain persistence and no end-user authentication. It has TypeScript interfaces, not server database models or DRF serializers.
- The earlier wording could imply all studyBuddy handler files were live APIs. The mounted worker routes are health, chat, quiz generation, flashcard generation, document analysis, answer evaluation, flashcard scheduling, progress analytics, concept clustering, and routine generation. Separate document upload/status/search, embedding, provider-adapter, and RAG handler modules are sketches or alternate code paths not mounted by `worker/src/index.ts`.
- The current mounted studyBuddy chat path calls Gemini directly. Provider fallback and vector-search/RAG code exists elsewhere, but it is not used by that mounted path. KV bindings exist, but the reviewed entry point does not implement a complete end-user rate limiter.
- studyBuddy additionally contains client-facing focus sessions, offline storage, settings, FAQ/privacy/terms screens, and error-handling/deployment documentation. These were omitted from the first “unique features” summary because they are frontend capabilities rather than backend LMS records.
- Aurex allows public demo credentials and uses a four-character schema minimum; these remain prototype security weaknesses and were intentionally not carried over.

## Issues found and fixed

| Problem | Why it mattered | Fix | Files |
|---|---|---|---|
| Child curriculum endpoints exposed modules/lessons/questions without enrollment and allowed cross-course creation. | Unenrolled learners could read content; instructors could attach content to another instructor's course. | Scoped querysets by active enrollment/ownership and validated parent ownership on every write. | `courses/serializers.py`, `courses/views.py`, `accounts/permissions.py` |
| Concepts had no author and only admins could safely update them. | The claimed instructor authoring flow was incomplete. | Added nullable `created_by`, author-scoped queries/writes, lesson ownership checks, and a migration. | `courses/models.py`, `courses/serializers.py`, `courses/views.py`, `courses/migrations/0002_*` |
| Only direct self-prerequisites were rejected. | Multi-node cycles make roadmap/topological reasoning invalid. | Added recursive cycle validation and tests. | `courses/serializers.py`, `courses/tests.py` |
| Explicit learning permission classes accidentally omitted an authenticated-user check. | Explicit classes replace DRF defaults; anonymous requests could reach unsafe queryset code. | Added authentication in `IsSelfOrTeachingStaff` and explicit authentication for child content/profile APIs. | `learning/permissions.py`, `learning/views.py`, `courses/views.py` |
| Generic instructor learner scoping could reveal records outside the taught course. | A teacher could see an enrolled learner's unrelated enrollment/attempt/event/mastery data. | Added model-specific course joins for instructor querysets. | `learning/views.py` |
| Students could author arbitrary roadmap steps, including against another enrollment. | Horizontal privilege escalation and plan tampering. | Staff-only mutation permissions, course ownership validation, learner-scoped reads, and safe completion action. | `learning/views.py`, `learning/serializers.py` |
| Attempts accepted any question/answer shape and did not require enrollment. | Learners could access hidden assessments and malformed types could be scored unpredictably. | Enforced active enrollment and per-kind answer validation; normalized short-answer comparison; retained atomic mastery updates. | `learning/serializers.py` |
| Duplicate learning profiles could raise database errors. | A second POST could become a 500 instead of a validation response. | Added serializer-level uniqueness validation; enrollment/mastery database uniqueness remains authoritative. | `learning/serializers.py` |
| Events accepted modules from unrelated courses. | Analytics could be forged across course boundaries. | Validated active enrollment for module-linked events. | `learning/serializers.py` |
| Document partial updates incorrectly required resending the source. | Valid PATCH requests failed. | Validation now combines incoming values with the existing instance and still enforces exactly one source. | `study_tools/serializers.py` |
| Documents, conversations, cards, and blocks accepted foreign objects owned by another user. | Cross-account references leaked metadata and created confused-deputy relationships. | Added course/enrollment and owner validation on create and update; child querysets are owner-scoped. | `study_tools/serializers.py`, `study_tools/views.py` |
| Citations were unvalidated JSON, not tied to source data. | A citation could name another user's document or a nonexistent chunk. | Added normalized `Citation -> DocumentChunk` records and nested read serialization. | `study_tools/models.py`, `study_tools/serializers.py`, migration `0002_citation.py` |
| Document chunks had no protected API. | The claimed RAG-ready resource could not be managed or retrieved end to end. | Added owner-scoped chunk viewset, filtering, ordering, and write validation. | `study_tools/views.py`, `config/urls.py` |
| Never-reviewed flashcards were missing from “due”. | New cards could never enter the review queue. | Included null due dates and tested successful/reset SM-2 paths. | `study_tools/views.py`, `study_tools/tests.py` |
| Generated apps had no admin registration. | Operators could not inspect domain records through Django admin. | Registered all models and configured the custom user admin. | each app's `admin.py` |
| Settings hard-coded the only secret and host/debug behavior. | Unsafe deployment defaults could be mistaken for production configuration. | Added environment overrides, a longer development-only key, and production documentation. | `config/settings.py`, `README.md` |
| OpenAPI could not infer conditional modules or nested card id. | Schema clients received ambiguous types. | Added explicit drf-spectacular annotations and regenerated validation-clean schema. | `courses/serializers.py`, `study_tools/views.py`, `schema.yml` |

## Validation scope

Automated tests cover registration, login/refresh, invalid/expired JWTs, profile safety, admin/instructor user visibility, content ownership, enrollment-gated reads, ordering constraints, question validation, prerequisite cycles, filtering/search/order/pagination, duplicate enrollment/mastery constraints, quiz grading/mastery, roadmap/event permissions, document/chunk ownership, structured citations, flashcard ownership/SM-2, routines/schedule blocks, development seeding, and seeded student/instructor journeys.

The seed command was executed twice against the development database; demo entity counts stayed stable. Django checks, migration drift checks, all tests, and OpenAPI validation are part of the final verification command set.

Initial audit result was 32/32 tests. After the RAG implementation, the final result is **57 tests discovered, 57 passed, 0 failed, 0 skipped in 62.942 seconds**. The `coverage` package is not installed, so no numeric app coverage is claimed. Development and production-mode Django checks pass, migrations show no drift, OpenAPI validates without warnings/errors, seeding is idempotent, and the live PowerShell RAG walkthrough passed.

## Final endpoint list

- Schema: `GET /api/schema/`; browser UI: `GET /api/docs/`.
- Auth/profile: `POST /api/v1/auth/register/`, `POST /api/v1/auth/token/`, `POST /api/v1/auth/token/refresh/`, `GET|PUT|PATCH /api/v1/auth/me/`.
- Read-only staff users: `GET /api/v1/users/` and `GET /api/v1/users/{id}/`.
- Curriculum CRUD: `/api/v1/courses/`, `/modules/`, `/lessons/`, `/concepts/`, and `/questions/`, with standard collection/detail methods allowed by each viewset.
- Learning: enrollment CRUD; learning-profile list/create and detail read/patch; mastery read-only; attempt and event list/create with read-only detail; roadmap CRUD for staff plus `POST /roadmap-steps/{id}/complete/`.
- Sources/chat: authorised document upload/list/detail/delete plus status/retry/reprocess/retrieval-preview actions; read-only active chunks; conversation CRUD plus messages, grounded ask, and archive actions.
- Review/planning: flashcard-deck and flashcard CRUD, `GET /flashcard-decks/{id}/due/`, `POST /flashcard-decks/{id}/cards/{card_id}/review/`, routine CRUD, and schedule-block CRUD.

The authoritative per-method paths and schemas are in `schema.yml`; DRF returns paginated `{count,next,previous,results}` collections, ordinary serializer objects for details/actions, and standard field-keyed validation errors. It intentionally does not wrap every response in a custom envelope.

## Remaining limitations and security work

- The development SQLite database and media directory are local conveniences, not deployment architecture.
- JWT refresh blacklist/revocation, general API throttling, CORS, CSP, audit logging, and account email verification/reset are not implemented. Expensive RAG actions are now per-user throttled.
- Uploads now use byte/container/UTF-8 inspection, size quotas, checksums, private API fields, and server-owned processing; malware scanning, private object storage, and signed delivery remain deployment requirements.
- Citation creation now occurs in the grounded pipeline and validates retrieved IDs and access before persistence.
- Concept cycle validation is application-level and can be bypassed by direct ORM writes; a service layer should own graph mutations if imports/admin editing become common.
- Query eager loading is applied to nested and frequently accessed paths, but production query budgets should be asserted with representative data volumes.
- Voice, career, risk, and advanced analytics remain outside this phase. RAG is implemented; native pgvector model fields/index automation, OCR, hybrid ranking, and distributed task locks remain next-phase work.

## RAG implementation follow-up

The earlier audit correctly identified RAG as missing. The focused follow-up added lifecycle/version fields, server-owned chunks, portable embeddings, provider usage telemetry, Celery processing, fake/OpenAI provider abstractions, extraction/chunking/retrieval/generation services, grounded question and preview APIs, throttles, demo embeddings, a failed retry fixture, deterministic tests, and a PowerShell walkthrough. Detailed tradeoffs are in [rag_architecture.md](rag_architecture.md).
