import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:edp_mobile/features/cms/public_pages.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:edp_mobile/l10n/app_localizations.dart';

class ContentAdapter implements HttpClientAdapter {
  final List<RequestOptions> requests = [];
  bool missing = false;
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    requests.add(options);
    final page = {
      'id': 'id',
      'slug': 'eligibility',
      'title': 'Public title',
      'body': '<script>plain text</script>',
    };
    return ResponseBody.fromString(
      jsonEncode(
        missing
            ? {
                'error': {'code': 'not_found'},
              }
            : options.path.endsWith('/pages')
            ? {
                'items': [page],
                'next_cursor': 'cursor',
              }
            : page,
      ),
      missing ? 404 : 200,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  testWidgets('public page renders literal content and recovers after retry', (
    tester,
  ) async {
    final adapter = ContentAdapter()..missing = true;
    final dio = Dio()..httpClientAdapter = adapter;
    final repo = PublicPageRepository(
      dio,
      '11111111-1111-1111-1111-111111111111',
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [publicPageRepositoryProvider.overrideWithValue(repo)],
        child: const MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: PublicPages(slug: 'eligibility'),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('This page is unavailable.'), findsOneWidget);
    adapter.missing = false;
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.text('Public title'), findsOneWidget);
    expect(find.text('<script>plain text</script>'), findsOneWidget);
  });

  test(
    'public contract uses locale and cursor without staff credentials',
    () async {
      final adapter = ContentAdapter();
      final dio = Dio()..httpClientAdapter = adapter;
      final repo = PublicPageRepository(
        dio,
        '11111111-1111-1111-1111-111111111111',
      );
      final list = await repo.list('ta', cursor: 'previous');
      expect(list.items.single.title, 'Public title');
      expect(list.nextCursor, 'cursor');
      expect(adapter.requests.single.queryParameters['locale'], 'ta');
      expect(adapter.requests.single.queryParameters['cursor'], 'previous');
      expect(
        adapter.requests.single.headers.containsKey('Authorization'),
        false,
      );
      expect(
        (await repo.get('eligibility', 'en')).body,
        '<script>plain text</script>',
      );
      adapter.missing = true;
      await expectLater(
        repo.get('missing', 'ta'),
        throwsA(isA<DioException>()),
      );
    },
  );
  test('unconfigured public organization fails closed', () async {
    final repo = PublicPageRepository(Dio(), '');
    await expectLater(repo.list('en'), throwsStateError);
  });
}
