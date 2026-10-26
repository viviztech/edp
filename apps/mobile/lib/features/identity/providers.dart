import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import 'auth_repository.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  const base = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );
  final uri = Uri.parse(base);
  if (!{'http', 'https'}.contains(uri.scheme) ||
      uri.host.isEmpty ||
      uri.userInfo.isNotEmpty ||
      uri.hasQuery ||
      uri.hasFragment ||
      uri.path != '/api/v1' ||
      (kReleaseMode && uri.scheme != 'https')) {
    throw StateError(
      'API_BASE_URL must be an HTTP(S) API base; release requires HTTPS',
    );
  }
  final dio = Dio(
    BaseOptions(
      baseUrl: base,
      connectTimeout: const Duration(seconds: 8),
      receiveTimeout: const Duration(seconds: 10),
      sendTimeout: const Duration(seconds: 10),
      followRedirects: false,
      maxRedirects: 0,
    ),
  );
  ref.onDispose(dio.close);
  return AuthRepository(dio, SecureTokenStore(const FlutterSecureStorage()));
});

final domainApiProvider = Provider<DomainApi>(
  (ref) => DomainApi(ref.watch(authRepositoryProvider)),
);

enum SessionStatus { restoring, signedOut, authenticated, unavailable }

class SessionState {
  final SessionStatus status;
  final UserProfile? profile;
  final ApiFailure? failure;
  final int generation;
  const SessionState({
    required this.status,
    this.profile,
    this.failure,
    this.generation = 0,
  });
}

final sessionStateProvider =
    NotifierProvider<SessionStateController, SessionState>(
      SessionStateController.new,
    );

final sessionEpochProvider = Provider<int>(
  (ref) => ref.watch(sessionStateProvider).generation,
);

class SessionStateController extends Notifier<SessionState> {
  bool _entered = false;
  bool _disposed = false;
  Future<void>? _restoring;
  int _operation = 0;

  @override
  SessionState build() {
    _disposed = false;
    final identity = ref.watch(authRepositoryProvider);
    final remove = identity.onInvalidated(invalidate);
    ref.onDispose(() {
      _disposed = true;
      remove();
    });
    return const SessionState(status: SessionStatus.restoring);
  }

  void invalidate() {
    if (_disposed) return;
    _operation++;
    state = SessionState(
      status: SessionStatus.signedOut,
      generation: state.generation + 1,
    );
  }

  Future<void> restoreAtEntry() {
    if (_restoring != null) return _restoring!;
    if (_entered) return Future.value();
    _entered = true;
    final pending = _restore();
    _restoring = pending;
    return pending.whenComplete(() => _restoring = null);
  }

  Future<void> retryRestore() {
    _entered = false;
    return restoreAtEntry();
  }

  Future<void> _restore() async {
    final operation = ++_operation;
    state = SessionState(
      status: SessionStatus.restoring,
      generation: state.generation,
    );
    try {
      final profile = await ref.read(authRepositoryProvider).restore();
      if (_disposed || operation != _operation) return;
      state = SessionState(
        status: profile == null
            ? SessionStatus.signedOut
            : SessionStatus.authenticated,
        profile: profile,
        generation: state.generation + 1,
      );
    } catch (error) {
      if (_disposed || operation != _operation) return;
      _unavailable(error);
    }
  }

  void _unavailable(Object error) {
    final failure = error is ApiFailure
        ? error
        : const ApiFailure(
            'service_unavailable',
            kind: ApiFailureKind.unavailable,
          );
    state = SessionState(
      status:
          failure.kind == ApiFailureKind.invalidSession ||
              failure.code == 'invalid_session'
          ? SessionStatus.signedOut
          : SessionStatus.unavailable,
      failure: failure,
      generation: state.generation + 1,
    );
  }

  Future<void> refreshProfile() async {
    final operation = ++_operation;
    try {
      final profile = await ref.read(authRepositoryProvider).profile();
      if (_disposed || operation != _operation) return;
      state = SessionState(
        status: SessionStatus.authenticated,
        profile: profile,
        generation: state.generation + 1,
      );
    } catch (error) {
      if (!_disposed && operation == _operation) _unavailable(error);
      rethrow;
    }
  }

  Future<void> login(String email, String password) async {
    _entered = true;
    final identity = ref.read(authRepositoryProvider);
    // login clears prior credentials and emits invalidation synchronously/asynchronously.
    final pending = identity.login(email, password);
    final operation = _operation;
    try {
      final profile = await pending;
      if (_disposed || operation != _operation) return;
      state = SessionState(
        status: SessionStatus.authenticated,
        profile: profile,
        generation: state.generation + 1,
      );
    } catch (error) {
      if (!_disposed && operation == _operation) _unavailable(error);
      rethrow;
    }
  }

  Future<void> logout({bool all = false}) async {
    invalidate();
    await ref.read(authRepositoryProvider).logout(all: all);
  }
}

final sessionProvider = NotifierProvider<SessionController, UserProfile?>(
  SessionController.new,
);

class SessionController extends Notifier<UserProfile?> {
  @override
  UserProfile? build() => ref.watch(sessionStateProvider).profile;
  void invalidate() {
    ref.read(sessionStateProvider.notifier).invalidate();
  }

  Future<void> restore() async {
    await ref.read(sessionStateProvider.notifier).restoreAtEntry();
  }

  Future<void> login(String email, String password) async {
    await ref.read(sessionStateProvider.notifier).login(email, password);
  }

  Future<void> logout({bool all = false}) async {
    await ref.read(sessionStateProvider.notifier).logout(all: all);
  }
}
