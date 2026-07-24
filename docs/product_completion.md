# studyEase product completion

## Compatibility and migrations

This phase preserves both original source projects and the four-app architecture. Three additive migrations extend rather than replace records:

- `courses/migrations/0003_*` adds course-scoped concepts, `Quiz`, ordered questions, and `QuizAnswerOption`. Its data migration assigns a concept's first lesson course, creates a quiz for every legacy lesson with questions, retains nullable lifecycle rules, and copies JSON options into stable option rows.
- `learning/migrations/0002_*` adds `QuizSubmission` and `QuizSubmissionAnswer`. Legacy `QuizAttempt` remains API-compatible; the new UI uses atomic submissions.
- `study_tools/migrations/0005_*` adds flashcard associations/review history and recurrence/timezone schedule fields. Legacy blocks become weekly/UTC with unknown weekday and must be completed before API editing.

## Curriculum, ownership, and prerequisites

`courses.models.Quiz` owns optional pass mark, attempt limit, availability, enforced time limit, and publication. `QuizQuestion.quiz`, `position`, and `is_required` add ordering/completeness while preserving its legacy lesson relationship. `QuizAnswerOption` provides stable option IDs; JSON options remain grading-compatible and `QuizQuestionSerializer._sync_options` synchronizes them. Correctness stays write-only.

`Concept.course` makes prerequisite scope explicit. `ConceptSerializer` validates course ownership, lesson-course consistency, same-course prerequisites, self-links, and indirect cycles. Course/module/lesson/quiz/question/option serializers validate nested ownership as well as URL objects. Owner-filtered querysets and DRF object permissions provide a second layer. Router CRUD is exposed for `/courses/`, `/modules/`, `/lessons/`, `/concepts/`, `/quizzes/`, `/questions/`, and `/quiz-options/`; students cannot author.

Frontend course sections are `/instructor/courses/[courseId]/{curriculum,concepts,quizzes,documents,students}`. Curriculum settings publish/update/delete; module/lesson deletes require confirmation. Concept controls show `prerequisite → concept`, and server cycle errors remain authoritative. Quiz controls manage lifecycle values and ordered questions.

## Atomic quizzes and reporting

`QuizSubmission` represents a started/submitted attempt; `QuizSubmissionAnswer` stores immutable graded answers. `QuizSubmitSerializer` validates duplicate IDs, quiz membership, required answers, types, publication, availability, enforced time limit, and prior submission. It then locks the row and grades answers, updates mastery, and stores total/maximum/percentage/pass state inside one transaction. Any failure rolls everything back.

1. `POST /quiz-submissions/` starts an authorised attempt and enforces the maximum.
2. `POST /quiz-submissions/{id}/submit/` accepts every `{question_id, answer}` exactly once.
3. `GET /quizzes/{id}/analytics/` returns privacy-safe attempts, unique students, mean/median/high/low, pass/completion rates, per-question correctness, and recent results to owners/admins.

The student page displays instructions, rules, attempts remaining, server-enforced limit, locally stored draft, unanswered count, confirmation, one atomic request, final result, feedback, and history. Legacy pass marks remain null, avoiding silent behavior changes.

## Flashcards and schedules

`FlashcardSerializer` supports owned CRUD, non-empty/duplicate validation, authorised associations, and course/lesson/concept consistency. SM-2 fields remain read-only. `FlashcardReview` stores interval transitions; an idempotency key prevents double scheduling. `/flashcards/{id}/reviews/` returns owned history. The UI supports search, create/edit/delete, due sessions, Space reveal, 0–5 shortcuts, screen-reader labels, server-confirmed advancement, and retained rating after errors.

`ScheduleBlock` stores either `once` plus date or `weekly` plus weekday 0–6, with IANA timezone, optional bounds/course, and active status. Validation covers end-after-start, recurrence consistency, bounds, IANA names, owner, and course access. Overlaps are allowed by documented policy because concurrent commitments can be intentional. The UI provides routine and block CRUD, confirmations, weekly/upcoming views, and stored/browser timezone disclosure.

## Uploads and long conversations

`frontend/src/lib/api/upload.ts` uses same-origin `XMLHttpRequest` through the existing BFF for real multipart progress, cancellation, DRF errors, and network failures. Transfer completion is distinct from queued/processing/ready extraction stages; cancellation cannot undo a request already fully received.

Conversation collections contain no messages and detail is capped at 30. `/conversations/{id}/history/?page=N` returns authorised 30-message pages, newest first at the database layer and chronological within each response. The UI loads earlier pages incrementally while retaining citation access.

## Tests and accessibility

Backend completion tests are `courses/test_completion.py`, `learning/test_quiz_completion.py`, and `study_tools/test_completion.py`: nested ownership, student denial, cycles, transactional rollback, duplicate/missing/foreign questions, availability, attempt limits, grading/analytics, review idempotency, recurrence/timezones, and conversation isolation.

Frontend tests cover transport/DRF errors, upload progress/cancellation/network errors, open redirects, validation, and accessible primitives. Playwright uses real seeded accounts for student/instructor/denial/atomic quiz flows and expanded axe scans. Fake AI providers prevent paid calls.

Automated scans do not establish WCAG compliance. Manually test NVDA with Firefox/Chrome; VoiceOver with Safari; keyboard-only dialogs, upload, ratings, builders, and history; 200%/400% zoom; Windows High Contrast; and mobile screen readers. Verify focus return, announcements, schedule reading order, and citation expansion.

## Remaining boundaries

- Recurrence supports one-time and weekly rules, not arbitrary RFC 5545 exceptions.
- Overlaps are permitted and not yet returned as advisory diagnostics.
- Course deletion is hard deletion where protected history allows it; production should add archival lifecycle.
- Quiz authoring edits JSON option text while synchronized stable option rows back the API.
- Manual assistive-technology validation remains outstanding.
