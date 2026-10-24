# Notifications contract and N01.1 implementation

Current continuation: [essential communications](../architecture/essential-communications.md) adds configurable global identity email delivery and a separate enrollment participant inbox. The sections below preserve the existing CRM/helpdesk contracts. SMTP capability means server acceptance only, not recipient delivery. All senders remain disabled by default.

Provider-neutral interface: enqueue event/recipient/template version; adapter delivery returns supported provider ID/status or classified retryable/permanent/ambiguous failure. No provider configured or messages sent in bootstrap.

## Global identity email and participant enrollment updates

Verification/password-reset intents are global, encrypted and committed with the challenge/audit before returning. `AUTH_DELIVERY_BACKEND=development` is explicitly a local/test no-delivery queue. `smtp` requires `AUTH_SMTP_ENABLED`, `AUTH_TEMPLATES_APPROVED`, an approved canonical origin/sender, credentials, verified implicit TLS or STARTTLS and explicit `AUTH_DELIVERY_RETENTION_DAYS`. Missing capability fails unavailable outside local/test. SMTP tasks carry only delivery IDs; the request path never contacts the sender.

The versioned English/Tamil message uses a fixed `/{locale}/account/verify` or `/reset` URL and a separately entered code. Code/password never appear in URLs or browser persistence and are cleared after success. A sending marker precedes protocol I/O; uncertain acknowledgements and interrupted sending require operator reconciliation rather than automatic resend. A final accepted DATA acknowledgement is retained even if QUIT fails. The trusted `python -m app.modules.identity.delivery_cli health` command exposes safe aggregate capability/status, while inspect/recover require the exact target/version and an explicit audit reason. Real sender activation and content/retention approval remain operational gates.

Enrollment conversion emits `enrollment.created`. `edp.participant_notifications.consume_outbox` validates its exact relational context, atomically creates a unique typed notice or records suppression, and settles the outbox. Unsupported/invalid/expired/exhausted events retain safe visible reasons. `PARTICIPANT_NOTIFICATION_RETENTION_DAYS` has no default; without it the consumer leaves work pending. The independent batch/attempt settings bound processing. API, worker and the single Beat share these values.

Recipient routes are `/api/v1/participant-notifications/organizations/{org}/mine`, `/preference` and `/{notice_id}/read`; the English/Tamil web inbox is `/{locale}/updates?organization={org}`. Current active account, `participant.self`, owning active/completed enrollment and participant are checked. Notices contain identifiers/topic/template/action and lifecycle metadata, not application answers or contact data. The only action is the same-organization schedule, which reauthorizes. Preferences suppress future events without erasing authorized history or backfilling suppressed events. Mark-read/preference writes require current versions and audit. Operations health is separately organization/permission scoped and exposes aggregate counts, not participant inbox contents.

The three new Beat entries recover identity deliveries, consume enrollment events and purge expired participant notices. Local protocol peers and direct task-function tests do not establish live SMTP or real Redis/worker/Beat operation. SMS/WhatsApp/FCM remain unavailable until separately implemented/configured against approved providers.

## Future provider contract

PostgreSQL outbox and notification dedupe precede Celery dispatch. Preferences/consent checked at dispatch; locale and approved transactional exception captured as metadata. No PII in task payloads: pass record IDs. Record queued/sent/delivered/failed only when evidenced by provider capability/callback. Retry with bounded backoff; ambiguous outcome reconciled rather than blindly resending. Administrative failure queue and audited replay required. Email/SMS/WhatsApp/FCM credentials remain server-side. Push text minimal; deep links reauthorize content. In-app notification remains available during provider outage. Singleton beat schedules reminders idempotently.

## N01.1: CRM assignment inbox

Assigning a CRM lead to a user writes a notification_intents row in the same PostgreSQL transaction as the lead update and audit entry. The event key includes the lead ID and new version, and (organization_id, recipient_user_id, event_key) is unique. A failed or conflicting lead edit therefore cannot leave an intent. Assigning the same lead again at a later version creates a distinct intent.

Celery beat invokes edp.notifications.deliver_in_app once per minute. Each invocation locks at most 100 pending intents with SKIP LOCKED. It checks that the recipient remains active, has crm.lead.view in the organization, still owns the lead, and has enabled the lead_assignment preference. It then marks the intent delivered or suppressed and writes a system audit record. A failed transaction leaves the intent pending for a later tick. Delivered means visible in the in-app inbox only; it does not imply an email, push message, or provider acknowledgement. A preference change affects pending delivery, not items already delivered.

