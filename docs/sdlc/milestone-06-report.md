# Milestone 6 implementation report

Status: L01.1-L01.3 and L02.1-L02.2 implemented and locally accepted; Milestone 6 remains in progress.

## Delivered behavior

Migration 7e6ae3e5a10d adds organization-scoped Course, ordered CourseModule, Lesson, private LessonMaterial, CohortCourse and CourseEnrollment. Composite foreign keys enforce parent and organization boundaries, unique constraints enforce ordering, and PostgreSQL triggers freeze course structure after publication.

Program Directors, Program Managers and Super Admins can author bilingual course structure, publish a complete draft with an exact version and reason, and assign the published course to a planned or active cohort. Participants receive lms.learn, but the service derives access through the authenticated Person, active Participant, active program Enrollment, cohort assignment and published Course. Starting is idempotent. Learner DTOs omit the private provider key.

The Next.js staff course studio and learner pathway provide English/Tamil loading, error and empty states, permission-aware navigation, CSRF-protected fixed BFF routes and responsive ordered course spines. Local/test private material delivery is implemented through a confined filesystem adapter; production object/video hosting remains a release gate.

## Definition of Done evidence

| Gate | Result |
| --- | --- |
| Story and acceptance criteria | Passed; documented in milestone-06-plan.md |
| Migration, constraints, indexes and rollback | Passed; downgrade/re-upgrade and drift clean |
| Business rules and stable errors | Passed; incomplete publication, frozen structure, publication and assignment rules tested |
| Permissions and scope | Passed; wrong organization and unassigned course denied; learner ownership is server-derived |
| Audit and sensitive data | Passed; writes audited; lesson bodies/provider keys excluded from audit and provider key excluded from learner responses |
| Web UI and API integration | Passed locally for staff and participant routes |
| Localization and accessibility | English/Tamil parity implemented; native labels, focus states and responsive browser checks pass |
| Automated tests | Passed: 84 backend tests and 32 Vitest tests |
| OpenAPI/client contract | Regenerated and typechecked |
| Security review | Passed for L01.1 boundary; signed media remains deliberately disabled |
| Logs/monitoring | Existing request correlation and stable error handling apply; no new worker introduced |
| Documentation | API, architecture, ERD, security, testing, deployment and user guidance updated |
| Lint, typing and builds | Focused LMS Ruff/strict MyPy and web lint/type/build pass; repository-wide legacy debt remains separately tracked |
| Manual/browser smoke | Authenticated Chrome journey passes staff authoring through learner start, persistence, responsive layout and no JS errors |
| Remote CI | Pending until this change is pushed |
| Native Flutter | Deferred under ADR 0004; no Flutter feature included in L01.1 |

## Remaining L01 scope

Flutter learning screens remain deferred under ADR 0004. L02.1 quizzes/automatic grading and L02.2 assignments/manual grading are complete; assessment completion eligibility, attendance and certificates remain later Phase 6 slices. Production object/video hosting and remote CI evidence remain release gates.

## L01.2 implementation

Implemented ordered lesson prerequisites, all-lessons/minimum-lessons completion rules, immutable lesson evidence, versioned course-enrollment aggregation, automatic completion, participant progress UI, and count-only staff cohort summaries. Local PostgreSQL acceptance proves prerequisite enforcement, idempotency, aggregation, finalization, and database immutability. Verification passed: both L01.2 migrations upgrade cleanly; the base migration and trigger-only hardening rollback/reapply without drift; focused Ruff and strict MyPy pass; the full API suite passes 84 tests; TypeScript, ESLint, 32 Vitest tests, and the Next 16 production build pass; authenticated Chrome acceptance completes a lesson, reaches 100% course completion, validates responsive layout, and reports no JavaScript errors. The generated OpenAPI and TypeScript contracts are current. Native Flutter remains deferred under ADR 0004, remote CI confirmation remains open, and existing repository-wide CMS/early-migration Ruff/MyPy debt is unchanged.

## L01.3 implementation

Implemented `lms.delivery.view`, Trainer grants, active center/cohort assignment enforcement, a bounded trainer delivery projection, learner and trainer material-access commands, actor-bound HMAC capabilities, reauthorization at file delivery, confined local-file resolution, audit evidence, binary BFF streaming and English/Tamil trainer and learner interfaces. ProgramStaffAssignment now accepts accounts holding either Training Center Coordinator or Trainer without creating duplicate scope tables. The migration adds permission catalog and role grants only; existing LMS entities remain unchanged.

Focused PostgreSQL acceptance proves unassigned denial, assigned cohort visibility, safe material metadata, trainer and learner file delivery, token tamper rejection and immediate revocation. Migration downgrade/re-upgrade/drift is clean. Focused Ruff and strict MyPy pass; the full API suite passes 86 tests; TypeScript, ESLint, 32 Vitest tests and the Next 16 production build pass. Authenticated Chrome proves trainer cohort scope, trainer and learner private-material downloads, progress completion, responsive layouts and no JavaScript errors. OpenAPI and generated TypeScript contracts are current. Production private object/video hosting, remote CI, native Flutter and legacy repository-wide CMS/MyPy debt remain open gates outside this slice.

## L02.1 implementation

Migration b2a8d4e6f901 adds organization-scoped quizzes, questions, choices, attempts and answer evidence with composite scope constraints, bounded values, immutable submissions and published-definition protection. Managers author bilingual single-choice quizzes; publication validates complete answer keys. Learners receive no correctness flags and submit through an enrollment-scoped command that derives score, percentage and pass state. Trainers see only bounded cohort result summaries.

Local acceptance passed: the full backend suite reports 86 tests; focused Ruff and strict MyPy pass; migration downgrade/re-upgrade/drift is clean; OpenAPI and TypeScript contracts are current; ESLint, TypeScript, all 32 Vitest tests and the Next 16 production build pass. Authenticated Chrome creates and publishes a quiz, submits failed and passing attempts, confirms automatic grading and persisted evidence, and reports no JavaScript errors. The local Next build uses one page-data worker because the Windows host cannot commit memory for the default 15 workers. Remote CI remains pending. The assignment/manual-grading work that followed is recorded in L02.2 below; completion eligibility and certificates remain open.

## L02.2 implementation

Migration `c3b9e5f7a012` adds organization-scoped assignment definitions, immutable learner revisions and immutable manual grades. Managers author bilingual text assignments before publication. Learner commands derive enrollment, enforce prerequisites and submission limits, and require grading before a later revision. Trainers grade only learners covered by their active cohort assignment; the server validates score bounds and derives pass state. Learner and trainer views expose scoped response/feedback evidence, while audit payloads omit that content.

Local acceptance passed for the focused PostgreSQL workflow, migration downgrade/re-upgrade/drift, focused Ruff and strict MyPy, generated OpenAPI and TypeScript contracts, ESLint, strict TypeScript, all 32 Vitest tests and the Next 16 production build. Authenticated Chrome creates an assignment, submits a learner response, records a trainer grade and confirms learner feedback visibility with no JavaScript errors. Text submission is complete; file uploads remain blocked on the shared secure-upload pipeline. Remote CI, assessment-based completion eligibility and certificates remain open.
