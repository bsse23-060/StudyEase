# Frontend architecture

The BFF now also carries measurable XHR uploads. Atomic quizzes, full flashcard CRUD, recurrence schedules, course-scoped builder routes, and paginated conversation history continue to share the central API and query boundaries. See [product_completion.md](product_completion.md).

## Shape and routing

`frontend/src/app` uses App Router route groups. Public routes are `/login` and `/register`. `(app)` routes share `AppShell`, which loads `/auth/me/`, guards unauthenticated navigation, and builds student or instructor navigation from the returned role. DRF permissions still enforce every direct URL and object operation.

The main student routes are dashboard, catalogue/detail, enrolled learning/lesson, quiz, roadmap/mastery, flashcards, schedule, documents, assistant, and profile. Instructor routes cover owned courses, builder, authorised students, and retrieval preview. Next loading, error, and not-found boundaries prevent blank screens.

## API and authentication

Browser code calls one client in `lib/api/client.ts`; endpoints live in `lib/api/endpoints.ts`. The client supports JSON, multipart bodies, cancellation through standard `RequestInit.signal`, DRF field errors, pagination, and network/server/permission/throttle messages.

Calls go to `/api/backend/*`. Its route handler reads `HttpOnly` cookies, attaches the access JWT, and on one 401 attempts exactly one refresh. Rotation writes the returned access and optional refresh token. Failure clears the session. Login/registration/logout use focused route handlers. This BFF choice is preferable to `localStorage`: injected browser code cannot extract a seven-day refresh token, CORS is unnecessary, and server-only `DJANGO_API_BASE_URL` is not exposed.

## State, forms, and validation

TanStack Query holds only server state. Keys are domain-specific; mutations invalidate their narrow collection/detail. Authentication cache clears on logout. Polling occurs only for non-terminal document states at five-second intervals and stops at a 60-poll ceiling. High-risk enrolment, quiz, RAG, processing, and review mutations are not optimistic.

React Hook Form is used for credential forms, where field association/error mapping matters most. Shared Zod schemas validate credentials, courses, files, questions, routines, and time ordering. Smaller authoring controls use local controlled state. DRF errors always win.

## Design and accessibility

The system uses semantic native controls, visible focus, a skip link, logical headings, table headers, progress semantics, live status/alert regions, and reduced-motion CSS. `ui.tsx` supplies buttons, labelled fields, badges, progress, skeleton/empty states, toasts, and a keyboard-dismissable confirmation dialog. Responsive desktop/mobile navigation is implemented without a heavyweight UI library.

Manual checks still required before production: complete screen-reader journeys (NVDA/VoiceOver), browser zoom at 200/400%, Windows High Contrast, touch target review on physical devices, and focus return after all future dialogs.

## Security and performance

No lesson or AI content is interpreted as HTML. External lesson links use `noopener` behavior. Return URLs accept only a single-leading-slash path. Headers disable framing, MIME sniffing, camera/microphone/geolocation, and restrict CSP sources. Client environment values contain no credentials.

Lists use backend pagination where exposed; search is deferred; Next splits routes; polling is controlled; query state is not duplicated globally. The dashboard requests small pages. Known limitation: the backend schema does not formally describe `page_size` as a public parameter even though DRF may ignore it under the default paginator.
