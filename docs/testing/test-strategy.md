# Testing strategy

Tests prove services and user outcomes rather than mirror implementations. Synthetic fixtures only, isolated PostgreSQL (not SQLite for concurrency/constraint evidence). Every feature follows DoD.

| Layer | Evidence |
|---|---|
| Backend unit | Transition tables, rubric weighting, permission scopes, retry classification, validation |
| PostgreSQL integration | FK/unique/checks, transactions+audit/outbox atomicity, refresh races, duplicate submissions/check-ins, downgrade/upgrade on disposable DB |
| API | Valid/invalid input, sanitized errors, auth/scope matrix, pagination limits, signed file access, idempotency |
| Worker/adapters | Retry/backoff, duplicate events, consent, provider capability differences, ambiguous timeout, Redis outage/recovery |
| Web | Localized critical component states; keyboard and form labels; auth/BFF CSRF; responsive layouts; production build |
| Flutter | Repository/session unit tests; localized widgets/navigation; device deep-link/push routing; secure storage logout; offline policy |
| E2E | Real API/DB and channel UI; no auth mocks for security acceptance |
| Operational | Compose health/job round-trip; staging restore; load/query plans; dependency/container/secret scan; manual accessibility |

## Required journey coverage (master Section 26)

1. Public → registration → application (A01/F02).
2. Meta webhook → lead → applicant conversion (C03/C02).
3. Reviewer → shortlist → interview → selection (A02).
4. Selected applicant → enrollment → participant login (P01).
5. Learner → lesson → quiz/assignment → progress (L01/L02).
6. Trainer session → QR check-in; replay/window rejection (L03).
7. Mentor assignment → session → action item (M01).
8. Business plan → mentor review (B01, P1).
9. Funding tracker transitions (K01).
10. Alumni business follow-up (B02 P1); minimal outcome separately P0 I01.
11. Ticket lifecycle (S01).
12. CMS publish → public web/mobile content (C01).
13. Unauthorized action denied across UI/API (F03 and every slice).
14. Sensitive export permission and audit (I01/C02).

CI: Python 3.13 Ruff, MyPy, Pytest; PostgreSQL migration upgrade→downgrade→upgrade and metadata drift; web ESLint, strict tsc, tests and Next build; Flutter format/analyze/test and supported build; secret/dependency scanning. Add critical E2E with features, never claim coverage from empty placeholder suites. Pin actions/dependencies as release hardening requires.

Bootstrap tests: health contract, readiness dependency failure without internals, request IDs, config failure, worker task function, localization key parity, localized shell widget. Live migration/Compose/mobile build results require their runtimes. Record exact commands/results/blockers in milestone report. No skipped or unavailable command counts as success.

Performance: obtain volume assumptions; build realistic synthetic distribution; measure p50/p95/p99/error rates and DB plans; agree budgets after baseline. No invented concurrency target. Manual smoke evidence includes environment, actor role, steps, result and screenshot where applicable.

## Foundation execution

Set AUTH_TEST_DATABASE_URL to a dedicated migrated edp_auth_test/edp_test database; tests deliberately truncate synthetic fixtures and reject any other database name. Current identity suite covers concurrency and real PostgreSQL constraints. `scripts/run-foundation-browser-test.py` uses separate edp_foundation_e2e/edp_test, spawns owned API and standalone web processes on loopback 8100/3100, generates ephemeral test keys and runs actual Chrome/Chromium UI acceptance. No live messaging. Playwright defaults to bundled Chromium; PLAYWRIGHT_CHANNEL=chrome selects locally installed Chrome. All test evidence/status is in the foundation continuation report; remote CI must still run.

Backend test discovery: `pytest -q` from apps/api and `pytest -q apps/api/tests` from the repository root both use the explicit API-root pythonpath in pyproject.toml. Integration tests still require the dedicated migrated AUTH_TEST_DATABASE_URL. Remote CI evidence and remaining gates are recorded in the foundation continuation report.

## C03 Meta ingestion evidence

Focused tests cover exact raw-body HMAC verification and tamper rejection, encrypted provider secrets, mapping allowlists and required name mapping, reduction of provider responses to configured CRM fields, and denial when an integration is outside the requested organization. PostgreSQL acceptance must additionally prove concurrent duplicate delivery creates one inbox row and one lead, constraints survive upgrade/downgrade/upgrade, queue outage remains replayable, and worker retries do not process a claimed event twice.

## A01.4 submission coverage

PostgreSQL tests exercise owner and organization isolation, open-cycle binding, one application per person/cycle, incomplete-answer and missing-acknowledgement rejection, optimistic conflict, idempotent successful retry, stable unique application number, atomic status/audit evidence and direct answer immutability after submission. Route tests use authenticated sessions. Web gates cover the exact BFF allowlist, localized contract compilation, lint, unit tests and production build. Isolated authenticated Chrome acceptance demonstrates cycle selection, final confirmation, immutable receipt, CSRF/scope enforcement and narrow-screen layout with no JavaScript errors.

## A02.2 selection scoring coverage

Database-backed tests exercise rubric-bound criterion validation, score ranges, required scores, deterministic weighted totals, reviewer ownership, conflict and active-cycle gates, optimistic versions, post-submission database immutability, moderation permission, reasoned exclude/restore and aggregate counts/means. Web tests cover the fixed BFF allowlist; strict TypeScript, ESLint and a production build validate the generated contract and reviewer workspace. Authenticated browser acceptance must save scores and a comment, submit, verify the locked total, moderate, and observe the aggregate change without exposing it to a reviewer account.

## A02.3 selection finalization coverage

PostgreSQL tests cover evidence-backed shortlisting, unauthorized reviewer decisions, panel eligibility, interview range and membership constraints, single-submit panel scores, database immutability, incomplete-panel completion rejection, calculated average, decision snapshots, optimistic application versions, terminal overrides, append-only decisions, scoped reviewer visibility, applicant status and finalizable-cycle rules. Migration verification runs downgrade/upgrade/drift against populated data. Authenticated Chrome covers the staff workflow from review through finalized selected state, including two override transitions and persisted database assertions.

## P01.2 program delivery coverage

PostgreSQL acceptance continues the real A02.3 workflow through finalized selected application conversion, capacity and duplicate guards, Person reuse, participant role creation, enrolled status receipt, atomic audit/outbox evidence, session date/mode validation, self-only schedule projection, chronological lifecycle events and immutable participant history. Migration verification uses populated downgrade/re-upgrade/drift. Web gates cover the exact BFF allowlist, generated contracts, strict TypeScript, ESLint, Vitest and production build.
