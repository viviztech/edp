import 'dart:async';

import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/features/identity/account_page.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/features/identity/providers.dart';
import 'package:edp_mobile/l10n/app_localizations.dart';
import 'package:edp_mobile/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class EmptyStore implements TokenStore {
  @override
  Future<String?> read() async => null;
  @override
  Future<void> write(String value) async {}
  @override
  Future<void> clear() async {}
}

class AccountFake extends AuthRepository {
  int logins = 0;
  bool loggedOut = false;
  AccountFake() : super(Dio(), EmptyStore());
  @override
  Future<UserProfile?> restore() async => null;
  @override
  Future<UserProfile> login(String email, String password) async {
    logins++;
    return UserProfile.fromJson({
      'id': 'synthetic',
      'display_name': 'Synthetic account',
      'email': email,
    });
  }

  @override
  Future<List<DeviceSession>> sessions() async => [];
  @override
  Future<void> logout({bool all = false}) async {
    loggedOut = true;
  }
}

UserProfile accountProfile(String id) => UserProfile.fromJson({
  'id': id,
  'display_name': 'Account $id',
  'email': '$id@example.com',
});

class RestoredAccountFake extends AccountFake {
  bool unavailable = false;
  bool offlineLogout = false;
  Future<List<DeviceSession>> Function()? sessionResult;
  @override
  Future<UserProfile?> restore() async {
    if (unavailable) {
      throw const ApiFailure('offline', kind: ApiFailureKind.offline);
    }
    return accountProfile('first');
  }

  @override
  Future<UserProfile> login(String email, String password) async =>
      accountProfile(email);

  @override
  Future<List<DeviceSession>> sessions() async =>
      sessionResult == null ? [] : await sessionResult!();

  @override
  Future<void> logout({bool all = false}) async {
    if (offlineLogout) {
      throw const AuthFailure('offline', kind: ApiFailureKind.offline);
    }
  }
}

Widget accountHarness(ProviderContainer container) => UncontrolledProviderScope(
  container: container,
  child: const MaterialApp(
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: AccountPage(),
  ),
);

void main() {
  testWidgets('unavailable restoration is explained and can be retried', (
    tester,
  ) async {
    final repository = RestoredAccountFake()..unavailable = true;
    final container = ProviderContainer(
      overrides: [authRepositoryProvider.overrideWithValue(repository)],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(accountHarness(container));
    await tester.pumpAndSettle();
    expect(
      find.text('Your account could not be restored. Retry or sign in.'),
      findsOneWidget,
    );
    repository.unavailable = false;
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.text('Account first'), findsOneWidget);
    expect(
      find.text('Your account could not be restored. Retry or sign in.'),
      findsNothing,
    );
  });

  testWidgets('device sessions never cross account or session generations', (
    tester,
  ) async {
    final repository = RestoredAccountFake()
      ..sessionResult = () async => [
        DeviceSession.fromJson({
          'id': 'first-device',
          'device_name': 'Private first device',
          'current': false,
        }),
      ];
    final container = ProviderContainer(
      overrides: [authRepositoryProvider.overrideWithValue(repository)],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(accountHarness(container));
    await tester.pumpAndSettle();
    expect(find.text('Private first device'), findsOneWidget);
    await container
        .read(sessionStateProvider.notifier)
        .login('second', 'synthetic');
    await tester.pumpAndSettle();
    expect(find.text('Private first device'), findsNothing);
    final pending = Completer<List<DeviceSession>>();
    repository.sessionResult = () => pending.future;
    await tester.tap(find.text('Retry'));
    await tester.pump();
    await container
        .read(sessionStateProvider.notifier)
        .login('third', 'synthetic');
    pending.complete([
      DeviceSession.fromJson({
        'id': 'second-device',
        'device_name': 'Private second device',
        'current': false,
      }),
    ]);
    await tester.pumpAndSettle();
    expect(find.text('Account third'), findsOneWidget);
    expect(find.text('Private second device'), findsNothing);
    expect(find.text('Private first device'), findsNothing);
  });

  testWidgets(
    'offline sign out reports that server revocation is unconfirmed',
    (tester) async {
      final repository = RestoredAccountFake()..offlineLogout = true;
      final container = ProviderContainer(
        overrides: [authRepositoryProvider.overrideWithValue(repository)],
      );
      addTearDown(container.dispose);
      await tester.pumpWidget(accountHarness(container));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Sign out'));
      await tester.pumpAndSettle();
      expect(container.read(sessionProvider), isNull);
      expect(
        find.textContaining('Server revocation could not be confirmed'),
        findsOneWidget,
      );
    },
  );

  testWidgets('account validates input, signs in and signs out', (
    tester,
  ) async {
    final repository = AccountFake();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authRepositoryProvider.overrideWithValue(repository)],
        child: const EdpApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Your account'));
    await tester.tap(find.text('Your account'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byType(TextFormField).at(0),
      'synthetic@example.com',
    );
    await tester.enterText(find.byType(TextFormField).at(1), 'short');
    await tester.ensureVisible(find.byType(FilledButton));
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();
    expect(repository.logins, 0);
    await tester.enterText(
      find.byType(TextFormField).at(1),
      'synthetic-input-only',
    );
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();
    expect(repository.logins, 1);
    expect(find.text('Synthetic account'), findsOneWidget);
    expect(find.text('No active devices.'), findsOneWidget);
    await tester.tap(find.text('Sign out'));
    await tester.pumpAndSettle();
    expect(repository.loggedOut, isTrue);
    expect(find.text('Synthetic account'), findsNothing);
    expect(find.byType(TextFormField), findsNWidgets(2));
  });
}
