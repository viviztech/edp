import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/core/navigation/destinations.dart';
import 'package:edp_mobile/features/applications/application_history.dart';
import 'package:edp_mobile/features/applications/application_models.dart';
import 'package:edp_mobile/features/applications/application_page.dart';
import 'package:edp_mobile/features/applications/application_repository.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/features/identity/providers.dart';
import 'package:edp_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'fixtures/application_fixture.dart';

class _Store implements TokenStore {
  @override
  Future<String?> read() async => null;
  @override
  Future<void> write(String value) async {}
  @override
  Future<void> clear() async {}
}

DomainApi _unusedApi() => DomainApi(AuthRepository(Dio(), _Store()));

class _Applications extends ApplicationRepository {
  _Applications() : super(_unusedApi());
  ApplicationRecord saved = applicationRecord();
  int saves = 0, submissions = 0;
  bool loseSave = false;
  @override
  Future<List<ApplicationCycle>> cycles(String org) async => [
    ApplicationCycle.fromJson(applicationCycleJson()),
  ];
  @override
  Future<ApplicationRecord> read(String org, String cycle) async =>
      org == applicationOrg
      ? saved
      : ApplicationRecord.fromJson(
          applicationRecordJson(org: org, answer: 'Other organization answer'),
        );
  @override
  Future<ApplicationReadiness> readiness(
    String org,
    ApplicationRecord record,
  ) async => ApplicationReadiness(record.version, true);
  @override
  Future<ApplicationRecord> save(
    String org,
    ApplicationRecord record,
    Map<String, String> answers,
  ) async {
    saves++;
    saved = applicationRecord(
      version: record.version + 1,
      answer: answers[applicationField]!,
    );
    if (loseSave) {
      loseSave = false;
      throw const ApiFailure(
        'request_timeout',
        kind: ApiFailureKind.timeout,
        outcome: CommandOutcome.uncertain,
      );
    }
    return saved;
  }

  @override
  Future<ApplicationRecord> submit(
    String org,
    ApplicationRecord record,
    Set<String> accepted,
  ) async {
    submissions++;
    return saved = applicationRecord(
      version: record.version + 1,
      answer: saved.answers[applicationField]!,
      state: 'submitted',
    );
  }
}

class _History extends ApplicationHistoryRepository {
  _History() : super(_unusedApi());
  @override
  Future<ApplicationHistoryBatch> list({String? cursor}) async =>
      ApplicationHistoryBatch.fromJson({'items': [], 'next_cursor': null});
}

class _Profile extends SessionController {
  @override
  UserProfile? build() => UserProfile.fromJson({
    'id': 'synthetic-owner',
    'display_name': 'Synthetic owner',
    'email': 'synthetic@example.com',
    'grants': [
      for (final (id, name) in [
        (applicationOrg, 'First organization'),
        (applicationOtherOrg, 'Second organization'),
      ])
        {
          'organization_id': id,
          'organization_name': name,
          'permissions': <String>[],
        },
    ],
  });
}

Future<GoRouter> _show(
  WidgetTester tester,
  _Applications repository, {
  String locale = 'en',
}) async {
  final router = GoRouter(
    initialLocation:
        '/applications?organization=$applicationOrg&cycle=$applicationCycle',
    routes: [
      GoRoute(
        path: '/',
        builder: (_, _) => const Scaffold(body: Text('Home')),
      ),
      GoRoute(
        path: '/applications',
        builder: (_, state) => ApplicationPage(
          key: ValueKey(state.uri.toString()),
          destination: MobileDestination.parse(state.uri.toString())!,
        ),
      ),
    ],
  );
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        applicationRepositoryProvider.overrideWithValue(repository),
        applicationHistoryRepositoryProvider.overrideWithValue(_History()),
        sessionProvider.overrideWith(_Profile.new),
      ],
      child: MaterialApp.router(
        locale: Locale(locale),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        routerConfig: router,
      ),
    ),
  );
  await tester.pumpAndSettle();
  return router;
}

Future<void> _tap(WidgetTester tester, String label) async {
  final target = find.text(label).last;
  await tester.ensureVisible(target);
  await tester.tap(target);
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() async {
    for (final family in ['Roboto', 'NotoSansTamil']) {
      await (FontLoader(
            family,
          )..addFont(rootBundle.load('assets/fonts/NotoSansTamil-Regular.ttf')))
          .load();
    }
  });

  testWidgets(
    'save, explicit submission confirmation, receipt and permitted history',
    (tester) async {
      final repository = _Applications();
      await _show(tester, repository);
      await tester.enterText(find.byType(TextField), 'Synthetic enterprise');
      await _tap(tester, 'Save draft');
      expect(repository.saves, 1);
      await _tap(tester, 'Synthetic declaration *');
      await _tap(tester, 'Synthetic consent *');
      await _tap(tester, 'Submit application');
      expect(repository.submissions, 0);
      await _tap(tester, 'Submit application');
      expect(repository.submissions, 1);
      expect(find.text('EDP-2026-00000001'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('Status history'),
        250,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('Status history'), findsOneWidget);
      expect(find.text('Submit application'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'lost save preserves text and never retries until explicit readback and decision',
    (tester) async {
      final repository = _Applications()..loseSave = true;
      await _show(tester, repository);
      await tester.enterText(find.byType(TextField), 'Preserve this input');
      await _tap(tester, 'Save draft');
      expect(repository.saves, 1);
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'Preserve this input',
      );
      await _tap(tester, 'Refresh saved record');
      expect(repository.saves, 1);
      expect(find.text('Saved version 2'), findsOneWidget);
      await _tap(tester, 'Keep my edits');
      await _tap(tester, 'Save draft');
      expect(repository.saves, 2);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'organization switch requires a decision and disposes the old editor',
    (tester) async {
      final repository = _Applications();
      final router = await _show(tester, repository);
      await tester.enterText(find.byType(TextField), 'Unsaved private text');
      await _tap(tester, 'Second organization');
      expect(find.byType(AlertDialog), findsOneWidget);
      await _tap(tester, 'Stay');
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'Unsaved private text',
      );
      await _tap(tester, 'Second organization');
      await _tap(tester, 'Leave');
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'Other organization answer',
      );
      expect(find.text('Unsaved private text'), findsNothing);
      expect(router.canPop(), isFalse);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('Tamil applicant layout fits 320 pixels with large text', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 850);
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.textScaleFactorTestValue = 1.4;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await _show(tester, _Applications(), locale: 'ta');
    await tester.enterText(find.byType(TextField), 'சோதனை தொழில்');
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/m01-tamil-320.png'),
    );
  });
}
