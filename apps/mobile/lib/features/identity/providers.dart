import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'auth_repository.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  const base = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );
  final uri = Uri.parse(base);
  if (kReleaseMode && uri.scheme != 'https') {
    throw StateError('Release API_BASE_URL must use HTTPS');
  }
  final dio = Dio(
    BaseOptions(
      baseUrl: base,
      connectTimeout: const Duration(seconds: 8),
      receiveTimeout: const Duration(seconds: 10),
      sendTimeout: const Duration(seconds: 10),
    ),
  );
  ref.onDispose(dio.close);
  return AuthRepository(dio, SecureTokenStore(const FlutterSecureStorage()));
});

final sessionProvider = NotifierProvider<SessionController, UserProfile?>(
  SessionController.new,
);

class SessionController extends Notifier<UserProfile?> {
  @override
  UserProfile? build() => null;
  void invalidate() {
    state = null;
  }

  Future<void> restore() async {
    state = await ref.read(authRepositoryProvider).restore();
  }

  Future<void> login(String email, String password) async {
    state = await ref.read(authRepositoryProvider).login(email, password);
  }

  Future<void> logout({bool all = false}) async {
    try {
      await ref.read(authRepositoryProvider).logout(all: all);
    } finally {
      state = null;
    }
  }
}
