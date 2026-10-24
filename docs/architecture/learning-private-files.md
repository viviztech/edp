# Learning file bindings

Recorded: 2026-10-23. This is the learning slice of Process 3. Collection and maintenance remain disabled by default. Policy examples and acceptance fixtures are synthetic; no real document list, notice or retention period is approved by this implementation.

## Assignment evidence

An assignment has no file requirement until a staff member explicitly configures an organization-scoped, published `assignment_submission` policy and minimum/maximum counts on a draft course. Empty rules preserve text-only submissions. Course publication pins the rule; subsequent policy retirement does not invalidate the existing published course's pin. The retired-policy exception requires a typed assignment binding, current enrollment and the original publication proof. It does not authorize an unbound shared file.

An upload intent belongs to one person, course enrollment, assignment and next submission revision. The server checks current course eligibility, course start, lesson prerequisites, previous revision grading, revision limits and bounded active-file counts. The enrollment lock serializes both count checks and exact idempotent replay. A changed request UUID payload conflicts. File size, MIME and notices come from the pinned policy and operational cap, not client-supplied storage references.

The owner explicitly selects binding IDs in `AssignmentSubmissionCreate.file_ids`; an omitted list remains empty. Submission freezes the exact verified clean object and its immutable storage version, hash and size in the same database transaction as the new revision. Deferred PostgreSQL constraints enforce required counts and typed frozen evidence. Submitted bindings cannot be removed or modified; a permitted resubmission creates new intent records for its new revision. A trainer downloads only through the current course/cohort staff relationship and exact submission binding. A peer or a staff account outside that relationship cannot use a discovered ID.

## Author material and recovery

The author material endpoint creates the `LessonMaterial` and its typed `lms_material` binding together. The server reserves `shared-file:{material_id}`; legacy metadata endpoints reject that namespace. No browser supplies an object key or bucket path. The request digest and UUID are checked again inside the course lock, preventing concurrent retries from creating duplicate lesson positions.

Material list and detail responses expose `state`, the binding `version`, a shared file view, an authoritative `usable` flag and safe frozen evidence. The list has organization/course-scoped cursor pagination, a maximum page size of 100 and a runtime collection cap. Shared file versions belong to byte upload leases; binding versions belong to removal/publication. They are separate optimistic concurrency tokens.

An abandoned or rejected intent remains visible to course authors and blocks publication while active. On a draft course, `DELETE /api/v1/courses/organizations/{org}/courses/{course}/material-files/{material}` accepts the bounded JSON command `{"expected_version": 1}`. It changes the binding to `removed`, increments its version and records an audit event. It retains the material row, file metadata and any bytes for the configured lifecycle. It does not delete evidence, shorten retention or override a legal hold. A lost response is reconciled with metadata GET before retrying; a stale version conflicts. Removed metadata cannot be resurrected, uploaded or downloaded. Published/frozen material cannot be removed.

Retained material history reserves its original lesson position. A replacement uses a new request UUID and the next unused position. Admin course structure retains history for inspection and position selection; learner and trainer structures omit removed material. Publication explicitly excludes only bindings already marked removed. Every remaining active shared material must be usable and frozen; incomplete active material is never silently skipped.

Migration `m8c4d0e6f123` follows the helpdesk migration and adds the removal state/version and database guards without rewriting the already applied learning migration. It preserves immutable identity, requires a draft parent course and a monotonic binding version, allows only explicit removal or exact clean evidence freezing, and prevents physical metadata deletion or resurrection.

## Byte and gateway boundaries

Only the exact typed raw PUT endpoints bypass the ordinary JSON body cap. They authorize before allocating a private buffer, count actual bytes independently of Content-Length, release database transactions while receiving the body, and reauthorize the current principal and binding afterward. A quoted shared-file version fences the upload. Unknown, unavailable, quarantined, rejected, expired and mismatched bytes are unusable.

Author, learner and trainer delivery use verified private snapshots. Shared material retains the existing short-lived actor/course/material token gateway and rechecks current enrollment, prerequisites, staff scope and session before delivery, including after provider verification. It does not return a transferable storage URL. Storage keys, provider versions and scanner credentials remain private. Downloads use attachment filenames derived from binding IDs, private no-store headers, nosniff and a sandbox policy. The web BFF has closed typed path/query allowlists, bounded UTF-8 metadata commands, origin/CSRF checks and server-held credentials; it refuses upstream redirects.

Legacy local material resolution remains a local/test facility. Staging and production cannot use it as an unscanned fallback; shared material requires an explicitly configured signing key and the private-file runtime. This slice does not implement an external video provider.

## Acceptance boundaries

Nine focused PostgreSQL cases passed locally after the removal migration. They cover real PDF bytes above the JSON cap, quarantine and verified scan, submission and material freezing, peer isolation, expired evidence, retired policy pins and concurrent replay, post-body authorization changes, post-provider session revocation, SQL required-evidence guards, abandoned/rejected recovery and immutable removed/published records. Test scanners are explicitly injected into fixture services; no fake-clean runtime setting exists.

Integrated API/web, migration and browser results belong in the Process 3 acceptance report once those runs finish. Live private storage, ClamD/signature freshness, worker/broker runtime, Linux confinement, native clients and approved collection/retention rules remain separate release gates.
