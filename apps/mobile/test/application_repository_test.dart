import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/features/applications/application_models.dart';
import 'package:edp_mobile/features/applications/application_repository.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fixtures/application_fixture.dart';

class _NoTokens implements TokenStore {
  @override
  Future<void> clear() async {}
  @override
  Future<String?> read() async => null;
  @override
  Future<void> write(String value) async {}
}

class _Api extends DomainApi {
  _Api() : super(AuthRepository(Dio(), _NoTokens()));
  Object? response = applicationRecordJson();
  final requests = <(String, String, Object?)>[];
  @override
  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    requests.add(('GET', path, queryParameters));
    return response;
  }

  @override
  Future<dynamic> post(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    requests.add(('POST', path, data));
    return response;
  }

  @override
  Future<dynamic> patch(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    requests.add(('PATCH', path, data));
    return response;
  }
}

void main() {
  test(
    'save uses the authoritative expected version and all pinned field IDs',
    () async {
      final api = _Api()
        ..response = applicationRecordJson(version: 3, answer: 'Saved');
      final repository = ApplicationRepository(api);
      final result = await repository.save(
        applicationOrg,
        applicationRecord(version: 2),
        {applicationField: 'Saved'},
      );
      expect(result.version, 3);
      expect(api.requests.single.$1, 'PATCH');
      expect(
        api.requests.single.$2,
        '/applications/organizations/$applicationOrg/draft/$applicationId',
      );
      expect(api.requests.single.$3, {
        'expected_version': 2,
        'answers': [
          {'field_id': applicationField, 'value': 'Saved'},
        ],
      });
    },
  );

  test(
    'a malformed successful command is uncertain and is never replayed',
    () async {
      final api = _Api()..response = {'state': 'submitted'};
      await expectLater(
        ApplicationRepository(
          api,
        ).save(applicationOrg, applicationRecord(), {}),
        throwsA(
          isA<ApiFailure>().having(
            (error) => error.uncertain,
            'uncertain',
            isTrue,
          ),
        ),
      );
      expect(api.requests, hasLength(1));
    },
  );

  test('foreign organization and wrong cycle responses fail closed', () async {
    final api = _Api()
      ..response = applicationRecordJson(org: applicationOtherOrg);
    final repository = ApplicationRepository(api);
    await expectLater(
      repository.read(applicationOrg, applicationCycle),
      throwsA(isA<ApiFailure>()),
    );
    api.response = applicationRecordJson(cycle: applicationOtherOrg);
    await expectLater(
      repository.read(applicationOrg, applicationCycle),
      throwsA(isA<ApiFailure>()),
    );
  });

  test(
    'legacy requested ID cannot resolve a different draft or cycle draft',
    () async {
      final api = _Api();
      final repository = ApplicationRepository(api);
      await expectLater(
        repository.readLegacy(applicationOrg, applicationId),
        throwsA(isA<ApiFailure>()),
      );
      api.response = applicationRecordJson(
        id: applicationOtherOrg,
        cycle: null,
      );
      await expectLater(
        repository.readLegacy(applicationOrg, applicationId),
        throwsA(isA<ApiFailure>()),
      );
      api.response = applicationRecordJson(cycle: null);
      expect(
        (await repository.readLegacy(applicationOrg, applicationId)).id,
        applicationId,
      );
    },
  );

  test(
    'cross-organization commands and malformed IDs are rejected before sending',
    () async {
      final api = _Api();
      final repository = ApplicationRepository(api);
      await expectLater(
        repository.save(applicationOtherOrg, applicationRecord(), {}),
        throwsA(isA<ApiFailure>()),
      );
      await expectLater(
        repository.start('https://example.test', applicationCycle),
        throwsA(isA<ApiFailure>()),
      );
      expect(api.requests, isEmpty);
    },
  );

  test(
    'readiness trusts usable evidence and the current application version',
    () async {
      final json = applicationRecordJson();
      final form = json['form'] as Map<String, dynamic>;
      form['document_requirements'] = [
        {
          'id': applicationConsent,
          'label_en': 'Evidence',
          'label_ta': 'ஆவணம்',
          'instructions_en': 'Synthetic only',
          'instructions_ta': 'சோதனை மட்டும்',
          'min_files': 1,
          'max_files': 1,
          'file_policy': {
            'id': applicationDeclaration,
            'edition': 1,
            'name': 'Synthetic',
            'notice_en': 'Synthetic',
            'notice_ta': 'சோதனை',
            'max_file_bytes': 1024,
            'max_upload_bytes': 1024,
            'max_files': 1,
            'retention_days': 1,
            'rejected_retention_days': 1,
            'allow_frozen_disposal': false,
            'allowed_mime_types': ['application/pdf'],
          },
        },
      ];
      final record = ApplicationRecord.fromJson(json);
      final api = _Api()
        ..response = {
          'application_id': applicationId,
          'application_version': 2,
          'next_cursor': null,
          'items': [
            {
              'requirement_id': applicationConsent,
              'usable': false,
              'removed_at': null,
              'replaced_by_id': null,
              'file': {'state': 'clean'},
            },
          ],
        };
      final repository = ApplicationRepository(api);
      final readiness = await repository.readiness(applicationOrg, record);
      expect(readiness.version, 2);
      expect(readiness.ready, isFalse);
    },
  );

  test(
    'scalar validation accepts partial values and rejects normalized invalid dates/nonfinite numbers',
    () {
      ApplicationField field(String type) => ApplicationField.fromJson({
        'id': applicationField,
        'key': 'value',
        'section': 'proposal',
        'label_en': 'Value',
        'label_ta': 'மதிப்பு',
        'field_type': type,
        'required': false,
        'position': 1,
      });
      expect(applicationAnswerIsValid(field('date'), ''), isTrue);
      expect(applicationAnswerIsValid(field('date'), '2026-02-30'), isFalse);
      expect(applicationAnswerIsValid(field('date'), '2024-02-29'), isTrue);
      expect(applicationAnswerIsValid(field('number'), 'NaN'), isFalse);
      expect(applicationAnswerIsValid(field('number'), 'Infinity'), isFalse);
      expect(applicationAnswerIsValid(field('number'), '-12.50e2'), isTrue);
      expect(applicationAnswerIsValid(field('boolean'), 'yes'), isFalse);
    },
  );
}
