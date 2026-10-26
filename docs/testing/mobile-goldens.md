# Mobile visual regression environment

Recorded: 2026-10-26 (Asia/Calcutta). Existing Tamil visual masters in
`apps/mobile/test/goldens` were captured and verified on Windows with Flutter
3.47.0. The `mobile` quality job uses `windows-2022`, explicit PowerShell Core
(`pwsh`) and the same pinned Flutter version as its canonical comparison
environment. It runs the complete ordinary Flutter suite, including every visual
assertion, with Flutter's unchanged pixel-for-pixel `LocalFileComparator`.

## Reason for the runner choice

The first published revision, `0a11311`, failed the Ubuntu mobile job in workflow
`40273598030`: analysis was clean and 178 tests passed, while all 11 failures were
Tamil golden comparisons (6.27%–12.13% differing pixels). The same source's full
ordinary suite passed on the existing Windows host: 189 passed and 28 opt-in
synthetic API cases skipped. Those opt-in cases require their owned fixture
runners; their skip condition is independent of visual comparison.

The visual tests already load the bundled Noto Sans Tamil font, including its
test-only `Roboto` alias where used, and the Material Icons font where needed.
Loading font files makes their content reproducible; it does not make font
rasterization identical across operating systems. Flutter explicitly documents
Windows-versus-other-OS font golden differences in
[`matchesGoldenFile`](https://api.flutter.dev/flutter/flutter_test/matchesGoldenFile.html#including-fonts).
The bundled SDK repeats this guidance in
`packages/flutter_test/lib/src/matchers.dart`. Flutter's own
[golden testing guide](https://github.com/flutter/flutter/blob/3.47.0/docs/contributing/testing/Writing-a-golden-file-test-for-package-flutter.md)
uses platform-specific references when validating several rendering environments.

The observed failure pattern is consistent with that documented host-rendering
difference. It does not establish a particular font-backend defect. Widget tests
default their framework target platform to Android, so this is not evidence that
`ThemeData` selected Windows controls locally and Linux controls in CI. Changing
production typography, accepting a percentage tolerance or replacing reviewed
images with Ubuntu output would obscure the existing visual contract.

## Checks and evidence

CI preserves locked dependency resolution, a lockfile diff check, formatting,
analysis, the full ordinary test suite and a JavaScript web build. It has no
visual-test exclusions, custom tolerant comparator, automatic baseline updates
or allowed-failure setting. Each piped native command checks its exit status
before continuing. The final source check includes all tests and PNG masters.

The job records its commit/mobile tree, exact runner image, Flutter version and
font/master SHA-256 values under `apps/mobile/build/mobile-quality`. An always-run
artifact step retains these records, command logs and Flutter's generated
`test/failures` master/current/difference images when present. The first execution
of the changed Windows CI job must supply its own result; an earlier local pass
does not count as that remote result.

To reproduce the canonical check on Windows using the pinned SDK:

```powershell
flutter pub get --enforce-lockfile
dart format --output=none --set-exit-if-changed lib test integration_test
flutter analyze --no-pub
flutter test --no-pub --reporter expanded
flutter build web --no-pub --dart-define=API_BASE_URL=https://example.invalid/api/v1
```

Review every visual mismatch using its master, current and difference images.
For an intentional UI change, update only the affected master on the canonical
environment, inspect it at the specified Tamil width/text scale and commit it
with the corresponding change. This CI repair changes no visual master.

`windows-2022` is an explicit supported GitHub runner label; keeping the label
and SDK explicit avoids implicit `latest` migrations. See
[GitHub runner and shell syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
The runner's actual image version is still recorded because images receive
updates.

Android compilation continues on Ubuntu and iOS simulator compilation continues
on macOS in their existing jobs. This visual policy does not accept Linux/macOS
pixel output, native devices, platform typography, TalkBack/VoiceOver or release
readiness. Additional visual platforms require separately reviewed reference
images and a defined environment; no such baseline is created by this change.
