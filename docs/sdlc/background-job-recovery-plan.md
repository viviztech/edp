# Background job recovery plan

Prepared: 2026-10-24. Status: **design only; implementation waits for the complete Process 3 secure-file checkpoint and owner progress report**. This is the background-job recovery process in the owner's revised six-process sequence. Essential communications is a separate subsequent process; the broader [communications and jobs plan](communications-jobs-plan.md) remains useful background, but does not authorize starting both processes together.

All work stays local. This plan authorizes no push, deployment, live provider request, external message or collection-policy change. Preserve the current secure-file work and its acceptance evidence.

## Problem and outcome

CRM export creation commits a `queued` database row before publishing its Celery message. A process loss between those operations strands the row. The worker then commits `running` before producing CSV; worker loss can strand that state as well. Neither step has a fenced execution lease. The worker also does not recheck the requester's current status or export permission. The current export tests cover CSV escaping, rather than those recovery paths.

Meta events already have durable recovery, attempts and a processing deadline. However, `recover_events` selects only rows below `MAX_ATTEMPTS`. A worker loss during attempt five can leave a `processing` row with an expired deadline outside recovery selection. Redelivered processing tasks are ignored, so no terminal failure is recorded before retention purge.

The outcome is bounded, recoverable execution of existing jobs, with current authorization and visible terminal failures. Database state remains authoritative when Redis is unavailable. This process does not implement enrollment notification delivery, authentication delivery or any other external sender.

Evidence in the current source:

- [CRM export creation and access](../../apps/api/app/modules/crm/service.py), `request_export`, `get_export` and `download_export`.
- [CRM export worker](../../apps/api/app/workers/crm_exports.py), `export_leads`.
- [Export model](../../apps/api/app/modules/crm/models.py), `ExportJob`, and its [original migration](../../apps/api/migrations/versions/92a3b4c5d6e7_crm_export_jobs.py).
- [Meta worker and recovery](../../apps/api/app/workers/meta_leads.py), `process_event`, `mark_failed` and `recover_events`.
- [Existing Meta recovery tests](../../apps/api/tests/test_meta_db.py), including the expired lease at attempt one.

## Scope and order

1. Add export schema guards and an execution service, preserving the existing four public statuses and current download scope.
2. Recover committed export requests and expired execution leases independently of their original broker publication.
3. Repair Meta exhausted-lease terminalization without changing provider contracts or making live requests.
4. Add scoped failure/recovery evidence and complete local acceptance. Prepare a progress report before essential communications begins.

The enrollment outbox consumer, bilingual notification templates, destination/consent rules, email/SMS/WhatsApp/FCM senders and production verification/reset delivery belong to essential communications. Flutter, staging and launch acceptance remain later processes.

## CRM export schema and state invariants

Use one Alembic revision following the accepted Process 3 head; do not alter applied historical migrations. Keep the existing UUID, organization, requester, creation time and 24-hour access expiry. Add these internal fields to `crm_export_jobs`:

| Field | Meaning |
| --- | --- |
| `version` | Positive monotonically increasing state version; each real transition increments it once |
| `attempt_count` | Nonnegative number of execution claims; publication and duplicate task delivery do not consume attempts |
| `lease_token_digest` | Hash of an unpredictable execution token; never return the token or digest in a DTO |
| `lease_until` | UTC execution deadline; both lease fields are present only while `running` |
| `next_attempt_at` | UTC time at which queued work becomes eligible; absent in other statuses |
| `disposed_at` | Nullable UTC marker for output disposal; does not imply deletion of job metadata or audit |

Retain `queued`, `running`, `completed` and `failed` externally. A retry is `queued` with a bounded future `next_attempt_at`, rather than a new public status. Add an index supporting `(status, next_attempt_at, id)` and expired-running selection by `(status, lease_until, id)`; retain the expiry and owner indexes.

Enforce the following through database checks and a transition guard, alongside service validation:

- Identity, requester, organization, creation time and access expiry are immutable after insertion. Rows begin `queued`, version 1, attempt count 0, without content or a lease.
- `running` requires both lease fields, no retry deadline, no CSV and no completion timestamp. Other statuses require both lease fields to be null.
- `queued` requires a retry deadline, no content and no completion timestamp. Due timestamps are normal; a constraint must not depend on the changing wall clock.
- `completed` requires CSV content, a bounded nonnegative row count, a completion timestamp and no lease/retry deadline. `failed` has a fixed error code, no CSV and a completion timestamp. Preserve the existing content/status relationship.
- Claiming `queued` work increments attempts once and version once. Every completion, retry or failure increments version once. Duplicate or stale execution has no effect.
- Terminal output cannot be overwritten by a late task. Only an explicitly defined disposal transition may remove completed CSV; preserve metadata and record `disposed_at`. Ordinary recovery cannot change terminal rows back to queued.
- Retry/replay must never extend `expires_at` or reset the cumulative attempt limit. An expired request cannot be claimed or completed.

