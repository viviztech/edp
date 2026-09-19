# Milestone 3 - CRM implementation report

Status: in progress; no production release claim.

## C02 registration identity link

Added an explicit, organization-scoped command linking a lead to an existing Person. The command requires `crm.lead.convert`, a matching optimistic version and an audit reason. It creates an immutable attribution snapshot and advances the lead to `registration_started`. It does not match or merge identities using email or phone, and it reserves `converted` for the future transaction that links a real application. Generic lead edits cannot set `converted` or `merged`. A misplaced activity expiry field from the preceding export slice was also removed before migration. OpenAPI and TypeScript contracts were regenerated; focused Ruff, MyPy, TypeScript and unit tests passed.


## C02 staff CRM workspace

Added an English/Tamil staff CRM workspace with an organization-scoped lead queue and detail ledger. Permission-aware actions cover lead creation and updates, assignment, follow-up activities, duplicate review resolution, export jobs and registration links. Browser traffic uses a fixed CRM BFF route allowlist, session-bound CSRF for mutations, bounded bodies and private/no-store responses. The layout uses a responsive case-ledger pattern with explicit loading, empty, conflict and permission states. Web lint, strict typecheck, eight Vitest tests and the Next.js production build passed.

## C02 lead organization and follow-up queue

Added organization-scoped lead tags with normalized uniqueness, permission-gated create, attach, detach and list operations, and audit records for every mutation. Follow-up activities now use optimistic versions and an explicit completion command; repeat or stale completion attempts return conflicts. The lead queue supports a database-level overdue filter using incomplete activities with due dates before the current time. The staff workspace exposes tags as compact case markers, pending follow-up completion, and an overdue-only queue toggle through the fixed BFF allowlist. The migration is reversible and remains the single Alembic head. OpenAPI and TypeScript contracts were regenerated. Focused backend lint, MyPy and six CRM tests, plus frontend lint, strict typecheck, eight Vitest tests and the production build passed.
