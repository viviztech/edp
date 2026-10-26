import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/features/applications/application_history.dart';
import 'package:edp_mobile/features/applications/application_models.dart';
import 'package:edp_mobile/features/applications/application_page.dart';
import 'package:edp_mobile/features/applications/application_repository.dart';
import 'package:edp_mobile/features/identity/account_page.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/features/identity/providers.dart';
import 'package:edp_mobile/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'fixtures/application_fixture.dart';

const _intake =
    '/applications?organization=$applicationOrg&cycle=$applicationCycle';

class _NoNetwork implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) => throw StateError('Navigation tests must not send network requests');

  @override
  void close({bool force = false}) {}
}

class _NoNativeStore implements TokenStore {
  @override
  Future<String?> read() async => null;
  @override
  Future<void> write(String value) async {}
  @override
  Future<void> clear() async {}
}

UserProfile _applicant() => UserProfile.fromJson({
  'id': 'zero-grant-applicant',
  'display_name': 'Synthetic applicant',
  'email': 'synthetic@example.com',
  'locale': 'en',
  'grants': <Object?>[],
});

class _Identity extends AuthRepository {
  final bool initiallySignedIn;
  int logins = 0;
  _Identity({this.initiallySignedIn = false})
    : super(Dio()..httpClientAdapter = _NoNetwork(), _NoNativeStore());

  @override
  Future<UserProfile?> restore() async =>
      initiallySignedIn ? _applicant() : null;
  @override
  Future<UserProfile> login(String email, String password) async {
    logins++;
    return _applicant();
  }

  @override
  Future<List<DeviceSession>> sessions() async => [];
}

class _Applications extends ApplicationRepository {
  final List<(String, String)> reads = [];
  _Applications(super.api);
  @override
  Future<List<ApplicationCycle>> cycles(String org) async => [
    ApplicationCycle.fromJson(applicationCycleJson()),
  ];
  @override
  Future<ApplicationRecord> read(String org, String cycle) async {
    reads.add((org, cycle));
    return applicationRecord();
  }

  @override
  Future<ApplicationReadiness> readiness(
    String org,
    ApplicationRecord record,
  ) async => ApplicationReadiness(record.version, true);
}

class _History extends ApplicationHistoryRepository {
  _History(super.api);
  @override
  Future<ApplicationHistoryBatch> list({String? cursor}) async =>
      ApplicationHistoryBatch.fromJson({'items': [], 'next_cursor': null});
}

class _Harness {
  final ProviderContainer container;
  final _Identity identity;
  final _Applications applications;
  _Harness(this.container, this.identity, this.applications);
  GoRouter get router => container.read(routerProvider);
  Uri get location => router.routeInformationProvider.value.uri;
}

Future<_Harness> _show(WidgetTester tester, {bool signedIn = false}) async {
  final identity = _Identity(initiallySignedIn: signedIn);
  final api = DomainApi(identity);
  final applications = _Applications(api);
  final container = ProviderContainer(
    overrides: [
      authRepositoryProvider.overrideWithValue(identity),
      applicationRepositoryProvider.overrideWithValue(applications),
      applicationHistoryRepositoryProvider.overrideWithValue(_History(api)),
    ],
  );
  addTearDown(container.dispose);
  addTearDown(identity.dio.close);
  await tester.pumpWidget(
    UncontrolledProviderScope(container: container, child: const EdpApp()),
  );
  await tester.pumpAndSettle();
  return _Harness(container, identity, applications);
}

String _accountNext(String destination) =>
    Uri(path: '/account', queryParameters: {'next': destination}).toString();

Future<void> _login(WidgetTester tester) async {
  await tester.enterText(
    find.byType(TextFormField).at(0),
    'synthetic@example.com',
  );
  await tester.enterText(
    find.byType(TextFormField).at(1),
    'synthetic-password-only',
  );
  final button = find.widgetWithText(FilledButton, 'Sign in');
  await tester.ensureVisible(button);
  await tester.tap(button);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
    'signed-out intake preserves organization and cycle through login',
    (tester) async {
      final harness = await _show(tester);
      harness.router.go(_intake);
      await tester.pumpAndSettle();
      expect(find.byType(ApplicationPage), findsNothing);
      expect(harness.applications.reads, isEmpty);
      await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
      await tester.pumpAndSettle();
      final accountUri = GoRouterState.of(
        tester.element(find.byType(AccountPage)),
      ).uri;
      expect(accountUri.path, '/account');
      expect(accountUri.queryParameters['next'], _intake);
      await _login(tester);
      expect(harness.identity.logins, 1);
      expect(harness.container.read(sessionProvider)!.grants, isEmpty);
      expect(harness.location.toString(), _intake);
      expect(find.byType(ApplicationPage), findsOneWidget);
      expect(harness.applications.reads, [(applicationOrg, applicationCycle)]);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('signed-in account entry forwards to its validated intake', (
    tester,
  ) async {
    final harness = await _show(tester, signedIn: true);
    harness.router.go(_accountNext(_intake));
    await tester.pumpAndSettle();
    expect(harness.identity.logins, 0);
    expect(harness.location.toString(), _intake);
    expect(find.byType(ApplicationPage), findsOneWidget);
    expect(harness.applications.reads, [(applicationOrg, applicationCycle)]);
    expect(tester.takeException(), isNull);
  });

  testWidgets('a validated next query on the open account route forwards', (
    tester,
  ) async {
    final harness = await _show(tester, signedIn: true);
    harness.router.go('/account');
    await tester.pumpAndSettle();
    expect(find.byType(AccountPage), findsOneWidget);
    harness.router.go(_accountNext(_intake));
    await tester.pumpAndSettle();
    expect(harness.location.toString(), _intake);
    expect(harness.applications.reads, [(applicationOrg, applicationCycle)]);
  });

  for (final (label, destination) in [
    ('external URL', 'https://untrusted.invalid/applications'),
    ('network path', '//untrusted.invalid/applications'),
    ('unsupported module', '/learn?organization=$applicationOrg'),
    ('unscoped cycle', '/applications?cycle=$applicationCycle'),
    (
      'extra token parameter',
      '/applications?organization=$applicationOrg&token=private',
    ),
    ('account loop', '/account'),
  ]) {
    testWidgets('signed-in account rejects $label as a next destination', (
      tester,
    ) async {
      final harness = await _show(tester, signedIn: true);
      final account = _accountNext(destination);
      harness.router.go(account);
      await tester.pumpAndSettle();
      expect(harness.location.toString(), account);
      expect(find.byType(AccountPage), findsOneWidget);
      expect(find.byType(ApplicationPage), findsNothing);
      expect(harness.applications.reads, isEmpty);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('unsupported next remains on account after a successful login', (
    tester,
  ) async {
    final harness = await _show(tester);
    final account = _accountNext('/learn?organization=$applicationOrg');
    harness.router.go(account);
    await tester.pumpAndSettle();
    await _login(tester);
    expect(harness.identity.logins, 1);
    expect(harness.location.toString(), account);
    expect(find.text('Synthetic applicant'), findsOneWidget);
    expect(harness.applications.reads, isEmpty);
    expect(tester.takeException(), isNull);
  });
}
