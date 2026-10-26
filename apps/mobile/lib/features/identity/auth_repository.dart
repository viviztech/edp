import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/request_safety.dart';

abstract interface class TokenStore {
  Future<String?> read();
  Future<void> write(String value);
  Future<void> clear();
}

class SecureTokenStore implements TokenStore {
  final FlutterSecureStorage storage;
  SecureTokenStore(this.storage);
  static const key = 'edp_refresh_token';
  @override
  Future<String?> read() => storage.read(key: key);
  @override
  Future<void> write(String value) => storage.write(key: key, value: value);
  @override
  Future<void> clear() => storage.delete(key: key);
}

class AuthFailure extends ApiFailure {
  const AuthFailure(
    super.code, {
    super.kind,
    super.outcome,
    super.statusCode,
    super.retryAfter,
  });

  factory AuthFailure.fromFailure(ApiFailure failure) => AuthFailure(
    failure.code,
    kind: failure.kind,
    outcome: failure.outcome,
    statusCode: failure.statusCode,
    retryAfter: failure.retryAfter,
  );
}

class OrganizationGrant {
  final String organizationId;
  final String organizationName;
  final Set<String> permissions;

  OrganizationGrant.fromJson(Map<String, dynamic> json)
    : organizationId = json['organization_id'] as String,
      organizationName = json['organization_name'] as String,
      permissions = Set.unmodifiable(
        (json['permissions'] as List).cast<String>(),
      );
}

class UserProfile {
  final String id;
  final String name;
  final String email;
  final String locale;
  final List<OrganizationGrant> grants;
  UserProfile.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      name = json['display_name'] as String,
      email = json['email'] as String,
      locale = (json['locale'] as String?) ?? 'en',
      grants = List.unmodifiable(
        ((json['grants'] as List?) ?? const []).map(
          (item) => OrganizationGrant.fromJson(
            Map<String, dynamic>.from(item as Map),
          ),
        ),
      );

  bool hasPermission(String organizationId, String permission) => grants.any(
    (grant) =>
        grant.organizationId == organizationId &&
        grant.permissions.contains(permission),
  );
}

class DeviceSession {
  final String id;
  final String name;
  final bool current;
  DeviceSession.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      name = json['device_name'] as String,
      current = json['current'] as bool;
}

class AuthRepository {
  // Raw Dio has no default bearer interceptor: public content stays anonymous.
  final Dio dio;
  final TokenStore _store;
  String? _access;
  Future<void>? _refreshing;
  int? _refreshGeneration;
  Future<void> _credentialOperations = Future.value();
  final Set<void Function()> _invalidations = {};
  int _generation = 0;
  AuthRepository(this.dio, TokenStore store) : _store = store;

  int get sessionGeneration => _generation;

  Future<void> _discardBody(Object? body) async {
    if (body is ResponseBody) {
      await body.stream.listen((_) {}, onError: (Object _) {}).cancel();
    }
  }

  void Function() onInvalidated(void Function() listener) {
    _invalidations.add(listener);
    return () => _invalidations.remove(listener);
  }

  Future<T> _credentials<T>(Future<T> Function() operation) {
    final next = _credentialOperations.then((_) => operation());
    _credentialOperations = next.then<void>(
      (_) {},
      onError: (Object _, StackTrace _) {},
    );
    return next;
  }

  Future<void> clearLocalSession() async {
    _generation++;
    _access = null;
    for (final listener in _invalidations.toList()) {
      listener();
    }
    await _credentials(() => _store.clear());
  }

  AuthFailure _failure(DioException error) {
    return AuthFailure.fromFailure(ApiFailure.fromDio(error));
  }

  Future<void> command(String operation, Map<String, dynamic> data) async {
    const allowed = {
      'register',
      'request-verification',
      'verify',
      'request-reset',
      'reset',
    };
    if (!allowed.contains(operation)) {
      throw const AuthFailure('invalid_request');
    }
    try {
      await dio.post<Map<String, dynamic>>(
        '/auth/$operation',
        data: data,
        options: Options(followRedirects: false, maxRedirects: 0),
      );
    } on DioException catch (error) {
      throw _failure(error);
    }
  }

