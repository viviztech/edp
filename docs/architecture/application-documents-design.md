# Application document bindings

Backend contract for Process 3, slice A01.3, introduced by migration
`i4e0f6a2b789` after `h3d9e5f1a678`. Collection remains disabled unless the server's
explicit file feature configuration enables it. This design does not approve a
document list, notice, format, size, count or retention period for real applicants.

## Form policy

An application form owns zero or more ordered document requirements. Existing
forms have none. The form's published edition freezes each requirement's key,
bilingual labels and instructions, explicit minimum and maximum file counts and
pinned `application_document` file-policy edition. Draft definition edits replace
their requirements; copying a published definition copies the rule values and
policy references into new draft rows. Publication validates every referenced
policy and the aggregate counts before freezing the form.

Definition commands carrying requirements require `files.policy.view` as well as
the existing application-form permission. Empty legacy forms retain their existing
permission behavior. A retired file-policy edition remains usable only through a
form that published while that edition was approved; creation must also insert its
exact typed binding. Publishing a copied form requires current published policy
references. Published requirement rows and their form publication provenance are
immutable in PostgreSQL.

The intended definition input is `document_requirements`, defaulting to an empty
list and bounded to twenty entries. Each entry contains `key`, `label_en`,
`label_ta`, `instructions_en`, `instructions_ta`, `file_policy_id`, `min_files` and
`max_files`. Counts are explicit, with zero minimum representing an optional
requirement. Requirements sharing a policy must fit that policy's aggregate
maximum; dividing a requirement cannot multiply the policy's allowance.

Form responses add requirement IDs, positions and the pinned policy summary:
edition, name, allowed MIME types, maximum bytes and files, retention periods,
bilingual notice and frozen-evidence disposal rule. Provider identities and
storage keys remain internal.
`max_upload_bytes` exposes the operational ceiling on form/list responses and the
minimum of that ceiling and the policy limit on each pinned policy summary.
Clients apply the smaller bound; the server independently checks it.

## Typed ownership and replacement

An application document binds the exact organization, application, form,
requirement, owner person and file object. Composite foreign keys prevent moving
a file between these contexts. A fresh document binding UUID is the file
object's trusted resource UUID. The domain service constructs this context after
authorization; a caller cannot supply a resource reference that grants access.

The application row serializes metadata creation, replacement, removal and
submission. Active bindings obey both the requirement maximum and the shared
policy maximum across the whole application. Pending, quarantined and scanning
bindings consume those allowances. Replaced and removed historical bindings do
not consume active allowances, and their bytes remain subject to the pinned
retention policy.

Replacement creates a fresh binding and immutable file identity and marks the
previous binding replaced in the same transaction. The pending replacement is
visible immediately and must finish verification and scanning before submission.
Removal is a metadata transition; it does not request immediate byte disposal.
Normalized client request UUIDs recover lost metadata responses, while changed
reuse conflicts. An operational intent limit applies before accepting new
untrusted metadata; exact request replay remains recoverable.

## HTTP boundary

Owner routes are scoped beneath
`/api/v1/applications/organizations/{org}/applications/{application_id}/documents`:

- `GET` lists bounded metadata and the current application version. It remains
  available for owned saved applications after intake closes.
- `GET /{document_id}` returns the same metadata even after removal or replacement,
  so a lost mutation response can be reconciled using an already known binding ID.
- `POST` creates metadata with `expected_version`, `client_request_id`,
  `requirement_id`, `media_type`, `byte_size`, `sha256` and optional
  `replaces_document_id`. Policy and resource identity are resolved by the server.
- `DELETE /{document_id}` accepts the expected application version and removes a
  draft binding without disposing bytes.
- `PUT /{document_id}/content` accepts bounded raw bytes with the registered exact
  media type and an `If-Match` file version. Owner and open-draft authorization
  precede private buffering and are repeated before claiming the upload lease.
  Session and current account state are also refreshed after buffering.
- `GET /{document_id}/content` reauthorizes owner access and serves only the
  verified clean pinned object through the shared private-download helper.

Metadata responses contain safe file state, sizes, digests, version and timestamps.
They never contain a storage key, provider version, upload token or scan lease.
Collection-disabled responses let the UI explain availability without exposing an
upload control. Current feature configuration also gates byte routes.

Create, upload and remove return `{application_version, document}`. Creation,
replacement and removal increase the application version; upload and scan progress
increase only the file version. The UI preserves unsaved scalar answers when
reconciling a changed application version. An `If-Match` value is one quoted
positive decimal version, such as `"3"`; weak tags, wildcard tags and tag lists are
not accepted. Actual body size must equal registered size regardless of the
optional Content-Length header. The body deadline is at most ninety seconds.

Reviewer list and download routes are scoped beneath the existing selection
assignment route. Every request requires the current `selection.review`
permission, that actor's current assignment, a clear conflict declaration and an
included assignment for the same organization/application. Assignment and cycle
state are rechecked before delivery. Owning a file, having an unrelated staff role
or remembering an earlier assignment is insufficient.

## Submission evidence

Submission locks the application, active bindings and their file objects in a
consistent order. Each active document must be verified clean; required minimum
counts must be met. A failed, pending or removed required document cannot satisfy
the form. File state changes and metadata edits cannot race this decision.

The transaction freezes immutable evidence containing the binding/file IDs,
policy ID, exact provider object version, byte count and digest, then marks the
application submitted. Freezing a file and recording domain evidence use
transaction-composable internal helpers; no intermediate commit can expose a
submitted application without its evidence. File metadata's operational version
can later increase for a legal hold, so evidence pins the stored-byte identity
rather than requiring permanent equality with that mutable operational version.
The owner-facing evidence summary contains file ID, file version at freezing,
digest, byte count and freezing time; the provider version remains internal.

Private delivery verifies the complete pinned snapshot in a worker thread, then
refreshes the session and repeats domain authorization before returning headers.
Failure closes the snapshot. Submission and delivery reject expired bytes even
when cleanup is delayed or a legal hold preserves them. Existing
`completion_percent` describes scalar answers; document states and submission
errors provide separate document progress.

Database guards preserve published requirement rows, immutable typed binding
identity, submitted binding/evidence and exact clean evidence. Retention and
legal-hold checks continue to apply to frozen files; publication or submission
does not imply an unapproved indefinite retention policy.

## Acceptance

PostgreSQL checks cover legacy empty requirements, definition copy and publication,
cross-organization/form/requirement/person/file mismatches, policy rotation,
aggregate counts, idempotent lost-response recovery and concurrent creation.
Application tests cover closed intake, owner/peer/reviewer/revoked permissions,
failed or unfinished scans, replace/remove, submit/upload races, immutable exact
evidence and rollback when any freeze fails. Transport tests retain byte bounds,
type/hash verification, no-store private delivery and disabled collection. Browser
acceptance uses synthetic files and policies only.
