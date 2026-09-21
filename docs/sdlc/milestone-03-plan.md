# Milestone 3 - CRM and lead integrations

Status: in progress. Authority: master Sections 7, 24, 30 and backlog C02-C03.

1. C02.1: organization-scoped attributed leads with assignments and lifecycle states.
2. C02.2: append-oriented follow-up activities and due dates.
3. C02.3: duplicate review and controlled merge preserving both records and attribution.
4. C02.4: permissioned asynchronous export with audit evidence.
5. C02.5: explicit conversion boundary into registration/application without automatic identity merge.
6. C03: verified Meta webhook inbox, mapping, retries and operational health.

All slices require scoped authorization, optimistic concurrency, bounded lists, PostgreSQL migration tests, generated contracts and negative cross-organization tests.

## C03.3 — Meta event retention enforcement

Requirement: master Section 7 requires a retention policy for webhook troubleshooting metadata. The approved period remains an operator setting (`META_EVENT_RETENTION_DAYS`); engineering does not choose a default. Existing events carry `retention_expires_at`.

Acceptance criteria:

1. A scheduled, bounded PostgreSQL task removes expired Meta inbox events and records an allowlisted audit entry for each disposal; CRM leads and their attribution remain intact.
2. Concurrent workers cannot create or replay a lead from an expired event. An active processing lease may finish only while its event is still within retention.
3. Fresh events remain available; old events disappear from staff history and active delivery counts, while a scoped expired-backlog count exposes cleanup delays. A repeated provider delivery after expiry may create a new inbox row but must link to the existing CRM lead without duplicating it.
4. Isolated PostgreSQL tests cover expiration boundaries, an expired queued event, lead preservation, duplicate delivery after disposal, and repeat cleanup. Ruff, MyPy, full API tests, migration check and local smoke pass.

Implementation: reuse the existing expiry column and audit table; no new schema or browser command. Celery beat runs a minutely batch task, and the worker claim path rejects expired events even if the scheduler is delayed. Purge is idempotent and handles at most 100 rows per invocation; later ticks continue the backlog. The scheduler and worker must share the same database and environment.

Scope: webhook operational metadata only. CRM lead and audit retention require separate policy decisions. Live provider activation and Compose runtime checks still require external prerequisites.
