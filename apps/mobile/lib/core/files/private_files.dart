import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../api/api_failure.dart';

const clientMaxFileBytes = 10 * 1024 * 1024;
const channelChunkBytes = 64 * 1024;
const privateMediaTypes = {
  'application/pdf',
  'image/png',
  'image/jpeg',
  'image/webp',
  'text/plain',
};

abstract interface class PrivateFiles {
  bool get supported;
  Future<void> initialize();
  Future<PrivateFileScope> createScope();
  Future<void> closeScopes();
}

abstract interface class PrivateFileScope {
  bool get closed;
  Future<PrivateSnapshot?> pick({
    required Set<String> allowedMediaTypes,
    required int maxBytes,
  });
  Future<PrivateSink> beginDownload({
    required String mediaType,
    required int maxBytes,
    required int expectedByteSize,
    required String expectedSha256,
  });
  Future<void> close();
}

abstract interface class PrivateSnapshot {
  String get id;
  String get mediaType;
  int get byteSize;
  String get sha256;
  Future<void> verify();
  Stream<List<int>> openRead();
  Future<void> dispose();
}

abstract interface class PrivateSink {
  Future<void> append(List<int> chunk);
  Future<PrivateSnapshot> finish();
  Future<void> abort();
}

const _cancelled = ApiFailure(
  'private_file_cancelled',
  kind: ApiFailureKind.cancelled,
  outcome: CommandOutcome.notSent,
);
const _unsupported = ApiFailure(
  'private_files_unsupported',
  kind: ApiFailureKind.unavailable,
  outcome: CommandOutcome.notSent,
);
const _invalid = ApiFailure(
  'private_file_invalid',
  kind: ApiFailureKind.validation,
  outcome: CommandOutcome.notSent,
);
final _identifier = RegExp(
  r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
);
final _digest = RegExp(r'^[0-9a-f]{64}$');

/// Native snapshots expose opaque IDs and bounded chunks, never provider paths.
class NativePrivateFiles implements PrivateFiles {
  final MethodChannel _channel;
  @override
  final bool supported;
  final Set<_NativeScope> _scopes = {};
  Future<void>? _initializing;
  bool _initialized = false, _broken = false;
  int _generation = 0;

  NativePrivateFiles({MethodChannel? channel, bool? supported})
    : _channel = channel ?? const MethodChannel('edp/private_files'),
      supported =
          supported ??
          (!kIsWeb &&
              {
                TargetPlatform.android,
                TargetPlatform.iOS,
              }.contains(defaultTargetPlatform));

  Future<T?> _invoke<T>(
    String method, [
    Map<String, Object?>? arguments,
  ]) async {
    try {
      return await _channel.invokeMethod<T>(method, arguments);
    } on PlatformException catch (error) {
      final kind = switch (error.code) {
        'private_file_cancelled' => ApiFailureKind.cancelled,
        'file_too_large' || 'private_file_limit' => ApiFailureKind.oversized,
        'file_changed' => ApiFailureKind.conflict,
        'file_type_invalid' ||
        'file_metadata_invalid' ||
        'invalid_request' => ApiFailureKind.validation,
        _ => ApiFailureKind.unavailable,
      };
      const codes = {
        'private_file_cancelled',
        'file_too_large',
        'private_file_limit',
        'file_changed',
        'file_type_invalid',
        'file_metadata_invalid',
        'private_file_missing',
        'invalid_request',
        'private_files_unavailable',
        'private_storage_unavailable',
      };
      throw ApiFailure(
        codes.contains(error.code) ? error.code : 'private_files_unavailable',
        kind: kind,
        outcome: CommandOutcome.notSent,
      );
    } on MissingPluginException {
      throw _unsupported;
    } on ApiFailure {
      rethrow;
    } catch (_) {
      throw const ApiFailure(
        'private_files_unavailable',
        kind: ApiFailureKind.unavailable,
        outcome: CommandOutcome.notSent,
      );
    }
  }

  @override
  Future<void> initialize() {
    if (!supported) return Future.value();
    if (_broken) return Future.error(_unsupported);
    if (_initialized) return Future.value();
    return _initializing ??= _initialize();
  }

