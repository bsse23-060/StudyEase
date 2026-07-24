# studyEase source analysis and unified architecture

Product completion adds explicit quiz lifecycles and atomic submissions, course-scoped concepts, timezone-aware recurrence, flashcard review history, and bounded conversation history. See [product_completion.md](product_completion.md).

## Source Analysis Corrections

The full re-audit and corrections are recorded in [audit_report.md](audit_report.md). Most of the original inventory was accurate, but the actual folder is `studyBuddy` (not `studdyBuddy`), several studyBuddy RAG/provider/document handlers are unmounted sketches rather than live routes, its mounted chat calls Gemini directly, and “FSRS-lite” in Aurex should not be read as complete modern FSRS support.

## What was found

Neither input is a Django/DRF application. Aurex is FastAPI + SQLAlchemy + Pydantic; studyBuddy is Angular with a stateless Cloudflare Hono worker and IndexedDB client storage. “Serializer” below therefore means Pydantic response/request schema in Aurex and TypeScript request/response interfaces in studyBuddy.

### Aurex26--ITU-AI-HACKATHON--Saram

Models: `User`, `LearningDNA`, `Course`, `Module`, `Concept`, directed `ConceptEdge`, `QuizItem`, `Attempt`, per-user `Mastery`, `EngagementEvent`, personalized `RoadmapStep`, concept `ReviewQueue`, `TutorMessage`, and `JobRole`. Its schemas cover auth/token output; courses/modules/concepts; adaptive quiz submissions and mastery deltas; onboarding, roadmap, recommendations, peer twins and career projections; instructor risk/burnout/course analytics; tutor messages and citations.

Endpoints:

