# Local development

Prerequisites: Python 3.13, Node 24/npm 11, Flutter 3.47.0 (the CI-pinned SDK) and platform SDK, Docker Engine/Desktop with Compose v2. Root `.python-version` and `.node-version` record the supported runtime lines; the mobile manifest requires Dart 3.12 or later and Flutter 3.47.0 or later. PowerShell users use `npm.cmd` if npm.ps1 is blocked. Docker was absent during initial audit; see milestone report for executed checks.

### Reproducible host dependencies

Use an isolated `.venv` and the committed locks. Do not replace a system Python installation to satisfy this project's Python 3.13 requirement. On this Windows workspace, uv 0.13.4 is installed under `.tool-cache/bootstrap/bin`; its managed Python installations and cache remain under the ignored `.tool-cache` directory. From the repository root:

```powershell
python -m pip install --target .tool-cache/bootstrap --cache-dir .tool-cache/pip uv==0.13.4
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD '.tool-cache/python'
$env:UV_CACHE_DIR = Join-Path $PWD '.tool-cache/uv'
$edpUv = Join-Path $PWD '.tool-cache/bootstrap/bin/uv.exe'
& $edpUv python install 3.13 --no-registry --no-bin
& $edpUv venv --python 3.13 .venv
& $edpUv pip sync --python .venv/Scripts/python.exe apps/api/requirements-dev.lock
& $edpUv pip install --python .venv/Scripts/python.exe --no-deps --editable './apps/api[dev]'
& $edpUv pip check --python .venv/Scripts/python.exe
```

The first command uses an existing Python only to bootstrap uv; it does not install API dependencies into that interpreter. Python installation stays project-local and does not change the Windows registry or PATH. See the [uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/) for other supported bootstrap methods. If Python 3.13 is already installed, `python -m venv .venv`, `python -m pip install -r apps/api/requirements-dev.lock` and `python -m pip install --no-deps -e './apps/api[dev]'` with the venv active provide the equivalent setup; finish with `python -m pip check`. On macOS/Linux the venv Python is `.venv/bin/python`. The editable install registers API dependency metadata without resolving unlocked versions, so the dependency check can catch a stale lock.

From `apps/web`, run `npm.cmd ci` with Node 24/npm 11. From `apps/mobile`, use Flutter 3.47.0 and run `flutter pub get --enforce-lockfile`. These commands install the recorded versions and fail when a manifest and its lock disagree. Update dependencies deliberately, regenerate the corresponding lock and review the diff before committing.

