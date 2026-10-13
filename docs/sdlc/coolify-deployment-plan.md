# Coolify deployment plan

Deploy the current EDP application to the user-supplied Coolify instance in an isolated staging environment. This infrastructure deployment does not mark the product's production acceptance gates complete.

Acceptance:
- Build the existing Next.js and FastAPI Dockerfiles from a dedicated deployment branch.
- Include public web assets in the standalone image.
- Run private PostgreSQL and Redis with persistent volumes and generated credentials.
- Apply Alembic migrations and seed identity permissions before starting API and workers.
- Expose only the web service through Coolify's HTTPS proxy; use secure cookies and the matching origin.
- Verify deployment logs, container health, both locales, static assets, and browser API access.
- Keep tokens, passwords, and private keys out of Git and deployment logs.

External email delivery, Meta integrations, admin provisioning, and approved retention policies require their existing configuration and remain outside this deployment task.
