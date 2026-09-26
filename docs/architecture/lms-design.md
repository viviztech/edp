# LMS design

Status: L01.1 and L01.2 implementation design.

## Boundary

The LMS module owns Course, CourseModule, Lesson, LessonMaterial, CohortCourse and CourseEnrollment. Programs owns cohorts, participants and the source Enrollment. Identity owns users, roles, permissions and audit evidence. LMS reads those boundaries through stable identifiers and never duplicates person data.

## Lifecycle

A course starts in draft. Ordered modules, lessons and private material references can be added only while the course is draft. Publication requires at least one module and at least one lesson in every module, increments the optimistic version and freezes the structure. A published course can be assigned to a cohort. CourseEnrollment is created idempotently when an eligible participant starts an assigned course.

## Authorization

- Super Admin, Program Director and Program Manager: view, manage, publish and assign courses within an organization grant.
- Participant: view/start published courses reachable through their own active Enrollment.
- Trainer: no LMS permission until a course/cohort trainer-binding model enforces assigned scope.
- Training Center Coordinator: no LMS permission in L01.1.

Every learner lookup resolves User -> Person -> Participant -> active Enrollment -> CohortCourse -> published Course. A caller-supplied enrollment identifier never establishes ownership.

## Materials

LessonMaterial stores a private provider reference and localized label. Learner DTOs omit the provider reference and report provider-pending availability. A future storage/video adapter will issue short-lived signed URLs after repeating the enrollment and lesson authorization check. L01.1 does not proxy arbitrary URLs or build video streaming.

## Integrity

Composite foreign keys enforce organization and parent scope. Unique constraints enforce module, lesson, material and cohort-course positions. PostgreSQL triggers reject structural insert, update or delete after publication. CourseEnrollment is unique by Enrollment and Course.

## L01.2 progress and completion

LessonPrerequisite links lessons inside the same organization and course. Authoring accepts only an earlier lesson in the ordered module/lesson spine, which makes cycles impossible. The database freezes prerequisite rows with the rest of the course structure after publication.

LessonProgress is one immutable completion record per course enrollment and lesson. Composite foreign keys prove that enrollment, course, lesson, and organization share one scope. The course progress view is derived from immutable lesson rows. CourseEnrollment is the mutable lifecycle aggregate: each new completion increments its version and transitions once from in_progress to completed when the frozen rule is met.

A course rule is either all_lessons or minimum_lessons. Rule changes require draft state, an exact course version, a reason, permission, and audit evidence. Publication rejects a minimum above the lesson count. Participant commands derive identity from the signed-in person and active participant enrollment, enforce prerequisites server-side, and are idempotent for an already-completed lesson. Staff catalog summaries expose cohort counts and percentages without participant identity.
