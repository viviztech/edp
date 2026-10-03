# LMS design

Status: L01.1-L01.3 and L02.1-L02.2 implementation design.

## Boundary

The LMS module owns Course, CourseModule, Lesson, LessonMaterial, CohortCourse, CourseEnrollment, quiz definitions and attempts, and assignment definitions, submissions and grades. Programs owns cohorts, participants and the source Enrollment. Identity owns users, roles, permissions and audit evidence. LMS reads those boundaries through stable identifiers and never duplicates person data.

## Lifecycle

A course starts in draft. Ordered modules, lessons and private material references can be added only while the course is draft. Publication requires at least one module and at least one lesson in every module, increments the optimistic version and freezes the structure. A published course can be assigned to a cohort. CourseEnrollment is created idempotently when an eligible participant starts an assigned course.

## Authorization

- Super Admin, Program Director and Program Manager: view, manage, publish and assign courses within an organization grant.
- Participant: view/start published courses reachable through their own active Enrollment.
- Trainer: delivery access to published courses, safe materials and learner progress, plus manual assignment grading, only for cohorts covered by an active ProgramStaffAssignment.
- Training Center Coordinator: no LMS permission in L01.1.

Every learner lookup resolves User -> Person -> Participant -> active Enrollment -> CohortCourse -> published Course. A caller-supplied enrollment identifier never establishes ownership.

## Materials

LessonMaterial stores a private provider reference and localized label. Learner and trainer DTOs omit provider references. L01.3 uses a local-filesystem adapter for local/test development and issues short-lived, actor-bound HMAC access tokens only after authorization. Delivery repeats current enrollment or trainer-scope authorization. The adapter boundary can be replaced by approved object/video hosting without exposing provider keys or building a streaming platform.

## Integrity

Composite foreign keys enforce organization and parent scope. Unique constraints enforce module, lesson, material and cohort-course positions. PostgreSQL triggers reject structural insert, update or delete after publication. CourseEnrollment is unique by Enrollment and Course.

## L01.2 progress and completion

LessonPrerequisite links lessons inside the same organization and course. Authoring accepts only an earlier lesson in the ordered module/lesson spine, which makes cycles impossible. The database freezes prerequisite rows with the rest of the course structure after publication.

LessonProgress is one immutable completion record per course enrollment and lesson. Composite foreign keys prove that enrollment, course, lesson, and organization share one scope. The course progress view is derived from immutable lesson rows. CourseEnrollment is the mutable lifecycle aggregate: each new completion increments its version and transitions once from in_progress to completed when the frozen rule is met.

A course rule is either all_lessons or minimum_lessons. Rule changes require draft state, an exact course version, a reason, permission, and audit evidence. Publication rejects a minimum above the lesson count. Participant commands derive identity from the signed-in person and active participant enrollment, enforce prerequisites server-side, and are idempotent for an already-completed lesson. Staff catalog summaries expose cohort counts and percentages without participant identity.

## L01.3 trainer delivery and private materials

ProgramStaffAssignment is reused as the center/cohort trainer boundary. A Trainer role grant alone does not expose LMS data: an active assignment must cover the course cohort. Program Directors, Program Managers and Super Admins retain organization-wide delivery visibility. The trainer projection is read-only and includes published course structure, safe material metadata, learner display name and derived course progress. It does not expose person records, provider keys, applicant evidence or authoring commands.

Material access is a two-step capability flow. The authenticated learner or trainer requests access for a specific course/material pair; the service verifies current scope and returns a short-lived BFF-relative URL signed with organization, actor, course, material, mode and expiry. Delivery validates the signature and authenticated actor, then repeats the current scope check before resolving a provider key below the configured root. Absolute paths, traversal, missing files and root escapes fail closed. Production requires a dedicated signing key; local/test may reuse the local BFF key. Every issuance and successful delivery is audited without token or filesystem path values.

## L02.1 quizzes and automatic grading

A draft course may contain ordered bilingual quizzes attached to lessons. Each quiz defines a pass mark and an attempt limit from 1 to 10. Questions carry positive integer points and ordered bilingual choices. Publication rejects a quiz with no questions, fewer than two choices for a question, or anything other than one correct choice. Published structure triggers prevent insert, update or delete of quiz definitions.

The learner projection exposes question and choice text without the correctness flag. Attempt submission derives the participant, enrollment and course from the authenticated user, requires the course to be started, enforces lesson prerequisites, locks the course enrollment, and accepts exactly one choice for every question. The server calculates score, maximum points, rounded percentage and pass/fail. A pass or exhausted limit closes further attempts. Attempts and answer evidence are immutable.

Trainer results are read-only summaries limited by the existing active ProgramStaffAssignment cohort boundary. They show attempt count, best percentage, pass state and last submission time without selected answers or the answer key. Quiz results do not yet change lesson-based course completion; assessment-based completion and certificates remain later L02 slices.

## L02.2 assignments, submissions and manual grading

A draft course may contain ordered bilingual assignment definitions attached to lessons. Each assignment freezes its instructions, maximum and passing points, and a submission limit from 1 to 10 when the course is published. This slice accepts bounded text responses only. File evidence remains disabled until the shared upload pipeline provides type inspection, malware quarantine, private storage, retention and authorized delivery.

The learner command derives ownership through the signed-in person, active participant enrollment and started course, then enforces lesson prerequisites. Each submission is an immutable numbered revision. A learner may submit a later revision only after the preceding revision has a grade and while the frozen limit remains. The service locks the course enrollment, while PostgreSQL independently rejects skipped or over-limit revisions.

Manual grading requires `lms.assessment.grade`. A Trainer must also hold an active staff assignment covering the exact course cohort; organization-wide assessment staff retain their existing scope. The server bounds the score by the frozen maximum and derives pass state from the passing threshold. One immutable grade and bounded feedback record is allowed per submission. Learners see only their own response and feedback; trainers see only submissions in their delivery scope. Assignment grades do not yet change course completion.
