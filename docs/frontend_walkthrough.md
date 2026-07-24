# Frontend developer walkthrough

Completion routes live under `/instructor/courses/[courseId]/{curriculum,concepts,quizzes,documents,students}`. Student quizzes use atomic submissions; documents use the cancellable uploader; assistant history uses `/history/`; flashcards and schedules expose owned CRUD. See [product_completion.md](product_completion.md).

## Foundation

- `app/layout.tsx` installs metadata, global styles, the skip link, query client, and toast provider.
- `components/app-shell.tsx` is the authenticated responsive shell. It asks `useSession` for the real user and derives navigation from `role`; it does not pretend this is authorization.
- `lib/api/client.ts` is the only browser transport. It maps DRF field/non-field errors into `ApiError` and leaves multipart headers to the browser.
- `app/api/backend/[...path]/route.ts` is the security boundary that attaches/refreshes JWTs. It forwards status and safe JSON content type, never cookie or host headers.
- `validation.ts` holds schemas reused across features. Validation improves feedback; serializers remain authoritative.

## Student pages

`dashboard` composes small authorised pages of enrolments, roadmap steps, decks, routines, documents, and conversations. Missing server aggregates are not fabricated. `courses` supports deferred search and pagination; detail performs a non-optimistic enrolment. `learn` renders ordered nested modules/lessons and plain-text content. `quiz` derives controls from question kind, never receives `correct_answer`, warns on browser exit, prevents resubmission while pending, and displays server feedback.

`roadmap` renders immutable server mastery and a timeline whose only learner mutation is the supported `complete` action. `flashcards` requests the supported due action, reveals answers locally, explains 0–5 ratings, and sends each rating once to the server SM-2 action. `schedule` validates start/end wall-clock values; its copy calls out the missing date/weekday/timezone fields.

## Documents and RAG

`documents` validates the advertised 10 MB/type limits and posts `FormData`. It polls only while status is uploaded/queued/processing. Detail exposes safe metadata, authorised chunks, retry/reprocess actions in applicable states, and confirmed soft deletion.

`assistant` creates/lists conversations and loads selected history. Questions remain in the text area when a request fails, duplicate submissions are disabled, and no fake streaming appears. Messages render as plain text. Citation controls reveal only returned filename/title, page, section, chunk, score/quote fields. An answer without citations gets an explicit insufficient-support warning.

## Instructor pages

`instructor/courses` receives the owner-filtered queryset. `builder` creates courses, explicit-position modules/lessons, and basic questions; opening another instructor’s ID produces the backend-derived unavailable state. `students` intersects visible users and enrolments. `retrieval` posts an authorised diagnostic scope and labels similarity scores appropriately.

## Tests and related failure states

Vitest tests URL construction, multipart safety, DRF error mapping, pagination encoding, validation edges, progress semantics, confirmation, and keyboard Escape. Playwright covers real seeded student/instructor journeys, a cross-instructor denial, and axe analysis. Tests do not call paid providers; local fake providers remain active.
