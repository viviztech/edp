# Milestone 4 implementation report

Status: A01.1 implemented locally; milestone remains in progress.

## A01.1 configurable applicant-owned drafts

Added organization-scoped published form versions and ordered bilingual typed fields. Applicant drafts belong to the authenticated Person, allow one draft per form version, and save immutable relational revisions with optimistic versions. Required-field completion is derived from the current revision. Owner/scope checks return not-found for another applicant. Create/save audit entries contain identifiers and changed-field names but no answers.

The Next.js applicant workspace uses a fixed application BFF allowlist, session-bound CSRF, a bounded request body, no-store/noindex responses and English/Tamil field labels and states. It exposes draft-only behavior and does not provide submission or document upload. A local-only operator command can create a synthetic review form; migrations do not seed business policy.

Evidence: migration b3e4f5a6b7c8 downgrade/upgrade and Alembic drift check passed on isolated PostgreSQL. Two focused PostgreSQL tests cover idempotent creation, immutable revisions, typed answers, completion, optimistic conflict, audit and cross-user denial. The full API suite passes 70 tests. Changed backend files pass Ruff and the applications module passes strict MyPy. OpenAPI/TypeScript contracts were regenerated. Web ESLint, strict TypeScript, 20 Vitest tests and the Next.js production build pass. The development database is at b3e4f5a6b7c8, a synthetic bilingual form was provisioned, /health, /ready, /docs, and the applicant page pass local HTTP smoke checks on ports 8000 and 3001, and the application API rejects an unauthenticated request with 401. Authenticated browser acceptance remains open for the milestone gate.
