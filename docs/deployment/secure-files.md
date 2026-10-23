# Secure-file runtime preparation

Recorded: 2026-10-23. Collection and maintenance default to disabled. Policy administration is available independently; publishing an edition configures rules and does not approve real collection. Use synthetic data until the document requirements, bilingual notices and retention rules are approved. All current development stays local.

## Configuration

Set `FILES_ENABLED=true` only for an approved deployment or an isolated synthetic acceptance fixture. `FILES_MAINTENANCE_ENABLED` separately enables expiry and abandoned-upload processing; it can remain enabled when collection is paused, provided approved retention and holds still apply. Neither flag bypasses policy or domain authorization. A disabled collection flag prevents new byte traffic and scans. The policy administration screen does not change these flags.

The API, file worker and Beat must use the same database, policy configuration and private storage provider. For staging/production, configure S3, bucket, region, explicit AES256 or KMS encryption, existing absolute private temporary directory, private ClamD endpoint and explicit maximum signature age. Choose an explicit credential pair or workload identity. The workload-identity factory excludes environment/shared-profile credential providers. Never put storage credentials, object keys or provider responses in browser settings.

`FILES_MAX_BYTES` is an operational ceiling, currently at most 10 MiB. Published policies must explicitly supply their own file-size/count/retention rules, and their limits may be lower. `FILES_INTENT_LIMIT_PER_WINDOW` bounds new metadata intents per actor/organization in a 15-minute window; exact request replays must recover the existing record. This operational bound does not define required documents.

Prepare the temporary directory before startup. On POSIX it must belong to the application user with no group/other permissions. Symlink/reparse ancestors are rejected. Review Windows ACLs for local tests. The API container creates `/var/lib/edp/files-tmp` with mode 0700 for its non-root user; capacity, encryption and temporary-file disposal remain operational acceptance. Local private object storage is restricted to local/test environments.

Provider acceptance must prove versioning, all public-access blocks, conditional creation, SHA-256 checksums, exact version reads/deletion, configured encryption and KMS permissions. Configure the canonical KMS key ARN returned by S3. SDK Stubber tests do not satisfy this gate. Do not enable a bucket lifecycle rule that silently deletes held/frozen evidence or invalidates the application's retention decisions.

Run ClamD with UTC, fresh signatures and a private trusted connection. TCP ClamD has no built-in authentication. Unknown/stale signatures, scanner limits, truncation, connection failures and ambiguous responses remain failures. Validate daemon size/archive/scan limits and detection-on-limit settings. There is no fake-clean runtime mode. See [adapter boundaries](../architecture/file-adapter-boundaries.md).

## Recovery jobs

Start the existing Celery worker and Beat with the application environment. Beat schedules `edp.files.queue_due` every 60 seconds. The poll reads bounded database candidates and sends individual scan, abandoned-upload or disposal jobs containing IDs and expected versions only. A broker failure does not advance database state; the next poll rediscovers the job.

Scans claim a fenced expiring lease. A duplicate job cannot finish a different lease. Scanner errors receive bounded attempts/backoff, then rejection. A terminated worker is recovered after lease expiry. Configure `FILES_SCAN_LEASE_SECONDS` between 30 and 900 seconds and at least 60 seconds longer than the scanner deadline. Per-file tasks have explicit time limits; measure actual provider latency and adjust within that range. Native worker process/time-limit behavior must be accepted on the deployment platform.

Maintenance rechecks the expected version, approved pinned policy, expiry, legal hold and frozen-evidence disposal rule under a row lock. It deletes only the exact recorded version and retains metadata/audit. It recovers and verifies objects left between storage completion and database completion before rejection/disposal. Unknown, corrupt or denied objects remain unresolved; operators must investigate through controlled tooling rather than deleting arbitrary keys. The pipeline creates metadata before writing bytes and never hard-deletes that metadata, so recovery uses recorded keys without bucket-wide listing.

Do not equate a successful direct worker-function test with a Redis/Celery round trip. This workstation has no Redis, ClamD, object-store or container runtime; those runtime gates remain open. Local protocol and database evidence is recorded in the [foundation checkpoint](../sdlc/secure-file-foundation-report.md). The remaining application/CMS/learning/helpdesk bindings must be accepted before Process 3 is locally complete.
