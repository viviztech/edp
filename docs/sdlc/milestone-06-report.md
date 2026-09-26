# Milestone 6 implementation report

Status: L01.1 and L01.2 implemented and locally accepted; Milestone 6 remains in progress.

## Delivered behavior

Migration 7e6ae3e5a10d adds organization-scoped Course, ordered CourseModule, Lesson, private LessonMaterial, CohortCourse and CourseEnrollment. Composite foreign keys enforce parent and organization boundaries, unique constraints enforce ordering, and PostgreSQL triggers freeze course structure after publication.

Program Directors, Program Managers and Super Admins can author bilingual course structure, publish a complete draft with an exact version and reason, and assign the published course to a planned or active cohort. Participants receive lms.learn, but the service derives access through the authenticated Person, active Participant, active program Enrollment, cohort assignment and published Course. Starting is idempotent. Learner DTOs omit the private provider key.

The Next.js staff course studio and learner pathway provide English/Tamil loading, error and empty states, permission-aware navigation, CSRF-protected fixed BFF routes and responsive ordered course spines. Signed media delivery remains unavailable pending an approved provider adapter.

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

Lesson progress, course-progress projection, prerequisites, trainer-scoped bindings, signed media access, Flutter learning screens and full course completion rules remain open. Quizzes, assignments and grading belong to L02.

## L01.2 implementation

Implemented ordered lesson prerequisites, all-lessons/minimum-lessons completion rules, immutable lesson evidence, versioned course-enrollment aggregation, automatic completion, participant progress UI, and count-only staff cohort summaries. Local PostgreSQL acceptance proves prerequisite enforcement, idempotency, aggregation, finalization, and database immutability. Verification passed: both L01.2 migrations upgrade cleanly; the base migration and trigger-only hardening rollback/reapply without drift; focused Ruff and strict MyPy pass; the full API suite passes 84 tests; TypeScript, ESLint, 32 Vitest tests, and the Next 16 production build pass; authenticated Chrome acceptance completes a lesson, reaches 100% course completion, validates responsive layout, and reports no JavaScript errors. The generated OpenAPI and TypeScript contracts are current. Native Flutter remains deferred under ADR 0004, remote CI confirmation remains open, and existing repository-wide CMS/early-migration Ruff/MyPy debt is unchanged.
