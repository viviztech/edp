# Notifications contract plan

Provider-neutral interface: enqueue event/recipient/template version; adapter delivery returns supported provider ID/status or classified retryable/permanent/ambiguous failure. No provider configured or messages sent in bootstrap.

PostgreSQL outbox and notification dedupe precede Celery dispatch. Preferences/consent checked at dispatch; locale and approved transactional exception captured as metadata. No PII in task payloads: pass record IDs. Record queued/sent/delivered/failed only when evidenced by provider capability/callback. Retry with bounded backoff; ambiguous outcome reconciled rather than blindly resending. Administrative failure queue and audited replay required. Email/SMS/WhatsApp/FCM credentials remain server-side. Push text minimal; deep links reauthorize content. In-app notification remains available during provider outage. Singleton beat schedules reminders idempotently.
