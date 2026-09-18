import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

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

class AuthFailure implements Exception {
  final String code;
  const AuthFailure(this.code);
}

class UserProfile {
  final String id;
  final String name;
  final String email;
  UserProfile.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      name = json['display_name'] as String,
      email = json['email'] as String;
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
  final Dio dio;
  final TokenStore store;
  String? _access;
  Future<void>? _refreshing;
  AuthRepository(this.dio, this.store);

  AuthFailure _failure(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['error'] is Map) {
      return AuthFailure(
        (data['error'] as Map)['code'] as String? ?? 'request_failed',
      );
    }
    return const AuthFailure('service_unavailable');
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
      await dio.post<Map<String, dynamic>>('/auth/$operation', data: data);
    } on DioException catch (error) {
      throw _failure(error);
    }
  }

  Future<UserProfile> login(String email, String password) async {
    try {
      final response = await dio.post<Map<String, dynamic>>(
        '/auth/login',
        data: {
          'email': email,
          'password': password,
          'device_name': 'Flutter app',
        },
      );
      await _save(response.data!);
      return await profile();
    } on DioException catch (error) {
      throw _failure(error);
    }
  }

  Future<void> _save(Map<String, dynamic> data) async {
    // Never persist the access token or a password.
    await store.write(data['refresh_token'] as String);
    _access = data['access_token'] as String;
  }

  Future<void> _rotate() async {
    final refresh = await store.read();
    if (refresh == null) throw const AuthFailure('invalid_session');
    try {
      final response = await dio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'token': refresh},
      );
      await _save(response.data!);
    } catch (_) {
      // Rotation timeout can mean the old token was consumed. Do not replay it.
      _access = null;
      await store.clear();
      rethrow;
    }
  }

  Future<void> _refresh() async {
    if (_refreshing != null) return _refreshing!;
    final pending = _rotate();
    _refreshing = pending;
    try {
      await pending;
    } finally {
      _refreshing = null;
    }
  }

  Future<Response<dynamic>> _get(String path) async {
    final used = _access;
    try {
      if (_access == null) await _refresh();
      return await dio.get<dynamic>(
        path,
        options: Options(headers: {'Authorization': 'Bearer $_access'}),
      );
    } on DioException catch (error) {
      if (error.response?.statusCode != 401) throw _failure(error);
      try {
        if (_access == used) await _refresh();
        return await dio.get<dynamic>(
          path,
          options: Options(headers: {'Authorization': 'Bearer $_access'}),
        );
      } on DioException catch (retryError) {
        _access = null;
        await store.clear();
        throw _failure(retryError);
      }
    }
  }

  Future<UserProfile> profile() async {
    final response = await _get('/auth/me');
    return UserProfile.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }

  Future<UserProfile?> restore() async {
    if (await store.read() == null) return null;
    return profile();
  }

  Future<List<DeviceSession>> sessions() async {
    final response = await _get('/auth/sessions');
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
      await dio.post<void>(
        '/auth/sessions/$id/revoke',
        data: <String, dynamic>{},
        options: Options(headers: {'Authorization': 'Bearer $_access'}),
      );
    } on DioException catch (error) {
      throw _failure(error);
    }
  }

  Future<void> logout({bool all = false}) async {
    try {
      await profile();
      await dio.post<void>(
        all ? '/auth/logout-all' : '/auth/logout',
        data: <String, dynamic>{},
        options: Options(headers: {'Authorization': 'Bearer $_access'}),
      );
    } on DioException catch (error) {
      throw _failure(error);
    } finally {
      _access = null;
      await store.clear();
    }
  }
}
