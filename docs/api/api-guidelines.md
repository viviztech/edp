# API conventions

Base `/api/v1`; FastAPI Pydantic v2 request/response schemas, UUID IDs and UTC RFC3339 timestamps. OpenAPI is authoritative. Health `/health` and readiness `/ready` are infrastructure exceptions; probes expose only status.

Resources use plural nouns; explicit actions for consequential transitions, e.g. `POST /applications/{id}/submit`, not arbitrary status PATCH. Master Section 24 defines module route groups. Authorization runs before object serialization and before all writes. Return minimal public DTOs rather than model dumping.

Success: resource object, or `{items, next_cursor}` for lists; default limit 25, maximum 100. Allowlisted sort/filter fields with stable ID tie-breaker; opaque cursor validated. No unbounded export endpoints: authorized jobs plus short-lived download URLs and audit. Aggregates specify cohort/period/timezone.

Errors: `{error: {code, message, request_id, details?}}`; details contain field paths and codes, never submitted secrets. Clients localize by stable code. 201 create, 204 deletion/logout where appropriate, 400 malformed command, 401 unauthenticated, 403 permission denied, 404 absent or deliberately concealed out-of-scope object, 409 transition/version/idempotency conflict, 413 oversized, 415 unsupported media, 422 validation, 429 throttled with Retry-After, 503 dependency unavailable. No stack traces in responses.

Server-generated UUID `X-Request-ID` propagated to logs/jobs; do not trust arbitrary incoming strings. For mutable workflow commands require version/If-Match; lock and compare inside transaction. Avoid retrying non-idempotent commands automatically.

Idempotency-Key required for submissions/imports and retryable commands: scoped unique `(actor, operation, key)`, request digest, state, response/resource reference and expiry. Same body returns prior response; differing body returns 409. Concurrent requests serialize via constraint/lock. Expiry policy documented per feature. Webhook inbox unique `(provider,event_id)` and provider lead IDs additionally unique where available.

Browser auth is same-origin BFF; secure cookie plus Origin/CSRF checks. Mobile uses Authorization bearer. CORS explicit trusted origins only, never wildcard credentialed requests. Auth throttling, upload quotas and request-size limits are endpoint-sensitive. Signed private upload/download URLs require ownership checks, MIME/signature/size validation, quarantine and scan status; arbitrary server URL fetching disallowed.

OpenAPI export to `packages/api-contracts/openapi.json`; TypeScript generated types and Dart generator evaluated before auth integration. Check schema diffs in CI; generated files never manually edited. Breaking changes require `/api/v2` or an explicitly coordinated deprecation. No fabricated contract for unimplemented routes.

## Implemented foundation routes

POST /auth/register (202 generic), /auth/login, /auth/refresh, /auth/request-verification (202), /auth/verify, /auth/request-reset (202), /auth/reset, /auth/logout, /auth/logout-all, /auth/sessions/{id}/revoke. GET /auth/me, /auth/sessions (bounded 100), /system/organizations/{id}/access and /system/organizations/{id}/audit (limit 1?100, offset 0?10000). Current list contracts are bounded arrays; pagination envelope remains the convention for future domain collections.

Mobile uses opaque bearer access; refresh request field is token. Browser internal login is hidden from public OpenAPI and requires BFF key. Next.js /api/session proxy has a fixed route allowlist, no client-supplied upstream URL, 8 KiB JSON body cap, configured Origin and CSRF validation. Browser response contains no access/refresh/session credentials. CSRF token is fetched separately into page memory. Errors expose stable codes (invalid_credentials, invalid_session, invalid_token, rate_limited, forbidden, delivery_unavailable, csrf_failed). No reset/verification token in public responses.

Implemented CMS/public routes and schemas are now exported in OpenAPI. CMS uses 256 KiB request caps, locale-specific expected_version transitions, and UUID keyset cursors (limit 1-100). Public lists use no-store; public details use revision ETags with mandatory revalidation, checking current visibility before 304. Public responses exclude draft and staff fields. Browser /api/cms is a fixed-route proxy with Origin/CSRF validation for POST/PATCH.

## A02.1 selection endpoints

