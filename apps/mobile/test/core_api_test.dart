import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/features/identity/providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class ApiMemoryStore implements TokenStore {
  String? value;
  @override
  Future<String?> read() async => value;
  @override
  Future<void> write(String value) async => this.value = value;
  @override
  Future<void> clear() async => value = null;
}

typedef ApiHandler = FutureOr<ResponseBody> Function(RequestOptions options);

class ControlledAdapter implements HttpClientAdapter {
  final ApiHandler handler;
  final List<RequestOptions> requests = [];
  ControlledAdapter(this.handler);
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return handler(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody jsonResponse(
  Object? body, [
  int status = 200,
  Map<String, List<String>>? headers,
]) => ResponseBody.fromString(
  jsonEncode(body),
  status,
  headers: {
    Headers.contentTypeHeader: ['application/json'],
    ...?headers,
  },
);

Map<String, dynamic> apiProfile() => {
  'id': 'owner',
  'display_name': 'Synthetic owner',
  'email': 'owner@example.com',
  'locale': 'ta',
  'grants': [
    {
      'organization_id': 'primary',
      'organization_name': 'Primary',
      'permissions': ['participant.self'],
    },
    {
      'organization_id': 'other',
      'organization_name': 'Other',
      'permissions': ['crm.lead.view'],
    },
  ],
};

ResponseBody? authResponse(RequestOptions options) => switch (options.path) {
  '/auth/login' => jsonResponse({
    'access_token': 'old-access',
    'refresh_token': 'old-refresh',
  }),
  '/auth/me' => jsonResponse(apiProfile()),
  _ => null,
};

void main() {
  test(
    'logout erases stored credentials before waiting for server revocation',
    () async {
      final pending = Completer<ResponseBody>();
      final revoking = Completer<void>();
      final adapter = ControlledAdapter((options) {
        if (options.path == '/auth/logout') {
          revoking.complete();
          return pending.future;
        }
        return authResponse(options)!;
      });
      final store = ApiMemoryStore();
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        store,
      );
      await identity.login('owner@example.com', 'synthetic-only-password');
      final logout = identity.logout();
      await revoking.future;
      expect(store.value, isNull);
      expect(await identity.restore(), isNull);
      pending.complete(jsonResponse(null, 204));
      await logout;
      expect(
        adapter.requests.where((item) => item.path == '/auth/refresh'),
        isEmpty,
      );
    },
  );

  test(
    'a superseded login cannot install another account credential',
    () async {
      final adapter = ControlledAdapter((options) {
        if (options.path == '/auth/login') {
          final account = (options.data as Map)['email'];
          return jsonResponse({
            'access_token': '$account-access',
            'refresh_token': '$account-refresh',
          });
        }
        return jsonResponse({
          'id': options.headers['Authorization'],
          'display_name': 'Synthetic account',
          'email': 'synthetic@example.com',
        });
      });
      final store = ApiMemoryStore();
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        store,
      );
      final first = identity.login('first', 'synthetic-only-password');
      final rejected = expectLater(
        first,
        throwsA(
          isA<AuthFailure>().having(
            (error) => error.outcome,
            'outcome',
            CommandOutcome.notSent,
          ),
        ),
      );
      final second = await identity.login('second', 'synthetic-only-password');
      await rejected;
      expect(second.id, 'Bearer second-access');
      expect(store.value, 'second-refresh');
      expect(
        adapter.requests.where((request) => request.path == '/auth/login'),
        hasLength(1),
      );
      expect((await identity.profile()).id, second.id);
    },
  );

