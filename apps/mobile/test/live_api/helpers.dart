import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:dio/io.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:flutter_test/flutter_test.dart';

const _syntheticOnly = bool.fromEnvironment('MOBILE_ACCEPTANCE_SYNTHETIC_ONLY');
const _fixturePath = String.fromEnvironment('MOBILE_ACCEPTANCE_FIXTURE');

/// Ordinary widget/unit suites must never contact even a loopback service.
String? get liveAcceptanceSkipReason => !_syntheticOnly || _fixturePath.isEmpty
    ? 'Requires the owned synthetic mobile/API acceptance runner.'
    : null;

void _require(bool accepted) {
  if (!accepted) throw StateError('Invalid synthetic mobile/API fixture');
}

Map<String, dynamic> jsonObject(Object? value) {
  _require(value is Map);
  return Map<String, dynamic>.from(value as Map);
}

List<Map<String, dynamic>> jsonItems(Object? value) {
  final items = jsonObject(value)['items'];
  _require(items is List);
  return (items as List).map(jsonObject).toList();
}

Matcher apiFailureWithStatus(int status) => isA<ApiFailure>().having(
  (failure) => failure.statusCode,
  'HTTP status',
  status,
);

/// The memory store exists only in acceptance tests; production still uses the
/// OS secure-storage plugin. Its values are never included in test descriptions.
class SyntheticTokenStore implements TokenStore {
  String? _value;

  bool get hasRefreshToken => _value != null;

  @override
  Future<String?> read() async => _value;

  @override
  Future<void> write(String value) async {
    _value = value;
  }

  @override
  Future<void> clear() async {
    _value = null;
  }
}

// Bypass Flutter's widget-test HTTP mock only after the fixture and exact
// loopback destination have passed validation. No external proxy is used.
class _SyntheticHttpOverrides extends HttpOverrides {}

class LiveApiClient {
  final Dio dio;
  final SyntheticTokenStore tokens;
  AuthRepository identity;
  DomainApi api;
  final UserProfile profile;

  LiveApiClient._(this.dio, this.tokens, this.identity, this.api, this.profile);

  Future<UserProfile?> restoreInNewRepository() async {
    identity = AuthRepository(dio, tokens);
    api = DomainApi(identity);
    return identity.restore();
  }

  Future<void> close() async {
    try {
      await identity.logout();
    } catch (_) {
      await identity.clearLocalSession();
    } finally {
      dio.close(force: true);
    }
  }
}

class LiveApiFixture {
  final Map<String, dynamic> _fixture;
  final Uri apiBase;
  final String organizationId;
  final String otherOrganizationId;

  LiveApiFixture._(
    this._fixture,
    this.apiBase,
    this.organizationId,
    this.otherOrganizationId,
  );

  static LiveApiFixture load() {
    _require(liveAcceptanceSkipReason == null);
    try {
      final cache = Directory('../../.tool-cache').resolveSymbolicLinksSync();
      final file = File(_fixturePath);
      final resolved = file.resolveSymbolicLinksSync();
      _require(
        resolved.startsWith('$cache${Platform.pathSeparator}mobile-api-'),
      );
      _require(file.uri.pathSegments.last == 'fixture.json');
      _require(file.lengthSync() <= 128 * 1024);
      final fixture = jsonObject(jsonDecode(file.readAsStringSync()));
      _require(fixture['synthetic_only'] == true);
      final base = Uri.parse(fixture['api_base'] as String);
      _require(
        base.scheme == 'http' && base.host == '127.0.0.1' && base.port == 8115,
      );
      _require(
        base.path == '/api/v1' &&
            base.userInfo.isEmpty &&
            base.query.isEmpty &&
            base.fragment.isEmpty,
      );
      final organization = fixture['organization_id'] as String;
      final otherOrganization = fixture['other_organization_id'] as String;
      final uuid = RegExp(
        r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
      );
      _require(uuid.hasMatch(organization) && uuid.hasMatch(otherOrganization));
      _require(organization != otherOrganization);
      _require(fixture['accounts'] is Map && fixture['enrollments'] is Map);
      return LiveApiFixture._(fixture, base, organization, otherOrganization);
    } catch (_) {
      // JSON/parser/filesystem errors can contain source snippets. Keep fixture
      // passwords and paths out of exception output even on malformed input.
      throw StateError('Invalid synthetic mobile/API fixture');
    }
  }

