# Process 1 / verified development baseline report

Current dependency update (2026-10-24): the unsuppressed npm audit and complete Python runtime/development lock audits report zero vulnerabilities after compatible security fixes. The historical nine-high `braces` result below has been superseded; no gate was suppressed. See the [secure-file continuation checkpoint](secure-files-acceptance-report.md) and `.local/dependency-audit-20261024.json`. Exact-revision remote CI remains unverified under the local-only instruction.

Recorded: 2026-10-23. Status: local functional verification complete; Process 1 remains open because the dependency security gate and exact-revision remote CI are not green. Scope and completion criteria are in the [baseline plan](baseline-verification-plan.md). This record distinguishes current checks from historical milestone evidence and does not declare a release.

## Changes

- Corrected the browser CI job to provision and use `edp_foundation_e2e`, including its PostgreSQL healthcheck. All four browser runners accept that isolated database. Backend tests retain `edp_test`; no database guard was weakened.
- Excluded `.local/` from the Docker build context. The directory contains local credentials, PostgreSQL data and ignored test artifacts and is not application source.
- Updated the npm lock within existing manifest ranges: Vitest and its mocker to 5.0.5, and `ip-address` to 10.7.4. Related tooling dependencies changed through their supported ranges; Next.js, Shadcn and direct manifest ranges were preserved. No forced downgrade, audit suppression or dependency override was introduced.
- Reconciled README, backlog, pending register, mobile README/architecture and Phase 10 plan/report. Reporting is implemented; Flutter authentication exists; remaining P0 journeys and release work precede conditional Phase 11/P1 tools.
- Added focused responsive screenshots to the existing reporting browser acceptance script so filters, a metric row and participant controls can be inspected without shrinking a long-page screenshot.

## Current verification

| Check | Result / evidence |
| --- | --- |
| API dependency consistency | `pip check` passes |
| API Ruff / formatting / strict MyPy | Pass; 176 files formatted, 104 source files type checked |
| API/PostgreSQL regression | 112 passed in 520.84 seconds; two existing upstream TestClient/AnyIO deprecation warnings. JUnit: `.local/baseline-20261023-api.xml` |
| Phase 10 migration | Fresh disposable database upgrade/head, downgrade to `e0a6b2c8d345`, re-upgrade/head and zero drift pass; only the newly created database removed |
| Full migration round trip | Separate fresh empty disposable database upgrade/head, downgrade/base, re-upgrade/head and zero drift pass; only the newly created database removed. This is not a populated production rollback proof |
| Existing synthetic databases | `edp_test` and `edp_foundation_e2e` upgraded to head with zero drift; development records were not truncated |
| API contract | Current API matches saved OpenAPI: 223 paths, 349 schemas |
| TypeScript contract | Regeneration passes with unchanged SHA-256 content |
| Web locked install | Clean `npm ci` passes; direct installed dependency checks pass |
| Web checks after dependency update | ESLint, TypeScript, all 180 tests across 37 files and production build pass |
| Flutter available checks | Flutter 3.47.0 / Dart 3.13.0; format 15 files with zero changes, analysis, all 8 tests and JavaScript web release compile pass. Offline `pub get --enforce-lockfile` also passes, with manifest/lock SHA-256 hashes unchanged |
| API vulnerability scans | Runtime 56/56 and development 94/94 pinned packages: zero vulnerabilities, zero skipped entries; Linux-only `uvloop` included. Both original lock hashes unchanged |
| npm vulnerability scan | **Fails:** 9 high, 0 moderate, 0 low, 0 critical after compatible remediation; all remaining records originate from unpatched `braces@3.0.3` |
| Source secret scan | Checksum-verified official Gitleaks 8.24.3, CI-equivalent redacted directory scan over the initial 580 Git-selected source candidates: zero findings. The final source scan is recorded in the containing commit message and ignored summary; no source edit follows that scan |
| Browser acceptance | All four fresh Chrome runners pass: reporting/impact, foundation/B01/B02, K01 and Phase 9 helpdesk/post-training. Combined command exits 0; no JavaScript errors. Tamil responsive overflow/numeric-cell assertions pass, and fresh focused screenshots were visually inspected |
| GitHub Actions | Verification branch: `chore/verified-baseline-20261023`. Remote `main` was `c01ca8158e64f13a21df33e01c13a0f909f2a709` when read; no current-baseline CI result obtained. The unauthenticated API returned 404 and existing Git authentication was unavailable without interaction |
| Docker / Redis / worker / Beat | Docker/runtime acceptance remains unavailable on this host; the existing remote Compose gate remains enabled |
| Native-device acceptance | Deferred under ADR 0004; Flutter web compilation does not establish Android/iOS session, device or store acceptance |

