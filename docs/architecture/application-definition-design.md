# Application definition administration design

Status: implemented in A01.2. Authority: master Sections 8, 15, 19, 21, 36 and 37.

## Policy boundary

An application definition belongs to one organization and has a monotonically increasing policy version. At most one definition may be an editable draft. A published or retired version is immutable policy evidence: titles and fields cannot be changed, and its ordered bilingual field rows cannot be inserted, updated or deleted. PostgreSQL triggers enforce this even when a write bypasses the service.

Creating the first policy or copying a published/retired version produces a new draft. Draft updates replace the complete ordered field set under an optimistic edit revision. Publication locks the draft, validates the revision, retires the current live definition, publishes the new version and audits the command in one transaction. Existing applicant drafts retain their original form and fields; only newly created drafts use the newest published definition.

Definitions contain stable field and section keys, English/Tamil labels, a bounded answer type, required flag and position. They do not define eligibility decisions, documents, declarations, consent, submission, review, or retention policy. Those remain unavailable until their separate requirements are approved.

## Authorization and audit

The organization-scoped permissions are application.form.view, application.form.create, application.form.update and application.form.publish. Program Managers receive view/create/update. Program Directors and Super Admins also receive publish. Every API command rechecks its permission. Publication is never inferred from edit access.

Create, update, copy and publish write an audit row with actor, organization, resource, request ID, edit revision and changed field names. Titles, labels and applicant answers are excluded from audit text.

## API and web

Staff endpoints are under /api/v1/applications/organizations/{organization}/definitions. Commands carry expected_revision and return 409 on stale state. Out-of-scope identifiers return 404 after the permission boundary. The Next.js workspace is /{locale}/admin/application-definitions and uses a dedicated fixed BFF allowlist, bounded JSON body, browser session, origin/CSRF validation, no-store responses and noindex headers.

## Operations and rollback

Apply migration c4f5a6b7c8d9 and rerun the idempotent identity role seed before using the workspace. Code rollback should leave the policy tables and trigger protections in place. Schema downgrade removes the triggers, partial draft index, publisher reference and edit revision, so it is destructive policy weakening and is limited to disposable databases unless an approved backup and rollback procedure exists.
