import 'dart:convert';
import 'dart:io';

import 'package:edp_mobile/features/applications/application_models.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fixtures/application_fixture.dart';

Map<String, dynamic> _documentRequirement() => {
  'id': '99999999-9999-4999-8999-999999999999',
  'key': 'synthetic_evidence',
  'label_en': 'Synthetic evidence',
  'label_ta': 'சோதனை ஆவணம்',
  'instructions_en': 'Use synthetic files only.',
  'instructions_ta': 'சோதனை கோப்புகளை மட்டும் பயன்படுத்தவும்.',
  'file_policy_id': applicationFormId,
  'min_files': 1,
  'max_files': 3,
  'position': 1,
  'file_policy': {
    'id': applicationFormId,
    'edition': 1,
    'name': 'Synthetic policy',
    'allowed_mime_types': ['application/pdf', 'text/plain'],
    'max_file_bytes': 8192,
    'max_upload_bytes': 4096,
    'max_files': 4,
    'retention_days': 30,
    'rejected_retention_days': 2,
    'notice_en': 'Synthetic collection notice.',
    'notice_ta': 'சோதனை சேகரிப்பு அறிவிப்பு.',
    'allow_frozen_disposal': false,
  },
};

void main() {
  test(
    'document DTO fixture matches exported pinned policy property names',
    () {
      final contract =
          jsonDecode(
                File(
                  '../../packages/api-contracts/openapi.json',
                ).readAsStringSync(),
              )
              as Map;
      final schemas = (contract['components'] as Map)['schemas'] as Map;
      final properties =
          (schemas['DocumentFilePolicyView'] as Map)['properties'] as Map;
      final policy = _documentRequirement()['file_policy'] as Map;
      expect(policy.keys.toSet(), properties.keys.toSet());
      final value = ApplicationDocumentRequirement.fromJson(
        _documentRequirement(),
      );
      expect(value.maxFileBytes, 8192);
      expect(value.maxUploadBytes, 4096);
      expect(value.policyMaxFiles, 4);
      expect(value.retentionDays, 30);
      expect(value.rejectedRetentionDays, 2);
      expect(value.effectiveUploadLimit(1024), 1024);
      expect(value.effectiveUploadLimit(65536), 4096);
      expect(value.effectiveUploadLimit(0), 0);
      expect(() => value.mimeTypes.add('image/png'), throwsUnsupportedError);
    },
  );

  test(
    'invalid limits cannot turn a malformed policy into usable collection',
    () {
      final fixture = _documentRequirement();
      (fixture['file_policy'] as Map)['max_file_bytes'] = 0;
      expect(
        () => ApplicationDocumentRequirement.fromJson(fixture),
        throwsFormatException,
      );
      final countFixture = _documentRequirement()..['min_files'] = 4;
      expect(
        () => ApplicationDocumentRequirement.fromJson(countFixture),
        throwsFormatException,
      );
    },
  );

  test('receipt retains pinned acknowledgements and applicant status only', () {
    final record = ApplicationRecord.fromJson(
      applicationRecordJson(
        version: 3,
        answer: 'Synthetic idea',
        state: 'submitted',
      ),
    );
    expect(record.isDraft, isFalse);
    expect(record.number, 'EDP-2026-00000001');
    expect(record.accepted.map((item) => item.id), [
      applicationDeclaration,
      applicationConsent,
    ]);
    expect(record.accepted.first.acceptedAt.isUtc, isTrue);
    expect(record.history.map((event) => event.state), ['draft', 'submitted']);
    expect(record.history.last.version, 3);
    expect(
      () => record.answers[applicationField] = 'Changed',
      throwsUnsupportedError,
    );
  });
}
