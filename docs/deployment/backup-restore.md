# Backup and restore runbook design

RPO/RTO, frequency, retention and incident contacts require owner approval. A local
synthetic PostgreSQL dump/restore drill now exists and has passed. No recurring
off-host backup, live object-store recovery or staging restore has been configured
or accepted by that local result.

1. Operator provisions encrypted, restricted off-host PostgreSQL backups and WAL/PITR if chosen provider supports it; configure alerts for failures/staleness. Protect encryption keys separately.
2. Version/backup private object storage; database references and object recovery point must be compatible. Include deployment configuration and secret recovery procedure without embedding secret values.
3. Restore into an isolated staging database/bucket with outbound notifications disabled. Never overwrite production as a drill.
4. Validate schema version, representative row counts/FKs, login scopes, application→enrollment chain, object access, audit continuity and outbox state. Suppress/reconcile already-delivered jobs before restarting dispatch.
5. Record backup age, restore duration, recovery point, losses, operator and evidence; compare approved targets. A backup is not accepted until this succeeds.
6. Incident recovery requires designated incident owner, maintenance communication, credential compromise assessment and controlled traffic cutover. Preserve evidence and document follow-up.

Deletion/anonymization policy must cover backup expiry and reapplication of deletion ledger after restore. Redis can be rebuilt; recover pending jobs from PostgreSQL outbox, not Redis alone.

## Guarded tooling

`python scripts/staging_drill.py` exercises new loopback-only databases and
separate generated migration/API/worker roles, normal transactions, denied
privileges, a custom-format dump, a fresh restore and target-reuse refusal. It
preserves an encrypted-delivery record, append-only audit and a worker-settled
outbox record. It cleans up only names that invocation created and retains its
sanitized report plus private local artifacts in ignored `.local/staging-drill-*`.
This is an actual local PostgreSQL restore; its pinned object bytes are an offline
fixture and cannot prove provider version/KMS behavior.

`python scripts/recovery_guard.py <recovery-manifest.json>` validates by default
without restoring. It verifies a nonempty dump hash, UTC recovery point, source/
configuration/schema identity, exact declared version inventory, object size/hash/
encryption/key availability, retained holds, and inaccessible disposed/revoked
fixtures. Missing dump/object bytes, bad paths, duplicate references and missing
keys fail closed. Inventory/source/key fields are operator evidence; validation
does not invent proof of their external truth. Never copy production personal data
into this synthetic tool.

An explicit `--restore edp_ops_drill_<12 lowercase hex>_restore --pg-restore
<trusted-tool-path>` uses `EDP_RECOVERY_ADMIN_URL` from the environment and creates
only a fresh loopback database. It refuses existing targets; no clean/overwrite
option exists. libpq host-address/service overrides are rejected. Restores run as
one transaction with owner/privilege statements excluded, outbound processes never
started, and child diagnostics suppressed. A failed fresh target is preserved for
inspection unless the owning drill cleans up its recorded created resources.
Reapply the reviewed schema ownership/grant policy before runtime acceptance; a
`--no-owner` restore does not establish least privilege by itself.

## Recovery ledger and dispatch reconciliation

Maintain a separately protected post-backup deletion/withdrawal/disposal ledger
under the approved privacy policy. Each entry identifies a scoped subject/resource
by restricted internal reference, decision (`disposed`, `revoked`, `withdrawn`,
`hold`, `hold_released`), decision UTC timestamp, authorized decision/audit reference
and policy version. Keep personal values out of ordinary evidence reports. The
ledger must survive the same failure that loses the database and have integrity,
custody and retention controls approved by the privacy/operations owner. This is
the required operational design; no real deletion policy is silently activated.

After restoring, replay approved post-recovery-point decisions into the current
authorization/disposal workflow before access. Recheck legal holds/frozen evidence
before deleting anything. Never resurrect disposed bytes, grant access to revoked
reviewers or force an unverified object to clean. Original exact version references
remain immutable. A new provider version cannot silently substitute for old proof;
unrecoverable versions stay unavailable pending a reviewed auditable mapping.

Pause Beat, outbound authentication/domain delivery, callbacks and disposal while
reconciling restored jobs against provider receipts and idempotency records. Mark
already-delivered or ambiguous jobs through their supported operator workflow;
never claim a timeout proved non-delivery or blindly replay every pending row.
Recheck current recipients, consent and ownership before enabling one scheduler.

For each rehearsal record source/image/config/schema identity, backup/recovery
point and age, restored schema/constraint checks, row/relationship and audit/outbox
continuity, exact object-version negatives, deletion/dispatch reconciliation,
elapsed restore/validation, unresolved losses, operator, cleanup and acceptance.
Compare measurements to owner-approved RPO/RTO, rather than inferring an SLA from
one synthetic timing. Staging acceptance and production traffic remain separate.
