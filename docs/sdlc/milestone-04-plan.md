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

## Planned follow-ups

- A01.2: approved application definition administration and policy versioning.
- A01.3: private documents after object storage, malware scanning and retention approval.
- A01.4: declarations, consent, validation, immutable submission and application number.
- P01 foundation: programs, centers and cohorts.
- A02: review, rubric, interviews, decisions and enrollment conversion.
