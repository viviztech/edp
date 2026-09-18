import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:flutter_test/flutter_test.dart';

class MemoryStore implements TokenStore {
  String? value;
  @override
  Future<String?> read() async => value;
  @override
  Future<void> write(String value) async {
    this.value = value;
  }

  @override
  Future<void> clear() async {
    value = null;
  }
}

class FakeAdapter implements HttpClientAdapter {
  int refreshes = 0;
  bool rejectRefresh = false;
  bool expireAccess = false;
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    var status = 200;
    Object body = <String, dynamic>{};
    if (options.path == '/auth/login') {
      body = {'access_token': 'access-one', 'refresh_token': 'refresh-one'};
    } else if (options.path == '/auth/refresh') {
      refreshes++;
      await Future<void>.delayed(const Duration(milliseconds: 10));
      if (rejectRefresh) {
        status = 401;
        body = {
          'error': {'code': 'invalid_session'},
        };
      } else {
        body = {'access_token': 'access-two', 'refresh_token': 'refresh-two'};
      }
    } else if (options.path == '/auth/me') {
      if (expireAccess &&
          options.headers['Authorization'] == 'Bearer access-one') {
        status = 401;
        body = {
          'error': {'code': 'invalid_session'},
        };
      } else {
        body = {
          'id': 'user',
          'display_name': 'Synthetic',
          'email': 'synthetic@example.com',
        };
      }
    } else if (options.path == '/auth/sessions') {
      body = <dynamic>[];
    }
    return ResponseBody.fromString(
      jsonEncode(body),
      status,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  test('persists refresh only and clears secure storage on logout', () async {
    final store = MemoryStore();
    final dio = Dio()..httpClientAdapter = FakeAdapter();
    final repository = AuthRepository(dio, store);
    await repository.login('synthetic@example.com', 'synthetic-input');
    expect(store.value, 'refresh-one');
    await repository.logout();
    expect(store.value, isNull);
  });
  test('concurrent expired requests perform one refresh', () async {
    final store = MemoryStore();
    final adapter = FakeAdapter();
    final repository = AuthRepository(
      Dio()..httpClientAdapter = adapter,
      store,
    );
    await repository.login('synthetic@example.com', 'synthetic-input');
    adapter.expireAccess = true;
    await Future.wait([repository.profile(), repository.profile()]);
    expect(adapter.refreshes, 1);
    expect(store.value, 'refresh-two');
  });
  test('failed rotation removes unusable refresh token', () async {
    final store = MemoryStore()..value = 'old-refresh';
    final adapter = FakeAdapter()..rejectRefresh = true;
    final repository = AuthRepository(
      Dio()..httpClientAdapter = adapter,
      store,
    );
    await expectLater(repository.restore(), throwsA(isA<AuthFailure>()));
    expect(store.value, isNull);
  });
}
