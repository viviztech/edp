# Milestone 6 plan

Status: L01.1-L01.3 and L02.1-L02.3 implemented and locally accepted; remote CI and later Phase 6 slices remain open.

## L01.1 course catalog and enrollment access

Story: as a program learning manager, I can prepare and publish a bilingual ordered course and assign it to a cohort; as an enrolled participant, I can see and start only courses assigned to my active enrollment.

Acceptance criteria:

1. Courses are organization scoped, bilingual, versioned and move from draft to published only when they contain at least one module and every module contains at least one lesson.
2. Modules, lessons and material references have database-enforced parent scope and unique ordering. Published course structure is immutable.
3. Only authorized Program Directors, Program Managers and Super Admins can author, publish and assign courses. Participants receive learning access only through their own active enrollment.
4. A course can be assigned only when published and the cohort belongs to the organization. Duplicate course/cohort and position assignments are rejected.
5. Learner responses expose lesson content and safe material metadata without exposing private provider keys. Actual signed media delivery remains blocked on the approved storage/provider adapter.
6. Starting a course is idempotent and creates one CourseEnrollment for the authenticated participant enrollment and course.
7. Consequential writes create reasoned audit evidence with identifiers and changed-field names only.
8. OpenAPI, generated TypeScript contracts, English/Tamil web states, PostgreSQL tests, lint, typing, migration round-trip/drift, build and authenticated browser acceptance satisfy the shared Definition of Done.

## Excluded from L01.1

- Lesson completion and prerequisite evaluation.
- Course progress projections and completion rules.
- Trainer course/cohort bindings.
- Signed media URL issuance and native media playback.
- Quizzes, assignments, grading and certificate eligibility.
- Native Flutter learning screens, deferred under ADR 0004.

## L01.2 lesson progress and completion

Scope: ordered prerequisites, draft-only completion-rule configuration, immutable lesson completion, derived learner progress, automatic course completion, cohort summary visibility, bilingual responsive web flows, version conflicts, audit, API contracts, migration rollback, and acceptance evidence. Native Flutter remains deferred under ADR 0004. Assessments, attendance, and certificates remain later slices.

## L01.3 trainer delivery and private materials

Scope: reuse active center/cohort ProgramStaffAssignment records for Trainer scope; expose a read-only published course and learner-progress delivery workspace; issue short-lived actor-bound material capabilities; stream local development files through the authenticated BFF; reauthorize on delivery; audit issuance and delivery; preserve provider-key secrecy; and document the production object/video adapter gate.

Acceptance criteria:

1. Trainer role access without an active center/cohort assignment is denied, and revocation removes access immediately.
2. Trainers see only published course delivery and learner progress for covered cohorts. Managers retain organization-wide delivery visibility.
3. Learners receive material access only after starting an assigned course and satisfying lesson prerequisites.
4. Access tokens bind organization, actor, mode, course, material and expiry; delivery repeats current authorization and rejects tampering, traversal and unavailable objects.
5. Provider keys, signing keys, tokens and filesystem paths never enter DTOs, client bundles, audit details or logs.
6. The local adapter is bounded to a configured read-only root. Production fails closed without a separate signing key and remains gated on approved private object/video hosting.
7. OpenAPI/contracts, English/Tamil web states, fixed BFF paths, PostgreSQL acceptance, focused lint/type checks, migration round trip, production build and authenticated browser evidence satisfy the shared Definition of Done.

Excluded: trainer authoring, public material URLs, custom video streaming, quizzes/assignments, attendance, certificates and native Flutter learning screens under ADR 0004.

## L02.1 quizzes and automatic grading

Scope: draft-only bilingual quiz/question/choice authoring, answer-key publication validation, immutable published definitions, enrollment-scoped attempts, server-derived scores, pass marks, attempt limits, safe learner projections and cohort-scoped trainer summaries.

Acceptance criteria:

1. Only lms.assessment.manage can create quiz definitions, and only while the course is draft.
2. Publication requires at least one question per quiz and at least two choices with exactly one correct choice per question.
3. Learner APIs and browser state never expose correct-choice flags.
4. Attempts require a started eligible course, satisfied prerequisites, one valid choice per question and available attempts.
5. The server derives attempt order, score, maximum, percentage and pass state.
6. Attempts and answer evidence are immutable and submissions are audited without answer content.
7. Trainer summaries require delivery scope and expose no answer key or selected-answer detail.
8. PostgreSQL, migrations, contracts, web checks, build and authenticated browser acceptance pass.

