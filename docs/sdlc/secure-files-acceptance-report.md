# Process 3 / secure files acceptance

Recorded: 2026-10-23; locally accepted: 2026-10-24. Status: **local implementation and acceptance complete; external release gates open** on `feat/secure-files-20261023`. The [foundation checkpoint](secure-file-foundation-report.md) was committed locally as `5ed91b3`; the complete typed integrations are prepared for their coherent local checkpoint. This report follows the [ordered plan](secure-files-plan.md). No push, deployment, live provider activation or external message was performed.

## Continuation checkpoint — 2026-10-24

The owner authorized the [six remaining development steps](remaining-development-plan.md) in order. Final-build acceptance is complete. Ten sequential browser runners passed against the same production web artifact `SO-9NHHX7GsUyJv7ZuRxf`: file policy, application documents, CMS media, learning files, helpdesk files, foundation, knowledge, legacy helpdesk, reports and the combined applicant/enquiry/editorial journeys. Each used guarded synthetic databases and owned temporary servers. Evidence: `.local/files-final-acceptance-15251ff0.json` and `.tool-cache/files-final-20261024-15251ff0/`.

Fresh web verification passes: all 406 tests across 72 files with two workers, ESLint, TypeScript and the production build. The lost-upload recovery test now holds its authoritative read unresolved, proves readiness remains false, and waits for the readiness effect after successful reconciliation; it still requires exactly one byte upload. The CMS HttpOnly-CSRF correction is implemented and its focused tests pass.

The unsuppressed npm audit on 2026-10-24 reports **zero vulnerabilities**. The old `braces` advisory was withdrawn; newly reported transitive findings were repaired with compatible `body-parser` 2.4.0, `undici` 7.30.1, `zod` 4.6.7 and `fast-uri` 3.1.9 updates, without overrides, forced major changes or scan exclusions. The dated historical findings below are not the current dependency result. Audit evidence is `.local/dependency-audit-20261024.json`.

Windows Code Integrity blocks the unsigned uv-managed Python. The official PSF-signed Python 3.13.17 installer was verified against its published SHA-256 and publisher signature and installed into the project tool cache. Standard `venv --upgrade` restored the original `.venv` without replacing its installed API dependencies; its executable has a valid PSF signature. Bundled pip 26.2.2 and the development-only filelock 4.2.1 security fix are reflected in the development lock. No machine security policy, system Python or PATH was changed. See [local setup](../deployment/local.md).

Fresh backend acceptance passes: Ruff, all 223 files formatted, strict MyPy for 129 sources, dependency consistency/import checks, and **289 API/PostgreSQL tests passed with one POSIX-only skip** in 828.23 seconds. The warnings are two upstream deprecations and an unwritable optional pytest cache; none is a test failure. Evidence: `.tool-cache/p3-backend-20261024-27be0dc4/result.json`, `api.xml` and logs. The POSIX confinement check remains a Linux runtime gate.

A newly owned disposable database passed fresh base to `m8c4d0e6f123`, downgrade to empty base, and re-upgrade to head. Complete unfiltered metadata and global Alembic checks report zero drift across 128 model tables after both upgrades; only the database created for this check was dropped. Evidence: `.local/file-migration-acceptance-57f8c916.json`. Regenerated OpenAPI and TypeScript contracts have identical hashes to the accepted artifact's source.

Both complete pinned Python locks audit clean: 61 runtime and 101 development packages, zero known vulnerabilities after the filelock fix. The audit checks every applicable exact pin directly (`--no-deps --disable-pip` avoids downloading an already resolved dependency graph); no package or advisory is ignored. Evidence: `.local/p3-runtime-audit-20261024.json` and `.local/p3-development-audit-20261024.json`.

Six fresh representative screenshots were inspected: applicant English desktop, reviewer Tamil mobile, CMS Tamil mobile, learner English mobile, learning author Tamil desktop and helpdesk mobile. Text/references wrap, controls and native inputs stay contained, and no blocking clipping/overlap was observed. This static review does not constitute full accessibility certification. Browser assertions retain keyboard, responsive, authorization and recovery checks.

The selected-source Gitleaks scan reports zero findings across 745 source files. The final updated ledger and intended source are sealed and scanned together before the local commit; `.local/process3-latest-source-scan.json` records the current manifest and result. No environment files, real uploaded bytes, credentials or generated build artifacts belong in the checkpoint. Remote CI, real providers, native devices and release approval remain open.

## Implemented scope

