# Backend walkthrough

New quiz flow: create/retrieve `/api/v1/quizzes/`, start with `POST /api/v1/quiz-submissions/`, submit all `{question_id, answer}` records to `/api/v1/quiz-submissions/{id}/submit/`, and retrieve owner analytics from `/api/v1/quizzes/{id}/analytics/`. Legacy `/attempts/` remains compatible. Details are in [product_completion.md](product_completion.md).

This guide explains how the backend works and why its boundaries exist. Paths are relative to the repository root.

## Request flow

`config/urls.py` registers DRF viewsets with `DefaultRouter`. A request first passes through SimpleJWT authentication from `config/settings.py`, then view permissions, queryset scoping, serializer validation, and finally Django's ORM/database constraints. Keeping all five layers matters: a hidden button in a frontend is never an authorization boundary.

List endpoints use page-number pagination. The configured filter backends provide exact filters, text search, and ordering only where a viewset declares allowed fields. `drf-spectacular` derives `schema.yml` and the `/api/docs/` interface from the real routes and serializers.

## accounts

Problem solved: identity, password handling, global role, and coarse staff visibility.

### Model

`accounts/models.py::User` extends `AbstractUser` but removes `username`. `email` is unique and is `USERNAME_FIELD`; `UserManager` normalizes email and always calls `set_password`, avoiding plaintext storage. `full_name` is display identity. `role` is student/instructor/admin authorization context. `level_preference` guides future tutor language. `weekly_hours`, `goal`, `language_preference`, `onboarding_data`, and `onboarded_at` support personalization. Inherited `is_staff` and `is_superuser` remain Django-admin controls; a role string alone does not grant Django admin.

An alternative was a separate profile model. The selected approach keeps frequently requested identity preferences in one row. Highly variable onboarding answers remain JSON rather than forcing unstable columns.

### Serializers and views

`RegisterSerializer` runs Django password validators, makes the password write-only, and calls `create_user`. It never accepts `role`, preventing public instructor/admin registration. `UserSerializer` excludes password and makes role and audit timestamps read-only.

`RegisterView` allows anonymous creation. `MeView` retrieves/updates only `request.user`. `UserViewSet` is read-only: admins see all users; instructors see only learners enrolled in their courses. `IsAdminRole`, `IsInstructorOrAdmin`, and `IsInstructorOwnerOrReadOnly` provide reusable role/object checks. Tests in `accounts/tests.py` cover registration, hashing, login, access/refresh tokens, invalid and expired tokens, safe profile updates, and staff visibility.

## courses

Problem solved: instructor-authored curriculum, ordered delivery, reusable knowledge concepts, and objective assessment definitions.

### Models and constraints

- `Course`: `instructor` owns the course; `slug` is a unique stable identifier; title/description are catalog text; `is_published` controls public catalog visibility; `metadata` holds non-core display attributes; timestamps audit changes.
- `Module`: belongs to a course and has title, summary, and position. `unique_module_position` prevents two modules occupying the same course position.
- `Lesson`: belongs to a module. `kind` distinguishes text/video/quiz, `content` and `resource_url` carry material, `estimated_minutes` supports planning, and position is unique within its module.
- `Concept`: `created_by` establishes instructor ownership; lessons indicate where it is taught; self-referential `prerequisites` create a directed graph; slug/name/description identify the skill.
- `QuizQuestion`: belongs to a lesson and optionally a concept. `kind`, JSON options/answer, explanation, normalized 0–1 difficulty, and points support multiple-choice, true/false, and short-answer questions. The answer is JSON because its type varies.

Database uniqueness handles concurrent ordering collisions. Serializer graph traversal rejects indirect prerequisite cycles during API updates; database SQL cannot conveniently express an arbitrary graph-cycle constraint.

### Serializers, viewsets, and permissions

`QuizQuestionSerializer` hides `correct_answer` on output, verifies multiple-choice option counts/indexes, and checks lesson ownership. `LessonSerializer` and `ModuleSerializer` validate the selected parent course belongs to the author. `CourseSerializer` conditionally nests curriculum only for admins, owners, and active enrollees; public catalog users see metadata without learning content. `ConceptSerializer` validates lesson ownership, direct self-links, and indirect cycles.

Every resource uses a `ModelViewSet`. `CourseViewSet` allows public reads of published courses and instructor/admin writes. Child viewsets require authentication and scope reads to owned or actively enrolled courses. `select_related`/`prefetch_related` avoid per-row relation queries for nested output. Declared filters, search, and ordering are reflected in OpenAPI. `courses/tests.py` covers ownership attacks, student denial, enrollment-gated reads, unique positions, hidden answer keys, invalid questions, graph cycles, and list backends.

## learning

Problem solved: connect learners to courses and store adaptive state without mixing it into authored curriculum.

### Models and constraints

- `Enrollment`: learner/course/status plus enrollment/completion dates. `unique_enrollment` permits one lifecycle row per learner/course instead of duplicate active enrollments.
- `LearningProfile`: one-to-one with a user. Five 0–1 values—modality, depth, pace, abstraction, preferred time—represent the Aurex learning fingerprint; `updated_at` records recalculation.
- `Mastery`: unique learner/concept probability, stability days, last seen, and update time. It is separate from attempts because it is a derived longitudinal estimate.
- `QuizAttempt`: learner, protected question, JSON answer, server-computed correctness/points, seconds, feedback, and creation time. `PROTECT` retains the assessed question while attempts exist.
- `RoadmapStep`: enrollment, same-course module, unique ordered position, optional target date, rationale, and completion timestamp.
- `EngagementEvent`: learner, indexed kind/time, optional module, and flexible payload. This is deliberately append-oriented analytics input.