Excluded: free-text/file assignments, manual grading, assessment-based completion, certificates, attendance and native Flutter screens under ADR 0004.

## L02.2 assignments, manual grading and feedback

Scope: draft-only bilingual text assignments, frozen points and submission limits, immutable learner revisions, review-before-resubmission, trainer-scoped manual grading, server-derived pass state, learner feedback visibility and audit evidence.

Acceptance criteria:

1. Only `lms.assessment.manage` can add assignment definitions, and only to a draft course and scoped lesson.
2. Learners require their own active enrollment, a started assigned course and satisfied lesson prerequisites.
3. The server assigns sequential revisions and rejects a retry while review is pending or after the frozen limit.
4. Only `lms.assessment.grade` may grade; Trainers also require an active assignment covering the exact cohort.
5. Scores cannot exceed the frozen maximum, pass state is server-derived, and one immutable grade is stored per submission.
6. Response text and feedback are bounded, scoped and excluded from audit payloads.
7. PostgreSQL independently rejects definition mutation, submission/grade mutation and invalid or over-limit revisions.
8. Migrations, contracts, backend/web checks, production build and authenticated browser acceptance pass.

Excluded: file uploads, grade amendment workflow, assessment-based completion eligibility, certificates, attendance and native Flutter screens under ADR 0004.

## L02.3 assessment completion eligibility and certificates

Scope: derived lesson/quiz/assignment eligibility, versioned bilingual certificate templates, manual permissioned issuance, immutable certificate snapshots, reasoned revocation, unique verification identifiers, SVG QR codes, privacy-minimized public verification, and bilingual staff/learner/public web states.

Acceptance criteria:

1. Eligibility requires the course lesson rule and every configured quiz and assignment to have passing evidence.
2. Clients cannot set eligibility, pass state, recipient identity, snapshot text or verification identifiers.
3. Program Managers may prepare templates; only Program Directors/Super Admins may publish, issue or revoke.
4. One published template per course, one valid certificate per enrollment and unique verification identifiers are enforced.
5. Issuance is manual, recalculates eligibility under lock, and records reasoned audit evidence without personal/score payloads.
6. Certificates are immutable except exact versioned valid-to-revoked transition; database triggers reject rewrites/deletes.
7. Anonymous verification and QR omit recipient identity, internal IDs, statement, scores, responses and feedback.
8. Migrations/contracts, PostgreSQL/API/web tests, lint/types, production build and authenticated plus anonymous browser acceptance pass.

Excluded: automatic issuance, attendance gates, signatory rendering, PDF download, assignment files and native Flutter screens under ADR 0004.

## L03 attendance and QR check-in

Scope: cohort attendance policy, scoped manual marking, immutable correction evidence, time-limited digest-only QR windows, participant check-in, duplicate prevention, derived percentages and low-attendance state, bilingual responsive web flows, audit, contracts, migration rollback, and acceptance evidence.

Acceptance criteria:

1. Only authorized staff can view/manage attendance; Trainers and Training Center Coordinators also require an active center/cohort assignment.
2. Policy values are bounded and optimistic-versioned; one active QR window is allowed per scheduled session.
3. Raw QR token material is returned once, stored only as a digest, omitted from audit/normal reads, and rejected outside the exact window.
4. Check-in derives participant, active enrollment, session and Present/Late state on the server and rejects duplicate or wrong-cohort evidence.
5. Manual records support Present, Absent, Late and Excused; changes require exact version and reason and append immutable correction evidence.
6. Percentages count Present/Late, exclude Excused from the denominator, treat unmarked elapsed sessions as missed, and derive the low-attendance state from policy.
7. No precise location, biometric, or device-fingerprint data is accepted or stored.
8. PostgreSQL/API, migration, contracts, web checks, production build and authenticated browser acceptance satisfy the shared Definition of Done.

Excluded: location enforcement, biometrics, automatic certificate attendance gating, outbound low-attendance notification delivery, native Flutter attendance screens under ADR 0004, and remote CI.
