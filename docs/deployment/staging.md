# Staging deployment plan

The current web/API stack is deployed to an isolated Coolify staging environment using the `deploy/coolify` branch. See [Coolify configuration](coolify.md) and the [deployment report](../sdlc/coolify-deployment-report.md) for resources and verification. PostgreSQL/Redis are private, web traffic uses HTTPS, and secrets are generated separately from local development. Alembic and identity permission seeding run before API/workers start.

This infrastructure deployment does not complete the product staging acceptance gate. Use synthetic data. Administrator/organization provisioning, external delivery and integrations, approved retention policies, private object storage, CI/device and critical-journey verification, monitoring, and backup/restore evidence remain subject to the existing release checklist. Exercise provider sandboxes only and record restore timing/consistency before accepting a release.
