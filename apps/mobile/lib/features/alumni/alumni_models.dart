import '../../core/api/api_failure.dart';

final alumniUuid = RegExp(
  r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
);
Map<String, dynamic> alumniObject(Object? value) =>
    Map<String, dynamic>.from(value as Map);
List<T> alumniList<T>(
  Object? value,
  T Function(Map<String, dynamic>) decode, {
  int max = 100,
}) {
  final list = value as List;
  if (list.length > max) throw const FormatException();
  return List.unmodifiable(list.map((item) => decode(alumniObject(item))));
}

String alumniId(Object? value) {
  if (value is! String || !alumniUuid.hasMatch(value)) {
    throw const FormatException();
  }
  return value;
}

String? alumniCursor(Object? value) => value == null ? null : alumniId(value);
int alumniVersion(Object? value, {bool zero = false}) {
  if (value is! int || value < (zero ? 0 : 1)) throw const FormatException();
  return value;
}

String alumniDate(Object? value) {
  if (value is! String ||
      !RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value) ||
      DateTime.tryParse(value)?.toIso8601String().startsWith('${value}T') !=
          true) {
    throw const FormatException();
  }
  return value;
}

const businessStages = ['idea', 'starting', 'operating', 'paused', 'closed'];
const moneyBands = [
  'none',
  'under_1l',
  '1l_to_5l',
  '5l_to_25l',
  'over_25l',
  'undisclosed',
];
const revenueBands = [
  'none',
  'under_10k',
  '10k_to_50k',
  '50k_to_2l',
  'over_2l',
  'undisclosed',
];
const fundingStates = ['none', 'seeking', 'applied', 'approved', 'disbursed'];
const profileFieldKeys = [
  'name',
  'sector',
  'products_services',
  'stage',
  'registration_info',
  'started_on',
  'team_size',
  'investment_band',
  'funding_status',
  'revenue_band',
  'support_needs',
  'public_opt_in',
];

class BusinessProfile {
  final String id, enrollmentId;
  final int version;
  final Map<String, dynamic> fields;
  final List<BusinessRevision> revisions;
  final List<BusinessFollowUp> followUps;
  BusinessProfile.fromJson(Map<String, dynamic> json)
    : id = alumniId(json['id']),
      enrollmentId = alumniId(json['enrollment_id']),
      version = alumniVersion(json['version']),
      fields = Map.unmodifiable({
        for (final key in profileFieldKeys) key: json[key],
      }),
      revisions = alumniList(
        json['revisions'],
        BusinessRevision.fromJson,
        max: 20,
      ),
      followUps = alumniList(
        json['follow_ups'],
        BusinessFollowUp.fromJson,
        max: 12,
      ) {
    validateProfile(fields, server: true);
  }
}

class BusinessRevision {
  final String id;
  final int version;
  final DateTime createdAt;
  final Map<String, dynamic> snapshot;
  BusinessRevision.fromJson(Map<String, dynamic> json)
    : id = alumniId(json['id']),
      version = alumniVersion(json['version']),
      createdAt = DateTime.parse(json['created_at'] as String),
      snapshot = Map.unmodifiable(alumniObject(json['snapshot']));
}

class BusinessFollowUp {
  final String id, dueOn, status;
  final int offsetDays;
  final BusinessOutcome? outcome;
  BusinessFollowUp.fromJson(Map<String, dynamic> json)
    : id = alumniId(json['id']),
      dueOn = alumniDate(json['due_on']),
      status = json['status'] as String,
      offsetDays = json['offset_days'] as int,
      outcome = json['outcome'] == null
          ? null
          : BusinessOutcome.fromJson(alumniObject(json['outcome'])) {
    if (!{'pending', 'completed'}.contains(status) ||
        offsetDays < 1 ||
        (status == 'completed') != (outcome != null)) {
      throw const FormatException();
    }
  }
}

