# Milestone 3 - CRM and lead integrations

Status: in progress. Authority: master Sections 7, 24, 30 and backlog C02-C03 and N01.

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

## N01.1 — durable staff assignment notifications

Authority: master Phase 3 communications foundation and backlog N01. This slice sends only in-app notifications for CRM lead assignment; external email/SMS/WhatsApp/FCM require approved providers and later slices. It uses no provider credentials or message text containing lead PII.

Acceptance: a successful lead reassignment writes one deduplicated PostgreSQL intent in the same transaction as the lead version and audit. Repeating or rolling back the mutation creates no extra intent. A bounded worker materializes an in-app item only for an active recipient who still has scoped CRM lead-view permission and has not disabled lead-assignment notices. Suppressed items remain auditable without being shown. The recipient can list only their own organization-scoped items, set a versioned preference, and mark a delivered item read. English/Tamil staff UI covers loading, empty, error and conflict states. Wrong-org and other-user access are denied.

Verification: migration upgrade/downgrade/check on disposable PostgreSQL; transaction, duplicate, opt-out, inactive-user and cross-organization tests; generated OpenAPI/types; backend and web lint/type/tests/build; local API/web smoke. One Celery beat schedule processes pending intents in bounded batches. No external delivery status is claimed.

## N01.2 - in-app notification retention enforcement

Authority: master Sections 19, 30 and 38; the privacy inventory and N01 backlog. This slice applies only to CRM assignment notification intents and preferences already in N01.1. NOTIFICATION_RETENTION_DAYS is deployment-approved configuration with no code default. A missing value blocks new assignment notices in staging/production, and remains a real-data launch blocker; synthetic local development can continue.

Acceptance: with a configured period, recipient inbox reads hide expired intents immediately, mark-read rejects an expired item, the delivery worker never exposes an expired pending intent, and a scheduled worker deletes at most 100 expired rows per invocation under row locks. Each deletion writes a minimal audit event in the same transaction. The parent CRM lead and user preference survive. Repeating cleanup is harmless. PostgreSQL tests cover cutoff, ownership, read denial, bounded repeat cleanup and lead preservation. Configuration validation, lint/type checks, full suite and local smoke must pass. No external delivery is added.


## N01.3 - CRM follow-up due reminders

Authority: master Sections 7 and 19 (followup.due), Phase 3 communications foundation, C02 activity queue and N01. Existing CRM activities have due dates and completion versions. This slice adds only in-app notices for incomplete, due follow-ups; no external channel or lead note/contact detail is copied into a notification.

Acceptance: a bounded scheduled scan creates at most one intent per due activity and current assignee, with database uniqueness and locking across concurrent runs. It skips future, completed, unassigned and merged/converted lead work. If a lead is reassigned, the old pending intent is suppressed at dispatch and the current assignee can receive a new one. Completing an activity before dispatch suppresses its pending reminder. Dispatch rechecks organization, activity, lead ownership, active recipient, CRM permission and a separate versioned follow-up preference. Inbox copy and controls work in English and Tamil; wrong-organization and other-recipient access remain denied. Migration upgrade/downgrade/drift, isolated PostgreSQL tests, generated contracts, web checks and local smoke must pass. Provider delivery remains outside scope.

## N01.4 - bounded in-app delivery recovery

Authority: master Phase 3 communications foundation, backlog N01 and the existing notification retention policy. Only in-app delivery is covered; no external provider state is inferred.

Acceptance: a failed dispatch attempt is isolated to one intent and recorded with a safe error code, attempt count, version and audit action. Automatic retries wait 2 then 4 minutes and stop after three attempts. A failed intent is visible only in its organization to staff with notification.operations.view. An audited, version-checked replay requires notification.operations.replay, a reason, and a still-retained failed intent; delivery rechecks recipient permission, lead ownership, due activity and preference. Suppressed/delivered/expired intents cannot be replayed. The staff operations UI supports English and Tamil, safe empty/error/loading states and a bounded list. PostgreSQL tests, migration round trip, contracts, backend/frontend checks and local smoke are required.
