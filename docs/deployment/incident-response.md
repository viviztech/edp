# Incident response and operational handover

Local runbook; live contacts are unconfigured. Assign incident commander/client
decision maker, operations/database/storage responder, engineering/queue/release
responder, security/privacy/key custodian, and program/support communication owner,
with escalation and coverage before release. Tooling contacts no recipients.

Record UTC detection/start/recovery, bounded failure categories, affected
capabilities and accepted artifact/config identities. Keep personal records,
credentials and capability URLs out of timelines; preserve restricted forensic
evidence separately with approved custody.

1. Assign commander, responder and communications owner. Verify alerts with
   independent readiness/dependency evidence. Stop unauthorized collection or
   delivery. Isolate affected identities without deleting immutable evidence/audit.
2. `database-dependency` / `edge-api`: check private connectivity, pool/load,
   TLS/origin/trust, compatible migrations and capacity. Roll back only to an
   accepted compatible artifact/config. Do not grant ownership or disable triggers.
3. `queue-recovery`: stop duplicate schedulers, inspect actual round trip, oldest
   due jobs/leases and exhaustion. Recover fenced PostgreSQL jobs; reconcile
   receipts before retrying uncertain effects. Never indiscriminately replay an
   outbox or erase Redis queues.
4. `delivery-recovery`: pause affected senders, preserve ambiguous attempts, recheck
   current consent/authorization and use operator recovery. A timeout does not prove
   non-delivery. Destinations/tokens/message/provider bodies stay out of alerts.
5. `private-files`: fail access closed for missing/mismatched/unscanned bytes.
   Verify exact version/hash/length/encryption/key, signatures and temporary
   confinement. Preserve holds/frozen evidence; never force clean scan or replace
   pinned versions to recover availability.
6. `backup-restore`: follow [isolated recovery](backup-restore.md), preserve original
   backup/keys and compare measured recovery/loss to approved RPO/RTO. Accept
   recovery before traffic or scheduler restarts.
7. Record verified resolution/negative scopes, compromise decision, cleanup and
   monitoring recovery. Client owner approves traffic restoration. Assign corrective
   work and post-incident review, separating source fixes from environment gates.

Handover requires synthetic critical journeys, admin/privilege review, guides,
backup/key custody, signed UAT, named incident/stabilization owners, deployment/
rollback rehearsal and approved monitoring recipients. These are release conditions,
not local test claims.
