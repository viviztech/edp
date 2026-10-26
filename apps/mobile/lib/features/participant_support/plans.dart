import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../identity/providers.dart';
import 'support_common.dart';

const planSections = [
  'executive_summary',
  'problem',
  'solution',
  'product_service',
  'customer_segments',
  'market',
  'competition',
  'value_proposition',
  'business_model',
  'pricing',
  'sales_marketing',
  'operations',
  'team',
  'investment',
  'revenue_assumptions',
  'expense_assumptions',
  'break_even_inputs',
  'funding_requirement',
  'risks',
  'milestones',
];
const planSectionTa = [
  'செயல் சுருக்கம்',
  'பிரச்சினை',
  'தீர்வு',
  'தயாரிப்பு / சேவை',
  'வாடிக்கையாளர் பிரிவுகள்',
  'சந்தை',
  'போட்டி',
  'மதிப்பு முன்மொழிவு',
  'வணிக மாதிரி',
  'விலை நிர்ணயம்',
  'விற்பனை / சந்தைப்படுத்தல்',
  'செயல்பாடுகள்',
  'குழு',
  'முதலீடு',
  'வருவாய் கணிப்புகள்',
  'செலவுக் கணிப்புகள்',
  'சமநிலை உள்ளீடுகள்',
  'நிதித் தேவை',
  'அபாயங்கள்',
  'மைல்கற்கள்',
];
Map<String, String> sectionMap(Object? value) {
  final map = object(value).cast<String, String>();
  if (map.length > 20 ||
      map.keys.any((k) => !planSections.contains(k)) ||
      map.values.any((v) => v.length > 10000)) {
    throw const FormatException();
  }
  return Map.unmodifiable(map);
}

class PlanReview {
  final String decision, reason;
  final Map<String, String> comments;
  PlanReview.fromJson(Map<String, dynamic> data)
    : decision = data['decision'] as String,
      reason = data['reason'] as String,
      comments = sectionMap(data['comments']);
}

class PlanSubmission {
  final String id, enrollmentId;
  final int version, number;
  final Map<String, String> snapshot;
  final DateTime createdAt;
  final PlanReview? review;
  PlanSubmission.fromJson(Map<String, dynamic> data)
    : id = identifier(data['id']),
      enrollmentId = identifier(data['enrollment_id']),
      version = versionOf(data['plan_version']),
      number = versionOf(data['number']),
      snapshot = sectionMap(data['snapshot']),
      createdAt = DateTime.parse(data['created_at'] as String),
      review = data['review'] == null
          ? null
          : PlanReview.fromJson(object(data['review']));
}

class BusinessPlan {
  final String id, enrollmentId, status;
  final int version, completed, total;
  final Map<String, String> sections;
  final List<PlanSubmission> submissions;
  BusinessPlan.fromJson(Map<String, dynamic> data)
    : id = identifier(data['id']),
      enrollmentId = identifier(data['enrollment_id']),
      status = data['status'] as String,
      version = versionOf(data['version']),
      completed = data['completed_sections'] as int,
      total = data['total_sections'] as int,
      sections = sectionMap(data['sections']),
      submissions = rows(data['submissions'], PlanSubmission.fromJson) {
    if (!{
          'draft',
          'submitted',
          'changes_requested',
          'approved',
        }.contains(status) ||
        total != 20 ||
        completed < 0 ||
        completed > total ||
        submissions.any((s) => s.enrollmentId != enrollmentId)) {
      throw const FormatException();
    }
  }
  bool get editable => status == 'draft' || status == 'changes_requested';
}

class PlanEntry {
  final String enrollmentId, programId;
  final BusinessPlan? plan;
  PlanEntry.fromJson(Map<String, dynamic> data)
    : enrollmentId = identifier(data['enrollment_id']),
      programId = identifier(data['program_id']),
      plan = data['plan'] == null
          ? null
          : BusinessPlan.fromJson(object(data['plan'])) {
    if (plan != null && plan!.enrollmentId != enrollmentId) {
      throw const FormatException();
    }
  }
}

final plansRepositoryProvider = Provider(
  (ref) => PlansRepository(ref.watch(domainApiProvider)),
);

class PlansRepository {
  final DomainApi api;
  PlansRepository(this.api);
  String root(String org) => '/business-plans/organizations/${identifier(org)}';
  Future<List<PlanEntry>> mine(String org) async {
    final data = await api.get('${root(org)}/mine');
    return decode(() => rows(object(data)['entries'], PlanEntry.fromJson));
  }

