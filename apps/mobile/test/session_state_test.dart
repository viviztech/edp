import 'dart:async';

import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/features/identity/providers.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class SessionEmptyStore implements TokenStore {
  @override
  Future<String?> read() async => null;
  @override
  Future<void> write(String value) async {}
  @override
  Future<void> clear() async {}
}

class SessionFixture extends AuthRepository {
  int restores = 0;
  Future<UserProfile?> Function()? restoreResult;
  Future<void> Function()? logoutResult;
  bool offlineLogout = false;
  SessionFixture() : super(Dio(), SessionEmptyStore());
  @override
  Future<UserProfile?> restore() async {
    restores++;
    return restoreResult == null ? null : await restoreResult!();
  }

  @override
  Future<UserProfile> login(String email, String password) async =>
      UserProfile.fromJson({
        'id': email,
        'display_name': 'Synthetic',
        'email': email,
      });
  @override
  Future<void> logout({bool all = false}) async {
    await clearLocalSession();
    if (logoutResult != null) await logoutResult!();
    if (offlineLogout) {
      throw const AuthFailure('offline', kind: ApiFailureKind.offline);
    }
  }
}

void main() {
  test('a delayed logout receipt cannot sign out a newer account', () async {
    final pending = Completer<void>();
    final identity = SessionFixture()..logoutResult = () => pending.future;
    final container = ProviderContainer(
      overrides: [authRepositoryProvider.overrideWithValue(identity)],
    );
    addTearDown(container.dispose);
    final controller = container.read(sessionStateProvider.notifier);
    await controller.login('first@example.com', 'synthetic');
    final logout = controller.logout();
    await controller.login('second@example.com', 'synthetic');
    pending.complete();
    await logout;
    expect(container.read(sessionProvider)?.email, 'second@example.com');
    expect(
      container.read(sessionStateProvider).status,
      SessionStatus.authenticated,
    );
  });

  test(
    'application entry restores once and nullable account projection stays compatible',
    () async {
      final identity = SessionFixture();
      final container = ProviderContainer(
        overrides: [authRepositoryProvider.overrideWithValue(identity)],
      );
      addTearDown(container.dispose);
      final controller = container.read(sessionStateProvider.notifier);
      expect(
        container.read(sessionStateProvider).status,
        SessionStatus.restoring,
      );
      await Future.wait([
        controller.restoreAtEntry(),
        controller.restoreAtEntry(),
      ]);
      await container.read(sessionProvider.notifier).restore();
      expect(identity.restores, 1);
      expect(
        container.read(sessionStateProvider).status,
        SessionStatus.signedOut,
      );
      expect(container.read(sessionProvider), isNull);
      await container
          .read(sessionProvider.notifier)
          .login('synthetic@example.com', 'synthetic-only');
      expect(
        container.read(sessionStateProvider).status,
        SessionStatus.authenticated,
      );
      expect(container.read(sessionProvider)?.locale, 'en');
      expect(container.read(sessionProvider)?.grants, isEmpty);
    },
  );

  test(
    'transient restore does not invent a signed-in profile and can be retried',
    () async {
      final identity = SessionFixture()
        ..restoreResult = () async =>
            throw const ApiFailure('offline', kind: ApiFailureKind.offline);
      final container = ProviderContainer(
        overrides: [authRepositoryProvider.overrideWithValue(identity)],
      );
      addTearDown(container.dispose);
      final controller = container.read(sessionStateProvider.notifier);
      await controller.restoreAtEntry();
      expect(
        container.read(sessionStateProvider).status,
        SessionStatus.unavailable,
      );
      expect(container.read(sessionStateProvider).profile, isNull);
      identity.restoreResult = () async => null;
      await controller.retryRestore();
      expect(
        container.read(sessionStateProvider).status,
        SessionStatus.signedOut,
      );
      expect(identity.restores, 2);
    },
  );

  test(
    'missing native secure storage is unavailable, never an in-memory fallback',
    () async {
      final identity = SessionFixture()
        ..restoreResult = () async => throw MissingPluginException();
      final container = ProviderContainer(
        overrides: [authRepositoryProvider.overrideWithValue(identity)],
      );
      addTearDown(container.dispose);
      await container.read(sessionStateProvider.notifier).restoreAtEntry();
      expect(
        container.read(sessionStateProvider).status,
        SessionStatus.unavailable,
      );
      expect(container.read(sessionProvider), isNull);
    },
  );

  test(
    'repository invalidation clears identity and advances feature generation',
    () async {
      final identity = SessionFixture();
      final container = ProviderContainer(
        overrides: [authRepositoryProvider.overrideWithValue(identity)],
      );
      addTearDown(container.dispose);
      await container
          .read(sessionProvider.notifier)
          .login('synthetic@example.com', 'synthetic-only');
      final generation = container.read(sessionEpochProvider);
      await identity.clearLocalSession();
      expect(
        container.read(sessionStateProvider).status,
        SessionStatus.signedOut,
      );
      expect(container.read(sessionProvider), isNull);
      expect(container.read(sessionEpochProvider), greaterThan(generation));
    },
  );

  test('late restore cannot restore a revoked identity', () async {
    final pending = Completer<UserProfile?>();
    final identity = SessionFixture()..restoreResult = () => pending.future;
    final container = ProviderContainer(
      overrides: [authRepositoryProvider.overrideWithValue(identity)],
    );
    addTearDown(container.dispose);
    final restoration = container
        .read(sessionStateProvider.notifier)
        .restoreAtEntry();
    await identity.clearLocalSession();
    pending.complete(
      UserProfile.fromJson({
        'id': 'old',
        'display_name': 'Old',
        'email': 'old@example.com',
      }),
    );
    await restoration;
    expect(
      container.read(sessionStateProvider).status,
      SessionStatus.signedOut,
    );
    expect(container.read(sessionProvider), isNull);
  });

  test(
    'offline logout clears local view while reporting unconfirmed server revocation',
    () async {
      final identity = SessionFixture()..offlineLogout = true;
      final container = ProviderContainer(
        overrides: [authRepositoryProvider.overrideWithValue(identity)],
      );
      addTearDown(container.dispose);
      await container
          .read(sessionProvider.notifier)
          .login('synthetic@example.com', 'synthetic-only');
      await expectLater(
        container.read(sessionProvider.notifier).logout(),
        throwsA(isA<AuthFailure>()),
      );
      expect(
        container.read(sessionStateProvider).status,
        SessionStatus.signedOut,
      );
      expect(container.read(sessionProvider), isNull);
    },
  );
}