Authenticated recipients can use GET /api/v1/notifications/organizations/{organization_id}/preference, POST .../preference, GET .../mine, and POST .../{notification_id}/read. Requests require crm.lead.view; inbox reads and read mutations are limited to the recipient and organization. Preference and read mutations use expected versions and produce audit records. The web workspace is /{locale}/admin/notifications in English and Tamil. Its fixed BFF route uses CSRF and origin checks for POST requests. Notifications contain a topic, lead UUID, timestamps and state; they store no lead name, contact details, or message body. The UI links to the scoped CRM queue, where access is checked again.

This slice does not install an external provider, delivery attempt table, or failure/replay console. Those remain future N01 work. Product/operations must approve notification and audit retention before real data is used; local development uses synthetic data. Run the API, Redis, Celery worker and beat against the same database for automatic in-app delivery; an API/web-only preview will display the inbox but will not dispatch pending intents.


## N01.2: notification retention

Set NOTIFICATION_RETENTION_DAYS only after the privacy owner approves the number of days. It has no default and is bounded to 1-3650. Local/test may use synthetic notices with this setting absent; staging/production reject lead assignment notice creation when it is absent, rolling back the associated assignment. API, worker and beat must share the setting. A shorter period takes effect immediately for existing notices, which are hidden from inbox reads before physical cleanup.

With a configured period, pending notices older than the cutoff cannot be delivered, expired delivered notices cannot be read or marked read, and the minutely edp.notifications.purge_expired task deletes at most 100 expired intents per invocation under row locks. It records one minimal audit event per disposal in the same transaction. The parent CRM lead and recipient preference survive. An unset policy causes the cleanup task to leave local/test data untouched. Audit and backup retention follow separate approved policies. Operators should monitor task health and backlog; this slice adds no external delivery provider.


## N01.3: CRM follow-up due reminders

The minutely edp.notifications.queue_due_followups task scans at most 100 incomplete CRM call, email, meeting or task activities whose due time has arrived. It skips unassigned leads and merged/converted leads. A row lock, activity/recipient uniqueness and an intent event key prevent duplicate queueing across concurrent scans. The activity records the last recipient queued so notification retention cleanup cannot requeue the same overdue work for an unchanged assignee. A new assignee can receive a new reminder; a previously queued reminder for the old assignee is suppressed at dispatch.

The intent stores only the activity and lead UUIDs, recipient, organization and topic. Dispatch rechecks active recipient, organization permission, current lead assignment, activity completion, due time and the separate followup_due preference. A completed or reassigned activity therefore does not expose a pending reminder to the wrong person. The staff inbox displays generic English/Tamil follow-up text and links to the authorized CRM queue; it does not copy activity notes or lead contact data. The existing preference endpoint accepts an allowlisted topic query, defaulting to lead_assignment for older clients. The browser BFF accepts only those two topics. Turning off follow-up reminders affects pending/future delivery, not items already delivered.

Staging/production skip creation while NOTIFICATION_RETENTION_DAYS is unset. API, worker and beat must use the same approved setting. Scheduled delivery can occur on the next beat tick after queueing. Celery task execution still requires a running Redis broker, worker and exactly one beat scheduler.

## In-app delivery recovery

Dispatch processes at most 100 due intents per invocation under row locks. A per-intent eligibility error creates a generic `dispatch_error` state without saving exception text. It retries after 2 and 4 minutes and then remains `failed` after the third attempt; ordinary revocation, reassignment, completion and opt-out remain intentional suppression. Database-wide failures still roll back the batch and should be investigated in worker logs. The staff failure list and manual replay are organization-scoped and require separate `notification.operations.view` and `notification.operations.replay` permissions. Seeded Program Directors/Managers and Super Admins have these permissions. Replay requires an audit reason and current version, resets that intent to pending and rechecks all delivery conditions. Expired intents are hidden and cannot be replayed. Operators must run the API, worker and beat against the same migrated database.

## Phase 9 ticket updates

Helpdesk uses dedicated durable `helpdesk_notices` and `helpdesk_preferences` with the event transaction, separate from CRM's worker-dispatched intents. Assignment notifies the recipient assignee; shared owner replies notify the current assignee; shared staff replies/status/reopen changes notify the owner. The actor does not notify themselves. Internal notes create no notice. Per-user organization opt-out prevents future notice creation; existing notices remain readable only while the recipient still has ticket access. Notices contain identifiers/event/version, never ticket subject, body or attachment text.

The helpdesk workspace contains its own inbox, exact-version read markers and preference. Availability means committed in-app data only; no email/push/SMS/WhatsApp attempt or delivery status is asserted. Event uniqueness prevents duplicates; a failed ticket transaction leaves no notice. Authorized retention/disposal and external-channel integration remain release/future N01 work.
