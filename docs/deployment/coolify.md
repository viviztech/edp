# Coolify deployment

Use the Docker Compose build pack with `/docker-compose.coolify.yml`, repository root as the base directory, and a repository-specific read-only deploy key for private Git access.

Set `WEB_ORIGIN` to the public HTTPS origin (no trailing slash). Configure the `web` service domain in Coolify with port `3000`. Set `COOKIE_SECURE=true` through the Compose definition.

Generate independent random URL-safe secrets for `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `BFF_KEY`, and `LMS_MATERIAL_SIGNING_KEY`; enter them in Coolify. Enable both build and runtime availability for all Compose variables: Coolify runs `docker compose build` with a separate build-time environment file, and Compose interpolates the entire definition even when building images. Enable Docker Build Secrets and disable automatic Dockerfile ARG injection so credentials are not embedded in images. Do not commit values or reuse local credentials. Set `PUBLIC_ORGANIZATION_ID` when an organization is provisioned through the trusted administrator procedure.

The migration service runs Alembic to head and seeds identity roles/permissions. It is excluded from overall health because it exits after success. API, Celery worker, and the single scheduler wait for migration completion. PostgreSQL, Redis, and private materials use persistent resource-scoped volumes. No database, Redis, or API port is published to the host.

The API image's shared Compose entrypoint constructs connection URLs inside the container from the injected URL-safe password variables, then executes the service command. This preserves identical database/cache credentials when Coolify's literal-variable handling adds YAML quotes. Set `WEB_ORIGIN` as a regular variable with literal mode disabled; embedding a literal-mode origin inside the CORS JSON would retain extra quotes.

Only web traffic is routed by the Coolify proxy. The API remains reachable internally at `http://api:8000`; `/ready` checks PostgreSQL and Redis. Check both `/en` and `/ta`, `/cse-logo.png`, and a browser session request after deployment. Inspect container health and migration logs.

The worker health check sends a broker control ping directly to its own hostname; it does not depend on environment exports made by the main entrypoint, which Docker health-check subprocesses do not inherit. Scheduler health requires an initialized schedule database updated within ten minutes. Confirm scheduler dispatch and worker task completion in runtime logs as part of the deployment smoke check.

This is a staging deployment of the current code, not evidence that the production product acceptance gates have passed. Email delivery and integrations remain subject to their existing provider and policy requirements. There is no default administrator account. Provision one through the trusted `app.modules.identity.cli bootstrap-admin` operator command when the administrator identity is supplied.

Before a production launch, complete `docs/sdlc/release-checklist.md`, including backup/restore, monitoring, UAT, privacy and retention requirements. For application rollback, redeploy the previous compatible commit and preserve database volumes; do not run a destructive schema downgrade or remove volumes.
