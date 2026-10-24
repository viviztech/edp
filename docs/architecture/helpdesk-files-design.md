# Shared helpdesk attachments

Migration `l7b3c9d5e012`, after learning-file migration `k6a2b8c4d901`, adds a shared
private-file path alongside the existing bounded TXT attachments. Collection is
disabled by default. No production document or retention rules are implied.

## Staging and policy

A file intent belongs to an exact organization, ticket, author user and person.
Its generated binding UUID is the shared file's resource identity. Composite
foreign keys bind the file's organization, owner, purpose and resource to that
ticket binding. The intent pins an explicitly published `helpdesk_attachment`
policy, media type, size, digest and shared/private audience. Policy changes do
not rewrite existing intent rules or notices.

The current policy summary is returned for new intent creation; each existing
file also returns its original policy summary. Limits include the smaller of
the approved policy's size limit and the operational upload ceiling. Staging
counts are bounded per ticket/author, and a posted message's selected files must
use one policy edition and obey that policy's file-count maximum. Existing TXT
attachments retain their separate three-file and 32 KiB restrictions.

Intent creation has a normalized request UUID and exact replay recovery. It does
not change the ticket version or create a message/history event. Each binding has
its own optimistic version. Upload and scanning change the shared file version;
posting and removal change the binding version. Removal retains metadata and
leaves byte disposal to the explicit retention policy.

## Message evidence

Binary files are staged after a ticket exists. A reply's `file_ids` selects clean,
unexpired files staged by that author for the same ticket and audience. The
existing ticket edit version still serializes the reply and its history/notice
changes. Selected files are validated and locked before creating the message.

`HelpdeskMessage.shared_file_ids` records the selection at message insertion.
The existing append-only message trigger freezes this array together with the
body and private-note flag. A file can transition from staged to posted only when
its ID is in that message's immutable selection. A deferred database guard
requires every selected file to be bound and frozen with exact storage version,
digest and size before commit. This prevents attaching more files to an earlier
message, including through direct SQL. A failed freeze rolls back the entire
message, ticket version, history, notifications and all earlier freezes.

Messages expose safe `files` metadata separately from their existing TXT
`attachments`. Object keys, provider versions and lease capabilities stay internal.
The `usable` flag reflects current clean verification, retention and immutable
posted evidence. Operational version changes for a legal hold do not rewrite the
stored-byte identity pinned by the message.

## Authorization and transport

Routes are under
`/api/v1/helpdesk/organizations/{org}/tickets/{ticket_id}/files`:

- `GET` returns bounded visible metadata, current policy, operational ceiling and
  collection availability. A cursor must belong to that same visible result set.
- `POST` accepts `client_request_id`, `policy_id`, explicit `internal`, media type,
  byte count and SHA-256. It returns a staged binding.
- `GET /{binding_id}` permits recovery of a known removed intent by its author.
- `DELETE /{binding_id}` accepts the binding's expected version and removes only
  that author's staged file while the ticket is writable.
- `PUT /{binding_id}/content` accepts raw bytes with the registered exact media
  Content-Type and one quoted positive `If-Match` shared-file version.
- `GET /{binding_id}/content` serves a verified private attachment snapshot.

Every operation first applies current ticket ownership/enrollment or current
assignee/admin permissions. Staged files are private to their author, including
when another administrator can read the ticket. Posted shared files follow shared
message visibility; posted private-note files remain invisible to the owner.
An earlier assignee loses access after reassignment, even to files they uploaded.
Owning a shared file record alone grants no ticket access.

Authorization precedes private body buffering and is repeated afterwards, before
an upload lease is acquired. No ticket lock spans the untrusted body deadline.
Delivery verifies the complete pinned snapshot in a worker thread, refreshes the
actual session/account and rechecks ticket/message access before returning headers.
Failure or cancellation closes the snapshot. Byte routes and new binary intents
require collection enabled; text-only messages and the original TXT path continue
to work when it is disabled.

## Verification

Acceptance covers owner/peer/organization/current-assignee/admin scope, private
notes and cursor negatives, staging privacy, exact retry recovery and concurrent
creation, count limits, unavailable scans, expired evidence, immutable message
selection, atomic failure rollback and session/reassignment changes during body
buffering or delivery. Provider tests use synthetic objects and scanner results;
live object storage and ClamAV remain separate deployment gates.
