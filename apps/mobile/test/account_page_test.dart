import 'package:dio/dio.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/features/identity/providers.dart';
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

void main() {
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
