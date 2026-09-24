# Milestone 4 - Registration and selection

Status: in progress. Authority: master Sections 8, 9, 30 and backlog A01/A02/P01.

## A01.1 - configurable applicant-owned drafts

Scope: establish the application boundary without inventing final program policy. A published, organization-scoped form version contains ordered English/Tamil typed fields. An authenticated Person can create one draft per form version, resume it, and save a new immutable relational revision using optimistic concurrency. Required-field completion is computed from the saved revision. Draft access is owner-only and consequential changes are audited without answer content.

Submission, application numbers, eligibility decisions, declarations/consent, documents, staff review and CRM final conversion remain unavailable until their product/privacy prerequisites are approved.

Acceptance criteria:

1. No draft can be created without an explicitly published form; no production form or business policy is seeded by migrations.
2. Each save creates a new immutable revision and typed relational answers; stale versions conflict.
3. Another user or organization cannot read or mutate the draft and receives no ownership disclosure.
4. The English/Tamil web flow covers unavailable, empty, saving, saved, conflict and responsive states through a fixed BFF allowlist.
5. Migration upgrade/downgrade/drift, PostgreSQL ownership/version/type tests, generated contracts, backend checks, web lint/type/tests/build and local smoke pass.
6. A local-only CLI may create clearly synthetic fields for development review. There is no submission endpoint.

## A01.2 - application definition administration and policy versioning

Scope: authorized staff create and edit one organization-scoped definition draft, copy an immutable published/retired version into the next policy version, inspect history and publish through a separate permission. Publication atomically retires the prior live policy. Existing applicant drafts stay pinned to their original definition.

Acceptance criteria:

1. Program Managers can view/create/update definitions; Program Directors and Super Admins additionally publish.
2. Draft writes use optimistic edit revisions, stable unique field keys, bounded bilingual labels and ordered typed fields.
3. Published/retired policy content is immutable in both the service and PostgreSQL; only the lifecycle transition to retired remains possible.
4. Publishing is atomic, audited without policy text, and does not alter existing applicant revisions.
5. The English/Tamil staff workspace uses a fixed BFF allowlist, CSRF/origin checks, bounded bodies, private no-store responses and permission-aware controls.
6. Migration round-trip/drift, PostgreSQL policy tests, authenticated API tests, contracts, backend checks, frontend tests/build and local smoke pass.

## A01.4 - declarations, consent and immutable submission

Scope: bind applicant drafts to an open application cycle and its immutable form policy; configure bilingual declaration/consent acknowledgements with that policy; validate all required answers and acknowledgements; submit exactly once; preserve the submitted revision and acceptance evidence; generate a non-PII application number; and expose applicant status history. Supporting documents remain disabled pending A01.3 storage, malware-scanning and retention approval.

Acceptance criteria:

1. Only the authenticated owner can submit a draft, and only to its organization-scoped open cycle during the configured UTC window.
2. Submission rejects missing required answers, missing required declaration/consent policy, stale versions and cycle/form mismatch without partial writes.
3. One application per person per cycle and a unique server-generated application number prevent duplicate submission; a retry of the successful command returns the same submitted result.
4. The current revision, acknowledgements, application number, submitted timestamp and status history are committed atomically and submitted applicant evidence is database-immutable.
5. The English/Tamil applicant workspace covers cycle selection, draft saving, declaration/consent review, final confirmation, submitted receipt, status, loading, empty, validation, conflict and error states through the secured BFF.
6. Migration round-trip/drift, PostgreSQL ownership/concurrency/immutability tests, authenticated API tests, contracts, backend checks, frontend tests/build and local smoke pass.

## P01.1 - program delivery foundation

Scope: add organization-scoped programs, training centers, cohorts and application cycles. Programs and centers form the reusable catalog; cohorts bind an active program to an active center and a delivery window; application cycles bind an active program, optional compatible cohort and published application definition to an intake window. All writes use optimistic versions and audited, reasoned lifecycle commands.

Acceptance criteria:

1. Composite foreign keys prevent cross-organization or cross-program references in PostgreSQL.
2. Program Managers and Directors can administer the organization catalog; Training Center Coordinators have read-only catalog access until narrower center bindings are designed.
3. Lifecycle transitions are explicit, version checked and audited with a reason; inactive dependencies cannot be activated or opened.
4. The English/Tamil staff workspace covers create, list, empty, loading, error and lifecycle states through a fixed, bounded, CSRF-protected BFF.
5. Migration round-trip/drift, PostgreSQL lifecycle/RBAC tests, contracts, backend checks, frontend tests and production build pass.
6. Participant, enrollment, session and selection behavior remains unavailable for A02/P01.2 so no second Person model or unapproved enrollment path is introduced.

