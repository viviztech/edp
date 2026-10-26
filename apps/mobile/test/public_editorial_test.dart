import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:edp_mobile/features/cms/public_editorial.dart';
import 'package:edp_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const organization = '11111111-1111-1111-1111-111111111111';

Map<String, dynamic> entry({
  String id = 'first',
  String kind = 'news',
  String slug = 'published-update',
  String title = 'Published update',
  String body = 'Summary',
}) => {'id': id, 'kind': kind, 'slug': slug, 'title': title, 'body': body};

ResponseBody response(Object body, {int status = 200}) =>
    ResponseBody.fromString(
      jsonEncode(body),
      status,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );

class EditorialAdapter implements HttpClientAdapter {
  final List<RequestOptions> requests = [];
  Future<ResponseBody> Function(RequestOptions) handler;

  EditorialAdapter(this.handler);

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) {
    requests.add(options);
    return handler(options);
  }

  @override
  void close({bool force = false}) {}
}

EditorialRepository repository(EditorialAdapter adapter) =>
    EditorialRepository(Dio()..httpClientAdapter = adapter, organization);

Widget app(
  EditorialRepository repository, {
  String kind = 'news',
  String? slug,
  Locale locale = const Locale('en'),
}) => ProviderScope(
  overrides: [editorialRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(
    locale: locale,
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: PublicEditorial(kind: kind, slug: slug),
  ),
);

void main() {
  test(
    'public editorial contract retains cursor, locale and full details',
    () async {
      final adapter = EditorialAdapter((options) async {
        if (options.path.endsWith('/editorial')) {
          return response({
            'items': [entry()],
            'next_cursor': 'next-id',
          });
        }
        return response({
          ...entry(),
          'starts_at': '2026-10-24T09:00:00Z',
          'ends_at': '2026-10-24T10:00:00Z',
        });
      });
      final repo = repository(adapter);
      final batch = await repo.list('news', 'ta', cursor: 'previous-id');
      expect(batch.items.single.title, 'Published update');
      expect(batch.nextCursor, 'next-id');
      expect(
        adapter.requests.single.path,
        '/public/organizations/$organization/editorial',
      );
      expect(adapter.requests.single.queryParameters, {
        'kind': 'news',
        'locale': 'ta',
        'limit': 25,
        'cursor': 'previous-id',
      });
      final detail = await repo.get('news', 'published-update', 'en');
      expect(detail.startsAt, DateTime.utc(2026, 10, 24, 9));
      expect(detail.endsAt, DateTime.utc(2026, 10, 24, 10));
      expect(
        adapter.requests.last.path,
        '/public/organizations/$organization/editorial/news/published-update',
      );
      expect(adapter.requests.last.queryParameters, {'locale': 'en'});
      for (final request in adapter.requests) {
        expect(request.headers.containsKey('Authorization'), isFalse);
        expect(request.headers.containsKey('X-BFF-Key'), isFalse);
      }
    },
  );

  test(
    'unconfigured organization and unsupported paths fail before a request',
    () async {
      final adapter = EditorialAdapter((_) async => response({}));
      final dio = Dio()..httpClientAdapter = adapter;
      await expectLater(
        EditorialRepository(dio, '').list('news', 'en'),
        throwsStateError,
      );
      final repo = EditorialRepository(dio, organization);
      await expectLater(repo.list('private', 'en'), throwsStateError);
      await expectLater(repo.get('news', '../staff', 'en'), throwsStateError);
      expect(adapter.requests, isEmpty);
    },
  );

  testWidgets('pagination keeps prior results and retries the same cursor', (
    tester,
  ) async {
    var failNextPage = true;
    final adapter = EditorialAdapter((options) async {
      if (options.queryParameters['cursor'] != null) {
        if (failNextPage) return response({}, status: 503);
        return response({
          'items': [
            entry(id: 'second', slug: 'second-update', title: 'Second update'),
          ],
          'next_cursor': null,
        });
      }
      return response({
        'items': [entry()],
        'next_cursor': 'page-two',
      });
    });
    await tester.pumpWidget(app(repository(adapter)));
    await tester.pumpAndSettle();
    expect(find.text('News'), findsOneWidget);
    await tester.tap(find.text('Load more'));
    await tester.pumpAndSettle();
    expect(find.text('Published update'), findsOneWidget);
    expect(find.text('This page is unavailable.'), findsOneWidget);
    failNextPage = false;
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.text('Published update'), findsOneWidget);
    expect(find.text('Second update'), findsOneWidget);
    expect(find.text('Load more'), findsNothing);
    expect(find.text('This page is unavailable.'), findsNothing);
    expect(adapter.requests.skip(1).map((r) => r.queryParameters['cursor']), [
      'page-two',
      'page-two',
    ]);
  });

  testWidgets(
    'item opens complete published detail and preserves list on back',
    (tester) async {
      final adapter = EditorialAdapter((options) async {
        if (options.path.endsWith('/editorial')) {
          return response({
            'items': [entry()],
            'next_cursor': null,
          });
        }
        return response({
          ...entry(
            body:
                '<script>Literal full detail, not executable markup.</script>',
          ),
          'starts_at': '2026-10-24T09:00:00Z',
          'ends_at': '2026-10-24T10:00:00Z',
        });
      });
      await tester.pumpWidget(app(repository(adapter)));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Published update'));
      await tester.pumpAndSettle();
      expect(find.byType(SelectableText), findsOneWidget);
      expect(
        find.text(
          '<script>Literal full detail, not executable markup.</script>',
        ),
        findsOneWidget,
      );
      expect(find.textContaining('Starts:'), findsOneWidget);
      expect(find.textContaining('Ends:'), findsOneWidget);
      expect(
        adapter.requests.last.path.endsWith('/news/published-update'),
        isTrue,
      );
      await tester.pageBack();
      await tester.pumpAndSettle();
      expect(find.text('Summary'), findsOneWidget);
      expect(adapter.requests, hasLength(2));
    },
  );

  testWidgets('list and missing detail expose an explicit retry', (
    tester,
  ) async {
    var available = false;
    final adapter = EditorialAdapter((options) async {
      if (!available) return response({}, status: 404);
      if (options.path.endsWith('/editorial')) {
        return response({
          'items': [entry()],
          'next_cursor': null,
        });
      }
      return response(entry(body: 'Complete recovered detail'));
    });
    final repo = repository(adapter);
    await tester.pumpWidget(app(repo));
    await tester.pumpAndSettle();
    expect(find.text('This page is unavailable.'), findsOneWidget);
    available = true;
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.text('Published update'), findsOneWidget);

    available = false;
    await tester.pumpWidget(app(repo, slug: 'published-update'));
    await tester.pumpAndSettle();
    expect(find.text('Summary'), findsNothing);
    expect(find.text('This page is unavailable.'), findsOneWidget);
    available = true;
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.text('Complete recovered detail'), findsOneWidget);
  });

  testWidgets('English and Tamil empty states use localized kind labels', (
    tester,
  ) async {
    final adapter = EditorialAdapter(
      (_) async => response({'items': <Object>[], 'next_cursor': null}),
    );
    final repo = repository(adapter);
    await tester.pumpWidget(app(repo, kind: 'event'));
    await tester.pumpAndSettle();
    expect(find.text('Events'), findsOneWidget);
    expect(find.text('No published items yet.'), findsOneWidget);
    await tester.pumpWidget(
      app(repo, kind: 'event', locale: const Locale('ta')),
    );
    await tester.pumpAndSettle();
    expect(find.text('நிகழ்வுகள்'), findsOneWidget);
    expect(find.text('வெளியிடப்பட்ட தகவல்கள் இன்னும் இல்லை.'), findsOneWidget);
    expect(adapter.requests.last.queryParameters['locale'], 'ta');
    expect(find.text('No published items yet.'), findsNothing);
    expect(editorialKindTitle('faq', 'en'), 'FAQs');
    expect(editorialKindTitle('testimonial', 'ta'), 'பங்கேற்பாளர் கருத்துகள்');
  });

  testWidgets(
    'late results for a previous kind cannot replace current content',
    (tester) async {
      final firstRequest = Completer<ResponseBody>();
      final adapter = EditorialAdapter((options) async {
        if (options.queryParameters['kind'] == 'news') {
          return firstRequest.future;
        }
        return response({
          'items': [entry(kind: 'faq', title: 'Current question')],
          'next_cursor': null,
        });
      });
      final repo = repository(adapter);
      await tester.pumpWidget(app(repo));
      await tester.pump();
      await tester.pumpWidget(app(repo, kind: 'faq'));
      await tester.pumpAndSettle();
      expect(find.text('Current question'), findsOneWidget);
      firstRequest.complete(
        response({
          'items': [entry()],
          'next_cursor': null,
        }),
      );
      await tester.pumpAndSettle();
      expect(find.text('Current question'), findsOneWidget);
      expect(find.text('Published update'), findsNothing);
    },
  );

  testWidgets('late prior-language failure cannot hide the translated detail', (
    tester,
  ) async {
    final englishRequest = Completer<ResponseBody>();
    final adapter = EditorialAdapter((options) async {
      if (options.queryParameters['locale'] == 'en') {
        return englishRequest.future;
      }
      return response(entry(title: 'தமிழ் செய்தி', body: 'முழு விவரம்'));
    });
    final repo = repository(adapter);
    await tester.pumpWidget(app(repo, slug: 'published-update'));
    await tester.pump();
    await tester.pumpWidget(
      app(repo, slug: 'published-update', locale: const Locale('ta')),
    );
    await tester.pumpAndSettle();
    expect(find.text('முழு விவரம்'), findsOneWidget);
    englishRequest.complete(response({}, status: 503));
    await tester.pumpAndSettle();
    expect(find.text('முழு விவரம்'), findsOneWidget);
    final localized = AppLocalizations.of(
      tester.element(find.byType(PublicEditorial)),
    )!;
    expect(find.text(localized.cmsUnavailable), findsNothing);
    expect(find.byType(TextButton), findsNothing);
  });
}