  Map<String, dynamic> enrollment(String name) =>
      jsonObject(jsonObject(_fixture['enrollments'])[name]);

  Map<String, dynamic> get applicationIntake =>
      jsonObject(_fixture['application_intake']);

  Map<String, dynamic> get documentIntake =>
      jsonObject(_fixture['document_intake']);
  Map<String, dynamic> get domainIntake =>
      jsonObject(_fixture['domain_intake']);

  Future<void> requestSyntheticScan(
    String fileId, {
    bool infected = false,
  }) async {
    _require(
      _fixture['document_intake'] is Map || _fixture['domain_intake'] is Map,
    );
    _require(RegExp(r'^[0-9a-f-]{36}$').hasMatch(fileId));
    final marker = File.fromUri(
      File(_fixturePath).parent.uri.resolve('scan-$fileId.json'),
    );
    await marker.writeAsString(
      jsonEncode({
        'file_id': fileId,
        'outcome': infected ? 'infected' : 'clean',
      }),
      flush: true,
    );
  }

  String accountUserId(String name) =>
      jsonObject(jsonObject(_fixture['accounts'])[name])['user_id'] as String;

  Future<LiveApiClient> signIn(String name) async {
    final account = jsonObject(jsonObject(_fixture['accounts'])[name]);
    final email = account['email'];
    final password = account['password'];
    _require(email is String && email.endsWith('@example.com'));
    _require(
      password is String && password.length >= 12 && password.length <= 128,
    );
    final dio = _newDio();
    final tokens = SyntheticTokenStore();
    final identity = AuthRepository(dio, tokens);
    try {
      final profile = await identity.login(email as String, password as String);
      return LiveApiClient._(
        dio,
        tokens,
        identity,
        DomainApi(identity),
        profile,
      );
    } catch (_) {
      await identity.clearLocalSession();
      dio.close(force: true);
      rethrow;
    }
  }

  Dio _newDio() {
    final dio = Dio(
      BaseOptions(
        baseUrl: apiBase.toString(),
        connectTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 10),
        sendTimeout: const Duration(seconds: 10),
      ),
    );
    dio.httpClientAdapter = IOHttpClientAdapter(
      createHttpClient: () {
        final client = _SyntheticHttpOverrides().createHttpClient(null);
        client.findProxy = (_) => 'DIRECT';
        return client;
      },
    );
    return dio;
  }

  Future<LiveApiClient> registerApplicant() async {
    final registration = jsonObject(_fixture['registration']);
    final email = registration['email'] as String;
    final password = registration['password'] as String;
    _require(
      email.endsWith('@example.com') &&
          password.length >= 12 &&
          password.length <= 128,
    );
    final dio = _newDio();
    final tokens = SyntheticTokenStore();
    final identity = AuthRepository(dio, tokens);
    try {
      await identity.command('register', {
        'email': email,
        'password': password,
        'display_name': 'Synthetic fresh applicant',
        'locale': 'ta',
      });
      final mailbox = File(
        _fixturePath,
      ).parent.uri.resolve('verification.json');
      final deadline = DateTime.now().add(const Duration(seconds: 20));
      while (!await File.fromUri(mailbox).exists()) {
        _require(DateTime.now().isBefore(deadline));
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
      final mail = File.fromUri(mailbox);
      _require(await mail.length() <= 4096);
      final token = jsonObject(jsonDecode(await mail.readAsString()))['token'];
      _require(token is String && token.length < 512);
      await identity.command('verify', {'token': token});
      final profile = await identity.login(email, password);
      return LiveApiClient._(
        dio,
        tokens,
        identity,
        DomainApi(identity),
        profile,
      );
    } catch (_) {
      await identity.clearLocalSession();
      dio.close(force: true);
      rethrow;
    }
  }
}
