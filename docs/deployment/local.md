# Local development

Prerequisites: Python 3.13, Node 24/npm, Flutter stable SDK and platform SDK, Docker Engine/Desktop with Compose v2. PowerShell users use `npm.cmd` if npm.ps1 is blocked. Docker was absent during initial audit; see milestone report for executed checks.

1. After installing backend dependencies, run `python scripts/init-local-env.py` with venv Python. It creates ignored API/web/Compose env files with random database/BFF keys and an encryption key; refuses overwrites. Or fill the .env.example files yourself. Never commit secrets.
2. `docker compose config --quiet` validates required settings.
3. `docker compose up --build -d` starts PostgreSQL, Redis, one-shot migrations, API, worker and web.
4. Open `http://localhost:3000/en`; API `http://localhost:8000/health`, `/ready`, `/docs` (development only).
5. `docker compose exec worker celery -A app.workers.celery_app:celery_app inspect ping` checks worker; execute `scripts/compose-smoke.py` from host Python for probes and queue round-trip.
6. `docker compose down` stops containers; do not remove volumes unless intentional disposable reset.

Host backend: `python -m venv .venv`; install `apps/api/requirements-dev.lock`; copy API `.env.example` to `apps/api/.env` and set URLs for isolated PostgreSQL/Redis; from apps/api run `python -m uvicorn app.main:app --reload`. Use venv Python for checks. API env is read from current working directory; Compose injects variables.

Host web: from apps/web `npm.cmd ci`, `npm.cmd run dev`. Mobile: from apps/mobile `flutter pub get`, `flutter run`; Android emulator API host is `10.0.2.2`, physical device needs reachable development host. Use synthetic accounts only. Account UI is at /en/account or /ta/account. For native Flutter pass --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1 on an Android emulator. Release builds require an HTTPS API URL. iOS native verification requires macOS.

Quality commands and results are in milestone report. Never point migration downgrade or integration tests at shared/production databases.

Native Windows PostgreSQL note: psycopg async connections require a selector event loop. `scripts/native-dependency-smoke.py` configures it for the test client; use the Linux Compose API for normal development. The isolated native smoke is not proof of the container or worker stack.

## Foundation account workflow

Apply migrations, then from apps/api run `python -m app.modules.identity.cli seed`. Create a synthetic account in web/mobile; an encrypted verification message is queued locally. Retrieve it using `python -m app.modules.identity.cli dev-message --email synthetic@example.com` in APP_ENV=local and enter its token into Verify email. This trusted local-only command intentionally prints the message; do not use real data, paste tokens in logs, or run it in CI with real accounts. No emails are sent. Reset follows the same local queue workflow.

Provision initial administrator with `python -m app.modules.identity.cli bootstrap-admin --email admin@example.com --name "Synthetic Admin" --organization "Synthetic Organization"`; password is prompted invisibly and never passed on command line. This creates a new account and organization, refuses existing accounts. Use `grant-role` / `revoke-role` with --email, --organization-id and --role for existing accounts; each changed binding is audited. No default administrator password.

Run backend integration tests only with AUTH_TEST_DATABASE_URL pointing to dedicated edp_auth_test or edp_test, migrated to head. They truncate fixture tables and refuse other database names. Browser acceptance uses edp_foundation_e2e or edp_test, prebuilt Next.js, and `python scripts/run-foundation-browser-test.py`. Set PLAYWRIGHT_CHANNEL=chrome to use installed Chrome locally; CI installs bundled Chromium. Runner owns temporary ports 8100/3100 and cleans its child processes. No production data.