Backfill existing rows explicitly: queued rows receive a due timestamp; running rows receive an already expired synthetic lease so normal recovery can settle them; completed/failed rows preserve existing outcomes. Do not fabricate completed results. Normalize inconsistent legacy timestamps/error fields before enabling stricter constraints. Validate fresh migration, upgrade/downgrade/re-upgrade and zero drift in a newly owned disposable database.

## Export execution and recovery

API creation commits request metadata and its audit together. Broker publication is best effort after that commit. If publishing fails, retain eligible queued work, return the durable accepted request, and record a sanitized dispatch failure. A database failure still fails the request. Do not claim that a message was published when only its database row exists.

Add a bounded periodic recovery task to the existing Celery schedule. It discovers retained due queued work and expired running leases. Use row locks with `SKIP LOCKED` for settlement, stable ordering and bounded batch sizes. Broker payloads carry only the job UUID. Enqueueing does not mark a job running or consume an execution attempt; repeat publication is safe because workers claim from the database. Broker failure leaves the row discoverable on the next poll.

For an expired running lease, clear the obsolete lease and either queue a bounded backoff retry or mark the request failed with `retry_exhausted`, `request_expired` or `requester_unavailable`, as appropriate. Settle exhausted or expired rows even when no further attempts are allowed. Do not exclude them from discovery merely because they cannot execute again.

The worker performs these steps:

1. Parse the UUID and lock the job. Ignore terminal, not-due or actively leased work. Reject expired or unauthorized requests before querying leads.
2. Claim with an unpredictable token, its stored digest, attempt count, version and deadline; commit this fenced claim. Execution limits and lease duration must be compatible. Choose bounded engineering settings, with the lease longer than the task hard limit plus recovery margin; they are not privacy policy.
3. Generate output outside a long database lock. Preserve the current organization filter, stable ordering, 10,000-row cap, CSV encoding and formula-prefix protection. Bound output bytes as well as rows, without silently truncating an individual field or returning a partial artifact as complete.
4. Before persisting CSV, reload and lock the job and reload the current requester. Completion requires the same attempt, version and token digest, `running` state, an unexpired lease and unexpired access. Recheck current authorization. The check and output/audit write share one transaction.
5. Apply errors or retries only through the same fence. A stale worker cannot fail, complete, erase or reschedule a newer claim. Persist fixed reason codes and audits; discard its in-memory CSV when its fence is lost.

Use current database state for claims and deadlines. Do not change the production clock or weaken SQL guards to make lease tests pass. Deterministic test clocks may drive service decisions, with corresponding synthetic expired/due database rows where constraints require them.

Exactly-once broker delivery is unnecessary. The claim and completion fences provide one accepted result for one request despite duplicate messages. If a provider is later introduced for another job, that provider's idempotency and ambiguous-response reconciliation are separate requirements.

## Current requester authorization

At both claim and completion, require an existing active `User`, the original organization and current `crm.lead.export` permission for that organization. Requery grants; do not reuse a cached ORM user/grant across CSV generation. A revoked grant, suspended/archived user or missing organization fails closed and discards generated content. Lock ordering must be consistent between execution and recovery.

Preserve download authorization: only the original requester with current organization export permission and an active authenticated session can read status or download within the access period. A bearer job ID never grants access. Test peer, other-organization, revoked permission and suspended requester negatives. If administrative recovery is exposed, use a distinct scoped permission, an expected version and an explicit reason; do not grant administrators a new blanket CSV download path.

## Retention and failure visibility

The existing 24-hour `expires_at` is an access deadline. Preserve expiry denial and do not extend it through retries. Existing opportunistic clearing on expired status access must not be presented as a complete disposal strategy.

Any new scheduled CSV disposal requires an explicitly configured, approved retention setting, with no invented privacy default. It must not delete output before its access deadline, must process a bounded batch, and must record disposal without deleting job/audit metadata. With no approved setting, the new scheduled disposal performs no deletion and reports that configuration is missing. Metadata/audit retention is a separate decision. Tests supply explicitly synthetic settings.

