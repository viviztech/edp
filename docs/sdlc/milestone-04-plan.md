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

## Planned follow-ups

- A01.3: private documents after object storage, malware scanning and retention approval.
- P01.2: program sessions, selected-application enrollment conversion, participant projection and schedule timeline.
- A02: review, rubric, interviews, decisions and enrollment conversion.