### Serializers, viewsets, permissions, and grading

`EnrollmentSerializer` always assigns the requester, restricts self-enrollment to students, and requires a published course. Its database unique constraint handles races. `LearningProfileSerializer` produces a friendly duplicate-validation error. `MasterySerializer` is entirely read-only.

`QuizAttemptSerializer` requires active enrollment, validates the answer type/range for the question kind, computes correctness/feedback/points, creates the immutable attempt, and updates mastery inside one transaction. Short answer matching is trimmed and case-insensitive; semantic AI grading is intentionally absent. The fixed `+0.10/-0.05` mastery step is a testable baseline rather than a claim of complete BKT.

`RoadmapStepSerializer` enforces enrollment/course consistency and instructor ownership. Students may read and complete their own step but only teaching staff may author or rewrite plans. `EngagementEventSerializer` prevents events against modules outside the learner's active courses.

The viewsets use model-specific query joins so instructors see only records connected to their courses; students see only themselves; admins see all. `learning/tests.py` and `learning/test_e2e.py` cover constraints, isolation, attempts/mastery, roadmap/event rules, and complete seeded journeys. `seed_demo` lives in `learning/management/commands/seed_demo.py`; it is development-only and uses stable keys with `get_or_create`/`update_or_create` for idempotency.

## study_tools

Problem solved: persist source-backed study activity while isolating every user's documents, chats, flashcards, and routines.

### Models and constraints

- `Document`: owner, optional course, title, exactly one uploaded file or URL, processing status, topics, metadata, and creation time.
- `DocumentChunk`: document, text, unique position, optional page, and `embedding_ref`. The reference is an external vector-store key; large vectors do not belong in ordinary SQL rows.
- `Conversation`: owner, optional course, title, and timestamps. `Message`: conversation, user/assistant/system role, content, legacy metadata, and creation time.
- `Citation`: message and protected document chunk, quote, and optional bounded similarity score. `unique_message_chunk_citation` avoids duplicate evidence links.
- `FlashcardDeck`: owner, name/description/topics and timestamp. `Flashcard`: deck, prompt/answer, source-document links, SM-2 easiness/interval/repetitions/next review, and review totals.
- `Routine`: owner, name, flexible preferences, active flag, generated suggestions, and timestamps. `ScheduleBlock`: routine, activity, start/end, category, flexibility, and notes.

### Serializers, viewsets, actions, and scheduling

`DocumentSerializer` combines PATCH data with existing fields, enforces exactly one source, and validates owned/enrolled course context. `DocumentChunkSerializer` allows only the document owner and hides the external embedding reference on reads. `CitationSerializer` returns a real chunk id, document title, page, quote, and score. Citations are nested under read-only `MessageSerializer`, preventing clients from inventing assistant evidence through the user-message action.

`ConversationSerializer`, `FlashcardDeckSerializer`, and `RoutineSerializer` use nested read views but separate child endpoints for controlled writes. Card serializers verify both deck and every source document belong to the requester, including on updates. Schedule blocks similarly validate the routine and time ordering.

All base querysets are owner-scoped. `ConversationViewSet.messages` creates a user-role message regardless of submitted role. `FlashcardDeckViewSet.due` includes new/null and overdue cards. Its `review` action accepts quality 0–5 and applies SM-2-style intervals: failed recall resets to one day; successful recall advances repetitions and ease-based intervals. These are scheduling fields clients cannot mass-assign. Tests in `study_tools/tests.py` cover source validation, cross-owner attacks, citations, due/review behavior, and routines.

### Document processing and RAG services

[rag_architecture.md](rag_architecture.md) contains the full design. `DocumentSerializer` verifies bytes, size, checksum, MIME/container shape, scope, and ownership. `DocumentViewSet.perform_create` queues `tasks.process_document_task` after commit. `services.document_processing.process_document` calls extraction, chunking, embedding, and atomic version replacement; clients cannot write chunks or embeddings.

`providers/base.py` defines vendor-neutral contracts. Fake providers make tests deterministic; OpenAI providers are optional and environment-configured. `services.access.authorised_documents` is reused by `services.retrieval.retrieve_chunks`, so list permissions cannot be bypassed by RAG. `services.rag_pipeline.answer_question` limits history, retrieves, generates, validates IDs, and atomically writes messages/citations. `ProviderUsage` stores counts and latency without prompts/source text.

Document actions report status, retry failures, reprocess versions, and provide staff retrieval preview. Conversation `ask` returns a cited assistant message; `archive` preserves history without exposing it as active. Expensive actions use per-user throttles. `study_tools/test_rag.py` covers services and HTTP behavior without external calls.

## Routing and endpoint conventions

`config/urls.py` exposes router collections under `/api/v1/`: users, courses, modules, lessons, concepts, questions, enrollments, learning-profiles, masteries, attempts, roadmap-steps, events, documents, document-chunks, conversations, flashcard-decks, flashcards, routines, and schedule-blocks. Router detail URLs append `{id}/`.

Custom actions are roadmap completion, conversation message creation, due cards, and card review. Auth uses register, token, token refresh, and me. The Django admin is `/admin/`; each app's `admin.py` registers its models.

## Alternatives and future boundaries

A single giant LMS app would reduce imports but couple unrelated release cycles. Generic JSON records would be flexible but lose referential integrity and safe ownership joins. Nested writable serializers would reduce request count but make authorization and partial failure harder. The current explicit resources favor correctness and inspectability.

Future AI calls should live in service modules and asynchronous tasks, not model `save()` or serializers. The service should retrieve only owner-authorized chunks, persist assistant messages and normalized citations atomically, and expose job state. Signals are intentionally absent: important state changes such as grading are explicit and testable in serializer/service flow rather than hidden side effects.