  Future<UserProfile> login(String email, String password) async {
    final clearing = clearLocalSession();
    final generation = _generation;
    await clearing;
    if (generation != _generation) {
      throw const AuthFailure(
        'invalid_session',
        kind: ApiFailureKind.invalidSession,
        outcome: CommandOutcome.notSent,
      );
    }
    try {
      final response = await dio.post<Map<String, dynamic>>(
        '/auth/login',
        data: {
          'email': email,
          'password': password,
          'device_name': 'Flutter app',
        },
        options: Options(followRedirects: false, maxRedirects: 0),
      );
      await _save(response.data!, generation);
      return await profile();
    } on DioException catch (error) {
      throw _failure(error);
    }
  }

  Future<void> _save(Map<String, dynamic> data, int generation) async {
    final refresh = data['refresh_token'];
    final access = data['access_token'];
    if (refresh is! String ||
        refresh.isEmpty ||
        access is! String ||
        access.isEmpty) {
      throw const AuthFailure(
        'invalid_response',
        kind: ApiFailureKind.invalidResponse,
      );
    }
    await _credentials(() async {
      if (generation != _generation) {
        throw const AuthFailure(
          'invalid_session',
          kind: ApiFailureKind.invalidSession,
        );
      }
      // Never persist the access token or a password.
      await _store.write(refresh);
      if (generation != _generation) {
        await _store.clear();
        throw const AuthFailure(
          'invalid_session',
          kind: ApiFailureKind.invalidSession,
        );
      }
      _access = access;
    });
  }