- Auth: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/auth/demo-accounts`.
- Catalog/admin: `GET /api/courses[/{id}]`; admin course CRUD; nested module create/update/delete.
- Onboarding: DNA scenarios, course diagnostic, onboarding completion.
- Student: roadmap, DNA, mastery, module detail/adaptive quiz, submit answer, switch course, complete roadmap step, record event.
- Tutor: ask/history, voice status, ElevenLabs TTS, Groq Whisper STT.
- Insights: skill graph, career match, peer twin; instructor dashboard/student detail/course analytics; admin analytics.

Authentication: custom bcrypt password hashing and signed bearer JWTs via `python-jose`. Tokens contain user id, email and role; FastAPI dependencies reload the user and enforce student/instructor/admin roles. Strength: clear role dependencies. Weakness: one access token only, hand-built password/token lifecycle, four-character password minimum, and a public demo-password endpoint.

Unique features: five-axis “Learning DNA”, Bayesian-style concept mastery, adaptive quizzes, prerequisite skill graph, generated roadmaps, at-risk/burnout/confusion analytics, career outcome simulator, peer “digital twin”, bilingual RAG tutor, and voice I/O.

### studyBuddy

There is no server-side ORM. Its TypeScript domain contracts describe `UserProfile`, `Conversation`/`Message`/citations, `Document`/`DocChunk`, generated multi-type `Quiz`/questions/attempts, SM-2 `Flashcard`/deck/review session, study sessions/progress reports/hallucination events/usage stats, and routines/schedule blocks/completions. Most persistence is browser IndexedDB; the worker uses KV for cache/rate-limit bindings.

Worker endpoints: `GET /api/health`, `POST /api/chat`, `/api/quiz/generate`, `/api/flashcards/generate`, `/api/documents/analyze`, `/api/answers/evaluate`, `/api/flashcards/schedule`, `/api/progress/analytics`, `/api/concepts/cluster`, and `/api/routine/generate`. Earlier handler files also sketch document upload/status/search and embedding routes, but they are not mounted by the current worker entry point.

Authentication: none for end users. API provider keys live in worker bindings, CORS is configurable, and input limits/timeouts exist, but the public endpoints have no identity or object authorization.

Unique features: source-document ingestion and RAG citations, provider fallback contracts, multiple quiz question types and free-text evaluation, full SM-2 flashcards, offline-first operation, focus/study-session analytics, AI concept clustering, hallucination reporting, usage accounting, and daily routine generation.

## Unified design and why

- Django’s custom email-based `User` plus SimpleJWT replaces both custom JWT code and no-auth endpoints. Django password hashing/validation, refresh tokens, and DRF authentication are safer and easier to maintain. Roles remain explicit, but object ownership is checked too; a role alone must not grant an instructor another instructor’s course.
- `Enrollment` is a join model instead of Aurex’s single `enrolled_course_id`. Learners can take many courses, retain history/status, and get a separate roadmap per enrollment.
- `Course > Module > Lesson` separates organization from deliverable content. Aurex placed markdown directly on modules; distinct lessons support text, video, and quiz content while stable modules remain useful for roadmaps.
- `Concept` uses a self-referential prerequisite relation instead of exposing an edge table everywhere. Django still creates a normalized join table, while the API becomes simpler. Concepts can span lessons, unlike Aurex’s one-module ownership.
- `QuizQuestion.correct_answer` is JSON to support MC index, true/false, and text answers from studyBuddy. It is write-only so students never receive answer keys. Server-side attempt creation grades objective equality atomically and updates mastery; AI/semantic grading should later be an isolated service, not trusted client input.
- `Mastery` preserves probabilistic knowledge state and stability. It is separate from attempts because an estimate changes over many observations. The included update is deliberately a transparent baseline, ready to be replaced by BKT/IRT.
- Documents and chunks are first-class owned records rather than transient worker payloads. `embedding_ref` points to an external vector store instead of putting large vectors in the relational database.
- Conversations persist messages and structured citations. This combines Aurex history with studyBuddy’s source-aware RAG contract. AI calls are intentionally not faked in the initial domain/API foundation.
- Flashcards use studyBuddy’s per-card SM-2 fields instead of Aurex’s concept-only review queue. This supports actual cards and preserves review statistics. The review action calculates scheduling on the server.
- Routines use a parent plus normalized schedule blocks; flexible preferences/suggestions stay JSON because those AI-shaped attributes change more often than stable scheduling fields.
- Engagement events remain append-only and schema-flexible for analytics. Core relational facts are not hidden in JSON; only event-specific payload data is.
- Document ingestion and RAG use asynchronous services rather than serializer/view logic. Sources are structurally extracted, version-chunked, embedded, retrieval-filtered by authorization, and answered through provider-neutral interfaces. Citations remain relational and traceable to exact chunk versions. See [rag_architecture.md](rag_architecture.md).

## Generated modules

### accounts

`User`: `email` is the unique login; `full_name` is display identity; `role` drives coarse authorization; `level_preference` adjusts tutor difficulty; `weekly_hours` and `goal` guide planning; `language_preference` supports localized tutoring; `onboarding_data` holds evolving answers; `onboarded_at` distinguishes completed onboarding. Django’s inherited flags/password timestamps remain available.

`RegisterSerializer` accepts a write-only password, runs Django validators, and delegates hashing to `create_user`. `UserSerializer` never exposes password and makes role/timestamps read-only to prevent privilege escalation. `RegisterView` is public; `MeView` only accesses the authenticated user; `UserViewSet` is read-only and admin-only. `IsAdminRole`, `IsInstructorOrAdmin`, and `IsInstructorOwnerOrReadOnly` enforce role and authored-course ownership.

### courses

`Course`: instructor owns authorship; slug is a stable public key; title/description are catalog content; `is_published` controls learner visibility; metadata holds presentation extras; timestamps audit changes. `Module`: course, title/summary, and unique position create ordered sections. `Lesson`: module, type, body/URL, duration, and unique position define individual learning units. `Concept`: author/slug/name/description identify reusable skills; lessons map coverage; prerequisites form the skill graph. `QuizQuestion`: lesson/concept connect assessment to content and mastery; kind/options/answer support three formats; explanation supplies feedback; normalized difficulty and points support adaptation/scoring.

Read serializers nest modules, lessons, and questions for useful course detail, while relationships remain primary keys on writes. `correct_answer` is write-only. Validation enforces viable MC options/index and prevents direct self-prerequisites. Viewsets use routers, filters/search/order, eager loading, and published-only catalog queries for ordinary users. Writes require instructor/admin status and object ownership; new courses automatically belong to the caller.

### learning

`Enrollment`: learner/course uniqueness, lifecycle status, and dates preserve course history. `LearningProfile`: five bounded 0–1 dimensions port Learning DNA without tying it to onboarding payload shape. `Mastery`: unique learner/concept probability, stability, and seen/update times support adaptive scheduling. `QuizAttempt`: immutable learner/question answer, server-computed correctness/points, duration, feedback, and timestamp provide an audit trail. `RoadmapStep`: enrollment/module, ordered position, target, rationale and completion timestamp model a personalized plan. `EngagementEvent`: learner, indexed kind/time, optional module, and event payload feed analytics.

Enrollment/event serializers assign the requester rather than trusting a learner id. Mastery is wholly read-only. Attempt creation grades and adjusts mastery in one transaction, so partial writes cannot corrupt learner state. Roadmap validation prevents cross-course modules. Learner-scoped viewsets prevent horizontal data access; teaching staff only see learners attached to their courses. Attempts and events are create/read only because history should not be rewritten. The `complete` action records server time.

### study_tools

`Document`: owner/course/lesson scope, visibility, validated source facts, lifecycle/error/timing, checksum, model/version data, and soft deletion support ingestion. `DocumentChunk`: versioned text with page/section/offset/checksum metadata and model-identified embeddings supports retrieval and immutable citations. `Conversation` and `Message`: owner/course/lesson, role/content, archive/deletion, citations/metadata, and timestamps persist RAG chat. `ProviderUsage` records provider-neutral counts, outcomes, and latency. Flashcards and routines retain their earlier responsibilities.

Nested serializers make conversation, deck, and routine retrieval useful without permitting unsafe nested bulk writes. Document validation enforces a single source. SM-2 review input is a bounded 0–5 serializer and computed schedule fields are read-only. Every viewset filters by owner; `messages`, `due`, and `review` are resource actions, so a user cannot access a child belonging to another user.

## API shape

All resources live under `/api/v1/` and use DRF router conventions (`GET collection`, `POST collection`, `GET/PUT/PATCH/DELETE detail`) where permitted: users, courses, modules, lessons, questions, concepts, enrollments, learning-profiles, masteries, attempts, roadmap-steps, events, documents, document-chunks, conversations, flashcard-decks, flashcards, routines, and schedule-blocks. Extra actions are `POST roadmap-steps/{id}/complete/`, `POST conversations/{id}/messages/`, `GET flashcard-decks/{id}/due/`, and `POST flashcard-decks/{id}/cards/{card_id}/review/`. Auth endpoints are register, token, token refresh, and me. OpenAPI schema/docs are `/api/schema/` and `/api/docs/`.

## Assumptions and deliberate boundaries

- A user has one global role for now; organizations/tenants and per-course instructor roles are not specified.
- SQLite is the development default; production should use PostgreSQL, environment-based secrets, HTTPS, CORS configuration, object storage, background ingestion, throttling, and SimpleJWT’s blacklist app if refresh-token revocation is required.
- AI provider credentials, embeddings, document parsing, generated quizzes/roadmaps/routines, semantic short-answer grading, voice, career matching, peer twins and risk analytics need product/provider requirements. The normalized persistence and permission boundaries are present, but fabricated AI responses are not.
- File size/type and malware checks belong in the deployment upload pipeline. The current API only validates file-versus-URL shape.
- Concepts record an author. Instructors manage their own concepts and may attach them only to lessons in their courses; admins retain global governance.
