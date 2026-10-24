# Application document web journey

The application definition, applicant and assigned reviewer workspaces use the
typed application-document API. File collection is disabled by default. A
published form or file policy does not approve document types, retention periods,
notices or real collection. Existing forms retain an empty requirement list.

## Definition administration

The definition editor begins without document requirements. Adding a requirement
creates blank bilingual labels/instructions, a blank policy choice and blank
minimum/maximum counts. Zero is an explicit optional minimum. Published
`application_document` policies are loaded through the staff policy API only when
the actor has `files.policy.view`. Nonempty definitions require that permission
alongside each existing create/update/copy/publish permission. Published forms and
their pinned rules remain immutable; a new edition is needed for changes.

Dirty fields and requirements block version switching, copying and publication.
Conflicts and uncertain writes retain the entered definition. Recovery reads the
current detail, or the single draft after uncertain creation/copy, and shows its
saved fields, acknowledgements and document rules. Selecting the saved revision
keeps entered values for explicit review and save. No write is retried
automatically. A confirmed save remains confirmed if only the list refresh fails.

## Applicant operation

Applicants receive their pinned document requirements and safe policy summaries
through their form and document list. They never call privileged policy APIs.
The displayed upload ceiling is the lower of the pinned policy and the server's
operational `max_upload_bytes`. Disabled collection shows an explanation and no
upload controls. Draft answer saves accept partial answers without requiring
final declaration/consent acceptance; final submission checks them explicitly.

Document mutations require saved scalar answers. A selected immutable browser
File is checked against the allowed MIME types and operational size before it is
read, then hashed with browser SHA-256. Registration sends the digest, byte count,
requirement ID, current application version and fresh client request UUID, never
the client filename or a storage reference. The subsequent raw PUT uses the exact
registered MIME and quoted optimistic file version.

An uncertain registration freezes its exact body and file. An explicit recovery
replays that registration UUID; byte continuation is a separate explicit action.
A lost PUT response is reconciled by reading the known binding, with no automatic
byte replay. Replacement creates a fresh binding; removal does not immediately
dispose stored bytes. File selections and uncertain commands participate in the
application's navigation/reload warning.

Acknowledged metadata mutations advance the application version without replacing
its scalar answers. Unexpected newer versions freeze edits until explicit reload
and review; entered answers remain visible until the user chooses to discard them.
Scan polling performs only reads, at three-second intervals for at most twenty
attempts. Failed polling permits manual refresh. Pending, infected, rejected,
disposed or otherwise unusable files never count toward submission readiness.
The server-derived `usable` flag includes current retention and exact verified scan
proof; a stale `clean` scan state alone does not advertise available bytes.

Submission retains the immutable file ID, frozen operational version, size,
digest and timestamp returned in the receipt. Later operational file versions do
not rewrite that evidence. Collection availability and current byte authorization
continue to apply to downloads.

## Reviewer and transport boundaries

Only a current assigned reviewer with `selection.review`, a clear conflict state
and an included assignment receives document controls. Explicit reads use the
assignment route and the pinned requirement descriptions. The component clears
old links after a failed/revoked read. Each private download rechecks current
server authorization; an earlier displayed link is insufficient.

The applications BFF allowlist admits only typed organization/application document
collection, detail and content routes. Reviewer routes are read-only beneath the
exact selection assignment. Bounded cursor/limit queries reject duplicate or
unknown parameters. JSON commands keep their existing caps. Raw PUT requires
origin/CSRF validation, exact MIME, quoted If-Match and no Content-Encoding. Its
counted stream has a 100 MiB hard ceiling matching the policy schema; the API's
lower operational/pinned/registered-size limits remain authoritative. Length
headers cannot replace actual counting. An early API rejection cancels the input.

Verified downloads use private/no-store, nosniff, sandbox CSP and a generated
binding-based attachment filename. Browser credentials cannot replace server-held
credentials, and provider headers, storage keys and cookies are stripped. Generic
upload, scanner, publication and arbitrary file routes remain closed.

## Local acceptance boundary

Focused component/transport tests cover version and lost-response recovery,
explicit rules, inherited MIME names, byte ceilings, truncated responses, current
retention and reviewer access. The isolated browser runner reserves loopback
8108/3108 and `edp_application_files_e2e`, confines synthetic bytes under ignored
`.tool-cache` directories and enables collection only in that child environment.
Its script supplies controlled scanner results directly to the service after
reading the exact synthetic bytes. The expiry case creates a historical synthetic
file with its original retention deadline already elapsed; it never shortens an
existing file's immutable retention or disables lifecycle guards. This is not live ClamAV, object-store,
production permission/ACL or deployment acceptance. No runtime fake-clean mode or
scanner callback is introduced.

See [domain design](application-documents-design.md) and
[shared file adapter boundaries](file-adapter-boundaries.md).
