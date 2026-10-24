# Durable background-job recovery

CRM export requests commit a queued job and audit before returning 202. The request path makes no broker call. The minutely `edp.crm.recover_exports` task discovers due work and publishes identifiers with bounded broker timeouts; a publication failure leaves the database row eligible. API availability therefore does not imply that a worker has received the request.

A worker locks and claims due work with a random token digest, monotonic version, cumulative attempt and expiring lease. It generates a bounded organization CSV outside that transaction, then locks the job again and rechecks the live fence and the requester's current active account/export permission before accepting output. Revocation during generation discards the result. Duplicate publication consumes no additional attempt while an active lease exists. Expired leases are retried with bounded backoff or settled as terminal failures, including the final attempt. SQL transition guards protect identity, access expiry, versions, terminal results and lease state.

The original four public statuses remain `queued`, `running`, `completed` and `failed`. Queued retries expose safe fixed reason codes. Export generation fails explicitly above 10,000 rows or the configured byte limit; it never labels partial data as complete. CSV values escape spreadsheet formula prefixes, including prefixes after whitespace. Output is never returned in task results or diagnostics.

Owner history uses `GET /api/v1/crm/organizations/{org}/exports`, with a default 25/max 100 limit and newest-first `(created_at,id)` keyset pagination. Cursors must resolve inside the authenticated requester's current organization scope. History excludes expired jobs and exposes neither CSV nor internal lease fields. Status and download repeat current requester authorization. The English/Tamil web history recovers references after reload or an uncertain POST without automatically repeating that POST or guessing which job it created. Opening a history row obtains current detail before offering a download.

Access expires after the existing 24 hours. Physical disposal has a separate explicit `CRM_EXPORT_RETENTION_DAYS` setting with no privacy default and never precedes access expiry. In staging/production, new requests and execution require that approved setting; a missing setting returns a definitive 503 `export_retention_unconfigured` before creation. Local/test accepts synthetic requests without that setting, but performs no scheduled output deletion. Disposal clears eligible bytes and preserves metadata/audit. Terminal jobs are not silently replayed; investigate the safe reason before explicitly requesting a separate export.

## Engineering configuration

API, worker and the single Beat scheduler must share these values:

| Setting | Default/bounds | Purpose |
| --- | --- | --- |
| `CRM_EXPORT_LEASE_SECONDS` | 120; 60–900 | Longer than the 30-second task hard limit plus recovery margin |
| `CRM_EXPORT_MAX_ATTEMPTS` | 3; 1–10 | Cumulative execution claims, not broker publication attempts |
| `CRM_EXPORT_RECOVERY_BATCH_SIZE` | 25; 1–100 | Bounded recovery/disposal work per poll |
| `CRM_EXPORT_MAX_BYTES` | 10 MiB; 1 KiB–20 MiB | UTF-8 CSV output ceiling |
| `CRM_EXPORT_RETENTION_DAYS` | unset; explicit 1–3650 | Approved output lifecycle, distinct from access expiry and metadata retention |

Trusted operators can run `python -m app.modules.crm.export_cli health` from the API environment. It uses a read-only repeatable snapshot, bounded connection/statements and aggregate counts only. Review due count/oldest age, expired running leases, failed/exhausted jobs and retained/overdue output. Missing retention is explicit. Database/configuration failure emits a safe exception classification and nonzero exit, never a connection URL. Dispatch warnings use fixed event names and job identifiers without content or exception text. An increasing oldest due age calls for broker, worker and Beat investigation; the health command does not establish that those processes work.

## Meta correction and acceptance boundary

Meta recovery includes expired processing leases at or above five attempts and settles them as `retry_exhausted` without another provider call. Success and failure both compare the captured monotonic claim version, attempt and live lease. An old worker cannot overwrite final settlement or a later authorized replay that reused an attempt number. Existing organization scope, retention and replay rules continue to apply.

Guarded PostgreSQL tests, direct task-function execution and a browser run with Redis deliberately unavailable establish database/API/UI behavior. They do not establish broker delivery or worker/Beat process recovery. A real isolated Redis, real workers and exactly one Beat must still pass queue round trip, outage/restart, process termination after claim and exhaustion acceptance before release. No live Meta request or deployment is part of this local checkpoint.

## Migration rollout boundary

Revision `n9d5e1f7a234` requires the matching application and worker revision. Its new non-null execution fields have no database defaults after backfill, and its transition trigger requires monotonic versions. Older API or worker writers cannot coexist with the upgraded schema. A future authorized rollout must pause CRM writes, drain or stop the relevant workers and scheduler, apply the migration, and start the matching revision before resuming work. The local disposable-database downgrade verifies migration mechanics; it does not establish a safe production rollback or mixed-version rolling deployment.
