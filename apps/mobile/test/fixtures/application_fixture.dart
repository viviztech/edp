import 'package:edp_mobile/features/applications/application_models.dart';

const applicationOrg = '11111111-1111-4111-8111-111111111111';
const applicationOtherOrg = '22222222-2222-4222-8222-222222222222';
const applicationCycle = '33333333-3333-4333-8333-333333333333';
const applicationId = '44444444-4444-4444-8444-444444444444';
const applicationFormId = '55555555-5555-4555-8555-555555555555';
const applicationField = '66666666-6666-4666-8666-666666666666';
const applicationConsent = '77777777-7777-4777-8777-777777777777';
const applicationDeclaration = '88888888-8888-4888-8888-888888888888';

Map<String, dynamic> applicationCycleJson() => {
  'id': applicationCycle,
  'code': 'synthetic-intake',
  'name_en': 'Synthetic intake',
  'name_ta': 'சோதனை சேர்க்கை',
  'form_id': applicationFormId,
  'opens_at': '2020-01-01T00:00:00Z',
  'closes_at': '2099-12-31T00:00:00Z',
};

Map<String, dynamic> applicationRecordJson({
  int version = 1,
  String answer = '',
  String state = 'draft',
  String id = applicationId,
  String org = applicationOrg,
  String? cycle = applicationCycle,
}) => {
  'id': id,
  'cycle_id': cycle,
  'state': state,
  'version': version,
  'revision': version,
  'completion_percent': answer.isEmpty ? 0 : 100,
  'updated_at': '2026-10-24T00:00:00Z',
  'form': {
    'id': applicationFormId,
    'organization_id': org,
    'version': 1,
    'title_en': 'Enterprise application',
    'title_ta': 'தொழில் விண்ணப்பம்',
    'collection_enabled': false,
    'max_upload_bytes': 1024,
    'fields': [
      {
        'id': applicationField,
        'key': 'idea',
        'section': 'proposal',
        'label_en': 'Business idea',
        'label_ta': 'தொழில் திட்டம்',
        'field_type': 'textarea',
        'required': true,
        'position': 1,
      },
    ],
    'acknowledgements': [
      {
        'id': applicationDeclaration,
        'key': 'declaration',
        'kind': 'declaration',
        'label_en': 'Synthetic declaration',
        'label_ta': 'சோதனை உறுதி',
        'required': true,
        'position': 1,
      },
      {
        'id': applicationConsent,
        'key': 'consent',
        'kind': 'consent',
        'label_en': 'Synthetic consent',
        'label_ta': 'சோதனை ஒப்புதல்',
        'required': true,
        'position': 2,
      },
    ],
    'document_requirements': <Object?>[],
  },
  'answers': [
    if (answer.isNotEmpty) {'field_id': applicationField, 'value': answer},
  ],
  if (state != 'draft') ...{
    'application_number': 'EDP-2026-00000001',
    'submitted_at': '2026-10-24T01:00:00Z',
    'accepted_acknowledgements': [
      for (final id in [applicationDeclaration, applicationConsent])
        {'definition_id': id, 'accepted_at': '2026-10-24T01:00:00Z'},
    ],
    'status_history': [
      {
        'from_state': null,
        'to_state': 'draft',
        'application_version': 1,
        'reason_code': 'applicant_started',
        'created_at': '2026-10-24T00:00:00Z',
      },
      {
        'from_state': 'draft',
        'to_state': state,
        'application_version': version,
        'reason_code': 'applicant_submitted',
        'created_at': '2026-10-24T01:00:00Z',
      },
    ],
  },
};

ApplicationRecord applicationRecord({
  int version = 1,
  String answer = '',
  String state = 'draft',
}) => ApplicationRecord.fromJson(
  applicationRecordJson(version: version, answer: answer, state: state),
);