API audit artifacts are under `.tool-cache/evidence/dependency-baseline-2026-10-23/`; secret-scan artifacts are under `.local/baseline-gitleaks-20261023/`. These are ignored local evidence, not deployable or committed application data. Initial restricted-network audit attempts failed; normal network-enabled retries succeeded. No failed network request is counted as a clean scan.

The initial browser attempt stopped before exercising the application because Windows Application Control blocked Python's multiprocessing DLL. The same isolated owned-server run passed after normal tool escalation; no DLL, runtime security setting or test guard was modified. Each runner stopped its temporary API/web processes. The project-owned loopback PostgreSQL cluster remains available for development.

Fresh reporting screenshots are `.tool-cache/evidence/reports-ta-mobile.png`, `reports-ta-mobile-qa-filters.png`, `reports-ta-mobile-qa-metrics.png`, `impact-owner-ta-mobile.png` and `impact-owner-ta-mobile-qa-controls.png`. The focused filter, metric and owner-form captures were inspected for readable controls, intact values and clipping. This closes Phase 10's previously pending responsive acceptance.

Runtime: project Python 3.13.16, Node 24.14.0 and npm 11.9.0. API checks ran from `apps/api`; web checks ran from `apps/web`. Commands included `python -m ruff check .`, `python -m ruff format --check .`, `python -m mypy app`, `python -m pytest -q`, `npm ci`, `npm run contracts`, `npm run lint`, `npm run typecheck`, `npm test` and `npm run build`. All database tests used the documented guarded synthetic databases. Browser commands from the root were `python scripts/run-reports-browser-test.py`, `python scripts/run-foundation-browser-test.py`, `python scripts/run-knowledge-browser-test.py` and `python scripts/run-helpdesk-browser-test.py`, with `PLAYWRIGHT_CHANNEL=chrome`.

Flutter compilation retains the recorded optional Wasm incompatibility in `flutter_secure_storage_web`, redundant `record-use` and CupertinoIcons font warnings. The selected compile target is JavaScript; Next.js remains the browser-account channel.

## Security disposition

The compatible updates address the reviewed [Vitest injection](https://github.com/advisories/GHSA-qxg6-89mg-rqv8), [Vitest Windows path handling](https://github.com/advisories/GHSA-xp26-3454-mjgp) and [`ip-address` validation](https://github.com/advisories/GHSA-rxp7-6hxx-x8q5) findings.

The [reviewed `braces` advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) lists affected versions through 3.0.3 and no patched release. Current supported Shadcn and Next ESLint dependency paths retain it. The observed standalone artifact excludes these tooling packages, but this observation does not waive or pass the existing full dependency gate. Track an upstream patched/removal release or a separately reviewed supported remediation; do not use the offered incompatible major downgrades merely to clear the audit.

## Remaining completion requirements

1. Obtain authorized GitHub access, publish the reviewed feature-branch revision and obtain CI results for that exact revision. Local functional acceptance does not establish remote Linux, Compose or security-gate results.
2. Resolve the remaining high dependency gate without weakening scans. Current local functional passes cannot substitute for this requirement.

Process 1 remains open until its completion criteria pass. The owner-requested notification and the transition to Process 2 must describe the actual status; no later process has started in this record.