  Future<void> _initialize() async {
    try {
      await _invoke<void>('initialize');
      _initialized = true;
    } catch (_) {
      _broken = true;
      rethrow;
    }
  }

  @override
  Future<PrivateFileScope> createScope() async {
    if (!supported) return _UnsupportedScope();
    final generation = _generation;
    await initialize();
    if (generation != _generation) throw _cancelled;
    final id = await _invoke<String>('createScope');
    if (id == null || !_identifier.hasMatch(id)) throw _invalid;
    if (generation != _generation) {
      await _invoke<void>('closeScope', {'scope': id});
      throw _cancelled;
    }
    final scope = _NativeScope(this, id);
    _scopes.add(scope);
    return scope;
  }

  @override
  Future<void> closeScopes() async {
    _generation++;
    final scopes = _scopes.toList();
    _scopes.clear();
    for (final scope in scopes) {
      scope._closed = true;
    }
    if (!supported || !_initialized) return;
    try {
      await _invoke<void>('closeScopes');
    } catch (_) {
      // Collection cannot resume if private cleanup could not be confirmed.
      _broken = true;
      rethrow;
    }
  }
}

class _UnsupportedScope implements PrivateFileScope {
  @override
  bool closed = false;
  @override
  Future<PrivateSnapshot?> pick({
    required Set<String> allowedMediaTypes,
    required int maxBytes,
  }) async => throw closed ? _cancelled : _unsupported;
  @override
  Future<PrivateSink> beginDownload({
    required String mediaType,
    required int maxBytes,
    required int expectedByteSize,
    required String expectedSha256,
  }) async => throw closed ? _cancelled : _unsupported;
  @override
  Future<void> close() async {
    closed = true;
  }
}

class _NativeScope implements PrivateFileScope {
  final NativePrivateFiles store;
  final String id;
  bool _closed = false;
  bool _picking = false;
  _NativeScope(this.store, this.id);
  @override
  bool get closed => _closed || store._broken;
  void _check() {
    if (closed) throw _cancelled;
  }

  void _limits(String mediaType, int maxBytes) {
    if (!privateMediaTypes.contains(mediaType) ||
        maxBytes < 1 ||
        maxBytes > clientMaxFileBytes) {
      throw _invalid;
    }
  }

  _NativeSnapshot _snapshot(
    Object? data, {
    Set<String>? allowed,
    int? maxBytes,
  }) {
    _check();
    if (data is! Map) throw _invalid;
    final handle = data['id'],
        type = data['media_type'],
        size = data['byte_size'],
        hash = data['sha256'];
    if (handle is! String ||
        !_identifier.hasMatch(handle) ||
        type is! String ||
        !privateMediaTypes.contains(type) ||
        size is! int ||
        size < 1 ||
        size > (maxBytes ?? clientMaxFileBytes) ||
        hash is! String ||
        !_digest.hasMatch(hash) ||
        (allowed != null && !allowed.contains(type))) {
      throw _invalid;
    }
    return _NativeSnapshot(this, handle, type, size, hash);
  }

  @override
  Future<PrivateSnapshot?> pick({
    required Set<String> allowedMediaTypes,
    required int maxBytes,
  }) async {
    _check();
    if (_picking || allowedMediaTypes.isEmpty) throw _invalid;
    for (final type in allowedMediaTypes) {
      _limits(type, maxBytes);
    }
    _picking = true;
    try {
      final data = await store._invoke<Object?>('pickSnapshot', {
        'scope': id,
        'allowed_types': allowedMediaTypes.toList()..sort(),
        'max_bytes': maxBytes,
      });
      _check();
      return data == null
          ? null
          : _snapshot(data, allowed: allowedMediaTypes, maxBytes: maxBytes);
    } finally {
      _picking = false;
    }
  }

