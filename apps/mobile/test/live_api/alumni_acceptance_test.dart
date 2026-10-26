import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:dio/io.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/features/alumni/alumni_repository.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import '../alumni_test.dart' show profileFields;
import 'helpers.dart' show SyntheticTokenStore, apiFailureWithStatus;

const enabled = bool.fromEnvironment('MOBILE_ACCEPTANCE_SYNTHETIC_ONLY');
const path = String.fromEnvironment('MOBILE_ACCEPTANCE_FIXTURE');

class _Overrides extends HttpOverrides {}

class _Client {
  final Dio dio;
  final AuthRepository identity;
  late final api = DomainApi(identity);
  late final repository = AlumniRepository(api);
  _Client(this.dio, this.identity);
  void close() => dio.close(force: true);
}

class _DropResponse implements HttpClientAdapter {
  final HttpClientAdapter delegate;
  final String ending;
  int commands = 0;
  _DropResponse(this.delegate, this.ending);
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final response = await delegate.fetch(options, requestStream, cancelFuture);
    if (options.method == 'POST' && options.path.endsWith(ending)) {
      commands++;
      if (commands == 1 &&
          response.statusCode >= 200 &&
          response.statusCode < 300) {
        await response.stream.drain<void>();
        throw DioException(
          requestOptions: options,
          type: DioExceptionType.connectionError,
        );
      }
    }
    return response;
  }

  @override
  void close({bool force = false}) => delegate.close(force: force);
}