Expose only safe state, counters and fixed reason codes needed by authorized users/operators. Never expose CSV contents in error responses, task results, logs or monitoring. Do not log lead contact data, database URLs, broker credentials, exception text or lease tokens. Preserve request/job correlation IDs. Track counts and oldest age of due queued work, expired running leases, failed dispatch, exhausted attempts and overdue disposal; do not label a direct task-function test as broker-health evidence.

Keep terminal failures visible. If reasoned replay is needed in this slice, define its permission, cumulative attempt budget and unchanged access expiry before adding it; otherwise document that the requester creates a new authorized export after investigating the failure. Do not add an implicit endless reset-to-zero retry path.

## Meta final-attempt recovery

Keep the existing five-attempt limit, organization/provider deduplication, retention deadline, retry backoff and current scoped replay permissions. Extend recovery selection to include expired `processing` leases at or above the attempt limit, separately from executable due rows.

Under a row lock, exhausted expired processing becomes `failed`, with `retry_exhausted`, a processing timestamp, cleared retry deadline, incremented version and a sanitized audit. It is not sent to the provider again. Running leases are left alone. Expired-retention events remain unusable and are handled by their existing approved purge path.

Preserve attempt fencing in both success and failure handlers. Late completion or failure from the dead attempt cannot overwrite the settled terminal state or a subsequent explicitly authorized replay. Retain bounded batches and broker-failure recovery for events that remain executable. This correction uses scripted provider doubles; it needs no Meta credentials or network request.

## Acceptance criteria

Use guarded, isolated synthetic PostgreSQL fixtures. Add meaningful tests of the transaction and recovery outcomes:

| Case | Required observation |
| --- | --- |
| Commit before publish, including publication exception | Durable queued request remains discoverable; later recovery and execution complete once |
| Worker death after claim | An active lease cannot be stolen; expiry permits bounded recovery |
| Duplicate tasks and concurrent workers | One valid claim/result; bounded attempts; no duplicate completion audit |
| Late success and late failure | Both fail the fence and leave the newer claim or terminal outcome unchanged |
| Final export attempt dies | Expired exhausted lease settles failed rather than becoming permanently running |
| Requester loses grant or is suspended during generation | No CSV is persisted; status/reason is safe; no cross-organization access |
| Request expires before claim or while generating | No accepted result after expiry; replay never extends access |
| CSV limits and escaping | Existing formula and ordinary values remain correct; row/byte limits fail explicitly where necessary |
| Approved disposal and absent configuration | Only eligible expired output is cleared under the explicit setting; metadata/audit remain; absent setting deletes nothing |
| Direct SQL invalid mutations | Invalid lease/status/content combinations, identity edits, version regressions and illegal terminal rewrites are rejected |
| Final Meta attempt dies | Expired processing at attempt five becomes failed with an audit and no provider call |
| Meta active/earlier/stale cases | Active attempt five remains processing; earlier expired attempts recover; late completions cannot undo settlement |

Run affected tests first, followed by required API Ruff/format, strict MyPy, the accepted integrated API/database checks and migration round trip/drift checks. Regenerate OpenAPI/TypeScript only if an external DTO changes; lease secrets remain internal. If API request/response behavior or user-visible failure handling changes, update English/Tamil web behavior and run affected component/BFF/browser checks plus required web static/build checks. No test, guard or security scan is removed to obtain a pass.

Record exact commands, revision/source state, passed/failed/deferred counts and retained evidence in a process report. A coherent local source checkpoint and owner progress notification are required before essential communications starts. Remote CI remains a release gate under the local-only instruction.

## Runtime boundary

Local database tests and direct calls to Celery task functions establish state invariants; they do not establish Redis, worker or scheduler operation. Runtime acceptance still requires isolated real Redis, real worker processes and exactly one Beat scheduler: queue round trip, duplicate publication, broker outage/recovery, worker termination after claim, deadline expiry, final-attempt settlement and monitoring. Use synthetic data and terminate only the test's owned processes.

If that runtime is unavailable, continue independent implementation and record the runtime gate as unexecuted. Do not claim it passed, contact a live provider or deploy to obtain evidence without the separately applicable authorization. Current interpreter recovery must be completed and verified before Python/database/browser execution resumes. Existing npm security findings, exact-revision remote CI, real provider configuration, native devices, staging, UAT and production approval remain separate open gates.
