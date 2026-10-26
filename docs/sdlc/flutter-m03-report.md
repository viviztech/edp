# Flutter M03 student journeys

Updated: 2026-10-24 (Asia/Calcutta). Local Dart/API checkpoint within the authorized Flutter domain sequence. Native compilation/device acceptance is recorded separately; this is not a production release.

## Implementation

The enrolled student's typed schedule, ordered course/module/lesson content, prerequisites, completion, quiz attempts, assignment text/file evidence, grades/feedback, certificate eligibility/public verification and attendance are connected to the existing bearer APIs. Student controls do not expose publishing, grading, certificate issuance or attendance-window management. Material/download paths are narrowly validated and private copies are bounded, measured and cleaned up.

Commands execute once. Lost quiz/submission/check-in results require authoritative readback and an explicit decision before another command; entered answers/text are retained. A successful write remains acknowledged if its follow-up read fails. Assignment registration pins its next submission revision and exact byte proof; only usable files enter the submitted snapshot. Session/context disposal clears private read models and late results cannot revive the previous screen.

Attendance supports manual codes and native QR adapter source. Android uses the official Google code scanner 16.1.0; iOS uses QR-only AVFoundation with camera permission and cancellation/background cleanup. A scan fills a validated `edp-attendance:` payload and requires a separate explicit **Check in** action. Missing/denied camera capabilities preserve manual entry. See the [native matrix and dependency decision](../testing/native-attendance-acceptance.md).

English/Tamil messages and supported state labels use generated ARB localization. Object links pin organization/course/lesson context, reload current authorized data and show an unavailable state rather than selecting a different course. Public certificate links use the minimal verification API and can refresh revocation status.

The audit fixed parent notification during attachment construction, teardown `setState`, redundant file-lock notifications and retained private read models after controller disposal. The scanner/channel tests reject foreign URLs, malformed/oversized payloads, newline suffixes and denied camera access; widget checks establish that scanning alone never sends attendance.

## Evidence

- `python scripts/run-mobile-api-tests.py --slice learning`: **2 real Flutter/API journey cases passed**, including lesson prerequisite rejection, quiz fail/pass, assignment registration/PUT/controlled scan/private download/submission/frozen evidence, trainer grade readback, certificate issuance/verification QR, schedule and attendance replay/peer denial.
- Guarded record `.local/mobile-api-learning-512e4f1a.json`; logs `.tool-cache/mobile-api-learning-512e4f1a`. One controlled synthetic scan completed; owned API/Flutter processes stopped and the credential fixture was removed.
- Exported schema SHA-256: `6ea0802b512a5cc1b47f66e19cc718896a70c8e944c0f021d20570e143e9d2d3`.
- Student repository/controller/file tests and the English/Tamil widget cases pass in the integrated mobile checks. Tamil 320-pixel/large-text golden: `apps/mobile/test/goldens/m03-tamil-320.png`. The integrated 18-case domain recovery/layout run also passed.

The slice adds no database schema: it consumes the existing learning/files/program/attendance/certificate services. Fixture permissions, collection and scanner control exist only in the guarded synthetic runner. Real collection remains disabled in ordinary environments. A direct controlled scan function does not establish Redis/worker/ClamD behavior.

## Remaining validation

The final native source must compile and run on both platforms. Android SDK/JDK/toolchain preparation and iOS Xcode/macOS availability are environmental gates; no historical build closes them. Camera/module/permission, secure storage, physical QR scans, protected-file lifecycle, process death, TalkBack/VoiceOver, approved app identity/signing and OS domain association require their real environments. Read-only models remain in memory; persistent/offline private learning content is not enabled without an approved policy.
