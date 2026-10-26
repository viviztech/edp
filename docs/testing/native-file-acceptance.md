# Native private-file acceptance — Flutter M02

Prepared: 2026-10-24 (Asia/Calcutta). Run on dedicated Android and iOS test installations with synthetic files/accounts, an isolated enabled file policy and the supported bearer API. Ordinary environments retain collection disabled. This checklist supplements [native session acceptance](native-session-acceptance.md) and [private-file architecture](../architecture/mobile-private-files.md). Local Dart/API acceptance does not establish any device row below.

## Build and evidence

Use the supported locked Flutter toolchain. Run `flutter pub get --enforce-lockfile`, `flutter gen-l10n`, `flutter analyze`, `flutter test`, then `flutter build apk --debug --dart-define=API_BASE_URL=HTTPS_TEST_API` and the equivalent iOS build on macOS. iOS requires Xcode; approved application identifiers and signing remain separate release gates. Do not distribute the existing development identifiers/debug signing as production.

Record revision/source manifest, OpenAPI digest, platform/OS, device/provider, build mode, actual observations and sanitized screenshots. Retain no credentials, provider URIs, original filenames or real participant documents in logs. A compilation pass cannot close a device test. The current Windows environment cannot execute iOS and lacks the native SDK/compiler setup needed to accept the new adapters.

## Device matrix

Run every row separately on both platforms, marking pass/fail/deferred with evidence.

| Scenario | Required observation |
| --- | --- |
| Collection disabled or unsupported platform | Metadata/notices remain readable; no picker, upload, removal or download byte action is available |
| Local and cloud document providers | Single-selection, supported MIME filters and read-only permission; no broad storage access, persistent grant, security bookmark or source mutation/deletion |
| Provider lies about length, reports unknown length, stalls or changes | Fixed-buffer snapshot counts exact bytes, rejects empty/over-limit/unsupported data, validates complete UTF-8, times out/cancels without leaving partial copies |
| PDF, PNG, JPEG, WebP and text | Exact snapshot type/size/SHA-256 agrees with the registered proof and received server bytes; rejected or unsafe content never becomes usable |
| Picker lifecycle ordering | Selection callback arriving before host resume waits for foreground; one registration, no automatic byte PUT; cancellation or route/session disposal discards the copy |
| Cancelled picker followed by a new session | Cancel/close the old scope while its system picker remains outstanding, switch account/organization or reattach the engine, then deliver its late result. The old selection must never become a new scope's snapshot. Same-bridge new picks remain blocked until the cancelled launch is drained; process-monotonic request codes cannot match a new bridge launch |
| Interrupted registration or upload | Unchanged request UUID/body for explicit registration recovery; known-detail read before any byte continuation; one PUT for a dropped successful response |
| Background and return | Active network transfer cancels, scans pause, only bounded reads resume; no background byte upload; scalar text remains intact |
| Force-stop/relaunch | Old native temporary copies are removed within guarded cleanup; no persisted document queue or filename recovery; exact pending binding can require identical re-selection |
| Private download | A new authorized typed GET each time; length/type/hash verified before receipt; no external viewer/share/URL credentials; explicit close, background or logout removes the private copy |
| Revocation during selection/upload/download | No late response restores private UI or delivers a completed copy to the next account; new download immediately denied |
| Platform storage and encryption | Verify Android cache bytes reside in credential-encrypted storage on every supported device/OS; an app-private `cacheDir` path alone is not evidence of at-rest encryption. Record device encryption state, locked-device/reboot-before-unlock behavior, handle access after lock and cleanup after unlock. Unsupported/unencrypted configurations cannot be accepted for sensitive document use. Verify Android backup-disabled behavior separately. On iOS verify complete file protection, backup exclusion and locked-device failure |
| Cleanup failure and bounds | Opaque registry refuses foreign IDs/paths, enforces handle/total-byte ceilings and fails closed when cleanup cannot be confirmed |
| Submitted record | Frozen version/hash/size/date stays immutable despite operational version changes; no edit/replacement/removal action |
| Accessibility | English/Tamil, small screens, large text, keyboard, TalkBack/VoiceOver labels, focus and scroll remain usable |

Controlled loopback scanner results establish workflow behavior only. Real storage/scanner freshness, workers, Linux confinement, retention approval, exact-revision remote CI, staging/UAT and release remain separately gated.

The Android bridge now fails closed before scope creation and protected byte operations unless the OS reports active credential-protected encryption, the context uses credential-protected storage, the context user is unlocked and a secure screen lock is configured and currently unlocked. Unsupported/inactive/activating/default-key-only encryption and unavailable status services are rejected. Byte loops recheck protection; cleanup is still allowed after lock. This uses [Android's encryption-status API](https://developer.android.com/reference/android/app/admin/DevicePolicyManager#getStorageEncryptionStatus()), [current-user unlock state](https://developer.android.com/reference/android/os/UserManager#isUserUnlocked()) and [KeyguardManager device security/lock state](https://developer.android.com/reference/android/app/KeyguardManager), without device-administrator enrollment or custom cryptography. Actual supported-device results must still be recorded above; neither the guard source nor compilation proves hardware/OS encryption behavior.
