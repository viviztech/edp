import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/files/file_transport.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import 'file_transport_test.dart' show FileTestSnapshot, FileTestTokens;

class _PartialUploadAdapter implements HttpClientAdapter {
  final calls = <RequestOptions>[];
  final sentBytes = <int>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    calls.add(options);
    if (options.path == '/auth/login') {
      return _json({
        'access_token': 'synthetic-access',
        'refresh_token': 'synthetic-refresh',
      });
    }
    if (options.path == '/auth/me') {
      return _json({
        'id': 'synthetic-owner',
        'display_name': 'Synthetic',
        'email': 'owner@example.com',
        'locale': 'en',
        'grants': [],
      });
    }
    expect(options.method, 'PUT');
    await for (final chunk in requestStream!) {
      sentBytes.addAll(chunk);
    }
    return _json({'accepted': true});
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _json(Object value) => ResponseBody.fromString(
  jsonEncode(value),
  200,
  headers: {
    'content-type': ['application/json'],
  },
);

void main() {
  test(
    'native notSent failure after a streamed chunk is uncertain after one PUT',
    () async {
      final adapter = _PartialUploadAdapter();
      final identity = AuthRepository(
        Dio()..httpClientAdapter = adapter,
        FileTestTokens(),
      );
      await identity.login('owner@example.com', 'synthetic-test-password');
      var sourceOpens = 0;
      final snapshot = FileTestSnapshot(
        [65, 66, 67, 68],
        reader: () async* {
          sourceOpens++;
          yield [65, 66];
          // The native snapshot API cannot know earlier chunks reached HTTP.
          throw const ApiFailure(
            'file_changed',
            kind: ApiFailureKind.conflict,
            outcome: CommandOutcome.notSent,
          );
        },
      );

      await expectLater(
        FileTransport(
          identity,
        ).upload('/documents/content', snapshot: snapshot, expectedVersion: 1),
        throwsA(
          isA<ApiFailure>()
              .having((failure) => failure.code, 'code', 'file_changed')
              .having(
                (failure) => failure.outcome,
                'outcome',
                CommandOutcome.uncertain,
              ),
        ),
      );
      expect(adapter.sentBytes, [65, 66]);
      expect(sourceOpens, 1);
      expect(adapter.calls.where((call) => call.method == 'PUT'), hasLength(1));
      expect(
        adapter.calls.where((call) => call.path == '/auth/refresh'),
        isEmpty,
      );
    },
  );
}
