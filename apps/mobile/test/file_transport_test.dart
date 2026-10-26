import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/files/file_transport.dart';
import 'package:edp_mobile/core/files/private_files.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:flutter_test/flutter_test.dart';

class FileTestTokens implements TokenStore {
  String? token;
  @override
  Future<void> clear() async => token = null;
  @override
  Future<String?> read() async => token;
  @override
  Future<void> write(String value) async => token = value;
}

class FileTestSnapshot implements PrivateSnapshot {
  final List<int> bytes;
  final String? registeredHash;
  final Stream<List<int>> Function()? reader;
  int verifications = 0, releases = 0;
  bool disposed = false;
  FileTestSnapshot(this.bytes, {this.registeredHash, this.reader});
  @override
  String get id => '22222222-2222-4222-8222-222222222222';
  @override
  String get mediaType => 'text/plain';
  @override
  int get byteSize => bytes.length;
  @override
  String get sha256 => registeredHash ?? cryptoHash(bytes);
  @override
  Future<void> verify() async {
    verifications++;
    if (disposed) throw StateError('private snapshot is disposed');
  }

  @override
  Stream<List<int>> openRead() =>
      reader?.call() ??
      Stream.fromIterable([
        for (var offset = 0; offset < bytes.length; offset += channelChunkBytes)
          bytes.sublist(
            offset,
            offset + channelChunkBytes < bytes.length
                ? offset + channelChunkBytes
                : bytes.length,
          ),
      ]);
  @override
  Future<void> dispose() async {
    disposed = true;
    releases++;
  }
}

String cryptoHash(List<int> bytes) => sha256.convert(bytes).toString();

class FileTestSink implements PrivateSink {
  final chunks = <List<int>>[];
  int aborts = 0, finishes = 0;
  FileTestSnapshot? result;
  Future<void> Function()? onAppend;
  Future<PrivateSnapshot> Function()? onFinish;
  @override
  Future<void> append(List<int> chunk) async {
    chunks.add(List.of(chunk));
    await onAppend?.call();
  }

  @override
  Future<PrivateSnapshot> finish() async {
    finishes++;
    if (onFinish != null) return onFinish!();
    return result ??= FileTestSnapshot(chunks.expand((c) => c).toList());
  }

  @override
  Future<void> abort() async {
    aborts++;
  }
}

class FileTestScope implements PrivateFileScope {
  @override
  bool closed = false;
  final FileTestSink sink = FileTestSink();
  FileTestSnapshot? selected;
  Future<PrivateSnapshot?> Function()? picker;
  Future<PrivateSink> Function()? downloadFactory;
  int picks = 0, downloads = 0, closes = 0;
  @override
  Future<PrivateSnapshot?> pick({
    required Set<String> allowedMediaTypes,
    required int maxBytes,
  }) async {
    picks++;
    return picker != null ? picker!() : selected;
  }

  @override
  Future<PrivateSink> beginDownload({
    required String mediaType,
    required int maxBytes,
    required int expectedByteSize,
    required String expectedSha256,
  }) async {
    downloads++;
    if (downloadFactory != null) return downloadFactory!();
    return sink;
  }

  @override
  Future<void> close() async {
    closed = true;
    closes++;
  }
}

typedef _Handler =
    FutureOr<ResponseBody> Function(RequestOptions, Stream<Uint8List>?);

class _Adapter implements HttpClientAdapter {
  final _Handler handler;
  final calls = <RequestOptions>[];
  _Adapter(this.handler);
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
    if (options.path == '/auth/refresh') {
      return _json({
        'access_token': 'rotated-access',
        'refresh_token': 'rotated-refresh',
      });
    }
    return handler(options, requestStream);
  }

  @override
  void close({bool force = false}) {}
}

class _StreamIdentity extends AuthRepository {
  final List<int> bytes;
  _StreamIdentity(this.bytes) : super(Dio(), FileTestTokens());
  @override
  Future<Response<dynamic>> authenticatedRequest(
    String path, {
    String method = 'GET',
    Object? data,
    Map<String, dynamic>? queryParameters,
    Map<String, String>? headers,
    ResponseType responseType = ResponseType.json,
    CancelToken? cancelToken,
    int? bodyLength,
    Duration? transferTimeout,
  }) async => Response<dynamic>(
    requestOptions: RequestOptions(path: path),
    statusCode: 200,
    headers: Headers.fromMap({
      'content-type': ['text/plain'],
    }),
    data: ResponseBody.fromBytes(bytes, 200),
  );
}

