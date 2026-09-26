# Milestone 6 plan

Status: L01.1 implemented and locally accepted; remote CI and later L01 slices remain open.

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
