# Native session acceptance - Milestone 1

Scope: F02/F04 native OS storage and account-session behavior. Run on dedicated Android and iOS test installations using synthetic accounts only. Do not use a participant device or real account. The integration test refuses to replace an existing refresh session; it deletes only its own refresh-token entry on completion.

## Automated native storage check

From apps/mobile, run `flutter pub get`, `flutter devices`, then:

```sh
flutter test integration_test/secure_token_store_test.dart -d DEVICE_ID
```

This invokes the real flutter_secure_storage platform plugin, not a method-channel mock. It checks read/write, persistence across store instances, replacement of the previous value, deletion and repeated deletion. It does not prove persistence across process death, server revocation, hardware-backed storage, release signing or iOS behavior from an Android result. No server or live messaging is required. Values are synthetic non-credentials.

## Connected account journey

Use the isolated API database and local encrypted message delivery described in ../deployment/local.md. Use HTTPS for release builds; Android debug emulator may use http://10.0.2.2:8000/api/v1. A physical device needs a reachable test API. Never expose the development API to the public internet.

| Check | Expected evidence |
|---|---|
| Register, verify and login | Pending account cannot login; local verification enables account; English/Tamil states render correctly |
| Force-stop and relaunch | Account restores through refresh; no password re-entry; access token/password absent from persistent storage |
| Refresh rotation | Old refresh credential replaced; simultaneous reads do not cause duplicate rotations |
| Revoke from a second session | Existing device loses protected access and cannot restore through revoked refresh credentials |
| Reset password | Existing sessions stop working; new password permits login |
| Online logout and relaunch | Device signed out; local refresh entry removed; server session revoked |
| Offline logout and relaunch | Local session cleared; failure visible; no claim of successful server revocation |
| Offline/timeout during rotation | Unusable refresh credential cleared; recovery requires sign-in |
| Android backup configuration | Release manifest disables backup; debug cleartext setting absent from release |
| iOS secure storage | Actual simulator/device plugin check passes; repeat lifecycle journey on iOS |

Record commit SHA, OS/API version, model or simulator, build mode, test command, result and sanitized evidence location. Never record token values, passwords or personal data. Use a second synthetic account/session for revocation. Manual steps require actual observations, not code inspection.

## Current evidence and blockers

On 2026-09-18, `adb devices -l` returned no connected device and the Android SDK emulator executable was absent. This Windows host cannot run an iOS simulator. Native runtime acceptance remains unexecuted. Existing Android debug compilation, Flutter unit tests and Flutter web CI do not close these gates. The approved backend CI fix was fast-forwarded into main at f28459c after all six jobs passed.

Production provider delivery, MFA, audit database-role separation, privacy approvals, TLS, monitoring and restore validation remain separately tracked launch gates. This checklist does not claim those are complete.

Preparation validation: `flutter analyze` passed, all 5 existing `flutter test` tests passed, and `flutter build apk --debug --target integration_test/secure_token_store_test.dart` passed (136.7 seconds). The ignored app-debug.apk is now the integration-test build, not the normal application build. This proves compilation only; the native storage test has not been executed on a device.
