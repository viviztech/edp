import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../../core/navigation/destinations.dart';
import '../identity/providers.dart';
import 'application_models.dart';

final applicationRepositoryProvider = Provider(
  (ref) => ApplicationRepository(ref.watch(domainApiProvider)),
);

class ApplicationReadiness {
  final int version;
  final bool ready;
  const ApplicationReadiness(this.version, this.ready);
}

bool applicationAnswerIsValid(ApplicationField field, String raw) {
  if (raw.length > 5000) return false;
  final value = raw.trim();
  if (value.isEmpty) return true; // Partial drafts are permitted.
  switch (field.type) {
    case 'number':
      return RegExp(
            r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$',
          ).hasMatch(value) &&
          double.tryParse(value)?.isFinite == true;
    case 'date':
      if (!RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value)) return false;
      final date = DateTime.tryParse(value);
      return date != null && date.toIso8601String().startsWith('${value}T');
    case 'boolean':
      return value == 'true' || value == 'false';
    default:
      return field.type == 'text' || field.type == 'textarea';
  }
}

class ApplicationRepository {
  final DomainApi api;
  ApplicationRepository(this.api);

  String _root(String organization) {
    _id(organization);
    return '/applications/organizations/$organization';
  }

  void _id(String id) {
    if (!MobileDestination.uuid.hasMatch(id)) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
  }

  T _decode<T>(T Function() read, {bool command = false}) {
    try {
      return read();
    } catch (_) {
      throw ApiFailure(
        'invalid_response',
        kind: ApiFailureKind.invalidResponse,
        outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
      );
    }
  }

  ApplicationRecord _record(
    Object? data,
    String org, {
    String? cycle,
    String? id,
    bool command = false,
    bool? draft,
  }) => _decode(() {
    final result = ApplicationRecord.fromJson(applicationObject(data));
    if (result.form.organizationId != org ||
        (cycle != null && result.cycleId != cycle) ||
        (id != null && result.id != id)) {
      throw const FormatException();
    }
    const types = {'text', 'textarea', 'number', 'date', 'boolean'};
    const states = {
      'draft',
      'submitted',
      'under_review',
      'shortlisted',
      'interview_scheduled',
      'selected',
      'waitlisted',
      'rejected',
      'enrolled',
    };
    final fields = result.form.fields;
    if (!MobileDestination.uuid.hasMatch(result.id) ||
        !MobileDestination.uuid.hasMatch(result.form.id) ||
        !states.contains(result.state) ||
        (draft != null && result.isDraft != draft) ||
        result.version < 1 ||
        result.form.version < 1 ||
        result.revision < 1 ||
        result.completionPercent < 0 ||
        result.completionPercent > 100 ||
        fields.length > 100 ||
        result.form.acknowledgements.length > 20 ||
        result.form.documents.length > 20 ||
        fields.any(
          (field) =>
              !types.contains(field.type) ||
              !MobileDestination.uuid.hasMatch(field.id),
        ) ||
        fields.map((field) => field.id).toSet().length != fields.length ||
        result.answers.keys.any(
          (id) => !fields.any((field) => field.id == id),
        ) ||
        (!result.isDraft &&
            (result.cycleId == null ||
                result.number == null ||
                result.number!.isEmpty ||
                result.submittedAt == null))) {
      throw const FormatException();
    }
    return result;
  }, command: command);

  Future<List<ApplicationCycle>> cycles(String org) async {
    final data = await api.get('${_root(org)}/cycles');
    return _decode(() {
      final items = (applicationObject(data)['items'] as List)
          .map((item) => ApplicationCycle.fromJson(applicationObject(item)))
          .toList();
      if (items.length > 100 ||
          items.map((item) => item.id).toSet().length != items.length ||
          items.any(
            (item) =>
                !MobileDestination.uuid.hasMatch(item.id) ||
                !MobileDestination.uuid.hasMatch(item.formId) ||
                !item.closesAt.isAfter(item.opensAt),
          )) {
        throw const FormatException();
      }
      return items;
    });
  }

  Future<ApplicationRecord> read(String org, String cycle) async {
    _id(cycle);
    return _record(
      await api.get('${_root(org)}/cycles/$cycle/application'),
      org,
      cycle: cycle,
    );
  }