class BusinessOutcome {
  final String id;
  final Map<String, dynamic> fields;
  final DateTime createdAt;
  BusinessOutcome.fromJson(Map<String, dynamic> json)
    : id = alumniId(json['id']),
      fields = Map.unmodifiable(
        Map.of(json)
          ..remove('id')
          ..remove('created_at'),
      ),
      createdAt = DateTime.parse(json['created_at'] as String) {
    validateOutcome(fields, server: true);
  }
}

class BusinessEntry {
  final String enrollmentId, programId;
  final BusinessProfile? profile;
  BusinessEntry.fromJson(Map<String, dynamic> json)
    : enrollmentId = alumniId(json['enrollment_id']),
      programId = alumniId(json['program_id']),
      profile = json['profile'] == null
          ? null
          : BusinessProfile.fromJson(alumniObject(json['profile'])) {
    if (profile != null && profile!.enrollmentId != enrollmentId) {
      throw const FormatException();
    }
  }
}

void _invalid({bool server = false}) {
  if (server) throw const FormatException();
  throw const ApiFailure(
    'invalid_business_fields',
    kind: ApiFailureKind.validation,
    outcome: CommandOutcome.notSent,
  );
}

void validateProfile(Map<String, dynamic> fields, {bool server = false}) {
  bool text(String key, int min, int max) =>
      fields[key] is String &&
      (fields[key] as String).trim().length >= min &&
      (fields[key] as String).length <= max;
  if (!text('name', 2, 160) ||
      !text('sector', 2, 120) ||
      !text('products_services', 1, 4000) ||
      !businessStages.contains(fields['stage']) ||
      !moneyBands.contains(fields['investment_band']) ||
      !revenueBands.contains(fields['revenue_band']) ||
      !fundingStates.contains(fields['funding_status']) ||
      fields['team_size'] is! int ||
      (fields['team_size'] as int) < 0 ||
      (fields['team_size'] as int) > 100000 ||
      fields['public_opt_in'] is! bool) {
    _invalid(server: server);
  }
  for (final key in ['registration_info', 'support_needs']) {
    if (fields[key] != null &&
        (fields[key] is! String ||
            (fields[key] as String).length >
                (key == 'registration_info' ? 240 : 4000))) {
      _invalid(server: server);
    }
  }
  if (fields['started_on'] != null) {
    try {
      alumniDate(fields['started_on']);
    } catch (_) {
      _invalid(server: server);
    }
    if (!server &&
        (fields['started_on'] as String).compareTo(
              DateTime.now().toUtc().toIso8601String().substring(0, 10),
            ) >
            0) {
      _invalid();
    }
  } else if ({'operating', 'paused', 'closed'}.contains(fields['stage'])) {
    _invalid(server: server);
  }
}

void validateOutcome(Map<String, dynamic> fields, {bool server = false}) {
  try {
    alumniDate(fields['reported_on']);
  } catch (_) {
    _invalid(server: server);
  }
  if (fields['business_started'] is! bool ||
      fields['business_active'] is! bool ||
      (fields['business_active'] == true &&
          fields['business_started'] != true) ||
      fields['jobs_created'] is! int ||
      (fields['jobs_created'] as int) < 0 ||
      (fields['jobs_created'] as int) > 100000 ||
      !moneyBands.contains(fields['funding_band']) ||
      !revenueBands.contains(fields['revenue_band'])) {
    _invalid(server: server);
  }
  if (!server &&
      (fields['reported_on'] as String).compareTo(
            DateTime.now().toUtc().toIso8601String().substring(0, 10),
          ) >
          0) {
    _invalid();
  }
  for (final key in [
    'challenges',
    'support_requested',
    'mentor_interventions',
    'outcomes',
  ]) {
    if (fields[key] != null &&
        (fields[key] is! String || (fields[key] as String).length > 4000)) {
      _invalid(server: server);
    }
  }
}

class ImpactEnrollment {
  final String id, nameEn, nameTa, status;
  ImpactEnrollment.fromJson(Map<String, dynamic> json)
    : id = alumniId(json['id']),
      nameEn = json['name_en'] as String,
      nameTa = json['name_ta'] as String,
      status = json['status'] as String {
    if (!{'active', 'completed'}.contains(status)) {
      throw const FormatException();
    }
  }
}

