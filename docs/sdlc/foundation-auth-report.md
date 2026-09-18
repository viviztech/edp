# Foundation authentication continuation report

Milestone 1, F02/F03 continuation. Implementation delivered; **Milestone 1 remains open** until live CI, Compose/Redis 7 worker smoke, native-device/iOS verification and remaining release gates are evidenced. No CMS/CRM or other business module started. No deployment or real email/SMS/push sent.

## Implemented

- PostgreSQL Person/User, organization, role/permission bindings, refresh sessions/tokens, verification/reset challenges, encrypted development delivery records, throttle counters and audit records. Revision 1de5e104c2f7, explicit keys/checks/indexes and audit UPDATE/DELETE rejection trigger; schema generated and reviewed before application.
- Email registration, pending/active/suspended/archived enforcement, Argon2id hashing, single-use expiring verification/reset, generic account-request responses and database-backed atomic throttling.
- Opaque 10-minute access tokens and rotated refresh families with 14-day absolute maximum by default, hash-only storage, replay revocation, device listing and current/all/per-device revocation. Account/role state checked on every protected request.
- Next.js server-only session boundary, backend-held opaque browser session, HttpOnly SameSite cookies, configured Origin and session-bound CSRF, fixed proxy routes, bounded request body, no access/refresh tokens in browser JavaScript. Secure cookies mandatory for non-loopback deployment origins.
- English/Tamil account forms and device controls on web and Flutter. Server-authorized organization staff shell and permissioned audit history. Flutter OS secure storage with Android backup disabled, memory-only access token and one concurrent refresh operation; ambiguous rotation failure clears the unusable credential.
- Trusted operator CLI for seeding, initial administrator provisioning and audited role grants/revocations. No default admin password; no unauthenticated privilege-grant endpoint. Organization scope only; program/center/self-domain policies arrive with their modules and are not implicitly granted now.
- Generated OpenAPI/TypeScript contracts, local environment generator, dedicated database test safeguards, browser test runner and CI jobs updated. Local message queue is encrypted and operator-only; production account delivery is explicitly unavailable until an approved provider adapter is implemented.

## Evidence

| Check | Result |
|---|---|
| Backend Ruff lint/format | Passed, 25 Python files |
| Backend MyPy | Passed, 17 source files |
| PostgreSQL migration upgrade, downgrade to base, re-upgrade and drift | Passed in dedicated edp_auth_test database; no drift |
| Backend tests | 25 passed, including refresh race/replay, expiry, suspension, reset invalidation, cross-account session denial, role revocation, wrong-org denial, CSRF, throttling, input-redaction and audit rollback/immutability |
| Web ESLint / strict typing / Vitest | Passed; 4 tests covering localization, real shell rendering and proxy/CSRF boundaries |
| Next.js production build | Passed |
| Real Chrome + PostgreSQL E2E | Passed: registration, verification, sign-in, no token leakage, HttpOnly/SameSite cookies, CSRF denial, staff grant, audit UI, wrong-org denial, logout-all, reset, new-password sign-in, sign-out and Tamil mobile-width layout. No JavaScript page errors |
| Flutter analyze / tests | Passed; 5 tests covering language switching, account validation/sign-in/sign-out, refresh-only persistence, token cleanup and concurrent refresh |
| Android native debug build | Passed; APK at apps/mobile/build/app/outputs/flutter-apk/app-debug.apk. Debug build only, no device installation or signing/release acceptance |
| Flutter web release compilation | Passed with explicit HTTPS placeholder API base; optional Wasm dry-run warning remains because secure-storage plugin uses JS interop |
| Dependency audits | Web clean; cryptography upgraded from 47.0.0 to patched 50.0.1 after advisories; Python audit clean after update |
| Docker / CI / iOS / device smoke | Not established by this local run; remain gates |

Executed commands: `ruff check .`, `ruff format --check .`, `mypy app`, `pytest -q` with AUTH_TEST_DATABASE_URL, Alembic upgrade/downgrade/upgrade/check, OpenAPI export and npm contracts, npm lint/typecheck/test/build/audit, pip-audit, Flutter gen-l10n/format/analyze/test/build web and the repository browser runner. Exact prerequisite/configuration commands are in deployment/local.md. Runtime and development Python lockfile versions are aligned.

Browser test corrections: the external Windows helper left child servers running; the repository runner now verifies free ports and terminates its own process tree. Next.js RSC prefetch prevented networkidle detection despite a hydrated form, so the test asserts visible form readiness. Browser testing then identified password helper text included in the accessible name; markup was corrected and the complete journey passed. Screenshot inspection confirmed readable English and Tamil layouts with no horizontal overflow at 390px.

## Security and operational limits

No credentials printed in test output or added to tracked artifacts; transient test secrets generated in memory. Synthetic data only. Local dev-message CLI intentionally exposes a development code to a trusted operator; unavailable in production. Production email delivery, consent/retention policy, audit DB-role separation, privileged MFA, secrets rotation, TLS/CSP rollout and backup/restore remain launch gates. This is not a production-ready identity claim.

Role catalog seeds only implemented permissions (system.access, audit.view), not broad unimplemented domain access. Role editing is an operator procedure, not an end-user administration feature. Account registration is email-only initially, as permitted by the master. Native mobile storage and remote-revocation behavior require device validation. If logout cannot reach the API, Flutter clears local credentials but cannot claim the server session was revoked; the UI surfaces the failure.

The initial bootstrap report remains historical. Read this report and ADR 0003 for the current state. DoD evidence is present for implemented local flows, but missing environment/device/CI gates prevent closing the milestone.

## Next

Complete native-device and Compose/CI verification, configure approved notification delivery and production security/operations, then close Milestone 1. Plan CMS/public as the next major milestone only after foundation gates pass. Unknown business/privacy/content policies remain in the open-questions register.

Final review: all documentation links resolve; CI/Compose YAML parses and carries required BFF configuration; runtime/development Python dependency pins agree; ignored local environment files are excluded from Git candidate files. This is not a substitute for the pending Gitleaks/container scan and remote CI runs.


## CI follow-up (2026-09-18)

Initial remote run: https://github.com/viviztech/edp-digital/actions/runs/35366293976 (commit c44dd32). Web, mobile, browser-auth, secrets and Compose passed. Compose established PostgreSQL 17 / Redis 7 readiness and a real Celery queue round-trip. These supersede the earlier unexecuted remote/Compose/secret-scan notes above. Native-device/iOS and production gates remain open.

Backend migrations, lint and typing passed, but pytest collection failed with `ModuleNotFoundError: app`; later contract/audit steps were skipped. Reproduced using the pytest executable without an editable package install. The API pytest configuration now explicitly adds its project root to the test import path, independent of shell PYTHONPATH and invocation directory. No runtime, API contract, permission or database changes. Regression verification uses the existing 25-test suite and direct console entry point; Ruff lint/format passed. Fix commit 53f354b passed all six remote CI jobs: https://github.com/viviztech/edp-digital/actions/runs/35370249112. Local verification also passed all 25 PostgreSQL-backed tests, Ruff lint/format, and MyPy (17 source files). Rollback: revert the pytest pythonpath setting.
