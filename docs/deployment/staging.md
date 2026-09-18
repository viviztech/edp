# Staging deployment plan

Not deployed. Provision isolated synthetic-data environment, private PostgreSQL/Redis, S3, TLS edge and secret references. Build immutable images from green CI. Run Alembic as a single release job, then API/web/worker. Smoke health/readiness/worker and critical journeys; verify scoped synthetic roles. Exercise provider sandboxes only. Restore a backup to an isolated target and record timing/consistency. Release checklist must pass before accepting staging. Real credentials, host/domain and deployment approval remain unsupplied.