  Future<BusinessPlan> _command(
    String org,
    String enrollment,
    String suffix,
    Object? body,
  ) async {
    final data = await api.post(
      '${root(org)}/enrollments/${identifier(enrollment)}$suffix',
      data: body,
    );
    return decode(() {
      final plan = BusinessPlan.fromJson(object(data));
      if (plan.enrollmentId != enrollment) throw const FormatException();
      return plan;
    }, command: true);
  }

  Future<BusinessPlan> create(String org, String enrollment) =>
      _command(org, enrollment, '', null);
  Future<BusinessPlan> save(
    String org,
    BusinessPlan plan,
    String code,
    String body,
  ) {
    if (!planSections.contains(code) || body.length > 10000) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    return _command(org, plan.enrollmentId, '/sections', {
      'expected_version': plan.version,
      'section_code': code,
      'body': body,
    });
  }

  Future<BusinessPlan> submit(String org, BusinessPlan plan) => _command(
    org,
    plan.enrollmentId,
    '/submit',
    {'expected_version': plan.version},
  );
}

class PlansController extends ChangeNotifier with SupportRetry {
  final PlansRepository repository;
  final String organizationId;
  List<PlanEntry> entries = [];
  BusinessPlan? plan, latest;
  String? selectedEnrollment;
  final Map<String, String> edits = {};
  bool busy = false,
      requiresReview = false,
      readbackReady = false,
      _disposed = false;
  ApiFailure? failure;
  PlansController(this.repository, this.organizationId);
  bool get dirty => edits.isNotEmpty;
  bool get canWrite =>
      !busy && !retryDelayed && !requiresReview && plan?.editable == true;
  void edit(String code, String value) {
    if (canWrite && planSections.contains(code)) {
      edits[code] = value;
      notifyListeners();
    }
  }

  Future<void> load({String? enrollment}) async {
    if (busy || retryDelayed || _disposed) return;
    busy = true;
    failure = null;
    readbackReady = false;
    notifyListeners();
    try {
      final result = await repository.mine(organizationId);
      if (_disposed) return;
      entries = result;
      final target =
          enrollment ?? selectedEnrollment ?? entries.firstOrNull?.enrollmentId;
      if (selectedEnrollment != null &&
          enrollment != null &&
          enrollment != selectedEnrollment &&
          dirty) {
        throw const ApiFailure(
          'unsaved_changes',
          kind: ApiFailureKind.conflict,
        );
      }
      selectedEnrollment = target;
      final entry = entries.where((e) => e.enrollmentId == target).firstOrNull;
      if (entry == null) {
        plan = null;
        latest = null;
        if (target != null) {
          throw const ApiFailure('not_found', kind: ApiFailureKind.notFound);
        }
      } else if (dirty || requiresReview) {
        latest = entry.plan;
        requiresReview = true;
        readbackReady = true;
      } else {
        plan = entry.plan;
        latest = null;
      }
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e);
        recordFailure(failure!);
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  void resolve({required bool keepEdits}) {
    if (busy || !requiresReview || !readbackReady) return;
    plan = latest;
    latest = null;
    requiresReview = false;
    readbackReady = false;
    if (!keepEdits) edits.clear();
    notifyListeners();
  }

  Future<void> create() async {
    if (busy ||
        retryDelayed ||
        requiresReview ||
        selectedEnrollment == null ||
        plan != null) {
      return;
    }
    await _write(() => repository.create(organizationId, selectedEnrollment!));
  }

  Future<void> save(String code) async {
    if (!canWrite || !edits.containsKey(code)) return;
    final body = edits[code]!;
    await _write(
      () => repository.save(organizationId, plan!, code, body),
      savedCode: code,
      savedBody: body,
    );
  }

  Future<void> submit() async {
    if (!canWrite || dirty || plan!.completed != 20) return;
    await _write(() => repository.submit(organizationId, plan!));
  }

  Future<void> _write(
    Future<BusinessPlan> Function() command, {
    String? savedCode,
    String? savedBody,
  }) async {
    busy = true;
    failure = null;
    readbackReady = false;
    notifyListeners();
    try {
      final saved = await command();
      if (_disposed) return;
      if (saved.enrollmentId != selectedEnrollment ||
          (plan != null && saved.id != plan!.id)) {
        throw const ApiFailure(
          'invalid_response',
          kind: ApiFailureKind.invalidResponse,
          outcome: CommandOutcome.uncertain,
        );
      }
      plan = saved;
      if (savedCode != null && edits[savedCode] == savedBody) {
        edits.remove(savedCode);
      }
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
        requiresReview =
            failure!.uncertain || failure!.kind == ApiFailureKind.conflict;
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    edits.clear();
    entries = [];
    plan = null;
    latest = null;
    super.dispose();
  }
}
