# Milestone 4 implementation report

Status: A01.1 and A01.2 implemented locally; milestone remains in progress.

## A01.1 configurable applicant-owned drafts

Added organization-scoped published form versions and ordered bilingual typed fields. Applicant drafts belong to the authenticated Person, allow one draft per form version, and save immutable relational revisions with optimistic versions. Required-field completion is derived from the current revision. Owner/scope checks return not-found for another applicant. Create/save audit entries contain identifiers and changed-field names but no answers.

The Next.js applicant workspace uses a fixed application BFF allowlist, session-bound CSRF, a bounded request body, no-store/noindex responses and English/Tamil field labels and states. It exposes draft-only behavior and does not provide submission or document upload. A local-only operator command can create a synthetic review form; migrations do not seed business policy.

Evidence: migration b3e4f5a6b7c8 downgrade/upgrade and Alembic drift check passed on isolated PostgreSQL. Two focused PostgreSQL tests cover idempotent creation, immutable revisions, typed answers, completion, optimistic conflict, audit and cross-user denial. The full API suite passes 70 tests. Changed backend files pass Ruff and the applications module passes strict MyPy. OpenAPI/TypeScript contracts were regenerated. Web ESLint, strict TypeScript, 20 Vitest tests and the Next.js production build pass. The development database is at b3e4f5a6b7c8, a synthetic bilingual form was provisioned, /health, /ready, /docs, and the applicant page pass local HTTP smoke checks on ports 8000 and 3001, and the application API rejects an unauthenticated request with 401. Authenticated browser acceptance now passes for identity, scoped CMS, application policy publication/versioning, responsive layouts and session recovery.


## A01.2 application definition administration and policy versioning

Added one editable definition draft per organization, optimistic edit revisions, ordered bilingual typed fields, immutable published/retired policy versions, clone-to-next-version and atomic publication that retires the previous live version. Existing applicant drafts remain pinned to their original form. PostgreSQL triggers reject published policy or field mutation outside the service.

Program Managers receive scoped view/create/update rights. Program Directors and Super Admins additionally receive the separate publish permission. Create, update, copy and publish are audited with identifiers and changed field names without copying policy text. The staff workspace exposes history, field ordering, explicit publication warning and permission-aware actions through a bounded fixed-allowlist BFF.

Evidence: migration c4f5a6b7c8d9 upgrade/downgrade and Alembic drift checks pass on isolated PostgreSQL. Three new PostgreSQL/API tests plus the existing applicant regressions cover RBAC, authenticated routes, stale writes, database immutability, policy copying, publication retirement, audit and applicant pinning. The full API suite passes 73 tests; changed backend files pass Ruff and the applications module passes strict MyPy. OpenAPI and TypeScript contracts were regenerated. Web strict TypeScript, ESLint, 23 Vitest tests and the Next.js production build pass. The isolated Playwright suite passes authenticated definition creation, publication, version copying, scoped navigation and mobile overflow checks with no JavaScript errors. Local API readiness, the admin route, live OpenAPI paths and unauthenticated BFF rejection also pass on ports 8000 and 3001.