  Future<void> _rotate() async {
    final generation = _generation;
    try {
      final refresh = await _credentials(() => _store.read());
      if (refresh == null || generation != _generation) {
        throw const AuthFailure(
          'invalid_session',
          kind: ApiFailureKind.invalidSession,
        );
      }
      final response = await dio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'token': refresh},
        options: Options(followRedirects: false, maxRedirects: 0),
      );
      await _save(response.data!, generation);
    } catch (error) {
      // Rotation timeout can mean the old token was consumed. Do not replay it.
      if (generation == _generation) await clearLocalSession();
      if (error is DioException) throw _failure(error);
      rethrow;
    }
  }

  Future<void> _refresh() async {
    if (_refreshing != null && _refreshGeneration == _generation) {
      return _refreshing!;
    }
    final pending = _rotate();
    _refreshing = pending;
    _refreshGeneration = _generation;
    try {
      await pending;
    } finally {
      if (identical(_refreshing, pending)) {
        _refreshing = null;
        _refreshGeneration = null;
      }
    }
  }

  /// Protected transport. A command is sent once; only a safe read can replay.
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
  }) async {
    validateApiPath(path);
    final safeHeaders = validateApiHeaders(headers);
    final verb = method.toUpperCase();
    if (!{'GET', 'POST', 'PATCH', 'PUT', 'DELETE'}.contains(verb)) {
      throw const ApiFailure(
        'unsafe_request',
        kind: ApiFailureKind.unsafeRequest,
        outcome: CommandOutcome.notSent,
      );
    }
    if ((bodyLength != null &&
            (verb != 'PUT' ||
                data is! Stream<List<int>> ||
                bodyLength <= 0 ||
                bodyLength > 10 * 1024 * 1024)) ||
        (transferTimeout != null &&
            (transferTimeout <= Duration.zero ||
                transferTimeout > const Duration(minutes: 2)))) {
      throw const ApiFailure(
        'unsafe_request',
        kind: ApiFailureKind.unsafeRequest,
        outcome: CommandOutcome.notSent,
      );
    }
    final generation = _generation;
    final command = verb != 'GET';
    if (_access == null) {
      try {
        await _refresh();
      } on ApiFailure catch (failure) {
        throw ApiFailure(
          failure.code,
          kind: failure.kind,
          outcome: CommandOutcome.notSent,
          statusCode: failure.statusCode,
          retryAfter: failure.retryAfter,
        );
      }
    }
    if (generation != _generation || _access == null) {
      throw const ApiFailure(
        'invalid_session',
        kind: ApiFailureKind.invalidSession,
        outcome: CommandOutcome.notSent,
      );
    }
    CancelToken? activeAttempt;
    Future<Response<dynamic>> send() async {
      final attempt = CancelToken();
      activeAttempt = attempt;
      if (cancelToken != null) {
        if (cancelToken.isCancelled) {
          attempt.cancel();
        } else {
          cancelToken.whenCancel.then((_) => attempt.cancel());
        }
      }
      final response = await dio.request<dynamic>(
        path,
        data: data,
        queryParameters: queryParameters,
        cancelToken: attempt,
        options: Options(
          method: verb,
          responseType: responseType,
          followRedirects: false,
          maxRedirects: 0,
          sendTimeout: transferTimeout,
          receiveTimeout: transferTimeout,
          validateStatus: (status) =>
              status != null && status >= 200 && status < 300,
          headers: {
            ...safeHeaders,
            if (bodyLength != null) Headers.contentLengthHeader: '$bodyLength',
            'Authorization': 'Bearer $_access',
          },
        ),
      );
      if (generation != _generation) {
        attempt.cancel();
        await _discardBody(response.data);
        throw const ApiFailure(
          'invalid_session',
          kind: ApiFailureKind.invalidSession,
        );
      }
      return response;
    }

    final used = _access;
    try {
      return await send();
    } on DioException catch (error) {
      activeAttempt?.cancel();
      await _discardBody(error.response?.data);
      if (generation != _generation) {
        throw const ApiFailure(
          'invalid_session',
          kind: ApiFailureKind.invalidSession,
        );
      }
      if (error.response?.statusCode != 401) {
        throw ApiFailure.fromDio(error, command: command);
      }
      if (command) {
        // Recover only for the next explicit action, never replay this write.
        if (_access == used) await _refresh();
        throw ApiFailure.fromDio(error, command: true);
      }
      if (_access == used) await _refresh();
      try {
        return await send();
      } on DioException catch (retryError) {
        activeAttempt?.cancel();
        await _discardBody(retryError.response?.data);
        if (retryError.response?.statusCode == 401 &&
            generation == _generation) {
          await clearLocalSession();
        }
        throw ApiFailure.fromDio(retryError);
      }
    }
  }

  Future<UserProfile> profile() async {
    try {
      final response = await authenticatedRequest('/auth/me');
      return UserProfile.fromJson(
        Map<String, dynamic>.from(response.data as Map),
      );
    } on ApiFailure catch (failure) {
      throw AuthFailure.fromFailure(failure);
    } on TypeError {
      throw const AuthFailure(
        'invalid_response',
        kind: ApiFailureKind.invalidResponse,
      );
    }
  }

  Future<UserProfile?> restore() async {
    if (await _credentials(() => _store.read()) == null) return null;
    return profile();
  }

  Future<List<DeviceSession>> sessions() async {
    final response = await authenticatedRequest('/auth/sessions');
    return (response.data as List)
        .map(
          (item) =>
              DeviceSession.fromJson(Map<String, dynamic>.from(item as Map)),
        )
        .toList();
  }

  Future<void> revoke(String id) async {
    await profile(); // Refresh before an explicit state-changing command.
    try {
      await authenticatedRequest(
        '/auth/sessions/$id/revoke',
        method: 'POST',
        data: <String, dynamic>{},
      );
    } on ApiFailure catch (failure) {
      throw AuthFailure.fromFailure(failure);
    }
  }

  Future<void> logout({bool all = false}) async {
    final access = _access;
    // Local sign-out must survive process death while the network is unavailable.
    await clearLocalSession();
    if (access == null) {
      throw const AuthFailure(
        'invalid_session',
        kind: ApiFailureKind.invalidSession,
        outcome: CommandOutcome.notSent,
      );
    }
    try {
      await dio.post<dynamic>(
        all ? '/auth/logout-all' : '/auth/logout',
        data: <String, dynamic>{},
        options: Options(
          followRedirects: false,
          maxRedirects: 0,
          headers: {'Authorization': 'Bearer $access'},
          validateStatus: (status) =>
              status != null && status >= 200 && status < 300,
        ),
      );
    } on DioException catch (error) {
      throw AuthFailure.fromFailure(ApiFailure.fromDio(error, command: true));
    }
  }
}
