The initial synthetic staging contract is `staging.compose.json`, with explicit
nonroot identities, resource/log limits, private services, separate migration/API/
worker environment files, one migration job and one scheduler. It refers to
pre-provisioned networks and services; it creates no infrastructure. Only the edge
publishes a host port. Service images must be immutable registry digests supplied
by the operator, and TLS keys/configuration remain outside this repository.

Start with [the staging runbook](../../docs/deployment/staging.md),
[`staging.env.example`](staging.env.example) and the
[manifest schema](release-manifest.schema.json). The example manifest contains
placeholders and cannot identify a release. `database-roles.sql` is a reviewed
post-migration grant policy with separate owner/API/worker inputs.
[Object permissions](object-permissions.md) describe the still-disabled file gate.

`python scripts/deployment_contract.py` performs static checks without deploying.
The acceptance harness and actual local PostgreSQL drill are documented in the
runbook. Release gates remain in
[the release checklist](../../docs/sdlc/release-checklist.md).
