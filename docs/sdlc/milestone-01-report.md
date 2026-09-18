# Milestone 1 execution report ? 2026-09-18

> Historical bootstrap snapshot. See [foundation authentication continuation](foundation-auth-report.md) for the implemented F02/F03 slice and current verification status.

## Status

Design baseline and minimum development bootstrap delivered. **Milestone 1 is not complete under the master Definition of Done.** The authentication/refresh-session/RBAC/audit vertical slice, live CI and container/native-device gates remain outstanding. No business feature is marked done, no production deployment made and no real user data collected.

## Plan and files

Read all of `EDP_CODEX_MASTER_INPUT.md` (the actual supplied filename), starting execution with Section 38. Audited the originally specification-only directory; initialized Git on main without a commit or remote. Created PRD, P0/P1/P2 stories with criteria/tasks/dependencies/complexity, DoD, release checklist, architecture and ADRs, domain ERDs, security/RBAC/privacy/API/testing plans, open questions, mobile/integration/operations/user-guide documents and the Milestone 1 plan. README links the review entry points.

Bootstrap: apps/api (FastAPI, settings, SQLAlchemy, Alembic, probes, JSON logging, Celery and tests); apps/web (Next.js strict TypeScript, Tailwind, English/Tamil public and staff-access notice shells, tests); apps/mobile (Flutter/Riverpod/GoRouter localized guest shell plus Android/iOS/web runners); Dockerfiles/Compose; generated OpenAPI and TypeScript probe types; dependency locks; quality configuration and GitHub Actions.

## Implementation and database

Modular monolith; one web application and one mobile application. Stable Person separate from account, enrollment and lead is the proposed identity design. Scoped permission bundles and a database outbox are designed, not implemented as pretend auth or messaging. Basic P0 outcome recording is distinguished from full P1 business profiles/follow-ups.

Only schema revision `0001_bootstrap` exists and is intentionally schema-neutral. Live migration tests used a newly initialized disposable PostgreSQL 17 cluster on loopback port 55432, not any existing database. No domain tables or application users were created. PostgreSQL's Alembic version row was verified as `0001_bootstrap`.

## Security

Required environment-supplied DB password in Compose; loopback port bindings; non-root application images; secrets/build/tool caches ignored. Public health/readiness contain status only. Errors exclude exception bodies/input values; request logs contain no request payloads. OpenAPI disabled outside local/test. No privileged endpoint or mock login grants access. Staff route is an unauthenticated availability notice containing no staff data. TLS/CSP/auth/CSRF/scoped audit/retention controls remain implementation/release gates.

## Executed verification

Commands below use repository venv Python; backend commands run in apps/api, web in apps/web, mobile in apps/mobile unless stated otherwise.

| Commands / check | Actual result |
|---|---|
| `python --version`, `node --version`, `npm.cmd --version`, `flutter.bat --version` | Python 3.13.13, Node 24.15.0, npm 11.12.1, Flutter 3.47.0 / Dart 3.13.0 |
| `uv pip compile ...`, `uv pip sync ...`; `npm.cmd install`; `flutter pub get` | Dependencies resolved/installed; lockfiles generated |
| `ruff check .`, `ruff format --check .` | Passed after fixing formatting; 12 Python files formatted |
| `mypy app` | Passed, 8 source files |
| `pytest -q` | 7 passed; initial read-only mock-target error fixed. Two upstream deprecation warnings (Starlette HTTPX/AnyIO) |
| `alembic upgrade head`, `alembic downgrade base`, `alembic upgrade head`, `alembic check` | Passed on isolated PostgreSQL; no new upgrade operations |
| `python scripts/export-openapi.py`; `npm.cmd run contracts` | Generated actual probe schema/types |
| `python scripts/native-dependency-smoke.py` with local service URLs | Live database and Redis readiness plus health passed. Native Redis 3.0.504 is test-only; this does not validate planned Redis 7 or Celery delivery |
| `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd test` | Passed; 2 tests including actual localized public shell |
| `npm.cmd run build` | Passed, Next.js 16.3.5 standalone production build |
| `dart format lib/main.dart test`, `flutter analyze`, `flutter test` | Passed; one language-switch widget test |
| `flutter build web` | Passed. Optional Wasm dry-run warns about secure-storage dependency; WebAssembly is not a target. Native device builds not validated |
| `pip-audit -r requirements.lock` | No known vulnerabilities found |
| `npm.cmd audit --audit-level=moderate` | No vulnerabilities after replacing vulnerable Vitest 3 with 5.0.1 |
| HTTP smoke of built standalone web | /en, /ta and /en/admin returned 200 with correct html language, main landmark and working CSS; / redirected to /en. Initial asset 404 resolved by copying assets before server startup |
| Ignore rules | Confirmed .env, venv, node_modules, .next and disposable DB excluded by Git |
| Docker/Compose smoke and Celery queue round-trip | Not executed: Docker absent; required script and CI job supplied |
| GitHub Actions / Gitleaks / container scans | Not executed remotely; CI supplied, no remote configured. Gitleaks not installed locally; container scanning remains launch hardening work |

Sandbox restrictions initially blocked package caches and build writes; rerun with tool approval completed the available checks. Git was initialized by the sandbox identity; elevated read-only Git commands used a command-scoped safe.directory override, not a global trust change. Dependency installation/scaffolding was authorized; no system Docker installation or provider setup attempted.

## Remaining gates and risks

- F02/F03 full Person/User/session/permission/audit schema and secure authentication across web/mobile are planned, not implemented. Do not proceed to CMS/business modules before this foundation slice passes DoD.
- Docker/Compose, actual Redis 7/Celery delivery, image builds and CI must run in an appropriate environment. HTTP probes cannot substitute for them.
- Android/iOS builds, signing/store identifiers, device smoke and push integration remain; generated com.example identifiers are development placeholders. Flutter web is only a bootstrap build check.
- Shell HTTP/component evidence is not an end-to-end product manual acceptance or browser accessibility review.
- Client approval of branding, Tamil content, privacy/retention, providers, final application/rubric/attendance/certificates, volumes, RPO/RTO and UAT ownership remains open.
- Native Windows psycopg async requires selector event loop; smoke script supplies it. Linux Compose is the intended backend runtime.
- Provider integrations, durable business outbox and production monitoring/backup/restore remain planned. No claim of operational backups.

## Next

Review architecture and unresolved policies; complete F02/F03 as the next Milestone 1 vertical slice with migrations, web BFF/mobile secure sessions, scoped authorization, audit and negative tests. Run Compose/CI and device gates, record manual evidence, then close Milestone 1. Only afterward plan CMS/public vertical slices. Stop here before the next major milestone.

Final static review: documentation relative links resolve; Compose YAML parses with six expected services (not runtime validation); runtime/development Python pins agree. Temporary PostgreSQL, Redis and web smoke processes stopped.


## CI verification update (2026-09-18)

Foundation fix commit 53f354b passed backend, web, mobile, Compose, browser-auth and secrets in [GitHub Actions run 35370249112](https://github.com/viviztech/edp-digital/actions/runs/35370249112). This closes the remote CI and Compose/Redis 7/Celery verification gaps for that revision. Backend pytest collection now works independently of invocation directory. See [foundation continuation report](foundation-auth-report.md) for implemented authentication scope and remaining native-device/iOS and operational gates. Milestone 1 remains open; no domain module or production deployment was started.