void main() {
  group(
    'M05 real synthetic Flutter API acceptance',
    () {
      late Map<String, dynamic> fixture;
      late String org, other;
      String enrollment(String name) =>
          (fixture['enrollments'] as Map)[name] as String;
      Future<_Client> signIn(String name) async {
        final account = (fixture['accounts'] as Map)[name] as Map;
        final dio = Dio(
          BaseOptions(
            baseUrl: fixture['api_base'] as String,
            connectTimeout: const Duration(seconds: 5),
            receiveTimeout: const Duration(seconds: 10),
            sendTimeout: const Duration(seconds: 10),
          ),
        );
        dio.httpClientAdapter = IOHttpClientAdapter(
          createHttpClient: () =>
              _Overrides().createHttpClient(null)..findProxy = (_) => 'DIRECT',
        );
        final identity = AuthRepository(dio, SyntheticTokenStore());
        await identity.login(
          account['email'] as String,
          account['password'] as String,
        );
        return _Client(dio, identity);
      }

      setUpAll(() {
        final file = File(path),
            root = Directory('../../.tool-cache').resolveSymbolicLinksSync();
        if (!file.resolveSymbolicLinksSync().startsWith(
              '$root${Platform.pathSeparator}mobile-api-alumni-',
            ) ||
            file.lengthSync() > 128 * 1024) {
          throw StateError('Invalid synthetic fixture');
        }
        fixture = Map<String, dynamic>.from(
          jsonDecode(file.readAsStringSync()) as Map,
        );
        final base = Uri.parse(fixture['api_base'] as String);
        if (fixture['synthetic_only'] != true ||
            base.scheme != 'http' ||
            base.host != '127.0.0.1' ||
            base.port != 8217 ||
            base.path != '/api/v1') {
          throw StateError('Invalid synthetic fixture');
        }
        org = fixture['organization_id'] as String;
        other = fixture['other_organization_id'] as String;
      });
      test(
        'lost private profile creation reads one saved record then updates with versioned immutable history',
        () async {
          final client = await signIn('owner');
          addTearDown(client.close);
          final dropped = _DropResponse(
            client.dio.httpClientAdapter,
            '/profiles',
          );
          client.dio.httpClientAdapter = dropped;
          await expectLater(
            client.repository.saveProfile(
              org,
              enrollment('owner'),
              profileFields(),
            ),
            throwsA(
              isA<ApiFailure>().having((e) => e.uncertain, 'uncertain', true),
            ),
          );
          final saved = (await client.repository.businesses(
            org,
          )).singleWhere((e) => e.enrollmentId == enrollment('owner')).profile!;
          expect(saved.version, 1);
          expect(saved.revisions, hasLength(1));
          expect(saved.followUps, hasLength(5));
          expect(dropped.commands, 1);
          final updated = await client.repository.saveProfile(
            org,
            enrollment('owner'),
            {...profileFields(), 'name': 'Updated synthetic bakery'},
            previous: saved,
          );
          expect(updated.version, 2);
          expect(updated.revisions.map((r) => r.version), [2, 1]);
          expect(
            updated.followUps.map((f) => f.dueOn),
            saved.followUps.map((f) => f.dueOn),
          );
          await expectLater(
            client.repository.saveProfile(
              org,
              enrollment('owner'),
              profileFields(),
              previous: saved,
            ),
            throwsA(apiFailureWithStatus(409)),
          );
        },
      );
      test(
        'completed owner is eligible while peer and organization ownership remain denied',
        () async {
          final alumni = await signIn('alumnus'), peer = await signIn('peer');
          addTearDown(alumni.close);
          addTearDown(peer.close);
          final entries = await alumni.repository.businesses(org);
          expect(entries.single.enrollmentId, enrollment('alumnus'));
          expect(
            (await alumni.repository.saveProfile(
              org,
              enrollment('alumnus'),
              profileFields(),
            )).enrollmentId,
            enrollment('alumnus'),
          );
          await expectLater(
            peer.repository.saveProfile(
              org,
              enrollment('owner'),
              profileFields(),
            ),
            throwsA(apiFailureWithStatus(404)),
          );
          await expectLater(
            alumni.repository.businesses(other),
            throwsA(apiFailureWithStatus(403)),
          );
        },
      );
      test(
        'outcome is immutable and lost response reconciles without a second write',
        () async {
          final owner = await signIn('owner'), peer = await signIn('peer');
          addTearDown(owner.close);
          addTearDown(peer.close);
          final profile = (await owner.repository.businesses(
            org,
          )).singleWhere((e) => e.enrollmentId == enrollment('owner')).profile!;
          final follow = profile.followUps.first;
          final body = {
            'reported_on': DateTime.now().toUtc().toIso8601String().substring(
              0,
              10,
            ),
            'business_started': true,
            'business_active': true,
            'jobs_created': 2,
            'funding_band': 'undisclosed',
            'revenue_band': 'undisclosed',
            'challenges': 'Synthetic only',
            'support_requested': null,
            'mentor_interventions': null,
            'outcomes': null,
          };
          await expectLater(
            peer.repository.submitOutcome(org, follow.id, body),
            throwsA(apiFailureWithStatus(404)),
          );
          await expectLater(
            owner.api.post(
              '/businesses/organizations/$org/follow-ups/${follow.id}/outcome',
              data: {...body, 'reported_on': '2999-01-01'},
            ),
            throwsA(apiFailureWithStatus(422)),
          );
          await expectLater(
            owner.api.post(
              '/businesses/organizations/$org/follow-ups/${follow.id}/outcome',
              data: {...body, 'business_started': false},
            ),
            throwsA(apiFailureWithStatus(422)),
          );
          final drop = _DropResponse(owner.dio.httpClientAdapter, '/outcome');
          owner.dio.httpClientAdapter = drop;
          await expectLater(
            owner.repository.submitOutcome(org, follow.id, body),
            throwsA(
              isA<ApiFailure>().having((e) => e.uncertain, 'uncertain', true),
            ),
          );
          final current = (await owner.repository.businesses(org))
              .singleWhere((e) => e.enrollmentId == enrollment('owner'))
              .profile!
              .followUps
              .singleWhere((f) => f.id == follow.id);
          expect(current.status, 'completed');
          expect(current.outcome!.fields['jobs_created'], 2);
          expect(drop.commands, 1);
          await expectLater(
            owner.repository.submitOutcome(org, follow.id, body),
            throwsA(apiFailureWithStatus(409)),
          );
        },
      );
      test(
        'independent impact cursors, definition pinning, revision and unchanged idempotency replay',
        () async {
          final client = await signIn('owner'), peer = await signIn('peer');
          addTearDown(client.close);
          addTearDown(peer.close);
          final first = await client.repository.impact(org);
          expect(first.enrollments, hasLength(25));
          expect(first.definitions, hasLength(25));
          expect(first.enrollmentCursor, isNotNull);
          expect(first.definitionCursor, isNotNull);
          final nextEnrollments = await client.repository.impact(
            org,
            enrollmentCursor: first.enrollmentCursor,
          );
          expect(nextEnrollments.enrollments, hasLength(1));
          expect(
            nextEnrollments.definitions.first.id,
            first.definitions.first.id,
          );
          final nextDefinitions = await client.repository.impact(
            org,
            definitionCursor: first.definitionCursor,
          );
          expect(nextDefinitions.definitions, hasLength(2));
          expect(
            nextDefinitions.enrollments.first.id,
            first.enrollments.first.id,
          );
          final body = {
            'enrollment_id': enrollment('owner'),
            'definition_id': first.definitions.first.id,
            'stage': 'baseline',
            'observed_on': DateTime.now().toUtc().toIso8601String().substring(
              0,
              10,
            ),
            'business_started': false,
            'business_active': false,
            'jobs_created': 0,
            'expected_revision': 0,
            'reason': 'Synthetic baseline',
            'request_id': newAlumniRequestId(),
          };
          final record = await client.repository.recordImpact(org, body);
          expect(record.revision, 1);
          expect(
            (await client.repository.recordImpact(org, body)).id,
            record.id,
          );
          await expectLater(
            client.repository.recordImpact(org, {
              ...body,
              'reason': 'Changed body with same request',
            }),
            throwsA(apiFailureWithStatus(409)),
          );
          await expectLater(
            peer.repository.recordImpact(org, {
              ...body,
              'request_id': newAlumniRequestId(),
            }),
            throwsA(apiFailureWithStatus(403)),
          );
          await expectLater(
            client.repository.recordImpact(org, {
              ...body,
              'request_id': newAlumniRequestId(),
              'expected_revision': 1,
              'definition_id': first.definitions[1].id,
            }),
            throwsA(apiFailureWithStatus(409)),
          );
          final revised = await client.repository.recordImpact(org, {
            ...body,
            'request_id': newAlumniRequestId(),
            'expected_revision': 1,
            'reason': 'Synthetic corrected baseline',
            'jobs_created': 1,
          });
          expect(revised.revision, 2);
          final history = await client.repository.impact(
            org,
            enrollmentId: enrollment('owner'),
            stage: 'baseline',
            observedOn: body['observed_on'] as String,
          );
          expect(history.records.map((r) => r.revision), [2, 1]);
          expect(
            (await client.repository.impact(
              org,
              enrollmentId: enrollment('owner'),
              stage: 'outcome',
            )).records,
            isEmpty,
          );
        },
      );
      test(
        'enrollment updates paginate, revalidate schedule targets, and version read/preferences',
        () async {
          final owner = await signIn('owner'), peer = await signIn('peer');
          addTearDown(owner.close);
          addTearDown(peer.close);
          final page = await owner.repository.notices(org);
          expect(page.items, hasLength(25));
          expect(page.cursor, isNotNull);
          final next = await owner.repository.notices(org, cursor: page.cursor);
          expect(next.items, hasLength(1));
          final notice = page.items.first;
          expect(
            await owner.repository.scheduleTarget(org, notice.id),
            notice.enrollmentId,
          );
          await expectLater(
            peer.repository.markRead(org, notice),
            throwsA(apiFailureWithStatus(404)),
          );
          expect(
            (await owner.repository.markRead(org, notice)).readAt,
            isNotNull,
          );
          await expectLater(
            owner.repository.markRead(org, notice),
            throwsA(apiFailureWithStatus(409)),
          );
          final preference = await owner.repository.preference(org);
          final disabled = await owner.repository.setPreference(
            org,
            preference,
            false,
          );
          expect(disabled.enabled, false);
          await expectLater(
            owner.repository.setPreference(org, preference, true),
            throwsA(apiFailureWithStatus(409)),
          );
          expect(
            (await owner.repository.setPreference(org, disabled, true)).enabled,
            true,
          );
          await expectLater(
            owner.api.get('/notifications/organizations/$org/mine'),
            throwsA(apiFailureWithStatus(403)),
          );
        },
      );
      test(
        'revoked session cannot reload private business, impact or inbox data',
        () async {
          final owner = await signIn('owner');
          addTearDown(owner.close);
          await owner.api.post('/auth/logout', data: <String, dynamic>{});
          await expectLater(
            owner.repository.businesses(org),
            throwsA(isA<ApiFailure>()),
          );
          await expectLater(
            owner.repository.impact(org),
            throwsA(isA<ApiFailure>()),
          );
          await expectLater(
            owner.repository.notices(org),
            throwsA(isA<ApiFailure>()),
          );
        },
      );
    },
    skip: !enabled || path.isEmpty
        ? 'Requires the owned synthetic M05 runner.'
        : false,
  );
}
