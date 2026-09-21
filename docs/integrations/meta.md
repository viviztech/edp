# Meta lead operations

C03.2 adds the staff connection workspace at `/{locale}/admin/meta`. Marketing Executive has organization-scoped view, manage and replay permissions. The UI can create and pause page connections, rotate one or more encrypted credentials, configure and pause form mappings, inspect delivery counts and history, and replay failed events with an audit reason. The API requires an expected version for updates and replay. A conflict means the operator must refresh before retrying.

## Configuration and delivery

Set a unique `META_SECRET_KEY` (Fernet key), an approved `META_EVENT_RETENTION_DAYS` value, and a verified, pinned `META_GRAPH_API_VERSION` in the API and worker environments. Keep the encryption key stable across restarts and rotate provider credentials through the admin action. Without an approved retention value, webhook ingestion is disabled. The webhook URL is `/api/v1/integrations/meta/webhook/{integration_id}`. Only the provider's HTTPS Graph endpoint is used for lead detail retrieval. Configure the provider app and subscription using its current official documentation before live delivery; this repository does not contain production credentials.

Run the API, Redis, a Celery worker and exactly one Celery beat scheduler. Compose provides `worker` and `beat` services. Beat calls `edp.meta.recover_events` and `edp.meta.purge_expired_events` every 60 seconds. The job requeues due queued/retrying events and expired processing leases in batches; a worker claims each event under a database lock. A failed broker send leaves the event due for another attempt. Transient provider failures retry with bounded backoff and a five-attempt limit. Permanent failures remain visible for an authorized operator to replay after correcting the underlying issue. Replay does not create another lead for a completed event.

For host development, from `apps/api` run `celery -A app.workers.celery_app:celery_app worker --loglevel=INFO` and `celery -A app.workers.celery_app:celery_app beat --loglevel=INFO` in separate terminals, with the same API environment and Redis. On Windows, use the virtualenv Celery executable; full worker behavior still needs production-like Compose verification. The API and web alone display the workspace but cannot process incoming leads without the worker and beat.

## Triage

Check `/ready` for database and Redis, the worker queue, and the beat process. In the workspace, inspect queued, processing, retrying, failed, delivered and expired-awaiting-cleanup counts. A processing event older than its 90-second lease should be requeued by the next recovery tick. Resolve provider credentials, Graph version, subscription, and form mapping errors before replay. Replays require a reason and create an audit entry. Never place raw tokens or lead data in logs or support tickets. Use synthetic provider payloads during development.

## Event retention

Each accepted event stores its expiry when ingested from the approved `META_EVENT_RETENTION_DAYS` setting. The minutely cleanup task deletes at most 100 expired inbox rows per run and writes an audit entry containing the event UUID, organization, version and fixed disposal reason; it stores no provider identifier or payload in that entry. Expired events are hidden from staff history and active delivery counts immediately, even before physical cleanup. The health view exposes the number still awaiting cleanup in the selected organization. A persistent or growing count means the scheduler, worker or database needs attention. Replay and worker lead creation reject expired events. A CRM lead and its attribution are retained under their separate policy.

Changing `META_EVENT_RETENTION_DAYS` affects newly accepted events; existing rows retain their recorded expiry. If policy must shorten existing retention, operations must arrange a reviewed data-remediation run rather than merely changing the environment variable. Audit records and backups follow their own approved retention schedules.

Delivery is at least once at the queue boundary. PostgreSQL inbox uniqueness and lead dedupe hash protect against duplicate webhook delivery and repeat worker execution. After an expired inbox row is deleted, a repeated provider delivery may create another inbox row but links to the existing CRM lead. Contact similarity is not an identity merge. Live provider activation remains pending business credentials and approval.