Selection uses /api/v1/selection/organizations/{org}. GET /workspace returns permission-filtered cycles, rubric versions, submitted summaries, eligible reviewers and assignments; reviewers receive only their own assignments and no management candidate lists. Cycle creation/update and explicit state commands are separate. Rubric replacement uses PUT /rubrics/{id} with expected_edit_version; publish and copy are explicit POST commands. Assignment and conflict declaration are explicit POST commands. The browser BFF mirrors only these UUID-shaped paths and does not allow score, decision, override, interview or enrollment routes before their scheduled slices.
## A02.2 review endpoints

`PUT /api/v1/selection/organizations/{org}/assignments/{assignment}/review` fully replaces a reviewer's draft scores and internal comment using `expected_version`. `POST .../submit` accepts only `expected_version`; the server validates completeness and calculates the weighted total. `POST .../moderation` accepts `expected_version`, `included|excluded` and a bounded reason under `selection.review.moderate`. The workspace returns score evidence with authorized assignments and manager-only application aggregates. Decimal scores serialize as strings. None of these commands accepts a weighted or aggregate score from a client.

## A02.3 interview and decision endpoints

`POST /api/v1/selection/organizations/{org}/interviews` schedules a panel interview for one shortlisted application with ISO-8601 timestamps, mode/location and unique panel user IDs. `POST .../interviews/{id}/score` submits the authenticated panel member's versioned score/comment once. `POST .../complete` accepts only the interview version and derives the average. `POST .../cycles/{cycle}/applications/{application}/decision` accepts the expected application version, target, bounded reason and explicit override flag. Weighted review scores, interview averages and decision snapshots are server-derived decimals serialized as strings. Cycle `closed` now means finalized and requires `selection.finalize`; generic cycle management cannot bypass finalization.

P01.2 extends `/api/v1/programs/organizations/{org}`. `POST /enrollments/convert` accepts application ID, exact version and reason; cohort/program/person are server-derived. `POST /sessions` creates a bilingual cohort session and `/sessions/{id}/state` completes or cancels it. `/participants/{id}/state` is an optimistic reasoned command. `GET /my-timeline` derives ownership from the authenticated Person and returns no staff selection evidence. The BFF mirrors only these exact UUID-shaped routes.


## P01.3 program staff assignment endpoints

P01.3 adds POST /api/v1/programs/organizations/{org}/staff-assignments and POST /api/v1/programs/organizations/{org}/staff-assignments/{id}/revoke. Creation accepts an existing coordinator email, center, optional cohort and reason; the response returns identifiers and display metadata but no role internals. Revocation requires the exact assignment version and reason. GET /catalog includes assignment state and applies coordinator scope before returning delivery data. The browser BFF permits only the two explicit mutation shapes.

## L01.1 learning endpoints

L01.1 uses /api/v1/courses/organizations/{org}. Authorized staff use GET /catalog, POST /, POST /modules, POST /lessons, POST /materials, POST /{course}/publish and POST /cohort-assignments. Publication requires an exact course version and reason. Assignment accepts only course, cohort, order and reason; organization scope and course publication are server validated.

Participants use GET /my-learning and idempotent POST /my-learning/{course}/start. Ownership is derived from the authenticated Person, active Participant and active program Enrollment. Learner material DTOs include safe labels and availability only; private provider keys never cross the learner API or browser BFF. The Next.js BFF allowlists only these exact UUID-shaped paths and applies Origin/CSRF checks to every mutation.

## L01.2 progress endpoints

Staff use POST /prerequisites and POST /{course}/completion-rule while a course is draft. Rule mutation requires expected_version and reason. Participants use POST /my-learning/{course}/lessons/{lesson}/complete with expected_course_enrollment_version. The command is idempotent after completion, returns the lesson evidence plus the recalculated course aggregate, and uses stable errors: course_not_started, lesson_prerequisite_incomplete, prerequisite_must_precede_lesson, completion_rule_invalid, and version_conflict. GET /catalog includes bounded cohort progress summaries; GET /my-learning includes lesson lock/completion state and derived progress.

## L01.3 trainer delivery and material endpoints

