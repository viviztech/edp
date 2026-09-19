# Milestone 3 - CRM implementation report

Status: in progress; no production release claim.

## C02 registration identity link

Added an explicit, organization-scoped command linking a lead to an existing Person. The command requires `crm.lead.convert`, a matching optimistic version and an audit reason. It creates an immutable attribution snapshot and advances the lead to `registration_started`. It does not match or merge identities using email or phone, and it reserves `converted` for the future transaction that links a real application. Generic lead edits cannot set `converted` or `merged`. A misplaced activity expiry field from the preceding export slice was also removed before migration. OpenAPI and TypeScript contracts were regenerated; focused Ruff, MyPy, TypeScript and unit tests passed.