  @override
  Future<PrivateSink> beginDownload({
    required String mediaType,
    required int maxBytes,
    required int expectedByteSize,
    required String expectedSha256,
  }) async {
    _check();
    _limits(mediaType, maxBytes);
    if (expectedByteSize < 1 ||
        expectedByteSize > maxBytes ||
        !_digest.hasMatch(expectedSha256)) {
      throw _invalid;
    }
    final handle = await store._invoke<String>('beginDownload', {
      'scope': id,
      'media_type': mediaType,
      'max_bytes': maxBytes,
      'expected_byte_size': expectedByteSize,
      'expected_sha256': expectedSha256,
    });
    _check();
    if (handle == null || !_identifier.hasMatch(handle)) throw _invalid;
    return _NativeSink(
      this,
      handle,
      mediaType,
      expectedByteSize,
      expectedSha256,
    );
  }

  @override
  Future<void> close() async {
    if (_closed) return;
    _closed = true;
    store._scopes.remove(this);
    try {
      await store._invoke<void>('closeScope', {'scope': id});
    } catch (_) {
      store._broken = true;
      rethrow;
    }
  }
}

class _NativeSnapshot implements PrivateSnapshot {
  final _NativeScope scope;
  @override
  final String id, mediaType, sha256;
  @override
  final int byteSize;
  bool _disposed = false;
  _NativeSnapshot(
    this.scope,
    this.id,
    this.mediaType,
    this.byteSize,
    this.sha256,
  );
  void _check() {
    scope._check();
    if (_disposed) throw _cancelled;
  }

  Map<String, Object?> get _args => {'scope': scope.id, 'id': id};

  @override
  Future<void> verify() async {
    _check();
    await scope.store._invoke<void>('verify', _args);
    _check();
  }

  @override
  Stream<List<int>> openRead() async* {
    await verify();
    var offset = 0;
    while (offset < byteSize) {
      _check();
      final remaining = byteSize - offset;
      final count = remaining < channelChunkBytes
          ? remaining
          : channelChunkBytes;
      final bytes = await scope.store._invoke<Uint8List>('read', {
        ..._args,
        'offset': offset,
        'count': count,
      });
      _check();
      if (bytes == null || bytes.length != count) throw _invalid;
      offset += bytes.length;
      yield bytes;
    }
    await verify();
  }

  @override
  Future<void> dispose() async {
    if (_disposed) return;
    _disposed = true;
    if (!scope.closed) {
      try {
        await scope.store._invoke<void>('release', _args);
      } catch (_) {
        scope.store._broken = true;
        rethrow;
      }
    }
  }
}

class _NativeSink implements PrivateSink {
  final _NativeScope scope;
  final String id, mediaType, sha256;
  final int byteSize;
  bool _terminal = false, _writing = false;
  int _received = 0;
  _NativeSink(this.scope, this.id, this.mediaType, this.byteSize, this.sha256);
  Map<String, Object?> get _args => {'scope': scope.id, 'id': id};
  void _check() {
    scope._check();
    if (_terminal || _writing) throw _invalid;
  }

  @override
  Future<void> append(List<int> chunk) async {
    _check();
    if (chunk.isEmpty ||
        chunk.length > channelChunkBytes ||
        _received + chunk.length > byteSize ||
        chunk.any((value) => value < 0 || value > 255)) {
      throw _invalid;
    }
    _writing = true;
    try {
      await scope.store._invoke<void>('append', {
        ..._args,
        'bytes': Uint8List.fromList(chunk),
      });
      scope._check();
      _received += chunk.length;
    } finally {
      _writing = false;
    }
  }

  @override
  Future<PrivateSnapshot> finish() async {
    _check();
    if (_received != byteSize) throw _invalid;
    _terminal = true;
    try {
      final result = await scope.store._invoke<Object?>('finish', _args);
      final snapshot = scope._snapshot(result);
      if (snapshot.id != id ||
          snapshot.mediaType != mediaType ||
          snapshot.byteSize != byteSize ||
          snapshot.sha256 != sha256) {
        await snapshot.dispose();
        throw _invalid;
      }
      return snapshot;
    } catch (_) {
      if (!scope.closed) await scope.store._invoke<void>('abort', _args);
      rethrow;
    }
  }

  @override
  Future<void> abort() async {
    if (_terminal) return;
    _terminal = true;
    if (!scope.closed) await scope.store._invoke<void>('abort', _args);
  }
}
