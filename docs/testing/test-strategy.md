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
