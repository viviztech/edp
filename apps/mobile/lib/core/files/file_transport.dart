import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';

import '../../features/identity/auth_repository.dart';
import '../api/api_failure.dart';
import '../api/request_safety.dart';
import 'private_files.dart';

const _responseLimit = 64 * 1024;
const _ioTimeout = Duration(seconds: 60);
const _totalTimeout = Duration(minutes: 2);
const _mediaTypes = {
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/webp',
  'text/plain',
};

class FileProof {
  final String mediaType;
  final int byteSize;
  final String sha256;
  const FileProof({
    required this.mediaType,
    required this.byteSize,
    required this.sha256,
  });

  void _validate() {
    if (!_mediaTypes.contains(mediaType) ||
        byteSize <= 0 ||
        byteSize > clientMaxFileBytes ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256)) {
      throw const ApiFailure(
        'invalid_file_proof',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
  }

  bool _matches(PrivateSnapshot snapshot) =>
      snapshot.mediaType == mediaType &&
      snapshot.byteSize == byteSize &&
      snapshot.sha256 == sha256;
}

/// The feature supplies a typed domain content path; no returned URL is followed.
/// Bytes stay in bounded streams between private snapshots and authenticated API.
class FileTransport {
  final AuthRepository _identity;
  FileTransport(AuthRepository identity) : _identity = identity;