  Future<ApplicationRecord> readLegacy(String org, String expectedId) async {
    _id(expectedId);
    final result = _record(await api.get('${_root(org)}/draft'), org);
    // The legacy endpoint can return a different draft; never display it as the requested one.
    if (result.id != expectedId || result.cycleId != null) {
      throw const ApiFailure(
        'application_unavailable',
        kind: ApiFailureKind.notFound,
        statusCode: 404,
      );
    }
    return result;
  }

  Future<ApplicationRecord> start(String org, String cycle) async {
    _id(cycle);
    return _record(
      await api.post(
        '${_root(org)}/cycles/$cycle/draft',
        data: <String, dynamic>{},
      ),
      org,
      cycle: cycle,
      command: true,
      draft: true,
    );
  }

  Future<ApplicationRecord> save(
    String org,
    ApplicationRecord record,
    Map<String, String> answers,
  ) async {
    _id(record.id);
    if (record.form.organizationId != org ||
        !record.isDraft ||
        record.form.fields.any(
          (field) => !applicationAnswerIsValid(field, answers[field.id] ?? ''),
        )) {
      throw const ApiFailure(
        'invalid_answer',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await api.patch(
      '${_root(org)}/draft/${record.id}',
      data: {
        'expected_version': record.version,
        'answers': [
          for (final field in record.form.fields)
            {'field_id': field.id, 'value': answers[field.id] ?? ''},
        ],
      },
    );
    return _record(
      data,
      org,
      id: record.id,
      cycle: record.cycleId,
      command: true,
      draft: true,
    );
  }

  Future<ApplicationRecord> submit(
    String org,
    ApplicationRecord record,
    Set<String> accepted,
  ) async {
    _id(record.id);
    if (record.form.organizationId != org ||
        record.cycleId == null ||
        accepted.isEmpty ||
        accepted.length > 20 ||
        accepted.any(
          (id) => !record.form.acknowledgements.any((item) => item.id == id),
        )) {
      throw const ApiFailure(
        'acknowledgement_required',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await api.post(
      '${_root(org)}/draft/${record.id}/submit',
      data: {
        'expected_version': record.version,
        'accepted_acknowledgement_ids': accepted.toList(),
      },
    );
    return _record(
      data,
      org,
      id: record.id,
      cycle: record.cycleId,
      command: true,
      draft: false,
    );
  }

  Future<ApplicationReadiness> readiness(
    String org,
    ApplicationRecord record,
  ) async {
    if (record.form.documents.isEmpty) {
      return ApplicationReadiness(record.version, true);
    }
    final counts = <String, int>{};
    final maximumBindings = record.form.documents.fold<int>(
      0,
      (sum, rule) => sum + rule.maxFiles,
    );
    var ready = true, version = record.version, total = 0;
    String? cursor;
    final cursors = <String>{};
    do {
      final data = applicationObject(
        await api.get(
          '${_root(org)}/applications/${record.id}/documents',
          queryParameters: {'limit': 100, 'cursor': ?cursor},
        ),
      );
      final pageVersion = data['application_version'] as int;
      if (data['application_id'] != record.id ||
          (total > 0 && pageVersion != version)) {
        throw const ApiFailure(
          'version_conflict',
          kind: ApiFailureKind.conflict,
        );
      }
      version = pageVersion;
      for (final value in data['items'] as List) {
        if (++total > maximumBindings) {
          throw const ApiFailure(
            'invalid_response',
            kind: ApiFailureKind.invalidResponse,
          );
        }
        final item = applicationObject(value);
        if (item['removed_at'] != null || item['replaced_by_id'] != null) {
          continue;
        }
        final requirement = item['requirement_id'] as String;
        counts[requirement] = (counts[requirement] ?? 0) + 1;
        ready = ready && item['usable'] == true;
      }
      cursor = data['next_cursor'] as String?;
      if (cursor != null && !cursors.add(cursor)) {
        throw const ApiFailure(
          'invalid_response',
          kind: ApiFailureKind.invalidResponse,
        );
      }
    } while (cursor != null);
    return ApplicationReadiness(
      version,
      ready &&
          record.form.documents.every(
            (rule) =>
                (counts[rule.id] ?? 0) >= rule.minFiles &&
                (counts[rule.id] ?? 0) <= rule.maxFiles,
          ),
    );
  }
}
