# Synthetic staging preparation and rollout runbook

Updated 2026-10-24. Local artifacts exist and a fresh PostgreSQL role/restore drill
has passed. No staging environment is deployed or accepted. Hosting/domain/costs,
service identities, DNS/TLS, alert recipients and deployment approval require their
actual owner/environment. Files, maintenance, senders and real collection remain
disabled in the initial contract.

## Artifacts and local checks

Review [the topology](../../infra/deployment/staging.compose.json),
[input reference](../../infra/deployment/staging.env.example),
[release schema](../../infra/deployment/release-manifest.schema.json),
[placeholder manifest](../../infra/deployment/release-manifest.example.json),
[TLS template](../../infra/nginx/staging.conf.template),
[database grants](../../infra/deployment/database-roles.sql) and
[object/key permissions](../../infra/deployment/object-permissions.md).

From the root using the project Python environment:

```text
python -m unittest discover -s scripts/tests -q
python scripts/deployment_contract.py
python scripts/staging_acceptance.py --output .local/staging-acceptance.json
python scripts/staging_drill.py
```

Use fresh output filenames. The acceptance harness records selected-source and
topology hashes, timestamps, fixed commands, outcomes and sanitized output hashes;
it rejects source changes during checks. Run it after final integration. It cannot
deploy, enable delivery or certify unexecuted runtime/client gates. Manifest gate
declarations remain unverified until reviewed evidence is accepted.

The Windows drill uses only the existing project-owned PostgreSQL 17 cluster on
loopback port 55432 and cached `pg_dump`/`pg_restore`. It reads ignored local
credentials without printing them, creates new `edp_ops_drill_<random>` databases
and `edp_ops_<random>` roles, migrates as a separate schema owner, runs API
registration and worker outbox settlement under runtime credentials, checks denied
privileges, restores to a fresh target, validates durable state and refuses target
reuse. Cleanup drops only names that invocation created. It never uses shared
development/test databases. Synthetic dumps, fixtures and private child logs stay
under ignored `.local/staging-drill-*`. Offline object checks do not prove live S3
version/KMS behavior or approved RPO/RTO.

## Prepare actual staging after owner authorization

1. Choose the isolated host, approved domain/costs, private PostgreSQL/Redis,
   registry and key custody. Enforce network isolation outside Compose; an external
   network name alone does not prove isolation.
2. Provision separate `NOINHERIT LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS`
   migration/API/worker identities. Set passwords through a secret manager or
   interactive `psql \password`, never command-line values. Runtime roles must
   not own schema objects or inherit owner membership.
3. Build from accepted exact source, explicitly supplying `PYTHON_IMAGE` and
   `NODE_IMAGE` as verified base-image digests to the Dockerfiles; mutable defaults
   serve development only. Record service image digests, provenance, dependency/
   container scan and SBOM evidence. Build/push/promotion requires its own
   authorization and is not activated by the repository.
4. Keep separate migration/API/worker/web env files, TLS key/certificate and rendered
   proxy config in restricted operator-owned locations outside source. Only the
   migration file has the owner DSN. Runtime DSNs use their distinct identities;
   API/web BFF keys match. Record secret references, never values. Use accepted TLS
   verification on private database/Redis connections and independent key custody.
5. Set canonical HTTPS `WEB_ORIGIN` and `CORS_ORIGINS` JSON containing exactly that
   origin. `TRUSTED_PROXY_IPS` contains only actual private edge addresses, pinned
   and verified on the pre-provisioned network. Never trust `*` or client forwarding
   headers. Set an explicit edge bind IP and distinct private/edge networks.
6. Render proxy using `python scripts/deployment_contract.py --render-proxy
   <fresh-output> --origin https://<approved-host>`. Check a filled release manifest
   with `--manifest <path>`. Alongside it, `--operator-values <path>` checks a
   non-secret JSON mapping of Compose input names for image/origin/proxy agreement
   and distinct external operator paths. It does not inspect secret file contents,
   ACLs, endpoint identity or actual network isolation.
7. Use `docker compose --env-file <restricted-file> -f
   infra/deployment/staging.compose.json config --quiet`. Never print resolved
   Compose configuration. Validate actual image identity, users, private interfaces,
   temp-volume ownership/limits and one scheduler. Run Nginx syntax and actual TLS
   origin/cookie/header/log negative tests in the isolated environment.

## Rollout, rollback, shutdown and rotation

Before traffic, accept the release evidence and isolated restore. Run one
compatible migration as owner, then apply the reviewed grant policy with explicit
`psql` variables `database`, `migration_role`, `api_role`, `worker_role`. API domain
DML is distinct from ownership/schema/TRUNCATE/audit rewrite permission. Worker
writes are scoped to existing jobs; new tables get no automatic worker grants.
Column-scoped identifier UPDATE grants support PostgreSQL authorization row locks
without granting changes to user status, permission content or role grants.

On authorized rollout start API/web/worker, prove readiness and actual `edp.probe`
round trip, reconcile durable queues and start one Beat. Exercise all synthetic
role journeys and permission negatives. Prove HTTPS secure cookies/exact-origin
mutations, forwarded-header rejection, upload limits, redacted logs, crash/lease
recovery and accepted storage/scanner behavior. Redis ping/readiness alone cannot
accept a worker, scheduler, object store or backup.

To stop, remove traffic, stop Beat, drain owned workers within the 120-second grace
period, preserve durable leases/outbox and stop processes. Do not clear all Redis
queues. Roll back to a previous immutable application with compatible schema and
config. Never routinely downgrade live schema, disable guards or erase evidence.

Rotate runtime credentials by creating new nonowner identities, reapplying reviewed
grants, updating restricted references, rolling consumers and verifying sessions/
jobs before revoking old logins. Check active connections and owner memberships.
Coordinate shared BFF keys across API/web. Encryption-key rotation needs accepted
retained-data/backup decryption migration, not simply replacing an env value.

Use the [recovery](backup-restore.md), [monitoring](../../infra/monitoring/README.md)
and [incident](incident-response.md) runbooks. Staging acceptance, UAT and production
release remain separate gates in the [release checklist](../sdlc/release-checklist.md)
and [operations report](../sdlc/staging-operations-report.md).