## A02.1 - selection configuration, rubric versioning and reviewer assignment

Scope: bind one organization-scoped selection cycle to an application cycle, configure ordered bilingual weighted criteria in versioned rubrics, publish immutable policy, activate review only after intake closure, assign submitted applications to eligible reviewers, and require the assigned reviewer to declare a conflict or clearance before scoring. Interviews, scores, decisions, overrides and enrollment conversion remain unavailable until A02.2/A02.3.

Acceptance criteria:

1. Program Managers can prepare cycles, rubrics and assignments; Program Directors and Super Admins additionally publish rubrics; Selection Committee members see only their own assignments.
2. Criterion keys are unique and bounded, score ranges are valid, weights total exactly 100, writes use optimistic versions, and one draft and one published rubric at most exist per cycle.
3. Published/retired rubrics and criteria are database-immutable; a new version is copied from a published/retired version and existing assignments retain their rubric.
4. Review activation requires a closed application cycle and a published rubric. Assignment requires the matching organization, intake, active cycle, published rubric and reviewer permission.
5. First assignment performs the only A02.1 application transition, submitted to under_review, with immutable status history and audit; submitted answers, consent, identity and receipt evidence remain frozen.
6. The English/Tamil staff workspace covers setup, versioning, publication, activation, assignment, reviewer inbox, conflict declaration, loading, empty and error states through a fixed, bounded, CSRF-protected BFF.
7. Migration round-trip/drift, PostgreSQL immutability/scope tests, authenticated API tests, contracts, backend checks, frontend tests/build and authenticated browser acceptance pass.

## Planned follow-ups

- A01.3: private documents after object storage, malware scanning and retention approval.
- P01.2: program sessions, selected-application enrollment conversion, participant projection and schedule timeline.
- P01.2 owns selected-application enrollment conversion after A02.3 finalization.

## A02.2 - reviewer scoring, comments, moderation and weighted aggregation

Scope: assigned reviewers may save criterion-score drafts and an internal comment after clearing conflicts, then submit once against the assignment's pinned rubric. The server normalizes each criterion within its configured range and applies published weights to produce a score out of 100. Submitted evidence is immutable. Program Directors and Super Admins may exclude or restore a completed review from aggregation with a reason; the evidence itself is unchanged. Managers see per-application averages over included completed reviews. Interviews and selection decisions remain A02.3.

Acceptance criteria:

1. Only the assigned reviewer can save or submit, and only while the selection cycle is active and conflict status is clear.
2. Scores reference only criteria in the pinned rubric, remain within configured bounds and include every required criterion before submission.
3. The API calculates the weighted score; clients cannot supply it. PostgreSQL prevents score/comment/evidence mutation after submission.
4. Moderation requires `selection.review.moderate`, a new optimistic version and a reason; every change is audited and only affects aggregate inclusion.
5. Aggregates average included, completed weighted scores and report completed, included and excluded counts; reviewers do not receive aggregate results.
6. English/Tamil browser flows, fixed BFF routes, OpenAPI contracts, migrations, RBAC, database tests, lint, types and builds meet the shared Definition of Done.

## A02.3 - interviews, decisions, overrides and finalization

Scope: turn completed review evidence into a reasoned shortlist, schedule one organization-scoped interview with one or more eligible panel members, accept one immutable score/comment from each panel member, calculate the interview average server-side, record selected/waitlisted/rejected decisions with evidence snapshots, permit reasoned terminal-decision overrides only to authorized directors, and finalize the selection cycle only when every assigned application is terminal and no interview remains open. Enrollment conversion remains P01.2 because it must create the participant and unique enrollment transaction together.

Acceptance criteria:

1. Shortlisting requires at least one included completed review and `selection.decision.manage`; reviewers cannot decide.
2. Interview scheduling requires a shortlisted application, active selection cycle, valid time range, mode/location rules and one to ten active users with `selection.interview.score`.
3. Each panel member can submit one bounded score and internal comment only for their assigned interview. Submitted panel evidence and completed interviews are database-immutable.
4. Interview completion requires every panel member score and calculates the arithmetic average on the server.
5. Selected, waitlisted and rejected decisions require `selection.finalize`, optimistic application versioning, an evidence-backed reason and a completed interview when one is scheduled.
6. Changing a terminal decision requires `selection.decision.override`, an explicit override flag and reason. Decision rows and review/interview score snapshots are append-only.
7. Cycle finalization requires `selection.finalize`, terminal decisions for every assigned application and no scheduled interview.
8. English/Tamil UI, fixed BFF routes, applicant status receipt, audit, migration rollback, API contracts, tests and authenticated browser acceptance satisfy the shared Definition of Done.