class ImpactDefinition {
  final String id, titleEn, titleTa, definitionEn, definitionTa, state;
  final int edition;
  ImpactDefinition.fromJson(Map<String, dynamic> json)
    : id = alumniId(json['id']),
      edition = alumniVersion(json['edition']),
      titleEn = json['title_en'] as String,
      titleTa = json['title_ta'] as String,
      definitionEn = json['definition_en'] as String,
      definitionTa = json['definition_ta'] as String,
      state = json['state'] as String {
    if (!{'published', 'archived'}.contains(state)) {
      throw const FormatException();
    }
  }
}

class ImpactObservation {
  final String id,
      enrollmentId,
      definitionId,
      stage,
      observedOn,
      reason,
      requestId;
  final int revision, jobsCreated;
  final bool businessStarted, businessActive;
  ImpactObservation.fromJson(Map<String, dynamic> json)
    : id = alumniId(json['id']),
      enrollmentId = alumniId(json['enrollment_id']),
      definitionId = alumniId(json['definition_id']),
      stage = json['stage'] as String,
      observedOn = alumniDate(json['observed_on']),
      reason = json['reason'] as String,
      requestId = alumniId(json['request_id']),
      revision = alumniVersion(json['revision']),
      jobsCreated = json['jobs_created'] as int,
      businessStarted = json['business_started'] as bool,
      businessActive = json['business_active'] as bool {
    if (!{'baseline', 'outcome'}.contains(stage) ||
        jobsCreated < 0 ||
        jobsCreated > 100000 ||
        (businessActive && !businessStarted)) {
      throw const FormatException();
    }
  }
}

class ImpactPage {
  final List<ImpactEnrollment> enrollments;
  final List<ImpactDefinition> definitions;
  final List<ImpactObservation> records;
  final String? enrollmentCursor, definitionCursor, recordCursor;
  ImpactPage.fromJson(Map<String, dynamic> json)
    : enrollments = alumniList(json['enrollments'], ImpactEnrollment.fromJson),
      definitions = alumniList(
        json['definitions'],
        ImpactDefinition.fromJson,
        max: 200,
      ),
      records = alumniList(json['records'], ImpactObservation.fromJson),
      enrollmentCursor = alumniCursor(json['enrollment_next_cursor']),
      definitionCursor = alumniCursor(json['definition_next_cursor']),
      recordCursor = alumniCursor(json['record_next_cursor']);
}

class EnrollmentNotice {
  final String id, enrollmentId;
  final int version;
  final DateTime createdAt, expiresAt;
  final DateTime? readAt;
  EnrollmentNotice.fromJson(Map<String, dynamic> json)
    : id = alumniId(json['id']),
      enrollmentId = alumniId(json['enrollment_id']),
      version = alumniVersion(json['version']),
      createdAt = DateTime.parse(json['created_at'] as String),
      expiresAt = DateTime.parse(json['expires_at'] as String),
      readAt = json['read_at'] == null
          ? null
          : DateTime.parse(json['read_at'] as String) {
    if (json['topic'] != 'enrollment_created' ||
        json['action_kind'] != 'schedule' ||
        json['template_version'] != 'enrollment-created-v1') {
      throw const FormatException();
    }
  }
}

class EnrollmentNoticePage {
  final List<EnrollmentNotice> items;
  final String? cursor;
  EnrollmentNoticePage.fromJson(Map<String, dynamic> json)
    : items = alumniList(json['items'], EnrollmentNotice.fromJson),
      cursor = alumniCursor(json['next_cursor']);
}

class EnrollmentNoticePreference {
  final bool enabled;
  final int version;
  EnrollmentNoticePreference.fromJson(Map<String, dynamic> json)
    : enabled = json['enabled'] as bool,
      version = alumniVersion(json['version'], zero: true) {
    if (json['topic'] != 'enrollment_created') throw const FormatException();
  }
}
