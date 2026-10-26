import 'dart:async';

import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/files/private_files.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const _scopeId = '11111111-1111-4111-8111-111111111111';
const _fileId = '22222222-2222-4222-8222-222222222222';
const _hash =
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';

Map<String, Object> _metadata({int size = 3, String hash = _hash}) => {
  'id': _fileId,
  'media_type': 'text/plain',
  'byte_size': size,
  'sha256': hash,
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('edp/test_private_files');
  final messenger =
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
  late List<MethodCall> calls;
  late FutureOr<Object?> Function(MethodCall) handler;

  setUp(() {
    calls = [];
    handler = (call) => switch (call.method) {
      'createScope' => _scopeId,
      'pickSnapshot' || 'finish' => _metadata(),
      'beginDownload' => _fileId,
      _ => null,
    };
    messenger.setMockMethodCallHandler(channel, (call) async {
      calls.add(call);
      return handler(call);
    });
  });
  tearDown(() => messenger.setMockMethodCallHandler(channel, null));

  test(
    'unsupported platforms never invoke a native picker or download',
    () async {
      final store = NativePrivateFiles(channel: channel, supported: false);
      await store.initialize();
      final scope = await store.createScope();
      await expectLater(
        scope.pick(allowedMediaTypes: {'text/plain'}, maxBytes: 10),
        throwsA(
          isA<ApiFailure>().having(
            (e) => e.code,
            'code',
            'private_files_unsupported',
          ),
        ),
      );
      await expectLater(
        scope.beginDownload(
          mediaType: 'text/plain',
          maxBytes: 10,
          expectedByteSize: 3,
          expectedSha256: _hash,
        ),
        throwsA(isA<ApiFailure>()),
      );
      await scope.close();
      expect(calls, isEmpty);
    },
  );

  test(
    'initialization is single-flight and native failures hide diagnostics',
    () async {
      final gate = Completer<void>();
      handler = (call) async {
        if (call.method == 'initialize') {
          await gate.future;
          throw PlatformException(
            code: 'provider_secret_path',
            message: '/private/provider/file',
          );
        }
        return null;
      };
      final store = NativePrivateFiles(channel: channel, supported: true);
      final first = store.initialize();
      final second = store.initialize();
      expect(identical(first, second), isTrue);
      final assertion = expectLater(
        first,
        throwsA(
          isA<ApiFailure>()
              .having((e) => e.code, 'code', 'private_files_unavailable')
              .having(
                (e) => e.toString(),
                'sanitized',
                isNot(contains('provider')),
              ),
        ),
      );
      gate.complete();
      await assertion;
      await expectLater(store.createScope(), throwsA(isA<ApiFailure>()));
      expect(calls.where((c) => c.method == 'initialize'), hasLength(1));
    },
  );

  test(
    'picker validates local limits before crossing native boundary',
    () async {
      final store = NativePrivateFiles(channel: channel, supported: true);
      final scope = await store.createScope();
      for (final limits in [
        <String>{},
        {'application/zip'},
      ]) {
        await expectLater(
          scope.pick(allowedMediaTypes: limits, maxBytes: 10),
          throwsA(isA<ApiFailure>()),
        );
      }
      for (final size in [0, clientMaxFileBytes + 1]) {
        await expectLater(
          scope.pick(allowedMediaTypes: {'text/plain'}, maxBytes: size),
          throwsA(isA<ApiFailure>()),
        );
      }
      expect(calls.where((c) => c.method == 'pickSnapshot'), isEmpty);
      await scope.close();
    },
  );

  test(
    'snapshot metadata rejects oversized, zero, foreign MIME and invalid proof',
    () async {
      final store = NativePrivateFiles(channel: channel, supported: true);
      final scope = await store.createScope();
      for (final metadata in [
        _metadata(size: 0),
        _metadata(size: 11),
        _metadata(hash: 'not-a-digest'),
        {..._metadata(), 'media_type': 'application/pdf'},
        {..._metadata(), 'id': '/private/source.txt'},
      ]) {
        handler = (call) => call.method == 'pickSnapshot' ? metadata : null;
        await expectLater(
          scope.pick(allowedMediaTypes: {'text/plain'}, maxBytes: 10),
          throwsA(
            isA<ApiFailure>().having(
              (e) => e.outcome,
              'outcome',
              CommandOutcome.notSent,
            ),
          ),
        );
      }
      await scope.close();
    },
  );

  test(
    'late scope creation after logout is closed and never exposed',
    () async {
      final created = Completer<String>();
      final entered = Completer<void>();
      handler = (call) {
        if (call.method == 'createScope') {
          entered.complete();
          return created.future;
        }
        return null;
      };
      final store = NativePrivateFiles(channel: channel, supported: true);
      final creating = store.createScope();
      final assertion = expectLater(
        creating,
        throwsA(
          isA<ApiFailure>().having(
            (e) => e.kind,
            'kind',
            ApiFailureKind.cancelled,
          ),
        ),
      );
      await entered.future;
      await store.closeScopes();
      created.complete(_scopeId);
      await assertion;
      expect(calls.where((c) => c.method == 'closeScope').single.arguments, {
        'scope': _scopeId,
      });
    },
  );

  test(
    'snapshot reads bounded exact chunks and re-verifies before and after',
    () async {
      final size = channelChunkBytes + 3;
      handler = (call) {
        if (call.method == 'createScope') return _scopeId;
        if (call.method == 'pickSnapshot') return _metadata(size: size);
        if (call.method == 'read') {
          final args = call.arguments as Map;
          expect(
            args.keys,
            unorderedEquals(['scope', 'id', 'offset', 'count']),
          );
          final count = args['count'] as int;
          expect(count, lessThanOrEqualTo(channelChunkBytes));
          return Uint8List(count);
        }
        return null;
      };
      final scope = await NativePrivateFiles(
        channel: channel,
        supported: true,
      ).createScope();
      final file = (await scope.pick(
        allowedMediaTypes: {'text/plain'},
        maxBytes: size,
      ))!;
      final chunks = await file.openRead().toList();
      expect(chunks.map((c) => c.length), [channelChunkBytes, 3]);
      expect(calls.where((c) => c.method == 'verify'), hasLength(2));
      expect(
        calls
            .where((c) => c.method == 'read')
            .map((c) => (c.arguments as Map)['offset']),
        [0, channelChunkBytes],
      );
      await file.dispose();
      await file.dispose();
      expect(calls.where((c) => c.method == 'release'), hasLength(1));
      await scope.close();
    },
  );

  test(
    'truncated native chunk cannot be emitted and closing cancels handles',
    () async {
      handler = (call) => switch (call.method) {
        'createScope' => _scopeId,
        'pickSnapshot' => _metadata(),
        'read' => Uint8List(2),
        _ => null,
      };
      final store = NativePrivateFiles(channel: channel, supported: true);
      final scope = await store.createScope();
      final file = (await scope.pick(
        allowedMediaTypes: {'text/plain'},
        maxBytes: 3,
      ))!;
      await expectLater(file.openRead().toList(), throwsA(isA<ApiFailure>()));
      await store.closeScopes();
      await expectLater(
        file.verify(),
        throwsA(
          isA<ApiFailure>().having(
            (e) => e.kind,
            'kind',
            ApiFailureKind.cancelled,
          ),
        ),
      );
      await file.dispose();
      expect(calls.where((c) => c.method == 'release'), isEmpty);
    },
  );

  test(
    'download sink rejects invalid chunks and mismatched immutable proof',
    () async {
      final scope = await NativePrivateFiles(
        channel: channel,
        supported: true,
      ).createScope();
      final sink = await scope.beginDownload(
        mediaType: 'text/plain',
        maxBytes: 3,
        expectedByteSize: 3,
        expectedSha256: _hash,
      );
      for (final chunk in [
        <int>[],
        [256],
        [-1],
        [1, 2, 3, 4],
      ]) {
        await expectLater(sink.append(chunk), throwsA(isA<ApiFailure>()));
      }
      await expectLater(sink.finish(), throwsA(isA<ApiFailure>()));
      await sink.append([1, 2, 3]);
      handler = (call) =>
          call.method == 'finish' ? _metadata(hash: 'b' * 64) : null;
      await expectLater(sink.finish(), throwsA(isA<ApiFailure>()));
      expect(calls.where((c) => c.method == 'append'), hasLength(1));
      expect(calls.where((c) => c.method == 'abort'), hasLength(1));
      expect(calls.where((c) => c.method == 'release'), hasLength(1));
      await scope.close();
    },
  );

  test('failed cleanup makes later collection unavailable', () async {
    final store = NativePrivateFiles(channel: channel, supported: true);
    final scope = await store.createScope();
    handler = (call) {
      if (call.method == 'closeScope') {
        throw PlatformException(code: 'private_files_unavailable');
      }
      return null;
    };
    await expectLater(scope.close(), throwsA(isA<ApiFailure>()));
    expect(scope.closed, isTrue);
    await expectLater(store.createScope(), throwsA(isA<ApiFailure>()));
    expect(calls.where((c) => c.method == 'createScope'), hasLength(1));
  });
  test(
    'storage protection denial is bounded and cannot open a picker or byte stream',
    () async {
      handler = (call) {
        if (call.method == 'createScope') {
          throw PlatformException(
            code: 'private_storage_unavailable',
            message: 'Sensitive native diagnostics must not cross the boundary',
          );
        }
        return null;
      };
      final store = NativePrivateFiles(channel: channel, supported: true);
      await expectLater(
        store.createScope(),
        throwsA(
          isA<ApiFailure>()
              .having(
                (f) => f.code,
                'bounded code',
                'private_storage_unavailable',
              )
              .having((f) => f.kind, 'unavailable', ApiFailureKind.unavailable)
              .having(
                (f) => f.toString().contains('Sensitive'),
                'redacted',
                isFalse,
              ),
        ),
      );
      expect(
        calls.where((c) => c.method == 'pickSnapshot' || c.method == 'read'),
        isEmpty,
      );
    },
  );
}
