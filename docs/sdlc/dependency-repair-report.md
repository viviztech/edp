# Dependency repair and B02 continuation report

Recorded: 2026-10-21. Core dependency repairs and the focused B02 fix are locally verified. The upstream security and environment gates below remain open; this is not a production release.

## Toolchain and dependencies

- Installed project-local Python 3.13.16 and an isolated `.venv`; the system Python 3.14 installation is unchanged. Node 24.14.0/npm 11.9.0 already matched the supported runtime line.
- Added Python/Node runtime declarations and web engine constraints. Installed Flutter 3.47.0 (Dart 3.13.0) from its official tagged repository into the ignored tool cache and aligned the mobile SDK minimum/lock metadata.
- Recompiled both API locks for Python 3.13 across platforms, preserving existing pins except the intentional certificate-bundle security update. Added the missing declared `qrcode` and `types-qrcode` dependencies and Linux `uvloop` marker. Installed the API editable metadata so dependency checks validate the manifest.
- Updated vulnerable compatible npm dependencies, including Next.js and its ESLint configuration to 16.4.2. Updated Python `certifi` to 2026.10.19; the runtime lock security scan reports no known vulnerabilities.
- Restored portable PostgreSQL 17.11 under the ignored tool cache, with SCRAM credentials, persistent UTC session/log settings, a project-owned cluster at `127.0.0.1:55432`, and isolated synthetic development/test/browser databases. Added repeatable initialization and updated start/stop scripts without changing OS services.
- CI now checks installed API metadata and enforces the Flutter lockfile. Existing security gates remain enabled.

## Code and development continuation

Repository-wide backend Ruff, formatting and strict MyPy checks now pass. Legacy CMS changes add types and expand compressed statements; selection Numeric mappings now use Decimal annotations. Runtime-statement comparison and generated OpenAPI confirm no business/schema change from this cleanup.

B02 profile editing now uses generated request/response types and explicit writable-field projection. Response identifiers, timestamps, version metadata, history and follow-up records cannot leak into a profile mutation. Component and API regression coverage exercises reload/update persistence, immutable history, version conflicts and authorization. The browser acceptance script includes the create/reload/edit/save/reload journey.

Standalone web packaging now includes the `public` directory in both the browser runner and Docker image. The browser suite checks that the logo is served and uses accessible CMS article/textbox selectors compatible with the current public design.

## Validation

- API dependency consistency/import checks: passed.
- API Ruff, formatting and strict MyPy: passed.
- API runtime and development dependency security scans: passed; no known vulnerabilities reported.
- Web clean locked installation, lint, TypeScript, all 46 component/unit tests and the Next.js 16.4.2 production build: passed.
- Flutter formatting, analysis, all 8 tests and JavaScript web release build: passed. The build reports existing optional WebAssembly/secure-storage incompatibility and font warnings; WebAssembly is not the selected output target.
- PostgreSQL migration upgrade, populated B02 downgrade/re-upgrade and zero drift: passed. Full downgrade to base/re-upgrade and zero drift on an emptied, guarded synthetic `edp_test` database: passed. Full API/PostgreSQL suite: **92 passed** in 194.94 seconds after the UTC correction, with two upstream TestClient/AnyIO deprecation warnings.
- Authenticated Chrome browser acceptance: passed across identity, CMS, applications, selection, enrollment, learning/assessment/certificates, attendance, mentoring, B02 create/reload/update/history, authorization and session recovery. The logo request returns HTTP 200; responsive B02 screenshot recorded; no JavaScript errors.
- Generated OpenAPI and TypeScript contracts: regenerated with no content drift.
- Final diff whitespace checks: passed. No production data, secrets or generated tool/build directories are tracked.

## Remaining gates

The npm audit still reports nine high-severity dependency records traced to one transitive `braces` stack-exhaustion advisory. Its [reviewed advisory lists no patched release](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm). Compatible available updates were applied; no forced CLI downgrade, dependency substitution or audit exclusion was introduced. The existing npm security gate therefore remains failing until upstream remediation or an explicitly reviewed resolution.

Docker/WSL and a Redis service are unavailable on this host, so Compose, broker/worker/Beat runtime acceptance remain unverified. Android/iOS device acceptance remains deferred under ADR 0004. Remote CI, production provider activation, staging, UAT and production release gates remain open. No production data, deployment or provider delivery is involved.

A full downgrade to base with populated enrolled applications is rejected by the earlier selection migration's narrower legacy state constraint. The validation above uses the same empty-database scope as CI for that full round trip; it does not establish a production data rollback policy or rewrite historical application states.
