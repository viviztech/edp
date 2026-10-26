# Flutter M02 applicant document checkpoint

Date: 2026-10-24 (Asia/Calcutta). Local Dart/API checkpoint verified. This checkpoint continues the authorized Flutter domain sequence after M00/M01. Native adapter compilation and device acceptance remain distinct from the Dart/API evidence below. Collection remains disabled outside isolated synthetic fixtures.

## Implementation

The applicant screen now renders pinned English/Tamil document notices, supported formats, effective byte limits, requirement/shared-policy counts and retention before selection. Typed owner endpoints support registration, raw streaming PUT, bounded scan polling, explicit replacement/removal, process-restart re-selection and private verified-download receipts. Submission remains gated by server `usable` evidence. Submitted proof uses frozen hash/size/version/date, and fresh authorized detail labels newly downloaded bytes.

The shared byte transport streams between immutable app-private snapshots and the existing authenticated identity client. It derives exact MIME, length and quoted file-version headers, verifies complete checksums, rejects foreign/redirected requests and bounds native chunks and responses. No multipart, filename/path upload, external viewer/export, durable offline document queue or automatic consequential replay was added. A late private sink/snapshot after timeout is disposed. Failures after a PUT starts remain uncertain; known typed readback precedes explicit continuation.

Android and iOS adapters expose opaque scope/snapshot IDs, fixed-buffer provider reads, private temporary files and bounded registry cleanup. iOS coordinates security-scoped reads, complete file protection and backup exclusion. Android retains internal cache and backup-disabled behavior without broad storage permissions. These are implementation/code-review facts; this host has not compiled or executed the new native adapters.

Lifecycle handling waits for foreground when a platform picker result precedes host resume, pauses scans/transfers in background and clears private receipts. Aggregate document/scalar version updates are serialized/coalesced; dirty scalar answers survive an acknowledged document update, and concurrent scalar changes still require explicit review. Both policy-wide and requirement counts apply. List/readiness guards derive from the pinned contract maximum (20 requirements × 100); existing API replacement/removal filtering was verified instead of adding a redundant API parameter.

## Verification ledger

| Check | Result and evidence |
| --- | --- |
| Focused document unit/widget acceptance | 56 passed; `.tool-cache/mobile-m02-document-unit-tests.log` |
| Queued scalar versions and partial-upload failures | Three additional tests passed, included in full suite; a native error after bytes start remains uncertain with one PUT and no replay |
| Full mobile suite | 138 passed; 16 opt-in live cases correctly skipped in ordinary suite; `.tool-cache/mobile-m02-full-tests.log` |
| Real loopback document journeys | Five passed; all supported MIME types, pending/unsafe scanning, replacement/removal, immutable submitted evidence/downloads, dropped response recovery, stale/changed intent, peer/organization denial and revoked sessions; `.local/mobile-api-documents-d24f6f95.json` |
| Real loopback applicant regression | Six passed; `.local/mobile-api-applicant-6b18c055.json` |
| Backend regressions | 36 passed in 78.03 seconds; `.tool-cache/mobile-m02-backend-0c5b4a75/pytest.log`; two dependency deprecation warnings retained |
| Backend typing and script lint | Strict MyPy passed all 140 API source files; Ruff passed the new/changed fixture runners and document regression |
| Web regression | All 473 tests across 79 files passed; ESLint and TypeScript passed; `.tool-cache/mobile-m02-web-tests.log`, `mobile-m02-web-lint.log`, `mobile-m02-web-typecheck.log` |
| Mobile formatting and analysis | Dart format and `flutter analyze --no-pub` passed with no issues; `.tool-cache/mobile-m02-analyze.log` |
| Locked dependencies | `flutter pub get --offline --enforce-lockfile` passed with the existing workspace `PUB_CACHE`; `.tool-cache/mobile-m02-lockfile.log`; no package-version upgrade |
| OpenAPI regeneration | Regenerated with inert schema-export settings; exact digest unchanged |
| Localization determinism | Regeneration preserved every generated localization digest; format check covered 55 Dart files with zero changes |
| Tamil visual acceptance | 320 logical pixels, 1.4 text scale; top/bottom goldens visually inspected, notices/digest wrap and download action remains reachable |
| Flutter web compilation | `flutter build web --no-pub --dart-define=API_BASE_URL=https://example.invalid/api/v1` passed; `.tool-cache/mobile-m02-web-build.log`. Existing optional Wasm secure-storage incompatibility and optional font warning remain recorded; this is compilation evidence |
| Android debug compile | Attempted; restricted-network download of Flutter Android SDK artifact failed before compilation; `.tool-cache/mobile-m02-android-build.log`. Not a compiler/device pass |
| iOS/native structure checks | Native whitespace, plist parsing, source registration and delimiter checks passed; no Swift/Xcode or Android/JDK compiler/device acceptance on this host |
| Selected-source secret scan | 852 Git-selected source files passed the checksum-verified cached Gitleaks scanner with zero findings; final identity in `.local/flutter-m02-latest-source-scan.json` |

The loopback runner enabled collection only in its guarded `edp_mobile_e2e` fixture and used bounded synthetic memory snapshots with an out-of-band controlled scanner. Ten synthetic scans completed. Both final runners stopped their owned API/Flutter/observer processes, removed ephemeral credential/verification files and recorded `cleanup_failed=false`. They did not exercise native storage/pickers or a real scanner/broker.

Source base remains local `832ca3f` plus the existing M00/M01 working tree and this M02 continuation. The final source-only scan record is `.local/flutter-m02-latest-source-scan.json`; it records the selected-source manifest identity and scanner result. No source publication or deployment occurred.

## Database and contract

No M02 schema, migration or API-shape change. A backend regression asserts that removed/replaced rows are excluded before owner pagination, excluded cursors are rejected and peer/other-organization access is denied. The existing M01 closed-intake scalar fix remains in the working tree. OpenAPI SHA-256 remains `565bb53866de3a40e2d7806b27ab12dc2ecd4fe854fd499df57002c5b4668ff6`.

## Remaining scope

Run [native file acceptance](../testing/native-file-acceptance.md) and the existing native session checklist on both platforms. Compiler/SDK availability, real file providers, process death, locked-device protection, accessibility, app identifiers and release signing remain gates. Controlled loopback scanning does not establish real ClamD/storage/worker runtime, retention approval or real collection. Remote CI, staging/UAT, provisioning and release remain separate.

Next in the authorized order is M03 student schedule, learning, materials, assessments and attendance, then M04 support/resources/plans and M05 alumni/outcomes. Only after the local Flutter scope is checked and reported do staging preparation and business tools follow. All work remains local.