- Explicit versioned purpose policies and a shared private byte lifecycle, including actual size/MIME/hash verification, quarantine, fenced scanning/recovery, retention, holds and metadata-preserving disposal. Policy publication does not enable collection.
- Application document requirements pinned to published form editions, draft owner upload/remove/replace, current-assignment reviewer authorization and atomic immutable submitted evidence. Existing empty requirements remain compatible.
- CMS typed source uploads, bounded metadata-stripped image derivatives scanned independently, exact verified public publication/revocation, private downloads and attachment-only public PDFs. Legacy metadata is unbacked until actual bytes are verified. The old unbound scanner callback returns 410 and cannot mark bytes clean.
- Assignment files scoped to the eligible owner's course enrollment and exact next revision; explicit selected IDs, required counts and frozen submitted proof. Learning materials use the current actor/course/material gateway and exact scanned pins. Draft authors can explicitly remove abandoned/rejected material, retaining history and reserving its position; incomplete active material blocks publication.
- Helpdesk staged attachments, atomic immutable message evidence, current owner/assignee/admin access and staff-note privacy. Existing bounded TXT attachments remain compatible. File intent writes do not advance ticket history/version; posted message writes do.
- English/Tamil interfaces, bounded raw byte BFF transports, closed domain route/query allowlists, origin/CSRF checks, current usable-state checks, preserved local input and explicit read-before-resend recovery. No generic file ID endpoint grants domain byte access.

Collection and maintenance remain disabled by default. The owner selected configurable rules; this implementation does not approve a real document list, bilingual notice, retention period or disposal policy. Test policies, people, scanner results and bytes are explicitly synthetic.

## Historical verification ledger — 2026-10-23

| Check | Current evidence |
| --- | --- |
| API static | Ruff passes; 223 files formatted; strict MyPy passes for 129 sources |
| API/database | Full integrated run: 288 passed, one POSIX-only skip, two upstream Starlette deprecation warnings in 942.74 s. After the reviewed cached-course refresh fix, final learning/private-gateway regression: 13 passed in 160.85 s, including the new concurrent-publication case |
| Migrations | Fresh empty database → `m8c4d0e6f123` → empty base → head passes; global Alembic check and metadata comparison report zero drift across all 128 model tables after both upgrades. The newly owned disposable database was removed; shared databases were untouched |
| Web | Final full suite: 404 passed across 72 files with two workers, followed by clean ESLint, TypeScript and production build. An earlier combined-load run hit four existing five-second timeouts; no assertion, timeout or case was removed. Bounded workers passed the unchanged checks |
| Contracts | 232 → 257 paths versus foundation checkpoint; 25 additions and no path removal. Nine existing schema changes add optional/defaulted fields without removing properties or adding required inputs. Intentional CMS changes require versioned verified publication and return 410 for the unbound scan callback; obsolete `AssetScanResult` is removed. Regenerated OpenAPI/TypeScript are deterministic |
| Application documents | Focused API and 52 web tests pass; isolated English/Tamil Chrome acceptance passes with actual upload/recovery/submission/reviewer flows, revocation negatives, keyboard checks and 360/390/768/1280 widths. Mobile Tamil reviewer and desktop applicant evidence visually inspected |
| CMS | Browser acceptance in progress. Its first actual mutation exposed an HttpOnly-CSRF-cookie handling defect missed by mocked component tests; a narrow endpoint-based token fix and regression are required before rerunning |
| Learning | Browser acceptance in progress; 20 focused interface tests pass. Actual final concurrency behavior and retained removal/replacement are covered by the database regression above |
| Helpdesk | Browser acceptance and legacy compatibility run in progress; focused component/transport checks and current ticket/assignment privacy database cases pass |
| Legacy regressions | Final-build foundation/knowledge/reports, policy and application rechecks pending; editorial/enquiry/applicant compatibility runner in progress |
| CI preparation | Dedicated `browser-files` workflow uses guarded per-domain databases, synthetic collection and installed Chromium. YAML parses locally. Remote execution remains deferred under the owner's local-only instruction |
| Source secrets | Final selected-source scan pending after acceptance fixes and documentation are stable |

Migration evidence: ignored `.local/file-migration-acceptance-dcbabe6b.json` and `.tool-cache/file-migration-acceptance-dcbabe6b.log`. Contract comparison: `.local/process3-integrated-contract-review.json`. Deterministic SHA256 values: OpenAPI `8B5A2CF44D94E4BC92BB11C94AEECA2F7044B039AEE2C5546ABBD4831481A525`; TypeScript `4DBFB3802A6EBD4C3433537623A07F869336F35D25A86DB15DA8B7AD863EA739`.

## Remaining acceptance and release boundaries

The 2026-10-24 continuation checkpoint supersedes the pending entries in the historical ledger. It closes local Process 3, including the CMS correction, native chooser reset, final-artifact regressions, visual review and source checks. The owner receives the progress report before background-job recovery starts; the [recovery plan](background-job-recovery-plan.md) separates job durability from subsequent essential communications.

Live private S3/IAM/encryption/versioning, ClamD signature freshness/network isolation, Redis/Celery worker/beat round trips, Linux confinement, backup/object restore consistency, volume/load acceptance, native-device file/session behavior and approved real collection rules remain separate runtime/release gates. Protocol peers, SDK stubs, injected fixture scanners and direct task-function tests do not satisfy those gates.

Current npm and complete Python runtime/development audits report zero findings. The earlier nine-high `braces` record is historical. Exact-revision remote CI, staging, UAT and production approval remain open. No security scan is suppressed and no production release is claimed.

See [application design](../architecture/application-documents-design.md), [CMS design](../architecture/cms-verified-media.md), [learning design](../architecture/learning-private-files.md), [helpdesk design](../architecture/helpdesk-files-design.md) and [runtime preparation](../deployment/secure-files.md).
