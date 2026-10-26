import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../../features/identity/auth_repository.dart';
import 'api_failure.dart';

/// Feature repositories supply typed DTOs; credentials remain with identity.
class DomainApi {
  final AuthRepository _identity;
  DomainApi(AuthRepository identity) : _identity = identity;

  Future<dynamic> get(String path, {Map<String, dynamic>? queryParameters}) =>
      _json(path, queryParameters: queryParameters);

  Future<dynamic> post(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      _json(path, method: 'POST', data: data, queryParameters: queryParameters);

  Future<dynamic> patch(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) => _json(
    path,
    method: 'PATCH',
    data: data,
    queryParameters: queryParameters,
  );

  Future<dynamic> put(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      _json(path, method: 'PUT', data: data, queryParameters: queryParameters);

  Future<dynamic> delete(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) => _json(
    path,
    method: 'DELETE',
    data: data,
    queryParameters: queryParameters,
  );

  Future<dynamic> _json(
    String path, {
    String method = 'GET',
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _identity.authenticatedRequest(
      path,
      method: method,
      data: data,
      queryParameters: queryParameters,
    );
    return response.data;
  }

  /// Streams are bounded before accumulating, including unknown Content-Length.
  /// Uploads accept an already bounded immutable snapshot, never a source URI.
  Future<Uint8List> requestBytes(
    String path, {
    String method = 'GET',
    Uint8List? data,
    Map<String, String>? headers,
    int maxBytes = 10 * 1024 * 1024,
  }) async {
    if (maxBytes <= 0 ||
        maxBytes > 50 * 1024 * 1024 ||
        (data != null && data.length > maxBytes)) {
      throw const ApiFailure(
        'response_too_large',
        kind: ApiFailureKind.oversized,
        outcome: CommandOutcome.notSent,
      );
    }
    final cancellation = CancelToken();
    final generation = _identity.sessionGeneration;
    final remove = _identity.onInvalidated(() => cancellation.cancel());
    final bytes = BytesBuilder(copy: false);
    var responseReceived = false;
    try {
      final response = await _identity.authenticatedRequest(
        path,
        method: method,
        data: data == null ? null : Uint8List.fromList(data),
        headers: headers,
        responseType: ResponseType.stream,
        cancelToken: cancellation,
      );
      responseReceived = true;
      final body = response.data;
      if (body is! ResponseBody) {
        throw const ApiFailure(
          'invalid_response',
          kind: ApiFailureKind.invalidResponse,
        );
      }
      final declared = int.tryParse(
        response.headers.value('content-length') ?? '',
      );
      if (declared != null && (declared < 0 || declared > maxBytes)) {
        await body.stream.listen((_) {}).cancel();
        throw const ApiFailure(
          'response_too_large',
          kind: ApiFailureKind.oversized,
        );
      }
      await for (final chunk in body.stream) {
        if (generation != _identity.sessionGeneration) {
          throw const ApiFailure(
            'invalid_session',
            kind: ApiFailureKind.invalidSession,
          );
        }
        if (bytes.length + chunk.length > maxBytes) {
          throw const ApiFailure(
            'response_too_large',
            kind: ApiFailureKind.oversized,
          );
        }
        bytes.add(chunk);
      }
      if (generation != _identity.sessionGeneration) {
        throw const ApiFailure(
          'invalid_session',
          kind: ApiFailureKind.invalidSession,
        );
      }
      if (declared != null && bytes.length != declared) {
        throw const ApiFailure(
          'invalid_response',
          kind: ApiFailureKind.invalidResponse,
        );
      }
      return bytes.takeBytes();
    } on DioException catch (error) {
      if (generation != _identity.sessionGeneration) {
        throw const ApiFailure(
          'invalid_session',
          kind: ApiFailureKind.invalidSession,
        );
      }
      throw ApiFailure.fromDio(error, command: method.toUpperCase() != 'GET');
    } on ApiFailure catch (failure) {
      if (method.toUpperCase() != 'GET' &&
          responseReceived &&
          failure.outcome == CommandOutcome.rejected) {
        throw ApiFailure(
          failure.code,
          kind: failure.kind,
          outcome: CommandOutcome.uncertain,
          statusCode: failure.statusCode,
          retryAfter: failure.retryAfter,
        );
      }
      rethrow;
    } catch (_) {
      throw ApiFailure(
        'request_failed',
        kind: ApiFailureKind.unavailable,
        outcome: method.toUpperCase() == 'GET'
            ? CommandOutcome.rejected
            : CommandOutcome.uncertain,
      );
    } finally {
      remove();
      cancellation.cancel();
      bytes.clear();
    }
  }
}
