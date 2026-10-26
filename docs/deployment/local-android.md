# Workspace-local Android compiler

Prepared 2026-10-24 for local debug compilation. This setup does not install Android
Studio, register a JDK, change machine/user PATH or submit any artifact to a store.
Physical-device behavior, iOS compilation/signing, release identity/signing and
exact-revision remote CI remain separate acceptance gates.

## Verified portable inputs

| Input | Official source | Publisher checksum |
| --- | --- | --- |
| Google command-line tools `commandlinetools-win-15859902_latest.zip`, CLI 22.0 | [Android downloads](https://developer.android.com/studio) | `90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a` |
| Microsoft OpenJDK 21.0.12.1 Windows x64 ZIP | [Microsoft release archive](https://learn.microsoft.com/en-us/java/openjdk/older-releases) and its linked checksum | `192441a9d27da813bada974bb88b4cf64d37a9589ed37f204374d411ca5ce07f` |
| Gradle `9.3.1-all.zip` | [Official distribution checksum](https://services.gradle.org/distributions/gradle-9.3.1-all.zip.sha256) | `17f277867f6914d61b1aa02efab1ba7bb439ad652ca485cd8ca6842fccec6e43` |
| NDK r28c Windows, revision `28.2.13676358` | [Official Android NDK archive](https://github.com/android/ndk/wiki/Unsupported-Downloads#r28c) | SHA-1 `086bba43ff2f5eb0e387b15c8278bb4e0d89ba1d` |

The JDK and command-line archives were actually hashed and matched against those
published checksums before extraction. Their archives are held under ignored
`.tool-cache`; extraction is confined to the workspace and rejects unsafe archive
paths. The Gradle value is the retrieved publisher checksum for wrapper validation.
The JDK was extracted under
`.tool-cache/jdk/jdk-21.0.12.1+1`, and command-line tools under
`.tool-cache/android-sdk/cmdline-tools/latest`. Official archive verification
evidence is in ignored `.local/android-toolchain-downloads.json`.

On 2026-10-26 the previously interrupted Gradle and NDK downloads were resumed and
completed over verified HTTPS. The Gradle archive is 234,893,460 bytes and matches
the published SHA-256 above; the NDK archive is 748,118,221 bytes and matches
Google's published SHA-1. Its additional local provenance SHA-256 is
`6bec98ac2354d8a919760889a1a41d020132e5e8cfa1b1fe51610a72c36a466b`.
Both ZIPs were checked before guarded workspace extraction/staging. The NDK's
`source.properties` and Windows Clang binary were verified. Evidence is
`.local/native-archive-verification-20261026.json`; installing these tools does not
establish a successful application compilation.

Project-selected packages are API 36, build-tools 36.0.0, platform-tools and
NDK 28.2.13676358. The official SDK manager obtains package metadata/checksums over
HTTPS and verifies package downloads. Use the selected versions rather than
upgrading the application's compiler configuration incidentally. Google's CLI 22.0
deprecates `sdkmanager` in favor of `android sdk`; the included `sdkmanager` still
supports these documented package/install/license operations.

## Session-only paths and compilation

From the repository root in PowerShell, set paths only for the current process:

```powershell
$env:JAVA_HOME = Join-Path (Get-Location).Path '.tool-cache/jdk/jdk-21.0.12.1+1'
$env:ANDROID_HOME = Join-Path (Get-Location).Path '.tool-cache/android-sdk'
$env:ANDROID_USER_HOME = Join-Path (Get-Location).Path '.tool-cache/android-user'
$env:GRADLE_USER_HOME = Join-Path (Get-Location).Path '.tool-cache/gradle'
$env:JAVA_OPTS = '-Duser.home=' + $env:ANDROID_USER_HOME
$env:PUB_CACHE = Join-Path (Get-Location).Path '.tool-cache/pub'
$env:PATH = $env:JAVA_HOME + '\bin;' + $env:PATH
```

Do not repurpose `HOME` or persist these values using machine/user environment
configuration. `ANDROID_USER_HOME` holds Android user state/debug keys; the scoped
JVM user-home setting also confines Java/Gradle home-based state. Preserve the
existing Flutter cache and lockfile. Application `android/local.properties` is an
ignored machine-local file, not a source-controlled absolute path.

Install the required packages with the official SDK manager and accept their
licenses through its normal flow. Keep HTTPS verification enabled:

```powershell
& '.tool-cache/android-sdk/cmdline-tools/latest/bin/sdkmanager.bat' --sdk_root=$env:ANDROID_HOME 'platform-tools' 'platforms;android-36' 'build-tools;36.0.0' 'ndk;28.2.13676358'
```

From `apps/mobile`, use the project Flutter SDK to build a synthetic debug APK:

```text
flutter build apk --debug --dart-define=API_BASE_URL=https://example.invalid/api/v1
```

Use a reachable development API only for explicitly scoped synthetic runtime tests.
The compilation define does not contact that URL during a build. Record the actual
build outcome, source identity and artifact hash in the mobile acceptance report;
tool installation alone is not a native compilation pass. Keep generated debug
keys, Gradle/SDK caches and APKs out of source control.

## Current native acceptance

The 2026-10-26 cached Android debug retry passed with exit zero and unchanged
Android/Dart source. The 165,530,645-byte APK has SHA-256
`ce4b427780cf07f4aa354d52457f744bf57dc81fed4c7958b5a971974695d526`.
The initial interrupted attempt remains excluded. Gradle installed API 34/35
dependency platforms inside this workspace; application compile/target remains
API 36. See [native completion](../sdlc/native-completion-report.md) and ignored
`.tool-cache/completion-step2-native/acceptance.json` for exact source/artifact
proof. This is compilation evidence, with no device installation or release pass.

Normal approved tool execution of `adb devices -l` succeeded and reported no
attached devices. Only device-state counts were retained; the newly started ADB
daemon was stopped. The restricted sandbox token's earlier profile-directory
failure is a distinct failed preflight, not evidence of an empty device list.
Neither `HOME` nor machine/user environment settings were changed. This host has
no established emulator or macOS/Xcode environment.