To update backend locks, run uv from the repository root with `--python-version 3.13 --universal` so the files include platform-specific requirements for Windows and Linux. Compile `apps/api/pyproject.toml` to `apps/api/requirements.lock`; then compile it with `--extra dev --constraint apps/api/requirements.lock` to `apps/api/requirements-dev.lock`. Retain existing output files to preserve pins; add upgrade flags only for an intentional version update. Run the sync, editable install and dependency check again afterward. See [uv's lock workflow](https://docs.astral.sh/uv/pip/compile/) and [Dart lock enforcement](https://dart.dev/tools/pub/cmd/pub-get).

### Local services

1. After installing backend dependencies, run `python scripts/init-local-env.py` with venv Python. It creates ignored API/web/Compose env files with random database/BFF keys and an encryption key; refuses overwrites. Or fill the .env.example files yourself. Never commit secrets.
2. `docker compose config --quiet` validates required settings.
3. `docker compose up --build -d` starts PostgreSQL, Redis, one-shot migrations, API, worker and web.
4. Open `http://127.0.0.1:3001/en`; API `http://localhost:8000/health`, `/ready`, `/docs` (development only).
5. `docker compose exec worker celery -A app.workers.celery_app:celery_app inspect ping` checks worker; execute `scripts/compose-smoke.py` from host Python for probes and queue round-trip.
6. `docker compose down` stops containers; do not remove volumes unless intentional disposable reset.

Host backend: complete the dependency setup above, then copy API `.env.example` to `apps/api/.env` and set URLs for isolated PostgreSQL/Redis. On Windows run `.venv\Scripts\python.exe scripts/run-native-api.py` from the repository root so psycopg uses a compatible selector event loop. On macOS/Linux, from apps/api run `python -m uvicorn app.main:app --reload`. Use venv Python for checks. API env is read from the apps/api working directory; Compose injects variables.

Host web: from apps/web `npm.cmd ci`, `npm.cmd run dev -- --hostname 127.0.0.1 --port 3001`. Set `WEB_ORIGIN=http://127.0.0.1:3001` and match API `CORS_ORIGINS`. Mobile: from apps/mobile `flutter pub get --enforce-lockfile`, `flutter run`; Android emulator API host is `10.0.2.2`, physical device needs reachable development host. Use synthetic accounts only. Account UI is at /en/account or /ta/account. For native Flutter pass --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1 on an Android emulator. Release builds require an HTTPS API URL. iOS native verification requires macOS.

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

Use an isolated PostgreSQL 17 cluster at `.local/postgres17/data`, bound to `127.0.0.1:55432`. It does not alter Windows PostgreSQL services. Download the [official EDB portable binaries](https://www.enterprisedb.com/download-postgresql-binaries) for PostgreSQL 17 and extract the archive so `pg_ctl.exe` is at `.tool-cache/postgresql17/pgsql/bin/pg_ctl.exe`. The restored toolchain uses the 17.11-3 Windows x64 archive. Initialize once from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init-local-postgres.ps1
```

Initialization generates an `edp_dev` role password in ignored `.local/postgres17/credentials.json`, enables SCRAM password authentication and creates only the synthetic `edp_dev`, `edp_test` and `edp_foundation_e2e` databases. It persistently configures both PostgreSQL `timezone` and `log_timezone` as `UTC`, matching CI and the API's UTC timestamp convention regardless of the workstation timezone. Rerunning initialization applies and reloads these settings for an existing project cluster. It preserves an existing initialized cluster and refuses an unrecognized nonempty data directory. Load the password from this file into local environment variables without printing it; use `postgresql+psycopg://edp_dev:PASSWORD@127.0.0.1:55432/edp_dev` for host development and `edp_test` for destructive integration tests. Existing environment files are not overwritten. Start and stop this cluster from the repository root with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-postgres.ps1
powershell -ExecutionPolicy Bypass -File scripts/stop-local-postgres.ps1
```

The start/stop scripts prefer the project-local binaries and fall back to an existing PostgreSQL 17 installation. Pass `-PostgresBin` explicitly if using another binary location. They manage only this project's data directory and never register or modify an operating-system service.

After starting PostgreSQL and Redis, apply schema changes from `apps/api` with `..\..\.venv\Scripts\alembic.exe upgrade head`, seed permissions with `..\..\.venv\Scripts\python.exe -m app.modules.identity.cli seed`, and launch the Windows API with `.venv\Scripts\python.exe scripts/run-native-api.py`. A successful `GET /ready` proves both PostgreSQL and Redis are reachable.


## Meta lead development

For C03, set the same `META_SECRET_KEY` in the API and worker, and set a current, verified `META_GRAPH_API_VERSION` plus an approved `META_EVENT_RETENTION_DAYS`. Compose reads these from root `.env` and runs a dedicated `beat` service alongside the worker. Restart both after changing Meta settings. The staff page is `/{locale}/admin/meta` for a Marketing Executive with an organization grant. Native host development also requires a running Redis, Celery worker and Celery beat process to process and recover events; API and web alone show only the admin workspace. See `docs/integrations/meta.md` for setup and triage.

## CRM assignment notifications

Apply migration f8a0b1c2d3e4 and run the API, Redis, Celery worker and beat with the same database URL. The beat dispatches pending assignment intents every minute; API and web alone do not deliver them. Staff with a scoped crm.lead.view grant can open /{locale}/admin/notifications. This N01.1 path is in-app only, uses no provider credentials, and is restricted to synthetic data until notification retention is approved.


Notification retention: set NOTIFICATION_RETENTION_DAYS in API, worker and beat environments only after policy approval, then restart all three. The minutely cleanup task removes expired intents in batches of 100. Staging/production lead assignments that would create notices return retention_policy_not_configured (503) while this setting is absent. Local/test synthetic notices remain available for development. See docs/integrations/notifications.md for the lifecycle and disposal behavior.


Follow-up reminders: the same Celery worker/beat pair used for assignment notices runs edp.notifications.queue_due_followups every minute. Confirm both tasks are registered and use the same PostgreSQL database as the API. A due activity must be incomplete, belong to an assigned active lead, and pass recipient permission and preference checks before appearing in the inbox. API/web-only preview cannot schedule reminders.

Notification recovery: apply migration a2d3e4f5a6b7, rerun the identity role seed and restart API/worker/beat. Program Directors/Managers with an organization grant can open `/{locale}/admin/notifications` to inspect failed in-app intents and request replay with an audit reason. The worker uses bounded automatic retries; a failed database transaction still requires infrastructure triage.

## Applicant draft development

Apply migrations through c4f5a6b7c8d9 and rerun python -m app.modules.identity.cli seed to add the application definition permissions. Program Directors can publish at /{locale}/admin/application-definitions?organization=UUID; Program Managers can prepare drafts. For applicant-only review, apply migration b3e4f5a6b7c8. In APP_ENV=local, provision one synthetic published form for a development organization from apps/api with python -m app.modules.applications.cli seed-demo --organization-id UUID. The command refuses non-local environments and preserves an existing published form. An authenticated person with an organization grant can open /{locale}/account and follow **Application draft** to /{locale}/applications?organization=UUID. This slice saves drafts only; submission and document upload are unavailable.

The local web BFF accepts `localhost` and `127.0.0.1` as equivalent Origin hostnames only on its configured HTTP port. Cookies remain host-scoped, so use one hostname consistently for an existing session. Production origins still require an exact match.

## Program delivery administration

Apply migration d5a6b7c8d9e0 and rerun python -m app.modules.identity.cli seed from apps/api. Authorized staff can open /{locale}/admin/programs?organization=UUID. Create and publish an application definition before creating an application cycle. This P01.1 slice does not provide participant enrollment or program sessions.

## Applicant submission development

Apply migration `e6b7c8d9e0f1`, rerun the identity permission seed, and use the program administration workspace to create and open an application cycle whose published form includes at least one required declaration and one required consent. An authenticated applicant opens `/{locale}/applications?organization=UUID`, selects the open cycle, saves required answers, accepts the policy and submits. The receipt is read-only and its application number is server-generated. Existing form-only development drafts cannot submit; create a cycle draft from the current workspace. Do not use real applicant data until submitted-answer retention is approved. Document upload remains disabled pending A01.3.


## P01.3 local coordinator bindings

Apply migration 6d59d2d4f99c, rerun python -m app.modules.identity.cli seed from apps/api, and restart the API before testing coordinator access. Create the coordinator account and organization role through the trusted operator procedure, then assign a center or cohort from the Programs workspace. A coordinator with the role but no active assignment is deliberately denied. Use synthetic accounts only.

## L01.1 local learning

Apply migration 7e6ae3e5a10d, rerun python -m app.modules.identity.cli seed, and restart the API. Program Directors and Program Managers open /{locale}/admin/learning?organization=UUID; enrolled participants open /{locale}/learning?organization=UUID. Build at least one lesson in every module before publishing, then assign the published course to a planned or active cohort. Material provider keys must be synthetic in development. Learner material delivery remains unavailable until the private media adapter is configured.

## L01.2 local learning

Run Alembic to head before using progress APIs. Existing courses receive the all_lessons rule. Re-run OpenAPI export and npm run contracts after backend schema changes. The local PostgreSQL test database must be named edp_auth_test or edp_test; progress acceptance truncates only synthetic fixture data. No Redis or Celery worker is required for synchronous lesson completion.

## L01.3 local private materials

Apply migration `a19d7a38e40b`, rerun `python -m app.modules.identity.cli seed`, and restart API/web. Set `LMS_MATERIAL_ROOT` in the host API environment to a private local directory. Place only synthetic development files beneath it and store their relative path as LessonMaterial.provider_key. Compose mounts `./.local/lms-materials` read-only at `/private-materials`. `LMS_MATERIAL_ACCESS_SECONDS` defaults to 300 and is restricted to 60-900 seconds. Local/test may fall back to BFF_KEY for signing; production must set a separate `LMS_MATERIAL_SIGNING_KEY` of at least 32 characters and an approved private object/video adapter before release. Do not place the material root under the web public directory.

## K01 local knowledge and funding

Apply migration `d9f5a1b7c234`, rerun the identity permission seed and restart API/web. Staff with `knowledge.manage` open `/{locale}/admin/knowledge?organization=UUID`; `funding.manage` separately grants the read-only case queue. Participants need an active organization enrollment and use `/{locale}/knowledge?organization=UUID`. Public `/{locale}/resources` uses `PUBLIC_ORGANIZATION_ID` and `API_INTERNAL_URL`; only published public entries appear there.

After the production web build and test-database migration, run `scripts/run-knowledge-browser-test.py` with the project Python environment. `DATABASE_URL` must select a guarded synthetic test/browser database, never a development/production dataset. Set `PLAYWRIGHT_CHANNEL=chrome` to use installed Chrome where bundled Chromium is unavailable. The runner refuses occupied ports 8101/3101, owns and stops temporary API/web processes, seeds a fresh synthetic organization and records evidence under `.tool-cache/evidence`. It does not need Redis/Celery or external funding providers for this synchronous workflow. The existing foundation runner uses different ports and remains a separate regression check.

## Phase 9 local helpdesk and post-training acceptance

Run Alembic to head (`e0a6b2c8d345`), rerun the identity permission seed and restart API/web. Participants and eligible completed alumni open `/{locale}/helpdesk?organization=UUID`; Support Executives and organization managers use `/{locale}/admin/helpdesk?organization=UUID`. B02 remains at `/{locale}/businesses` and `/{locale}/admin/businesses`.

After migration and a production web build, run `scripts/run-helpdesk-browser-test.py` with the project Python environment and `DATABASE_URL` selecting an isolated synthetic browser/test database. Set `PLAYWRIGHT_CHANNEL=chrome` for installed Chrome. The runner refuses occupied ports 8102/3102, starts hidden owned API/web servers and always stops them. It covers helpdesk plus post-training profiles/policies/outcomes and writes responsive evidence under `.tool-cache/evidence`. In-app ticket notices are committed with ticket events and need no Redis/provider; CRM/Meta scheduled jobs still require their existing worker/beat infrastructure. Never use real support documents in local acceptance.

## Phase 10 local reporting and impact acceptance

Apply Alembic head `f1b7c3d9e456`, rerun the identity role seed and restart API/web. Directors/managers open `/{locale}/admin/reports?organization=UUID`; eligible participants open `/{locale}/impact?organization=UUID`. No measurement policy is seeded: create and publish a synthetic bilingual definition before recording local evidence. B02 profiles are not required. Report dates use UTC regardless of the PostgreSQL session timezone.

After a production web build and isolated database migration, run `scripts/run-reports-browser-test.py` with the project Python environment, a guarded synthetic browser database and `PLAYWRIGHT_CHANNEL=chrome` for installed Chrome. The runner owns hidden API/web servers on 8103/3103, refuses occupied ports, uses fresh synthetic actors/organizations and always stops its processes. Evidence is stored beneath `.tool-cache/evidence`. Bounded report generation/export needs PostgreSQL only; it does not dispatch provider/worker jobs. Core CRM/Meta schedules retain their existing Redis/worker requirements. Use the supplied API runner/structured logging and configure any staging proxy to omit capability URLs from access logs; do not enable raw download URL logging.
