# Flutter M00 shared client and navigation checkpoint

Date: 2026-10-24 (Asia/Calcutta). Local checkpoint accepted; the full Flutter process remains in progress. This follows accepted secure files, background recovery and communications. No release, native-device acceptance or provider activation is implied.

## Delivered

- Central restoring/signed-out/authenticated/unavailable session state, app-entry restoration, server locale and organization permission grants. Existing account controls remain compatible.
- One authenticated relative-path JSON/byte transport with single-flight refresh, fenced credential writes, central invalidation and at-most-once commands. Errors distinguish rejected/not-sent/uncertain results; unknown command results require domain readback. No bearer defaults reach public requests.
- Bounded streamed downloads with length checks, cancellation and rejection of foreign paths, traversal, redirects and unsafe custom headers. Token and sensitive response bodies do not enter error diagnostics.
- Validated internal destinations retained through account entry; private feature state is unmounted on session identity/generation/context change. Owner application history is available independently of staff/participant grants.
- Discoverable public news/events/FAQ/stories with pagination, complete details, retry, empty/loading states and stale-response protection. English/Tamil shell and a narrow-screen enlarged-text visual check.
- Reconciled participant-notification plan with the accepted enrollment inbox, without exposing CRM notices to participants.
- Bounded web improvements: language switching preserves pathname and validated intake context, and participant timeline labels/dates are localized.

## Verification

Executed with the existing supported project Flutter toolchain and Python 3.13 environment:

| Check | Result |
| --- | --- |
| Dart formatting; `flutter analyze --no-pub` | Passed; no analyzer issues |
| `flutter test --no-pub --reporter expanded` | 35 passed; five opt-in live tests correctly skipped by the ordinary suite |
| `python scripts/run-mobile-api-tests.py --slice m00` | Five real loopback API tests passed against guarded `edp_mobile_e2e` |
| `flutter build web --no-pub --dart-define=API_BASE_URL=https://example.invalid/api/v1` | JavaScript compile passed; existing secure-storage plugin is incompatible with optional Wasm dry run |
| Tamil 320 logical-pixel width at 1.4 text scale | Golden generated with bundled font, visually inspected; content remains scrollable |
| Web focused navigation/timeline checks | 11 tests and TypeScript check passed; full final web acceptance follows the combined changes |

Live API checks exercise real profile/grants/locale, restoration, zero-grant history, enrollment notices/read/preferences, stale versions, peer/cross-organization/CRM denials and owned history. Evidence: ignored `.local/mobile-api-m00-72f20288.json` and `.tool-cache/mobile-api-m00-72f20288/flutter.log`. Owned API/Flutter processes were cleaned up and the credential-bearing ephemeral fixture removed. The recorded contract SHA-256 is `565bb53866de3a40e2d7806b27ab12dc2ecd4fe854fd499df57002c5b4668ff6`.

No API/schema/migration change was required. Existing database authorization remains authoritative. Production refresh tokens still use the OS secure-storage implementation; the in-memory token store is confined to acceptance tests.

## Remaining scope

M01 applicant editor, M02 documents, M03 student learning/attendance, M04 support/resources/plans and M05 alumni/outcomes remain open. Android/iOS secure-storage, file-provider/camera, lifecycle/deep links, signing and accessibility still require native execution. Live queue/storage/scanner/provider, remote CI, staging and release gates remain separate. The golden is widget-layout evidence and the web build is compilation evidence.

Continue M01, then M02 within applicant delivery; report each accepted local slice before student-domain acceptance.
