# Flutter M01 applicant intake checkpoint

Date: 2026-10-24 (Asia/Calcutta). Local scalar applicant checkpoint accepted. This is the scalar applicant slice of the authorized mobile sequence; document delivery is M02. No staging deployment, sender activation or real collection is implied.

## Scope

The application route now discovers open intakes in an explicit organization, starts/resumes an owned cycle draft, renders the pinned English/Tamil fields and acknowledgements, saves partial answers and shows the immutable submission number, accepted acknowledgement dates and permitted status history. Owner history remains independent of open-intake discovery and organization grants. Closed drafts and submitted applications remain readable.

Commands are sent once. Conflicts and uncertain saves/submissions preserve current-screen input, read that exact owned cycle/application, and require an explicit saved-answer/edit decision. Unknown or inaccessible requested records never fall back to another application. Consequential commands are disabled while busy and respect server retry delays. Navigation warns about unsaved or uncertain work; switching organization/intake disposes the previous editor. Resume revalidates through safe reads.

The backend now rejects scalar updates after the linked intake closes. This closes a demonstrated server gap rather than relying on the mobile read-only state. There is no schema or migration change and no API shape change.

The preceding foundation review also closed concurrent-account login/refresh races, rejected-stream cancellation, previous-account device-session rendering, unavailable restore/retry and offline logout. Logout deletes persisted credentials before attempting remote revocation and cannot invalidate a newer login when the old network request finishes. Invalid successful byte-command responses are uncertain rather than safe to replay. Only implemented internal destinations survive sign-in.

## Verification ledger

Checks use the existing cached Flutter SDK, guarded local PostgreSQL databases and synthetic identities only. The ordinary suite explicitly skips opt-in live tests; they are run separately through the owned loopback runner.

| Check | Result |
| --- | --- |
| Applicant editor/repository unit checks | 16 passed; policy/DTO/history checks: five passed |
| English applicant workflow and uncertain-save widgets | Four passed: confirmed submission/receipt/history, lost-save recovery, organization disposal and Tamil layout |
| Tamil 320-pixel layout at 1.4 text scale | Golden generated and visually inspected; title/fields/buttons wrap and content scrolls |
| Live guarded PostgreSQL/API applicant checks | Six passed via `python scripts/run-mobile-api-tests.py --slice applicant` |
| Backend application regression | All 26 affected applications, submission, history, definitions and documents tests passed |
| Full mobile suite | 79 passed; 11 opt-in live tests skipped in ordinary suite; final log `.tool-cache/mobile-m01-full-tests.log` |
| Localization regeneration, Dart format, `flutter analyze --no-pub` | Passed; no analyzer issues |
| Flutter web compilation | JavaScript build passed; optional Wasm dry run remains incompatible with the existing secure-storage web plugin |
| Android debug compile | Unavailable: SDK artifact download failed under restricted network access before compilation |
| Dependency lock enforcement | `flutter pub get --offline --enforce-lockfile` passed |
| Selected-source secret scan | Passed with zero findings; final seal includes navigation checks |

Live evidence: ignored `.local/mobile-api-applicant-e8c0e678.json` and `.tool-cache/mobile-api-applicant-e8c0e678/flutter.log`. The runner migrated only `edp_mobile_e2e`, created a new zero-grant synthetic applicant, retrieved its development verification message out of band, and removed both ephemeral fixture files and owned API/Flutter/observer processes. No production test endpoint or sender was added. The six checks cover partial answers and types, missing acknowledgements, successful pinned receipt, two-device optimistic conflicts, exactly one real save/submit during dropped-response recovery, closed-intake edit denial, peer/cross-organization denial and true 25-row history pagination.

Backend evidence: `.tool-cache/mobile-m01-submission.log`. The guarded `edp_auth_test` database was upgraded to migration head before route regression verification. Ruff format/lint passed for changed Python files. No new dependency or lockfile change was required.

Expanded backend evidence: `.tool-cache/mobile-m01-applications-verified.log` (26 passed in 125.81 seconds). The initial expanded run had 22 passes and four document failures because Windows denied `CreateFileW` access to the default pytest temporary-directory ancestor outside the workspace. Rerunning with a fresh guarded `.tool-cache/mobile-m01-pytest-2ae7588f57` temporary root passed without modifying or substituting storage confinement. No test failure was suppressed.

Navigation regressions cover actual app routes and preserved organization/cycle through login, immediate forwarding for an already authenticated user, updated account queries and external/unsupported/unscoped/looping destination rejection. They use deterministic identity repositories without native storage or network calls.

Executed compile commands: `flutter build web --no-pub --dart-define=API_BASE_URL=https://example.invalid/api/v1` and `flutter build apk --debug --no-pub --dart-define=API_BASE_URL=https://example.invalid/api/v1`. The Android attempt could not retrieve the required Flutter Android SDK artifact from the restricted environment; it provides no Android compile or device evidence. iOS remains unavailable on Windows. The web build is compilation evidence only and is not an approved secure-storage production channel.

Base source: `832ca3f` plus the existing uncommitted M00 and this M01 work. Contract digest (SHA-256): `565bb53866de3a40e2d7806b27ab12dc2ecd4fe854fd499df57002c5b4668ff6`. Final selected-source identity and scan evidence are retained in ignored `.local/flutter-m01-latest-source-scan.json`.

## Remaining boundaries

M02 supplies native secure-file selection/transport and document UI before the complete applicant journey can be accepted. M03–M05 student/support/alumni slices, operational preparation and business tools follow in order. Android/iOS storage, file providers, lifecycle, accessibility, signing and links need native execution; loopback API/widget results cannot close those gates. Runtime/provider, remote CI, staging/UAT and release remain separate.
