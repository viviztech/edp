import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../identity/providers.dart';
import 'alumni_models.dart';

final alumniRepositoryProvider = Provider(
  (ref) => AlumniRepository(ref.watch(domainApiProvider)),
);
String newAlumniRequestId() {
  final random = Random.secure(), bytes = List.generate(16, (_) => 0);
  for (var i = 0; i < 16; i++) {
    bytes[i] = random.nextInt(256);
  }
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}

class AlumniRepository {
  final DomainApi api;
  AlumniRepository(this.api);
  String _root(String module, String organization) {
    _id(organization);
    return '/$module/organizations/$organization';
  }

  void _id(String value) {
    if (!alumniUuid.hasMatch(value)) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
  }

  T _decode<T>(T Function() decode, {bool command = false}) {
    try {
      return decode();
    } catch (_) {
      throw ApiFailure(
        'invalid_response',
        kind: ApiFailureKind.invalidResponse,
        outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
      );
    }
  }

  Future<List<BusinessEntry>> businesses(String organization) async {
    final data = await api.get('${_root('businesses', organization)}/mine');
    return _decode(
      () => alumniList(alumniObject(data)['entries'], BusinessEntry.fromJson),
    );
  }

  Future<BusinessProfile> saveProfile(
    String organization,
    String enrollment,
    Map<String, dynamic> fields, {
    BusinessProfile? previous,
  }) async {
    _id(enrollment);
    if (previous != null) _id(previous.id);
    validateProfile(fields);
    // Public opt-in is deliberately false: this owner flow has no publication contract.
    final body = {
      for (final key in profileFieldKeys) key: fields[key],
      'public_opt_in': false,
    };
    final data = await api.post(
      previous == null
          ? '${_root('businesses', organization)}/profiles'
          : '${_root('businesses', organization)}/profiles/${previous.id}/update',
      data: {
        ...body,
        if (previous == null)
          'enrollment_id': enrollment
        else
          'expected_version': previous.version,
      },
    );
    return _decode(() {
      final profile = BusinessProfile.fromJson(alumniObject(data));
      if (profile.enrollmentId != enrollment ||
          (previous != null && profile.id != previous.id)) {
        throw const FormatException();
      }
      return profile;
    }, command: true);
  }

  Future<BusinessOutcome> submitOutcome(
    String organization,
    String followUp,
    Map<String, dynamic> fields,
  ) async {
    _id(followUp);
    validateOutcome(fields);
    final data = await api.post(
      '${_root('businesses', organization)}/follow-ups/$followUp/outcome',
      data: Map.of(fields),
    );
    return _decode(
      () => BusinessOutcome.fromJson(alumniObject(data)),
      command: true,
    );
  }

  Future<ImpactPage> impact(
    String organization, {
    String? enrollmentCursor,
    String? definitionCursor,
    String? recordCursor,
    String? enrollmentId,
    String? stage,
    String? observedOn,
    int limit = 25,
  }) async {
    for (final value in [
      enrollmentCursor,
      definitionCursor,
      recordCursor,
      enrollmentId,
    ]) {
      if (value != null) _id(value);
    }
    if (stage != null && !{'baseline', 'outcome'}.contains(stage)) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    if (observedOn != null) {
      _decode(() => alumniDate(observedOn));
    }
    final data = await api.get(
      '${_root('impact', organization)}/mine',
      queryParameters: {
        'limit': limit,
        'enrollment_cursor': ?enrollmentCursor,
        'definition_cursor': ?definitionCursor,
        'record_cursor': ?recordCursor,
        'enrollment_id': ?enrollmentId,
        'stage': ?stage,
        'observed_on': ?observedOn,
      },
    );
    return _decode(() => ImpactPage.fromJson(alumniObject(data)));
  }

