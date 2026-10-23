# EDP mobile foundation

One Flutter app with English/Tamil public CMS views and account registration, verification, login, password reset and session controls. The authentication repository includes secure refresh-token storage and single-flight rotation. Applicant, student and alumni domain workflows, deep links and native-device acceptance remain open; the existing secure-storage integration test still requires Android/iOS execution under ADR 0004.

See [mobile architecture](../../docs/mobile/mobile-architecture.md), [local setup](../../docs/deployment/local.md), [native acceptance](../../docs/testing/native-session-acceptance.md), the current [baseline verification plan](../../docs/sdlc/baseline-verification-plan.md) and its [verification report](../../docs/sdlc/baseline-verification-report.md). Local web/API acceptance does not close the native-device gates. Platform identifiers `com.example.edp_mobile` are development placeholders, not approved store identifiers.
