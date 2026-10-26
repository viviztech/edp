import 'package:edp_mobile/features/identity/providers.dart';

/// Guest layout checks do not exercise native secure storage or network I/O.
class GuestSession extends SessionStateController {
  @override
  SessionState build() => const SessionState(status: SessionStatus.signedOut);
  @override
  Future<void> restoreAtEntry() async {}
}
