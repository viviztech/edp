# Backup and restore runbook design

RPO/RTO, frequency, retention and incident contacts require owner approval. No backup has been configured or tested in this bootstrap.

1. Operator provisions encrypted, restricted off-host PostgreSQL backups and WAL/PITR if chosen provider supports it; configure alerts for failures/staleness. Protect encryption keys separately.
2. Version/backup private object storage; database references and object recovery point must be compatible. Include deployment configuration and secret recovery procedure without embedding secret values.
3. Restore into an isolated staging database/bucket with outbound notifications disabled. Never overwrite production as a drill.
4. Validate schema version, representative row counts/FKs, login scopes, application→enrollment chain, object access, audit continuity and outbox state. Suppress/reconcile already-delivered jobs before restarting dispatch.
5. Record backup age, restore duration, recovery point, losses, operator and evidence; compare approved targets. A backup is not accepted until this succeeds.
6. Incident recovery requires designated incident owner, maintenance communication, credential compromise assessment and controlled traffic cutover. Preserve evidence and document follow-up.

Deletion/anonymization policy must cover backup expiry and reapplication of deletion ledger after restore. Redis can be rebuilt; recover pending jobs from PostgreSQL outbox, not Redis alone.
