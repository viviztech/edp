# Native compilation in CI

Prepared 2026-10-26 (Asia/Calcutta). The foundation workflow preserves its existing
quality jobs and adds two required compilation jobs after the `mobile` checks.
This workflow definition has been prepared locally; a passing remote run must be
recorded against the actual published revision before CI acceptance is claimed.

| Job | Environment | Compile target |
| --- | --- | --- |
| `mobile-android-compile` | GitHub-hosted Ubuntu, Temurin JDK 21, Flutter 3.47.0 | Normal application debug APK |
| `mobile-ios-simulator-compile` | GitHub-hosted macOS 15 and its recorded Xcode, Flutter 3.47.0 | Unsigned iOS simulator debug app |

Both jobs enforce `pubspec.lock`, build with
`API_BASE_URL=https://example.invalid/api/v1`, and reject tracked mobile-source or
lockfile changes caused by the build. No reachable API, provider credentials,
release keys, provisioning profiles, store account or deployment target is used.
Android uses the project's API 36, build-tools 36.0.0 and NDK 28.2.13676358, alongside
the source-controlled Gradle 9.3.1 checksum and AGP/Kotlin settings. The hosted
Android runner must provide `sdkmanager` and the normal accepted SDK licences;
missing tooling or an unaccepted licence fails the job rather than skipping it.

The commands are:

```text
flutter pub get --enforce-lockfile
flutter build apk --debug --no-pub --dart-define=API_BASE_URL=https://example.invalid/api/v1
flutter build ios --simulator --debug --no-codesign --no-pub --dart-define=API_BASE_URL=https://example.invalid/api/v1
```

## Evidence

Each job retains a uniquely named seven-day compile artifact containing its build
log, actual checked-out Git revision, mobile Git tree identity, Flutter/toolchain
versions, lockfile digest and explicit acceptance boundary. Successful compilation
also packages the APK or a compressed `Runner.app` bundle and a `SHA256SUMS`
manifest covering the packaged files. The iOS tar archive preserves executable
permissions and app-bundle structure across artifact download. On a failed build,
the upload step retains any preparation/build evidence already produced; a
partial directory is not a successful compilation artifact.

Download a successful artifact, then verify its contents from the extracted
artifact directory with `sha256sum -c SHA256SUMS` on Linux or
`shasum -a 256 -c SHA256SUMS` on macOS. The revision is the actual checkout, including
GitHub's merge revision for pull-request builds, rather than an assumed branch tip.

## Acceptance boundary

These jobs compile only. They do not launch a simulator or device, exercise secure
storage or file providers, verify camera/deep-link/background behavior, establish
release signing, scan native dependencies, or approve a release. The Android APK
uses debug signing and the iOS app is simulator-only and unsigned. The existing
application identifiers remain development placeholders until their owner approves
real identifiers. Continue with the [native session](native-session-acceptance.md),
[private-file](native-file-acceptance.md) and
[attendance](native-attendance-acceptance.md) acceptance procedures on both platforms.

Local YAML parsing and shell syntax checks cannot establish successful action
execution, hosted-runner availability or an Xcode/Gradle compilation result. Record
the remote run URL, exact revision and artifact digests when those jobs actually run.

## Primary references

- [Flutter action version selection](https://github.com/subosito/flutter-action)
- [GitHub Java setup](https://github.com/actions/setup-java/tree/v4)
- [GitHub artifact upload and permission preservation](https://github.com/actions/upload-artifact/tree/v4)
- [GitHub workflow syntax and runner labels](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [Flutter iOS build prerequisites](https://docs.flutter.dev/deployment/ios)
