# Local development

Prerequisites: Python 3.13, Node 24/npm, Flutter stable SDK and platform SDK, Docker Engine/Desktop with Compose v2. PowerShell users use `npm.cmd` if npm.ps1 is blocked. Docker was absent during initial audit; see milestone report for executed checks.

1. After installing backend dependencies, run `python scripts/init-local-env.py` with venv Python. It creates ignored API/web/Compose env files with random database/BFF keys and an encryption key; refuses overwrites. Or fill the .env.example files yourself. Never commit secrets.
2. `docker compose config --quiet` validates required settings.
3. `docker compose up --build -d` starts PostgreSQL, Redis, one-shot migrations, API, worker and web.
4. Open `http://127.0.0.1:3001/en`; API `http://localhost:8000/health`, `/ready`, `/docs` (development only).
5. `docker compose exec worker celery -A app.workers.celery_app:celery_app inspect ping` checks worker; execute `scripts/compose-smoke.py` from host Python for probes and queue round-trip.
6. `docker compose down` stops containers; do not remove volumes unless intentional disposable reset.

Host backend: `python -m venv .venv`; install `apps/api/requirements-dev.lock`; copy API `.env.example` to `apps/api/.env` and set URLs for isolated PostgreSQL/Redis. On Windows run `.venv\Scripts\python.exe scripts/run-native-api.py` from the repository root so psycopg uses a compatible selector event loop. On macOS/Linux, from apps/api run `python -m uvicorn app.main:app --reload`. Use venv Python for checks. API env is read from the apps/api working directory; Compose injects variables.

Host web: from apps/web `npm.cmd ci`, `npm.cmd run dev -- --hostname 127.0.0.1 --port 3001`. Set `WEB_ORIGIN=http://127.0.0.1:3001` and match API `CORS_ORIGINS`. Mobile: from apps/mobile `flutter pub get`, `flutter run`; Android emulator API host is `10.0.2.2`, physical device needs reachable development host. Use synthetic accounts only. Account UI is at /en/account or /ta/account. For native Flutter pass --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1 on an Android emulator. Release builds require an HTTPS API URL. iOS native verification requires macOS.

Quality commands and results are in milestone report. Never point migration downgrade or integration tests at shared/production databases.

Native Windows PostgreSQL note: psycopg async connections require a selector event loop. `scripts/run-native-api.py` configures it for the host API, and `scripts/native-dependency-smoke.py` does the same for the test client. The project-owned host database supports local development; Compose remains the production-like full-stack path and is still required for container and worker evidence.

## Foundation account workflow

Apply migrations, then from apps/api run `python -m app.modules.identity.cli seed`. Create a synthetic account in web/mobile; an encrypted verification message is queued locally. Retrieve it using `python -m app.modules.identity.cli dev-message --email synthetic@example.com` in APP_ENV=local and enter its token into Verify email. This trusted local-only command intentionally prints the message; do not use real data, paste tokens in logs, or run it in CI with real accounts. No emails are sent. Reset follows the same local queue workflow.

Provision initial administrator with `python -m app.modules.identity.cli bootstrap-admin --email admin@example.com --name "Synthetic Admin" --organization "Synthetic Organization"`; password is prompted invisibly and never passed on command line. This creates a new account and organization, refuses existing accounts. Use `grant-role` / `revoke-role` with --email, --organization-id and --role for existing accounts; each changed binding is audited. No default administrator password.

Run backend integration tests only with AUTH_TEST_DATABASE_URL pointing to dedicated edp_auth_test or edp_test, migrated to head. They truncate fixture tables and refuse other database names. Browser acceptance uses edp_foundation_e2e or edp_test, prebuilt Next.js, and `python scripts/run-foundation-browser-test.py`. Set PLAYWRIGHT_CHANNEL=chrome to use installed Chrome locally; CI installs bundled Chromium. Runner owns temporary ports 8100/3100 and cleans its child processes. No production data.

## CMS pages

Apply migration 2b3fcc875606, rerun the trusted `identity.cli seed` command to add CMS permissions, and grant Content Manager in the intended organization. Existing role grants acquire only their explicit seeded catalog. Set `PUBLIC_ORGANIZATION_ID` to that organization's UUID in the web environment (and root Compose .env); restart the web process. Flutter requires `--dart-define=PUBLIC_ORGANIZATION_ID=UUID` alongside API_BASE_URL. Missing configuration shows content unavailable; no arbitrary organization is auto-selected.

Staff authoring: /en/admin/pages or /ta/admin/pages; public list: /en/pages or /ta/pages; detail: /{locale}/pages/{slug}. CMS body is plain text in this first slice. Save before preview/publish. Published content stays unchanged until another publish. After stale-write conflict, reload the page from the page list and reconcile edits. Archive removes only the selected locale; restore creates an unpublished draft.

Rollback code without dropping published data. Schema downgrade is destructive and for disposable tests only; production disposal needs backup and approval.

### Project-owned Windows PostgreSQL

This workstation uses an isolated PostgreSQL 17 cluster at `.local/postgres17/data`, bound to `127.0.0.1:55432`. It does not alter the Windows PostgreSQL services on ports 5432 or 5433. The ignored `apps/api/.env` points to database `edp_dev` with the generated `edp_dev` role; `edp_test` is reserved for destructive integration tests. Start and stop this cluster from the repository root with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-postgres.ps1
powershell -ExecutionPolicy Bypass -File scripts/stop-local-postgres.ps1
```

After starting PostgreSQL and Redis, apply schema changes from `apps/api` with `..\..\.venv\Scripts\alembic.exe upgrade head`, seed permissions with `..\..\.venv\Scripts\python.exe -m app.modules.identity.cli seed`, and launch the Windows API with `.venv\Scripts\python.exe scripts/run-native-api.py`. A successful `GET /ready` proves both PostgreSQL and Redis are reachable.


## Meta lead development

For C03, set the same `META_SECRET_KEY` in the API and worker, and set a current, verified `META_GRAPH_API_VERSION` plus an approved `META_EVENT_RETENTION_DAYS`. Compose reads these from root `.env` and runs a dedicated `beat` service alongside the worker. Restart both after changing Meta settings. The staff page is `/{locale}/admin/meta` for a Marketing Executive with an organization grant. Native host development also requires a running Redis, Celery worker and Celery beat process to process and recover events; API and web alone show only the admin workspace. See `docs/integrations/meta.md` for setup and triage.

## CRM assignment notifications

Apply migration f8a0b1c2d3e4 and run the API, Redis, Celery worker and beat with the same database URL. The beat dispatches pending assignment intents every minute; API and web alone do not deliver them. Staff with a scoped crm.lead.view grant can open /{locale}/admin/notifications. This N01.1 path is in-app only, uses no provider credentials, and is restricted to synthetic data until notification retention is approved.
