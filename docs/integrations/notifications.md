# Notifications contract and N01.1 implementation

Provider-neutral interface: enqueue event/recipient/template version; adapter delivery returns supported provider ID/status or classified retryable/permanent/ambiguous failure. No provider configured or messages sent in bootstrap.

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