  Future<ImpactObservation> recordImpact(
    String organization,
    Map<String, dynamic> body,
  ) async {
    for (final key in ['enrollment_id', 'definition_id', 'request_id']) {
      _id(body[key] as String);
    }
    final date = _decode(() => alumniDate(body['observed_on']));
    if (date.compareTo(
              DateTime.now().toUtc().toIso8601String().substring(0, 10),
            ) >
            0 ||
        !{'baseline', 'outcome'}.contains(body['stage']) ||
        body['business_started'] is! bool ||
        body['business_active'] is! bool ||
        (body['business_active'] == true && body['business_started'] != true) ||
        body['jobs_created'] is! int ||
        (body['jobs_created'] as int) < 0 ||
        (body['jobs_created'] as int) > 100000 ||
        body['expected_revision'] is! int ||
        (body['expected_revision'] as int) < 0 ||
        body['reason'] is! String ||
        (body['reason'] as String).trim().length < 3 ||
        (body['reason'] as String).length > 500) {
      throw const ApiFailure(
        'invalid_impact_fields',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await api.post(
      '${_root('impact', organization)}/records',
      data: Map.of(body),
    );
    return _decode(() {
      final result = ImpactObservation.fromJson(alumniObject(data));
      if (result.requestId != body['request_id'] ||
          result.definitionId != body['definition_id'] ||
          result.enrollmentId != body['enrollment_id'] ||
          result.observedOn != body['observed_on'] ||
          result.stage != body['stage']) {
        throw const FormatException();
      }
      return result;
    }, command: true);
  }

  Future<EnrollmentNoticePage> notices(
    String organization, {
    String? cursor,
  }) async {
    if (cursor != null) _id(cursor);
    final data = await api.get(
      '${_root('participant-notifications', organization)}/mine',
      queryParameters: {'limit': 25, 'cursor': ?cursor},
    );
    return _decode(() => EnrollmentNoticePage.fromJson(alumniObject(data)));
  }

  Future<EnrollmentNoticePreference> preference(String organization) async {
    final data = await api.get(
      '${_root('participant-notifications', organization)}/preference',
    );
    return _decode(
      () => EnrollmentNoticePreference.fromJson(alumniObject(data)),
    );
  }

  Future<EnrollmentNoticePreference> setPreference(
    String organization,
    EnrollmentNoticePreference previous,
    bool enabled,
  ) async {
    final data = await api.post(
      '${_root('participant-notifications', organization)}/preference',
      data: {'expected_version': previous.version, 'enabled': enabled},
    );
    return _decode(
      () => EnrollmentNoticePreference.fromJson(alumniObject(data)),
      command: true,
    );
  }

  Future<EnrollmentNotice> markRead(
    String organization,
    EnrollmentNotice notice,
  ) async {
    _id(notice.id);
    final data = await api.post(
      '${_root('participant-notifications', organization)}/${notice.id}/read',
      data: {'expected_version': notice.version},
    );
    return _decode(() {
      final result = EnrollmentNotice.fromJson(alumniObject(data));
      if (result.id != notice.id ||
          result.enrollmentId != notice.enrollmentId) {
        throw const FormatException();
      }
      return result;
    }, command: true);
  }

  Future<EnrollmentNotice> noticeById(
    String organization,
    String noticeId,
  ) async {
    _id(noticeId);
    String? cursor;
    final seen = <String>{};
    EnrollmentNotice? selected;
    do {
      final page = await notices(organization, cursor: cursor);
      selected = page.items
          .where(
            (item) =>
                item.id == noticeId &&
                item.expiresAt.isAfter(DateTime.now().toUtc()),
          )
          .firstOrNull;
      if (selected != null) break;
      cursor = page.cursor;
      if (cursor != null && !seen.add(cursor)) {
        throw const ApiFailure(
          'invalid_response',
          kind: ApiFailureKind.invalidResponse,
        );
      }
    } while (cursor != null);
    if (selected == null) {
      throw const ApiFailure(
        'notice_unavailable',
        kind: ApiFailureKind.notFound,
      );
    }
    return selected;
  }

  Future<String> scheduleTarget(String organization, String noticeId) async {
    final selected = await noticeById(organization, noticeId);
    final timeline = alumniObject(
      await api.get('${_root('programs', organization)}/my-timeline'),
    );
    final enrollments = timeline['enrollments'] as List;
    if (!enrollments.any(
      (entry) =>
          alumniObject(entry)['id'] == selected.enrollmentId &&
          {'active', 'completed'}.contains(alumniObject(entry)['status']),
    )) {
      throw const ApiFailure(
        'enrollment_unavailable',
        kind: ApiFailureKind.notFound,
      );
    }
    return selected.enrollmentId;
  }
}
