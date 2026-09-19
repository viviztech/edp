# Milestone 3 - CRM implementation report

Status: in progress; no production release claim.

## C02 registration identity link

Added an explicit, organization-scoped command linking a lead to an existing Person. The command requires `crm.lead.convert`, a matching optimistic version and an audit reason. It creates an immutable attribution snapshot and advances the lead to `registration_started`. It does not match or merge identities using email or phone, and it reserves `converted` for the future transaction that links a real application. Generic lead edits cannot set `converted` or `merged`. A misplaced activity expiry field from the preceding export slice was also removed before migration. OpenAPI and TypeScript contracts were regenerated; focused Ruff, MyPy, TypeScript and unit tests passed.


## C02 staff CRM workspace

Added an English/Tamil staff CRM workspace with an organization-scoped lead queue and detail ledger. Permission-aware actions cover lead creation and updates, assignment, follow-up activities, duplicate review resolution, export jobs and registration links. Browser traffic uses a fixed CRM BFF route allowlist, session-bound CSRF for mutations, bounded bodies and private/no-store responses. The layout uses a responsive case-ledger pattern with explicit loading, empty, conflict and permission states. Web lint, strict typecheck, eight Vitest tests and the Next.js production build passed.
