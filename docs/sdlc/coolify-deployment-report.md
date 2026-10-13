# Coolify staging deployment report

Verified on 13 October 2026. The current web/API stack is deployed and Coolify reports `running:healthy`. The deployment operation finished successfully.

## Deployment

- Public site: https://edp.200.234.34.140.sslip.io/ (redirects to `/en`).
- Coolify: http://200.234.34.140:8000/, version 4.4.6.
- Project: `CSJE EDP` (`cgeavixt3zfsfgcfwsynddxi`).
- Environment: `staging` (`0oc89js2hlz7xbt6unzztgvw`).
- Application: `csje-edp` (`koemokjev1yw9fyyaln2axlr`).
- Repository branch: `deploy/coolify`; deployed application commit `5b55110a1bd975ffd14f126f5cddf30457e6aa52`.
- Successful deployment: `5ylpbus2qguqcumemzlp9e5m`.
- Build pack: Docker Compose, `/docker-compose.coolify.yml`, repository-root context.

GitHub access uses a repository-scoped read-only deploy key. Independent generated secrets are stored in Coolify; none are committed. Auto-deploy is disabled; deploy the desired branch commit through Coolify for subsequent changes.

## Implementation

The stack runs Next.js, FastAPI, PostgreSQL 17, Redis 7, a Celery worker and one scheduler. A one-shot migration service applies Alembic and seeds identity roles/permissions before dependent services start. PostgreSQL, Redis and private materials use resource-scoped persistent volumes; only the web service has public proxy routing.

The web image now includes public assets. API runtime/dev lockfiles now include the already-declared QR-code dependency that previously prevented container startup. Compose builds receive required variables through Coolify's build-time environment, with BuildKit secrets enabled and automatic ARG injection disabled. Runtime connection URLs are constructed from injected password variables to preserve credentials across Coolify's literal quoting. Worker and scheduler probes verify broker replies and schedule freshness.

## Verification

- Compose YAML, dependency ordering, Dockerfile paths and private port configuration validated; `git diff --check` passed.
- `npm.cmd run build` passed, including TypeScript and page generation.
- Runtime lockfile installed in an isolated environment; all API imports and staging app creation passed with production dependencies only.
- Remote Docker image builds completed. Alembic/role seeding exited successfully; API readiness passed; final Coolify state is `running:healthy`.
- HTTPS certificate verification passed using normal trust checks. `/`, `/en`, `/ta`, `/en/account`, `/cse-logo.png` and `/illustrations/program-path.svg` returned 200.
- `/api/session/csrf` returned valid JSON with a Secure, SameSite=Strict cookie; unauthenticated `/api/session/me` returned 401.
- Headless Chrome rendered the English page with zero console errors or warnings; screenshot saved locally to `output/playwright/coolify-live.png`.
- Worker connected to Redis. Scheduler-dispatched notification and Meta maintenance tasks completed successfully against the empty staging data set.

## Remaining configuration

No administrator or organization was provisioned; `PUBLIC_ORGANIZATION_ID` is empty. Provision the initial administrator through the trusted operator procedure and then configure the public organization. Email delivery, Meta/provider integrations, and approved retention policies are unconfigured.

This report verifies infrastructure deployment, not the product's production acceptance. UAT, full workflow/device validation, backup/restore, monitoring and other release-gate evidence remain outstanding. Use synthetic data until the existing acceptance gates are completed. Operational setup and rollback guidance is in `docs/deployment/coolify.md`.
