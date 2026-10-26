# Native completion checkpoint

Updated: 2026-10-26 (Asia/Calcutta). Item 2 of the
[six-step plan](completion-six-step-plan.md). Toolchain preparation and Android
debug compilation are complete; iOS compilation and device acceptance remain open.

## Delivered preparation and source repair

- Completed the official Gradle 9.3.1 and NDK r28c Windows archives from their
  interrupted downloads. Exact publisher sizes/checksums match. Extraction rejects
  unsafe ZIP paths and symlinks and remains inside the workspace. The portable
  JDK/SDK/Gradle setup changes no machine/user environment, OS protections or
  application compiler versions. See [local Android setup](../deployment/local-android.md).
- Confirmed Flutter's selected Android defaults: compile/target API 36, minimum
  API 24 and NDK `28.2.13676358`. The project uses JDK 21, Gradle 9.3.1, AGP 9.1.0
  and Kotlin 2.4.0.
- Fixed an iOS private-file engine-lifecycle gap found during review. The bridge
  is now published so Flutter can invoke its detach callback. Detachment marks
  the bridge unavailable, suppresses late method replies, cancels picker/provider
  work and serially removes app-owned scopes, including a scope creation already
  in flight. Coordinator cancellation and stream closure run off the UI thread.
  The registration contract was checked against the cached FlutterPlugin header
  and FlutterEngine implementation. This source review is not iOS compilation or
  runtime evidence.
- No Dart, API, database, dependency lock, privacy policy, approved app identity
  or release-signing change was made by this native checkpoint.

## Executed evidence

| Check | Actual result |
| --- | --- |
| Gradle archive | 234,893,460 bytes; publisher SHA-256 `17f277867f6914d61b1aa02efab1ba7bb439ad652ca485cd8ca6842fccec6e43` matches |
| NDK archive | 748,118,221 bytes; publisher SHA-1 `086bba43ff2f5eb0e387b15c8278bb4e0d89ba1d` matches; source properties and Clang binary present |
| Android debug compilation | Cached retry of `flutter build apk --debug --no-pub --dart-define=API_BASE_URL=https://example.invalid/api/v1` passed with exit zero at 2026-10-26 05:38:42 UTC; initial interrupted attempt is excluded |
| Android device enumeration | Approved normal ADB invocation succeeds; zero attached devices. Newly started daemon cleaned up; no hardware identifiers recorded |
| Android runtime | Not executed: no device/emulator established |
| iOS compilation/runtime | Not executed: this Windows host has no macOS/Xcode environment |
| Release identity/signing | Not approved or verified; development identifiers/debug signing remain unsuitable as release evidence |

Evidence paths are ignored local artifacts:
`.local/native-archive-verification-20261026.json`,
`.local/native-device-probe-20261026.json` and
`.tool-cache/completion-step2-native/` (source manifest and build logs).
The successful artifact is `apps/mobile/build/app/outputs/flutter-apk/app-debug.apk`,
165,530,645 bytes, SHA-256
`ce4b427780cf07f4aa354d52457f744bf57dc81fed4c7958b5a971974695d526`.
The Android/Dart source manifest is unchanged before/after compilation:
`8e5c62782d8d648d31639a878db55550849157779e8572e18108ab2464832fba`.
The exact command, source identity and artifact proof are in
`.tool-cache/completion-step2-native/acceptance.json`. Gradle also installed API
34/35 platform dependencies inside the workspace; the application's compile/target
remains API 36. The interrupted log is preserved separately. The generated APK,
keys and compiler caches remain ignored and are not published as repository source.

## Outstanding platform acceptance

Run the existing [session](../testing/native-session-acceptance.md),
[file](../testing/native-file-acceptance.md) and
[attendance](../testing/native-attendance-acceptance.md) checklists on actual
Android and iOS test installations with synthetic accounts. Include secure
storage, rotation/revocation/logout, process death, protection lock/unlock,
provider-URI interruption, private cleanup, camera permissions, accessibility and
deep-link reauthorization. A compiler or widget result cannot substitute for
those observations.

On iOS also create and destroy an engine while a picker, provider copy or download
is pending. Verify prompt UI dismissal/cancellation, no reply after engine
destruction, cleanup of app-owned private scopes, and successful initialization
of a replacement engine. Repeat teardown racing with scope creation. Force-kill
acceptance remains a separate startup-sweep check because teardown callbacks
cannot execute after abrupt process termination.

Approved platform identifiers, signing/store custody, an Android test target and
macOS/Xcode access are still needed. No store submission, external message,
personal-data collection or deployment was performed.
