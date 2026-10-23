# Flutter architecture

One app; feature-first directories, Riverpod for state, GoRouter for navigation, Dio repositories for API access. Foundation includes account forms, secure token repository, single-flight refresh and session/device controls; student workflows remain planned.

Guest tabs Home/Programs/Opportunities/Resources/Account; applicant Home/Application/Updates/Resources/Profile; student Home/Learn/Opportunities/Support/Profile. Actual navigation follows server-authorized capabilities and enrollment state, never a locally chosen role. Mentor access pending policy.

The central session manager serializes refresh, uses OS secure storage for the refresh token and memory for the access token, revokes/clears on logout and surfaces expired sessions. Central error codes map to localized messages. ARB English/Tamil keys support scalable text and semantic labels. Planned deep links and push routes must reauthorize server objects. Environment/flavor contains the public API base only; no provider credentials. FCM is deferred until approved configuration. Planned read-only public/learning caching must exclude sensitive documents. Non-destructive retries are bounded; consequential domain writes must use server idempotency keys. The app-version endpoint and update policy remain planned. Android/iOS builds and on-device smoke are release gates; iOS requires macOS signing setup.

Flutter web builds are compile checks, not the supported secure-storage production channel; Next.js handles browser accounts. Native Android/iOS secure-storage and device tests remain required. On ambiguous refresh failure, clear the possibly consumed refresh token rather than replaying it. Logout clears local storage even if remote revocation cannot be confirmed; network failure is shown and other sessions can be revoked after reconnecting. Dart models currently implement the small generated OpenAPI subset manually; full Dart generator adoption remains pending evaluation.

Android manifest disables OS backup for application data so secure-storage credentials are not restored onto another device. Debug manifest alone permits cleartext traffic for the local emulator; release API configuration rejects non-HTTPS URLs. Native Android debug APK compilation passed; actual device lifecycle/secure-storage tests remain pending.

The [2026-10-23 baseline report](../sdlc/baseline-verification-report.md) records current available checks and unresolved dependency/CI gates. Phase 10's local web/API acceptance does not establish Flutter domain or native-device acceptance.