ResponseBody _json(
  Object? value, {
  int status = 200,
  Map<String, List<String>>? headers,
}) => ResponseBody.fromString(
  jsonEncode(value),
  status,
  headers: {
    'content-type': ['application/json'],
    ...?headers,
  },
);

Future<(AuthRepository, _Adapter)> _identity(_Handler handler) async {
  final adapter = _Adapter(handler);
  final identity = AuthRepository(
    Dio()..httpClientAdapter = adapter,
    FileTestTokens(),
  );
  await identity.login('owner@example.com', 'synthetic-test-password');
  return (identity, adapter);
}

FileProof _proof(List<int> bytes) => FileProof(
  mediaType: 'text/plain',
  byteSize: bytes.length,
  sha256: cryptoHash(bytes),
);

void main() {
  test(
    'raw upload streams exact bytes with derived length and quoted file version',
    () async {
      final bytes = utf8.encode('Synthetic Tamil text: வணக்கம்');
      final sent = <int>[];
      final (identity, adapter) = await _identity((options, stream) async {
        expect(options.method, 'PUT');
        expect(options.headers['content-type'], 'text/plain');
        expect(options.headers['if-match'], '"7"');
        expect(options.headers['content-length'], '${bytes.length}');
        expect(options.headers.containsKey('content-encoding'), isFalse);
        expect(options.headers.containsKey('content-disposition'), isFalse);
        expect(options.headers['Authorization'], 'Bearer synthetic-access');
        expect(options.followRedirects, isFalse);
        await for (final chunk in stream!) {
          sent.addAll(chunk);
        }
        return _json({'accepted': true});
      });
      final snapshot = FileTestSnapshot(bytes);
      final result = await FileTransport(
        identity,
      ).upload('/documents/content', snapshot: snapshot, expectedVersion: 7);
      expect(result, {'accepted': true});
      expect(sent, bytes);
      expect(snapshot.verifications, 1);
      expect(adapter.calls.where((c) => c.method == 'PUT'), hasLength(1));
      expect(snapshot.disposed, isFalse);
    },
  );

  test(
    'unknown-length download splits native writes and verifies the complete digest',
    () async {
      final bytes = List.generate(channelChunkBytes + 9, (i) => i % 251);
      final (identity, _) = await _identity(
        (options, _) => ResponseBody(
          Stream.value(Uint8List.fromList(bytes)),
          200,
          headers: {
            'content-type': ['text/plain; charset=utf-8'],
          },
        ),
      );
      final scope = FileTestScope();
      final result = await FileTransport(
        identity,
      ).download('/documents/content', scope: scope, proof: _proof(bytes));
      expect(scope.sink.chunks.map((c) => c.length), [channelChunkBytes, 9]);
      expect(result.sha256, cryptoHash(bytes));
      expect(scope.sink.aborts, 0);
      expect(scope.sink.result!.verifications, 1);
    },
  );

  test(
    'download rejects MIME and declared length before allocating private output',
    () async {
      final bytes = [1, 2, 3];
      var headers = {
        'content-type': ['application/pdf'],
      };
      final (identity, _) = await _identity(
        (options, _) => ResponseBody.fromBytes(bytes, 200, headers: headers),
      );
      final scope = FileTestScope();
      for (final value in [
        {
          'content-type': ['application/pdf'],
        },
        {
          'content-type': ['text/plain'],
          'content-length': ['4'],
        },
        {
          'content-type': ['text/plain'],
          'content-length': ['-1'],
        },
      ]) {
        headers = value;
        await expectLater(
          FileTransport(
            identity,
          ).download('/documents/content', scope: scope, proof: _proof(bytes)),
          throwsA(isA<ApiFailure>()),
        );
      }
      expect(scope.downloads, 0);
    },
  );

  test(
    'overflow, truncation and wrong digest abort partial private downloads',
    () async {
      final expected = [1, 2, 3];
      var received = [1, 2, 3, 4];
      final (identity, _) = await _identity(
        (options, _) => ResponseBody.fromBytes(
          received,
          200,
          headers: {
            'content-type': ['text/plain'],
          },
        ),
      );
      for (final bytes in [
        [1, 2, 3, 4],
        [1, 2],
        [1, 2, 9],
      ]) {
        received = bytes;
        final scope = FileTestScope();
        await expectLater(
          FileTransport(identity).download(
            '/documents/content',
            scope: scope,
            proof: _proof(expected),
          ),
          throwsA(isA<ApiFailure>()),
        );
        expect(scope.sink.aborts, 1);
        expect(scope.sink.finishes, 0);
      }
    },
  );

  test(
    'snapshot mutation is uncertain after one upload and is never retried',
    () async {
      final (identity, adapter) = await _identity((options, stream) async {
        await stream!.drain<void>();
        return _json({'accepted': true});
      });
      final snapshot = FileTestSnapshot([
        1,
        2,
        3,
      ], registeredHash: cryptoHash([1, 2, 4]));
      await expectLater(
        FileTransport(
          identity,
        ).upload('/documents/content', snapshot: snapshot, expectedVersion: 1),
        throwsA(
          isA<ApiFailure>()
              .having((e) => e.code, 'code', 'file_integrity_failed')
              .having((e) => e.uncertain, 'uncertain', isTrue),
        ),
      );
      expect(adapter.calls.where((c) => c.method == 'PUT'), hasLength(1));
    },
  );

  test(
    'invalid successful upload metadata stays uncertain without replay',
    () async {
      final (identity, adapter) = await _identity((options, stream) async {
        await stream!.drain<void>();
        return ResponseBody.fromString(
          'not json',
          200,
          headers: {
            'content-type': ['application/json'],
          },
        );
      });
      await expectLater(
        FileTransport(identity).upload(
          '/documents/content',
          snapshot: FileTestSnapshot([1, 2, 3]),
          expectedVersion: 1,
        ),
        throwsA(
          isA<ApiFailure>().having((e) => e.uncertain, 'uncertain', isTrue),
        ),
      );
      expect(adapter.calls.where((c) => c.method == 'PUT'), hasLength(1));
    },
  );

  test(
    'malformed successful upload length remains uncertain after exactly one PUT',
    () async {
      final (identity, adapter) = await _identity((options, stream) async {
        await stream!.drain<void>();
        return _json(
          {'accepted': true},
          headers: {
            'content-length': ['-1'],
          },
        );
      });
      await expectLater(
        FileTransport(identity).upload(
          '/documents/content',
          snapshot: FileTestSnapshot([1, 2, 3]),
          expectedVersion: 1,
        ),
        throwsA(
          isA<ApiFailure>().having((e) => e.uncertain, 'uncertain', isTrue),
        ),
      );
      expect(adapter.calls.where((c) => c.method == 'PUT'), hasLength(1));
    },
  );

  testWidgets('late private sink after creation timeout is aborted', (
    tester,
  ) async {
    final bytes = [1, 2, 3];
    final identity = _StreamIdentity(bytes);
    final created = Completer<PrivateSink>();
    final entered = Completer<void>();
    final scope = FileTestScope()
      ..downloadFactory = () {
        entered.complete();
        return created.future;
      };
    final downloading = FileTransport(
      identity,
    ).download('/documents/content', scope: scope, proof: _proof(bytes));
    final assertion = expectLater(
      downloading,
      throwsA(
        isA<ApiFailure>().having((e) => e.kind, 'kind', ApiFailureKind.timeout),
      ),
    );
    for (var attempt = 0; attempt < 12 && !entered.isCompleted; attempt++) {
      await tester.pump();
      await tester.runAsync(() => Future<void>.delayed(Duration.zero));
    }
    expect(entered.isCompleted, isTrue);
    await tester.pump(const Duration(seconds: 61));
    await assertion;
    created.complete(scope.sink);
    await tester.pump();
    expect(scope.sink.aborts, 1);
    expect(scope.sink.finishes, 0);
  });

  testWidgets('late completed snapshot after finish timeout is deleted', (
    tester,
  ) async {
    final bytes = [1, 2, 3];
    final identity = _StreamIdentity(bytes);
    final completed = Completer<PrivateSnapshot>();
    final entered = Completer<void>();
    final scope = FileTestScope();
    scope.sink.onFinish = () {
      entered.complete();
      return completed.future;
    };
    final downloading = FileTransport(
      identity,
    ).download('/documents/content', scope: scope, proof: _proof(bytes));
    final assertion = expectLater(
      downloading,
      throwsA(
        isA<ApiFailure>().having((e) => e.kind, 'kind', ApiFailureKind.timeout),
      ),
    );
    for (var attempt = 0; attempt < 12 && !entered.isCompleted; attempt++) {
      await tester.pump();
      await tester.runAsync(() => Future<void>.delayed(Duration.zero));
    }
    expect(entered.isCompleted, isTrue);
    await tester.pump(const Duration(seconds: 61));
    await assertion;
    final snapshot = FileTestSnapshot(bytes);
    completed.complete(snapshot);
    await tester.pump();
    expect(snapshot.disposed, isTrue);
    expect(scope.sink.aborts, 1);
  });

  test(
    '401 refresh recovers only the next action and never replays the raw PUT',
    () async {
      final (identity, adapter) = await _identity((options, stream) async {
        await stream!.drain<void>();
        return _json({
          'error': {'code': 'invalid_session'},
        }, status: 401);
      });
      await expectLater(
        FileTransport(identity).upload(
          '/documents/content',
          snapshot: FileTestSnapshot([1]),
          expectedVersion: 1,
        ),
        throwsA(isA<ApiFailure>()),
      );
      expect(adapter.calls.where((c) => c.method == 'PUT'), hasLength(1));
      expect(
        adapter.calls.where((c) => c.path == '/auth/refresh'),
        hasLength(1),
      );
    },
  );

  test(
    'caller cancellation before upload sends no bytes or authenticated request',
    () async {
      final (identity, adapter) = await _identity(
        (options, stream) => _json({}),
      );
      final token = CancelToken()..cancel();
      final snapshot = FileTestSnapshot([1]);
      await expectLater(
        FileTransport(identity).upload(
          '/documents/content',
          snapshot: snapshot,
          expectedVersion: 1,
          cancelToken: token,
        ),
        throwsA(
          isA<ApiFailure>().having(
            (e) => e.outcome,
            'outcome',
            CommandOutcome.notSent,
          ),
        ),
      );
      expect(adapter.calls.where((c) => c.method == 'PUT'), isEmpty);
      expect(snapshot.verifications, 0);
    },
  );

  test(
    'session revocation while appending cannot expose a verified download',
    () async {
      final bytes = [1, 2, 3];
      final (identity, _) = await _identity(
        (options, _) => ResponseBody.fromBytes(
          bytes,
          200,
          headers: {
            'content-type': ['text/plain'],
          },
        ),
      );
      final scope = FileTestScope();
      scope.sink.onAppend = identity.clearLocalSession;
      await expectLater(
        FileTransport(
          identity,
        ).download('/documents/content', scope: scope, proof: _proof(bytes)),
        throwsA(
          isA<ApiFailure>().having(
            (e) => e.kind,
            'kind',
            ApiFailureKind.invalidSession,
          ),
        ),
      );
      expect(scope.sink.aborts, 1);
      expect(scope.sink.finishes, 0);
    },
  );

  test(
    'redirect and foreign origins cannot forward bearer credentials',
    () async {
      final (identity, adapter) = await _identity(
        (options, _) => ResponseBody.fromBytes(
          [],
          302,
          headers: {
            'location': ['https://untrusted.invalid/private'],
          },
        ),
      );
      final scope = FileTestScope();
      await expectLater(
        FileTransport(
          identity,
        ).download('/documents/content', scope: scope, proof: _proof([1])),
        throwsA(isA<ApiFailure>()),
      );
      await expectLater(
        FileTransport(identity).download(
          'https://untrusted.invalid/private',
          scope: scope,
          proof: _proof([1]),
        ),
        throwsA(
          isA<ApiFailure>().having(
            (e) => e.outcome,
            'outcome',
            CommandOutcome.notSent,
          ),
        ),
      );
      expect(
        adapter.calls.where((c) => c.path == '/documents/content'),
        hasLength(1),
      );
      expect(adapter.calls.where((c) => c.path.contains('untrusted')), isEmpty);
      expect(scope.downloads, 0);
    },
  );
}
