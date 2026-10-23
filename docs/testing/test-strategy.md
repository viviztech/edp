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
    Phase 9 adds `scripts/run-helpdesk-browser-test.py`: separate owner, peer, support, admin and unrelated accounts; claim/assignment, shared/private text and files, waiting/reply/resolution/closure/reopen, notices/opt-out, stale-write recovery, ownership negatives, bilingual responsive layouts and B02 policy-freeze/outcome evidence. See the [phase report](../sdlc/milestone-09-report.md) for executed local results; native/remote/operational gates remain distinct.
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


## P01.3 coordinator scope coverage

PostgreSQL/API tests create two centers and cohorts, prove that an unassigned coordinator is denied, create a center binding, and confirm that catalog and schedule access include only the assigned center. Negative cases cover wrong-cohort mutation, duplicate active assignment, incompatible account role and direct database scope tampering. Revocation is optimistic, audited and immediately removes access. Route coverage exercises assignment creation/revocation through authenticated HTTP. Migration verification downgrades to P01.2, upgrades to head and checks metadata drift. Web tests pin the exact BFF allowlist; strict TypeScript, ESLint, Vitest, production build and authenticated responsive browser acceptance remain the UI gates.

## L01.1 evidence

The PostgreSQL workflow test covers incomplete publication rejection, bilingual ordered course creation, private material metadata, publication, cohort assignment, duplicate rejection, enrollment-scoped visibility, provider-key non-disclosure, idempotent course start, unauthorized course denial, audit creation and direct database mutation rejection after publication. The full database-backed API suite passes 84 tests.

Migration 7e6ae3e5a10d passes downgrade to P01.3, re-upgrade and Alembic drift checks. Focused LMS Ruff and strict MyPy pass. Generated OpenAPI and TypeScript contracts are current. Web TypeScript, ESLint, 32 Vitest tests and the Next.js production build pass. Authenticated Chrome completes staff authoring/publication/assignment and learner access/start, checks persisted evidence and mobile overflow, and reports no JavaScript errors. Repository-wide Ruff/MyPy remains red on separately recorded legacy CMS and selection findings.

## L01.2 evidence

The PostgreSQL LMS acceptance test covers reverse prerequisite rejection, blocked out-of-order completion, idempotent retry, 50% aggregation, automatic final completion, cohort summary aggregation, audit evidence, and database rejection of completion-evidence mutation. Migration downgrade/upgrade/drift, focused Ruff and strict MyPy, the full API suite, TypeScript, ESLint, Vitest, Next production build, and authenticated browser acceptance form the release gate.

## L01.3 delivery evidence

PostgreSQL/API acceptance creates a Trainer role and proves denial without a staff assignment, cohort-bounded visibility after assignment, provider-key non-disclosure, learner progress visibility, learner and trainer material issuance/delivery, signed-token tamper rejection and immediate denial after assignment revocation. Additional negative checks cover missing provider configuration and confined path resolution. Web tests pin exact trainer/access/delivery BFF paths and malformed-token rejection. Strict TypeScript, ESLint, Vitest, production build and authenticated browser material download are release gates. Migration validation runs upgrade, downgrade to L01.2, re-upgrade and drift against the disposable `edp_test` database.

## L02.1 assessment evidence

PostgreSQL/API acceptance covers draft authoring, incomplete publication rejection, answer-key validation, learner answer-key non-disclosure, started-course and prerequisite gates, failed and passing attempts, bounded retries, server-derived scores, trainer cohort summaries, audit evidence and database rejection of attempt mutation. Migration validation performs downgrade to L01.3, re-upgrade and metadata drift checks. Web coverage includes exact BFF paths, bilingual admin/learner/trainer states, strict TypeScript, ESLint, 32 Vitest tests, a single-worker production build for the constrained local host, and authenticated Chrome authoring plus two automatically graded attempts.

## L02.2 assignment evidence

PostgreSQL/API acceptance covers draft assignment authoring, learner availability and prerequisite scope, immutable revision creation, pending-review and submission-limit conflicts, trainer cohort scope, bounded manual scores, server-derived pass state, feedback visibility, audit evidence, and database rejection of submission/grade mutation and over-limit direct inserts. Migration validation downgrades to L02.1, upgrades to head and checks metadata drift. Generated OpenAPI/TypeScript contracts, exact BFF routes, bilingual admin/learner/trainer states, strict TypeScript, ESLint, all Vitest tests, the Next production build, and authenticated Chrome submission/grading/feedback form the local release gate.

## L02.3 certificate evidence

PostgreSQL/API acceptance proves incomplete-assessment denial, exact quiz/assignment/lesson eligibility counts, Trainer issue denial, authorized template publication, manual issuance, duplicate prevention, revocation, minimal anonymous verification, SVG QR output and database rejection of template/certificate rewrites. Migration validation downgrades to L02.2, upgrades to head and checks metadata drift. Fixed authenticated and public BFF allowlists, generated contracts, bilingual staff/learner/public states, strict lint/types, Vitest, production build and an anonymous Chrome verification journey form the local gate.

## L03 attendance evidence

PostgreSQL/API acceptance covers policy creation/version conflict, wrong-organization denial, one-active-window enforcement, valid QR check-in, invalid-token and duplicate rejection, manual marking, versioned correction, staff/learner projections, audit minimization, explicit close, and database rejection of record/correction mutation. Migration validation downgrades to L02.3, upgrades to head, and checks metadata drift. BFF allowlist tests reject traversal, unsupported verbs, and any token-bearing QR read route. Generated contracts, English/Tamil staff and learner states, focused Ruff/strict MyPy, TypeScript, ESLint, Vitest, production build, and authenticated browser check-in form the local gate.
## M01 mentoring evidence

The PostgreSQL acceptance journey creates an eligible mentor profile, expertise and availability, assigns an active enrollment, rejects overlapping availability and sessions, records private/shared notes, advances a goal, completes an action and session, schedules a follow-up, submits one immutable participant feedback record, and ends the assignment. It asserts cross-organization rejection, duplicate assignment/feedback rejection, participant exclusion of private notes, aggregate monitoring, audit events and database immutability triggers. The web gate tests the BFF allowlist and compiles the generated M01 contracts; authenticated browser acceptance covers both staff and participant projections.