  Future<Map<String, dynamic>> upload(
    String typedPath, {
    required PrivateSnapshot snapshot,
    required int expectedVersion,
    CancelToken? cancelToken,
    void Function(int sent, int total)? onProgress,
  }) async {
    validateApiPath(typedPath);
    final proof = FileProof(
      mediaType: snapshot.mediaType,
      byteSize: snapshot.byteSize,
      sha256: snapshot.sha256,
    ).._validate();
    if (expectedVersion <= 0 || expectedVersion > 2147483647) {
      throw const ApiFailure(
        'file_version_required',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final transfer = _Transfer(_identity, cancelToken, command: true);
    _UploadBody? body;
    var attempted = false;
    var responseReceived = false;
    try {
      transfer.check();
      await snapshot.verify().timeout(_ioTimeout);
      transfer.check();
      body = _UploadBody(snapshot, proof, transfer, onProgress);
      attempted = true;
      final response = await _identity.authenticatedRequest(
        typedPath,
        method: 'PUT',
        data: body.stream(),
        bodyLength: proof.byteSize,
        transferTimeout: _ioTimeout,
        responseType: ResponseType.stream,
        cancelToken: transfer.token,
        headers: {
          'content-type': proof.mediaType,
          'if-match': '"$expectedVersion"',
          'accept': 'application/json',
        },
      );
      responseReceived = true;
      transfer.check(sent: true);
      if (!body.complete || _mime(response.headers) != 'application/json') {
        throw _invalid(command: true);
      }
      final source = _streamBody(response);
      final declared = _declaredLength(response.headers);
      if (declared != null && declared > _responseLimit) {
        throw _oversized(command: true);
      }
      final bytes = BytesBuilder(copy: false);
      await for (final chunk in source.stream.timeout(_ioTimeout)) {
        transfer.check(sent: true);
        if (bytes.length + chunk.length > _responseLimit) {
          throw _oversized(command: true);
        }
        bytes.add(chunk);
      }
      transfer.check(sent: true);
      if (declared != null && declared != bytes.length) {
        throw _invalid(command: true);
      }
      final Object? decoded;
      try {
        decoded = jsonDecode(utf8.decode(bytes.takeBytes()));
      } catch (_) {
        throw _invalid(command: true);
      }
      if (decoded is! Map<String, dynamic>) throw _invalid(command: true);
      return Map<String, dynamic>.unmodifiable(decoded);
    } catch (error) {
      if (responseReceived &&
          error is ApiFailure &&
          error.outcome == CommandOutcome.rejected) {
        throw transfer.failure(
          ApiFailure(
            error.code,
            kind: error.kind,
            outcome: CommandOutcome.uncertain,
            statusCode: error.statusCode,
            retryAfter: error.retryAfter,
          ),
          sent: true,
        );
      }
      throw transfer.failure(body?.failure ?? error, sent: attempted);
    } finally {
      transfer.close();
    }
  }

  Future<PrivateSnapshot> download(
    String typedPath, {
    required PrivateFileScope scope,
    required FileProof proof,
    CancelToken? cancelToken,
  }) async {
    validateApiPath(typedPath);
    proof._validate();
    final transfer = _Transfer(_identity, cancelToken, command: false);
    PrivateSink? sink;
    PrivateSnapshot? result;
    var accepted = false;
    try {
      transfer.check();
      if (scope.closed) throw _closed();
      final response = await _identity.authenticatedRequest(
        typedPath,
        responseType: ResponseType.stream,
        transferTimeout: _ioTimeout,
        cancelToken: transfer.token,
        headers: {'accept': proof.mediaType},
      );
      transfer.check();
      if (response.statusCode != 200 ||
          _mime(response.headers) != proof.mediaType) {
        throw _invalid();
      }
      final declared = _declaredLength(response.headers);
      if (declared != null && declared != proof.byteSize) throw _invalid();
      final source = _streamBody(response);
      sink = await _privateStep<PrivateSink>(
        scope.beginDownload(
          mediaType: proof.mediaType,
          maxBytes: clientMaxFileBytes,
          expectedByteSize: proof.byteSize,
          expectedSha256: proof.sha256,
        ),
        (late) => late.abort(),
      );
      transfer.check();
      final digest = _DigestSink();
      final hash = sha256.startChunkedConversion(digest);
      var count = 0;
      try {
        await for (final chunk in source.stream.timeout(_ioTimeout)) {
          transfer.check();
          if (scope.closed) throw _closed();
          if (count + chunk.length > proof.byteSize) throw _oversized();
          for (
            var offset = 0;
            offset < chunk.length;
            offset += channelChunkBytes
          ) {
            final end = (offset + channelChunkBytes < chunk.length)
                ? offset + channelChunkBytes
                : chunk.length;
            final bounded = Uint8List.fromList(chunk.sublist(offset, end));
            hash.add(bounded);
            await sink.append(bounded).timeout(_ioTimeout);
            transfer.check();
          }
          count += chunk.length;
        }
      } finally {
        hash.close();
      }
      transfer.check();
      if (count != proof.byteSize || digest.value.toString() != proof.sha256) {
        throw const ApiFailure(
          'file_integrity_failed',
          kind: ApiFailureKind.invalidResponse,
        );
      }
      result = await _privateStep<PrivateSnapshot>(
        sink.finish(),
        (late) => late.dispose(),
      );
      transfer.check();
      if (!proof._matches(result)) throw _invalid();
      await result.verify().timeout(_ioTimeout);
      transfer.check();
      accepted = true;
      return result;
    } catch (error) {
      throw transfer.failure(error);
    } finally {
      transfer.close();
      if (!accepted) {
        await _cleanup(() async => result?.dispose());
        await _cleanup(() async => sink?.abort());
      }
    }
  }
}

class _Transfer {
  final AuthRepository identity;
  final int generation;
  final bool command;
  final CancelToken token = CancelToken();
  late final void Function() _remove;
  late final Timer _deadline;
  bool _timedOut = false;
  _Transfer(this.identity, CancelToken? caller, {required this.command})
    : generation = identity.sessionGeneration {
    _remove = identity.onInvalidated(() => token.cancel());
    if (caller != null) {
      if (caller.isCancelled) {
        token.cancel();
      } else {
        caller.whenCancel.then((_) => token.cancel());
      }
    }
    _deadline = Timer(_totalTimeout, () {
      _timedOut = true;
      token.cancel();
    });
  }

  void check({bool sent = false}) {
    if (generation != identity.sessionGeneration || token.isCancelled) {
      throw ApiFailure(
        generation != identity.sessionGeneration
            ? 'invalid_session'
            : _timedOut
            ? 'request_timeout'
            : 'request_cancelled',
        kind: generation != identity.sessionGeneration
            ? ApiFailureKind.invalidSession
            : _timedOut
            ? ApiFailureKind.timeout
            : ApiFailureKind.cancelled,
        outcome: command && sent
            ? CommandOutcome.uncertain
            : command
            ? CommandOutcome.notSent
            : CommandOutcome.rejected,
      );
    }
  }

  ApiFailure failure(Object error, {bool sent = false}) {
    try {
      check(
        sent:
            sent &&
            !(error is ApiFailure && error.outcome == CommandOutcome.notSent),
      );
    } on ApiFailure catch (failure) {
      return failure;
    }
    if (error is ApiFailure) {
      return ApiFailure(
        RegExp(r'^[a-z][a-z0-9_]{0,79}$').hasMatch(error.code)
            ? error.code
            : 'file_transfer_failed',
        kind: error.kind,
        outcome: !sent && command ? CommandOutcome.notSent : error.outcome,
        statusCode: error.statusCode,
        retryAfter: error.retryAfter,
      );
    }
    if (error is DioException) {
      return ApiFailure.fromDio(error, command: command);
    }
    return ApiFailure(
      error is TimeoutException ? 'request_timeout' : 'file_transfer_failed',
      kind: error is TimeoutException
          ? ApiFailureKind.timeout
          : ApiFailureKind.unavailable,
      outcome: command && sent
          ? CommandOutcome.uncertain
          : command
          ? CommandOutcome.notSent
          : CommandOutcome.rejected,
    );
  }

  void close() {
    _deadline.cancel();
    _remove();
    token.cancel();
  }
}

class _UploadBody {
  final PrivateSnapshot snapshot;
  final FileProof proof;
  final _Transfer transfer;
  final void Function(int, int)? progress;
  bool complete = false;
  ApiFailure? failure;
  _UploadBody(this.snapshot, this.proof, this.transfer, this.progress);

  Stream<List<int>> stream() async* {
    final digest = _DigestSink();
    final hash = sha256.startChunkedConversion(digest);
    var count = 0;
    try {
      await for (final chunk in snapshot.openRead().timeout(_ioTimeout)) {
        transfer.check(sent: true);
        if (chunk.length > channelChunkBytes ||
            count + chunk.length > proof.byteSize) {
          throw _oversized(command: true);
        }
        final bounded = Uint8List.fromList(chunk);
        hash.add(bounded);
        count += bounded.length;
        yield bounded;
        progress?.call(count, proof.byteSize);
      }
      hash.close();
      if (count != proof.byteSize || digest.value.toString() != proof.sha256) {
        throw const ApiFailure(
          'file_integrity_failed',
          kind: ApiFailureKind.invalidResponse,
          outcome: CommandOutcome.uncertain,
        );
      }
      complete = true;
    } catch (error) {
      // Opening the body means the HTTP adapter may already have sent headers
      // or bytes. Native validation failures here cannot establish non-delivery.
      final problem =
          error is ApiFailure && error.outcome == CommandOutcome.notSent
          ? ApiFailure(
              error.code,
              kind: error.kind,
              outcome: CommandOutcome.uncertain,
              statusCode: error.statusCode,
              retryAfter: error.retryAfter,
            )
          : error;
      failure = transfer.failure(problem, sent: true);
      throw failure!;
    } finally {
      if (digest.value == null) hash.close();
    }
  }
}

class _DigestSink implements Sink<Digest> {
  Digest? value;
  @override
  void add(Digest data) => value = data;
  @override
  void close() {}
}

ResponseBody _streamBody(Response<dynamic> response) {
  if (response.data is! ResponseBody) throw _invalid();
  return response.data as ResponseBody;
}

String? _mime(Headers headers) =>
    headers.value('content-type')?.split(';').first.trim().toLowerCase();

int? _declaredLength(Headers headers) {
  final value = headers.value('content-length');
  if (value == null) return null;
  if (!RegExp(r'^[0-9]{1,12}$').hasMatch(value)) throw _invalid();
  return int.parse(value);
}

ApiFailure _invalid({bool command = false}) => ApiFailure(
  'invalid_response',
  kind: ApiFailureKind.invalidResponse,
  outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
);

ApiFailure _oversized({bool command = false}) => ApiFailure(
  'response_too_large',
  kind: ApiFailureKind.oversized,
  outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
);

ApiFailure _closed() =>
    const ApiFailure('private_file_closed', kind: ApiFailureKind.cancelled);

Future<void> _cleanup(Future<void> Function() action) async {
  try {
    await action().timeout(const Duration(seconds: 5));
  } catch (_) {
    // Cleanup remains within the caller's private scope; never expose native details.
  }
}

/// Future.timeout does not stop native work. Dispose a late private result too.
Future<T> _privateStep<T>(
  Future<T> operation,
  Future<void> Function(T) releaseLate,
) async {
  try {
    return await operation.timeout(_ioTimeout);
  } on TimeoutException {
    unawaited(
      operation.then<void>(
        (late) => _cleanup(() => releaseLate(late)),
        onError: (Object _, StackTrace _) {},
      ),
    );
    rethrow;
  }
}
