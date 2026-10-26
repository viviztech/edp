# Native attendance QR acceptance

Prepared: 2026-10-24 (Asia/Calcutta). Use synthetic accounts and a dedicated test API on both Android and iOS. Dart channel/widget checks are local workflow evidence; they do not close a device row.

Android uses `com.google.android.gms:play-services-code-scanner:16.1.0`. Google Play services supplies the camera UI, so this adapter does not request the application's own camera permission or obtain image frames. The scanner's optional module may be downloaded before first use; missing services/module/network must preserve manual entry. This implementation decision follows the [official Google code scanner guide](https://developers.google.com/ml-kit/vision/barcode-scanning/code-scanner), replacing the plan's generic application-camera-permission assumption on Android. iOS uses [AVFoundation capture](https://developer.apple.com/documentation/avfoundation/setting-up-a-capture-session) and [camera permission](https://developer.apple.com/documentation/avfoundation/avcapturedevice/requestaccess(for:completionhandler:)) with QR-only metadata, an explicit cancel action and capture cleanup on background/dismissal.

The channel returns only `edp-attendance:` followed by 32–128 URL-safe token characters. Both boundaries reject other QR payloads. The app fills the attendance field after a successful scan and waits for the participant to press **Check in**; it never opens a scanned URL or automatically sends a check-in. No raw code or camera image belongs in logs or retained screenshots.

| Scenario | Required observation on each platform |
| --- | --- |
| Final native compilation | Build final adapter/dependency source; record SDK, JDK/Xcode, architecture and build mode |
| First camera action | Explicit participant action opens only the QR scanner; iOS explains and requests camera permission; Android uses Play services' camera UI |
| Permission/services/module unavailable | Localized failure and usable manual-code entry; no invented check-in success |
| Cancellation/background/foreground | Capture stops when appropriate; code/input is cleared on background; one completion callback; no late result reaches a different session |
| Valid attendance code | Only fills the form; separate explicit check-in stores the authorized server record |
| Foreign URL, other QR, malformed/oversized payload | Rejected without navigation, headers, raw error payload or token diagnostics |
| Expired/replayed/out-of-window code | API failure is displayed; authoritative attendance read establishes the result |
| Lost response | Read current attendance before another explicit command; no automatic replay |
| Logout/revocation/organization change | Old screen/scanner result cannot restore private state; next command reauthorizes |
| Accessibility | English/Tamil, large text, TalkBack/VoiceOver, focus, cancel and manual entry remain usable |

An Android debug build does not establish device capture, and Windows cannot compile or execute iOS. Approved application identifiers, signing, owned-domain associations, store submission and production release remain separate gates. Add observations and sanitized evidence before marking any row passed.
