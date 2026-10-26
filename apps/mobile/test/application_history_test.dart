import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/features/applications/application_history.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fixtures/application_fixture.dart';

const _nextId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';

class _NoTokens implements TokenStore {
  @override
  Future<void> clear() async {}
  @override
  Future<String?> read() async => null;
  @override
  Future<void> write(String value) async {}
}

class _HistoryApi extends DomainApi {
  Object? payload;
  int requests = 0;
  _HistoryApi() : super(AuthRepository(Dio(), _NoTokens()));
  @override
  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    requests++;
    return payload;
  }
}

Map<String, dynamic> _entry(String id) => {
  'id': id,
  'organization_id': applicationOrg,
  'organization_name': 'Synthetic organization',
  'cycle_id': applicationCycle,
  'cycle_name_en': 'Synthetic intake',
  'cycle_name_ta': 'சோதனை சேர்க்கை',
  'application_number': null,
  'state': 'draft',
  'version': 1,
};

ApplicationHistoryBatch _batch({String? cursor, String id = applicationId}) =>
    ApplicationHistoryBatch.fromJson({
      'items': [_entry(id)],
      'next_cursor': cursor,
    });

class _HistoryRepository extends ApplicationHistoryRepository {
  final List<String?> cursors = [];
  bool failed = false;
  _HistoryRepository() : super(_HistoryApi());
  @override
  Future<ApplicationHistoryBatch> list({String? cursor}) async {
    cursors.add(cursor);
    if (cursor == null) return _batch(cursor: applicationId);
    if (!failed) {
      failed = true;
      throw const ApiFailure('offline', kind: ApiFailureKind.offline);
    }
    return _batch(id: _nextId);
  }
}

void main() {
  test(
    'history validates cursors and rejects duplicate or cycling pages',
    () async {
      final api = _HistoryApi();
      final repository = ApplicationHistoryRepository(api);
      await expectLater(
        repository.list(cursor: 'hostile'),
        throwsA(isA<ApiFailure>()),
      );
      expect(api.requests, 0);
      api.payload = {
        'items': [_entry(applicationId), _entry(applicationId)],
        'next_cursor': null,
      };
      await expectLater(repository.list(), throwsA(isA<ApiFailure>()));
      api.payload = {
        'items': [_entry(_nextId)],
        'next_cursor': applicationId,
      };
      await expectLater(
        repository.list(cursor: applicationId),
        throwsA(isA<ApiFailure>()),
      );
      api.payload = {
        'items': [_entry(applicationId)],
        'next_cursor': null,
      };
      final batch = await repository.list();
      expect(batch.items.single.cycleNameTa, 'சோதனை சேர்க்கை');
      expect(() => batch.items.clear(), throwsUnsupportedError);
    },
  );

  testWidgets('history retries the failed page and preserves earlier entries', (
    tester,
  ) async {
    final repository = _HistoryRepository();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          applicationHistoryRepositoryProvider.overrideWithValue(repository),
        ],
        child: const MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: Locale('ta'),
          home: Scaffold(
            body: SingleChildScrollView(child: ApplicationHistory()),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('சோதனை சேர்க்கை'), findsOneWidget);
    final context = tester.element(find.byType(ApplicationHistory));
    final text = AppLocalizations.of(context)!;
    await tester.tap(find.text(text.cmsMore));
    await tester.pumpAndSettle();
    expect(find.text('சோதனை சேர்க்கை'), findsOneWidget);
    await tester.tap(find.text(text.cmsRetry));
    await tester.pumpAndSettle();
    expect(repository.cursors, [null, applicationId, applicationId]);
    expect(find.text('சோதனை சேர்க்கை'), findsNWidgets(2));
  });
}
