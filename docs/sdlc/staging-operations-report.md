# Local staging operations preparation report

Date: 2026-10-24 (Asia/Calcutta). Scope:
[staging operations plan](staging-operations-plan.md), under the
[development closure plan](development-closure-plan.md). Local preparation is
implemented; staging deployment/acceptance, UAT and production release remain open.

## Implemented artifacts

- Host-neutral synthetic staging Compose configuration, immutable digest inputs,
  one migration/one scheduler, separate migration/API/worker env references,
  private services, explicit nonroot identities, bounded process/memory/CPU/temp
  storage, graceful shutdown and applied rotating logs.
- Release manifest schema/example and static/operator-value validator, binding
  image/origin/CORS/proxy identities and separate operator paths. TLS edge template
  rejects alternate hosts, overwrites forwarding headers, limits requests and
  hides diagnostics. Logs exclude capability-bearing paths/queries.
- Explicit post-migration PostgreSQL grants and object/KMS capability matrix.
  Runtime roles are nonowners without schema, role, TRUNCATE or audit mutation
  privileges. Worker writes are scoped; identifier-column grants support current
  authorization row locks without granting user-status/permission-content changes.
- Guarded fresh synthetic backup/restore drill and dry-run recovery validator,
  pinned offline version/hash/encryption/key/hold/disposal fixtures, deletion and
  outbox reconciliation design, incident/rollout/rollback/rotation runbooks.
- Bounded read-only local operations collector, low-cardinality signal catalog,
  local recording alert evaluator and non-deploying source/config acceptance
  ledger. Unavailable runtime signals remain null; unknown/stale/unsafe samples
  fail. CI now includes operations regression/lint/format checks; remote execution
  has not been claimed.

## Executed evidence

`python -m unittest discover -s scripts/tests -q`: 14 tests passed. Coverage
includes mutable-image/shared-identity/privileged/public-service rejection,
origin/header/config injection, operator input agreement, missing/tampered/unsafe
backup/object paths, absent versions/keys/scopes, retained holds and disposed/
revoked access, local dependency failure, forbidden connection overrides and
sanitized alert failure/recovery without external delivery. Declaring all release
gates passed does not cause the static validator to certify their evidence.

Operations scripts/tests pass Ruff check and format using the API project's Python
3.13 configuration. `python scripts/deployment_contract.py` validates the static
topology without contacting infrastructure. The final selected-source acceptance
ledger is rerun by the integration owner after source changes settle.

Actual local PostgreSQL drill evidence is retained under ignored
`.local/staging-drill-99eea3a8b2b2/report.json`: migration `q3b9c5d1e678` ran as a
separate schema owner; API registration/audit and worker settlement executed under
distinct runtime logins; 26 privilege negatives passed; a custom-format dump
restored audit/identity/outbox/schema state to a fresh isolated database; an
existing-target restore was refused; cleanup passed. Restore execution measured
3.830 seconds for that synthetic fixture. It is not
an approved RPO/RTO or representative capacity result. This final rerun includes
the connection-override hardening, read-only operational aggregate probe and final
quotation catalogue-reference nullability constraint. A prior user-interrupted
trial was separately cleaned after verifying its source identity, empty rolled-back
restore target and absence of active connections; it is not counted as a pass.

## Unexecuted external gates

| Gate | Position |
| --- | --- |
| Docker/Nginx process, TLS/cookie/proxy and Linux confinement | Unavailable on this host; static templates do not replace runtime tests |
| Redis/worker round trip, one-Beat and crash/lease recovery | Requires actual isolated services; PostgreSQL settlement probe is separate |
| Live S3/IAM/KMS/version/ClamD freshness and retained objects | Unavailable; offline synthetic bytes are explicitly labeled |
| Off-host scheduled backups, deletion ledger custody and approved RPO/RTO | Requires owner policy, infrastructure, keys and accepted staged restore |
| Registry image builds/promotion, vulnerability scan/SBOM and exact-revision remote CI | Deferred under local-only source/publication boundary |
| Hosting/domain/costs, secrets, alert/incident recipients and live dashboards | Owner/environment inputs pending; nothing provisioned or activated |
| Real collection/sender/privacy/content/retention approval, UAT, measured accessibility/performance | Separate client/release acceptance |
| Staging/production rollout | No deployment authorized or performed |

No source publication, provider call, real message, paid resource, real personal
data collection, DNS/TLS operation or deployment occurred during this work.