  test(
    'a new account does not join refresh rotation from an old session',
    () async {
      final oldRefresh = Completer<ResponseBody>();
      final refreshing = Completer<void>();
      var rotations = 0;
      final adapter = ControlledAdapter((options) {
        if (options.path == '/auth/login') {
          final account = (options.data as Map)['email'];
          return jsonResponse({
            'access_token': '$account-access',
            'refresh_token': '$account-refresh',
          });
        }
        if (options.path == '/auth/me') return jsonResponse(apiProfile());
        if (options.path == '/auth/refresh') {
          rotations++;
          if ((options.data as Map)['token'] == 'first-refresh') {
            refreshing.complete();
            return oldRefresh.future;
          }
          return jsonResponse({
            'access_token': 'second-rotated-access',
            'refresh_token': 'second-rotated-refresh',
          });
        }
        if (options.headers['Authorization'] !=
            'Bearer second-rotated-access') {
          return jsonResponse({
            'error': {'code': 'invalid_session'},
          }, 401);
        }
        return jsonResponse({'owned': true});
      });
      final store = ApiMemoryStore();
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        store,
      );
      await identity.login('first', 'synthetic-only-password');
      final rejected = expectLater(
        DomainApi(identity).get('/one'),
        throwsA(isA<ApiFailure>()),
      );
      await refreshing.future;
      await identity.login('second', 'synthetic-only-password');
      final second = DomainApi(identity).get('/two');
      await Future<void>.delayed(Duration.zero);
      oldRefresh.complete(
        jsonResponse({
          'access_token': 'first-rotated-access',
          'refresh_token': 'first-rotated-refresh',
        }),
      );
      expect((await second)['owned'], isTrue);
      await rejected;
      expect(rotations, 2);
      expect(store.value, 'second-rotated-refresh');
    },
  );

  test(
    'failed streamed read cancels its body before authentication recovery',
    () async {
      var cancelled = 0;
      final denied = StreamController<Uint8List>(onCancel: () => cancelled++);
      addTearDown(denied.close);
      final adapter = ControlledAdapter((options) {
        final auth = authResponse(options);
        if (auth != null) return auth;
        if (options.path == '/auth/refresh') {
          return jsonResponse({
            'access_token': 'new-access',
            'refresh_token': 'new-refresh',
          });
        }
        if (options.headers['Authorization'] == 'Bearer old-access') {
          return ResponseBody(denied.stream, 401);
        }
        return ResponseBody.fromBytes([42], 200);
      });
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        ApiMemoryStore(),
      );
      await identity.login('owner@example.com', 'synthetic-only-password');
      expect(await DomainApi(identity).requestBytes('/content'), [42]);
      expect(cancelled, 1);
    },
  );

  test(
    'profile decodes locale and organization-scoped grants without role inference',
    () {
      final profile = UserProfile.fromJson(apiProfile());
      expect(profile.locale, 'ta');
      expect(profile.hasPermission('primary', 'participant.self'), isTrue);
      expect(profile.hasPermission('other', 'participant.self'), isFalse);
      expect(profile.hasPermission('primary', 'crm.lead.view'), isFalse);
      expect(() => profile.grants.clear(), throwsUnsupportedError);
    },
  );

  test(
    'protected feature reads share one refresh and public requests have no bearer',
    () async {
      var refreshes = 0;
      final adapter = ControlledAdapter((options) async {
        final auth = authResponse(options);
        if (auth != null) return auth;
        if (options.path == '/auth/refresh') {
          refreshes++;
          await Future<void>.delayed(const Duration(milliseconds: 5));
          return jsonResponse({
            'access_token': 'new-access',
            'refresh_token': 'new-refresh',
          });
        }
        if (options.path == '/public/content') {
          expect(options.headers.containsKey('Authorization'), isFalse);
          return jsonResponse({'items': []});
        }
        if (options.headers['Authorization'] == 'Bearer old-access') {
          return jsonResponse({
            'error': {'code': 'invalid_session'},
          }, 401);
        }
        return jsonResponse({'owned': true});
      });
      final dio = Dio()..httpClientAdapter = adapter;
      final store = ApiMemoryStore();
      final identity = AuthRepository(dio, store);
      await identity.login('owner@example.com', 'synthetic-only-password');
      final api = DomainApi(identity);
      final result = await Future.wait([api.get('/one'), api.get('/two')]);
      expect(result.every((item) => item['owned'] == true), isTrue);
      expect(refreshes, 1);
      expect(store.value, 'new-refresh');
      await dio.get<dynamic>('/public/content');
      expect(
        adapter.requests
            .where((request) => request.path != '/public/content')
            .every((request) => !request.followRedirects),
        isTrue,
      );
    },
  );

  test(
    'real identity login through central controller survives its own credential invalidation',
    () async {
      final adapter = ControlledAdapter((options) => authResponse(options)!);
      final store = ApiMemoryStore();
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        store,
      );
      final container = ProviderContainer(
        overrides: [authRepositoryProvider.overrideWithValue(identity)],
      );
      addTearDown(container.dispose);
      await container.read(sessionStateProvider.notifier).restoreAtEntry();
      await container
          .read(sessionStateProvider.notifier)
          .login('owner@example.com', 'synthetic-only-password');
      expect(
        container.read(sessionStateProvider).status,
        SessionStatus.authenticated,
      );
      expect(container.read(sessionProvider)?.locale, 'ta');
      expect(store.value, 'old-refresh');
    },
  );

  test('401 recovers authentication but never replays a command', () async {
    var commands = 0;
    var refreshes = 0;
    final adapter = ControlledAdapter((options) {
      final auth = authResponse(options);
      if (auth != null) return auth;
      if (options.path == '/auth/refresh') {
        refreshes++;
        return jsonResponse({
          'access_token': 'new-access',
          'refresh_token': 'new-refresh',
        });
      }
      if (options.method == 'POST') {
        commands++;
        return jsonResponse({
          'error': {'code': 'invalid_session'},
        }, 401);
      }
      return jsonResponse({'revision': 4});
    });
    final identity = AuthRepository(
      Dio()..httpClientAdapter = adapter,
      ApiMemoryStore(),
    );
    await identity.login('owner@example.com', 'synthetic-only-password');
    final api = DomainApi(identity);
    await expectLater(
      api.post('/submit', data: {'expected_version': 3}),
      throwsA(
        isA<ApiFailure>().having(
          (error) => error.outcome,
          'outcome',
          CommandOutcome.rejected,
        ),
      ),
    );
    expect(commands, 1);
    expect(refreshes, 1);
    expect((await api.get('/owned'))['revision'], 4);
  });

  test(
    'lost command response is uncertain with no automatic resend or sensitive diagnostics',
    () async {
      var commands = 0;
      final adapter = ControlledAdapter((options) {
        final auth = authResponse(options);
        if (auth != null) return auth;
        commands++;
        throw DioException(
          requestOptions: options,
          type: DioExceptionType.receiveTimeout,
          message: 'private source details must not leave the transport',
        );
      });
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        ApiMemoryStore(),
      );
      await identity.login('owner@example.com', 'synthetic-only-password');
      try {
        await DomainApi(
          identity,
        ).post('/submit', data: {'private': 'secret-body'});
        fail('Expected timeout');
      } on ApiFailure catch (error) {
        expect(error.kind, ApiFailureKind.timeout);
        expect(error.uncertain, isTrue);
        expect(error.toString(), isNot(contains('secret')));
        expect(error.toString(), isNot(contains('private')));
      }
      expect(commands, 1);
    },
  );

  test(
    'temporary failure after a safe refresh preserves the rotated credential',
    () async {
      final store = ApiMemoryStore();
      final adapter = ControlledAdapter((options) {
        final auth = authResponse(options);
        if (auth != null) return auth;
        if (options.path == '/auth/refresh') {
          return jsonResponse({
            'access_token': 'new-access',
            'refresh_token': 'new-refresh',
          });
        }
        return jsonResponse({
          'error': {'code': 'service_unavailable'},
        }, options.headers['Authorization'] == 'Bearer old-access' ? 401 : 503);
      });
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        store,
      );
      await identity.login('owner@example.com', 'synthetic-only-password');
      await expectLater(
        DomainApi(identity).get('/owned'),
        throwsA(isA<ApiFailure>()),
      );
      expect(store.value, 'new-refresh');
    },
  );

  test(
    'unsafe paths, caller credentials and redirects cannot forward bearer tokens',
    () async {
      final adapter = ControlledAdapter(
        (options) => jsonResponse(null, 302, {
          'location': ['https://untrusted.invalid'],
        }),
      );
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        ApiMemoryStore(),
      );
      final api = DomainApi(identity);
      for (final path in [
        'https://untrusted.invalid',
        '//untrusted.invalid',
        '/one/../two',
        '/%2e%2e/two',
        '/one?token=value',
        '/one\\two',
      ]) {
        await expectLater(
          api.get(path),
          throwsA(
            isA<ApiFailure>().having(
              (error) => error.outcome,
              'outcome',
              CommandOutcome.notSent,
            ),
          ),
        );
      }
      await expectLater(
        api.requestBytes('/owned', headers: {'Authorization': 'other'}),
        throwsA(isA<ApiFailure>()),
      );
      expect(adapter.requests, isEmpty);
    },
  );

  test(
    'redirect response is rejected without following returned location',
    () async {
      final adapter = ControlledAdapter(
        (options) =>
            authResponse(options) ??
            jsonResponse(null, 302, {
              'location': ['https://untrusted.invalid'],
            }),
      );
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        ApiMemoryStore(),
      );
      await identity.login('owner@example.com', 'synthetic-only-password');
      await expectLater(
        DomainApi(identity).get('/owned'),
        throwsA(
          isA<ApiFailure>().having(
            (error) => error.code,
            'code',
            'redirect_rejected',
          ),
        ),
      );
      expect(
        adapter.requests.where((request) => request.path == '/owned').length,
        1,
      );
      expect(adapter.requests.last.followRedirects, isFalse);
    },
  );

  test(
    'bounded byte reads reject unknown-length overflow and truncated declared bytes',
    () async {
      var truncated = false;
      final adapter = ControlledAdapter(
        (options) =>
            authResponse(options) ??
            ResponseBody(
              Stream.fromIterable([
                Uint8List.fromList([1, 2]),
                Uint8List.fromList([3, 4]),
              ]),
              200,
              headers: truncated
                  ? {
                      'content-length': ['5'],
                    }
                  : {},
            ),
      );
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        ApiMemoryStore(),
      );
      await identity.login('owner@example.com', 'synthetic-only-password');
      final api = DomainApi(identity);
      await expectLater(
        api.requestBytes('/content', maxBytes: 3),
        throwsA(
          isA<ApiFailure>().having(
            (error) => error.kind,
            'kind',
            ApiFailureKind.oversized,
          ),
        ),
      );
      truncated = true;
      await expectLater(
        api.requestBytes('/content', maxBytes: 8),
        throwsA(
          isA<ApiFailure>().having(
            (error) => error.kind,
            'kind',
            ApiFailureKind.invalidResponse,
          ),
        ),
      );
    },
  );

  test(
    'invalid successful upload responses remain uncertain until readback',
    () async {
      var calls = 0;
      var truncated = true;
      final adapter = ControlledAdapter((options) {
        final auth = authResponse(options);
        if (auth != null) return auth;
        calls++;
        return ResponseBody.fromBytes(
          [1, 2],
          200,
          headers: {
            'content-length': [truncated ? '5' : '12'],
          },
        );
      });
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        ApiMemoryStore(),
      );
      await identity.login('owner@example.com', 'synthetic-only-password');
      final api = DomainApi(identity);
      for (final kind in [
        ApiFailureKind.invalidResponse,
        ApiFailureKind.oversized,
      ]) {
        await expectLater(
          api.requestBytes(
            '/upload',
            method: 'PUT',
            data: Uint8List.fromList([42]),
            maxBytes: 8,
          ),
          throwsA(
            isA<ApiFailure>()
                .having((failure) => failure.kind, 'kind', kind)
                .having((failure) => failure.uncertain, 'uncertain', isTrue),
          ),
        );
        truncated = false;
      }
      expect(calls, 2);
    },
  );

  test('revocation discards a protected response already in flight', () async {
    final pending = Completer<ResponseBody>();
    final requested = Completer<void>();
    final adapter = ControlledAdapter((options) {
      final auth = authResponse(options);
      if (auth != null) return auth;
      requested.complete();
      return pending.future;
    });
    final identity = AuthRepository(
      Dio()..httpClientAdapter = adapter,
      ApiMemoryStore(),
    );
    await identity.login('owner@example.com', 'synthetic-only-password');
    final request = DomainApi(identity).get('/owned');
    final assertion = expectLater(
      request,
      throwsA(
        isA<ApiFailure>().having(
          (error) => error.kind,
          'kind',
          ApiFailureKind.invalidSession,
        ),
      ),
    );
    await requested.future;
    await identity.clearLocalSession();
    pending.complete(jsonResponse({'private': 'must be discarded'}));
    await assertion;
  });

  test(
    'Retry-After supports seconds and HTTP dates without replaying requests',
    () {
      expect(parseRetryAfter('120'), const Duration(minutes: 2));
      expect(
        parseRetryAfter(
          'Sun, 25 Oct 2026 12:01:00 GMT',
          now: DateTime.utc(2026, 10, 25, 12),
        ),
        const Duration(minutes: 1),
      );
      expect(parseRetryAfter('invalid'), isNull);
    },
  );
}