`GET /api/v1/courses/organizations/{org}/trainer-delivery` returns only published courses in the caller's active delivery scope, safe material metadata and bounded learner progress. `POST /my-learning/{course}/materials/{material}/access` and `POST /trainer-delivery/{course}/materials/{material}/access` return a short-lived BFF-relative URL after current authorization. `GET /material-delivery/{token}` requires the same authenticated actor, validates the signed capability and repeats current enrollment or assignment authorization before returning the file with attachment, private no-store and nosniff headers. Tokens and provider keys are never response fields. The browser BFF allowlists the exact UUID/token shapes, applies CSRF to access issuance and streams non-JSON responses.

## L02.1 quiz and automatic-grading endpoints

Authorized assessment managers use POST /api/v1/courses/organizations/{org}/quizzes, /quiz-questions, and /quiz-choices while the course is draft. Correct-answer flags appear only in the staff catalog. Course publication returns quiz_structure_incomplete unless every quiz has a question and every question has at least two choices and exactly one correct answer.

Participants submit POST /my-learning/{course}/quizzes/{quiz}/attempts with one question and choice pair per question. Identity, enrollment scope, prerequisites, attempt number, score, percentage and pass state are server-derived. GET /my-learning omits answer keys and returns attempt count, remaining attempts, best percentage and pass state. Trainer delivery returns only cohort-scoped result summaries.

## L02.2 assignment and manual-grading endpoints

Authorized assessment managers use `POST /api/v1/courses/organizations/{org}/assignments` while the course is draft. The request identifies the scoped course and lesson and supplies ordered bilingual instructions, maximum points, passing points and the submission limit. Published course protection freezes the definition.

Participants use `POST /my-learning/{course}/assignments/{assignment}/submissions` with a bounded text response. The server derives the enrollment and revision. It returns `assignment_review_pending` when the latest revision has no grade and `assignment_submission_limit_reached` when the frozen limit is exhausted. `GET /my-learning` returns only the learner's revisions, grade, pass state and feedback.

Authorized graders use `POST /trainer-delivery/{course}/assignment-submissions/{submission}/grade` with score points and bounded feedback. The server verifies exact cohort delivery scope, derives pass state, and permits one immutable grade. `GET /trainer-delivery` returns text submissions and grades only for authorized learners. File-upload fields and routes are intentionally absent until the shared secure-upload pipeline is approved.

## L02.3 eligibility and certificate endpoints

`GET /my-learning` and `GET /trainer-delivery` include a server-derived certificate eligibility projection with lesson-rule state, required/passed quiz and assignment counts, stable blocking reasons, and any issued certificate visible within the caller's existing scope.

`certificate.manage` uses `POST /certificate-templates` for bilingual drafts. `certificate.issue` uses `POST /certificate-templates/{template}/publish`, `POST /certificates/issue`, and `POST /certificates/{certificate}/revoke`; publish/revoke are optimistic and all commands require an audit reason. Issuance accepts only enrollment and published-template identifiers and recalculates eligibility server-side. Stable conflicts include `certificate_not_eligible`, `certificate_template_unavailable`, `certificate_already_issued`, and `certificate_already_revoked`.

Anonymous `GET /api/v1/certificates/verify/{code}` and `/qr` are read-only, length/pattern bounded, and return minimal verification fields. They omit recipient identity, organization identifiers, enrollment identifiers and certificate statement. The QR is an SVG encoding the public verification endpoint.

## L03 attendance endpoints

Attendance routes use `/api/v1/attendance/organizations/{organization}`. Staff read `GET /staff-workspace`, save a cohort policy with `PUT /policy`, create/close a window with `POST /windows` and `/windows/{id}/close`, create a manual record with `POST /sessions/{id}/records`, and correct it with `POST /records/{id}/correct`. Window creation returns the raw token and generated SVG data URL once so the secret never appears in a later request URL. Policy, close, and correction commands use expected versions. Every staff mutation requires a bounded reason.

Participants read `GET /my-attendance` and send `POST /check-in` with the one-time-displayed opaque token. The server derives actor, enrollment, session, status, percentage, and low-attendance state. Stable errors include `attendance_policy_required`, `attendance_window_active`, `check_in_window_closed`, `invalid_check_in`, `attendance_already_marked`, `attendance_unchanged`, `staff_assignment_required`, and `version_conflict`. No endpoint accepts latitude, longitude, or a client-derived attendance result.
