# Milestone 6 plan

Status: L01.1, L01.2 and L01.3 implemented and locally accepted; remote CI and later Phase 6 slices remain open.

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
