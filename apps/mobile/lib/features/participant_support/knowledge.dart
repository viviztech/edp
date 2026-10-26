import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../../core/links/external_links.dart';
import '../identity/providers.dart';
import 'support_common.dart';

const fundingTransitions = <String, List<String>>{
  'interested': ['eligibility_check'],
  'eligibility_check': ['document_preparation'],
  'document_preparation': ['applied'],
  'applied': ['under_review'],
  'under_review': ['approved', 'rejected'],
  'approved': ['disbursed'],
  'rejected': [],
  'disbursed': [],
};

class KnowledgeItem {
  final String id,
      kind,
      locale,
      title,
      provider,
      description,
      eligibility,
      benefits,
      sector,
      geography,
      process,
      officialUrl,
      availability,
      contact;
  final List<String> tags, documents;
  final DateTime verifiedAt;
  final DateTime? opensOn, closesOn;
  final String? minimum, maximum;
  KnowledgeItem.fromJson(Map<String, dynamic> d)
    : id = identifier(d['id']),
      kind = d['kind'] as String,
      locale = d['locale'] as String,
      title = d['title'] as String,
      provider = d['provider'] as String,
      description = d['description'] as String,
      eligibility = d['eligibility'] as String,
      benefits = d['benefits'] as String,
      sector = d['sector'] as String,
      geography = d['geography'] as String,
      process = d['application_process'] as String,
      officialUrl = d['official_url'] as String,
      availability = d['availability'] as String,
      contact = d['contact'] as String,
      tags = List.unmodifiable((d['tags'] as List).cast<String>()),
      documents = List.unmodifiable((d['documents'] as List).cast<String>()),
      verifiedAt = DateTime.parse(d['last_verified_at'] as String),
      opensOn = d['opens_on'] == null
          ? null
          : DateTime.parse(d['opens_on'] as String),
      closesOn = d['closes_on'] == null
          ? null
          : DateTime.parse(d['closes_on'] as String),
      minimum = d['funding_amount_min']?.toString(),
      maximum = d['funding_amount_max']?.toString() {
    if (!{'scheme', 'funding', 'opportunity'}.contains(kind) ||
        !{'en', 'ta'}.contains(locale) ||
        d['state'] != 'published' ||
        validatePublicLink(officialUrl) == null) {
      throw const FormatException();
    }
  }
}

class SavedKnowledge {
  final String itemId;
  final KnowledgeItem? item;
  SavedKnowledge.fromJson(Map<String, dynamic> d)
    : itemId = identifier(d['item_id']),
      item = d['item'] == null
          ? null
          : KnowledgeItem.fromJson(object(d['item'])) {
    if (item != null && item!.id != itemId) throw const FormatException();
  }
}

class OpportunityInterest {
  final String id, itemId, title;
  OpportunityInterest.fromJson(Map<String, dynamic> d)
    : id = identifier(d['id']),
      itemId = identifier(d['item_id']),
      title = d['item_title'] as String;
}

class FundingHistory {
  final String status, reason;
  final DateTime createdAt;
  FundingHistory.fromJson(Map<String, dynamic> d)
    : status = d['status'] as String,
      reason = d['reason'] as String,
      createdAt = DateTime.parse(d['created_at'] as String);
}

class FundingCase {
  final String id, itemId, title, status;
  final int version;
  final KnowledgeItem source;
  final List<FundingHistory> history;
  FundingCase.fromJson(Map<String, dynamic> d)
    : id = identifier(d['id']),
      itemId = identifier(d['item_id']),
      title = d['item_title'] as String,
      status = d['status'] as String,
      version = versionOf(d['version']),
      source = KnowledgeItem.fromJson(object(d['source'])),
      history = rows(d['history'], FundingHistory.fromJson) {
    if (!fundingTransitions.containsKey(status) || source.id != itemId) {
      throw const FormatException();
    }
  }
}

class KnowledgeMine {
  final List<SavedKnowledge> saved;
  final List<OpportunityInterest> interests;
  final List<FundingCase> cases;
  final String? savedCursor, interestCursor, caseCursor;
  KnowledgeMine.fromJson(Map<String, dynamic> d)
    : saved = rows(d['saved_items'], SavedKnowledge.fromJson, max: 100),
      interests = rows(d['interests'], OpportunityInterest.fromJson, max: 100),
      cases = rows(d['funding_cases'], FundingCase.fromJson, max: 100),
      savedCursor = d['next_saved_cursor'] == null
          ? null
          : identifier(d['next_saved_cursor']),
      interestCursor = d['next_interest_cursor'] == null
          ? null
          : identifier(d['next_interest_cursor']),
      caseCursor = d['next_case_cursor'] == null
          ? null
          : identifier(d['next_case_cursor']);
}

final knowledgeRepositoryProvider = Provider(
  (ref) => KnowledgeRepository(
    ref.watch(domainApiProvider),
    ref.watch(authRepositoryProvider).dio,
  ),
);

class KnowledgeRepository {
  final DomainApi api;
  final Dio publicApi;
  KnowledgeRepository(this.api, this.publicApi);
  String root(String org) => '/knowledge/organizations/${identifier(org)}';
  Future<PageBatch<KnowledgeItem>> catalog(
    String org,
    Map<String, String> filters, {
    String? cursor,
    bool public = false,
  }) async {
    final query = <String, dynamic>{
      ...filters,
      'limit': 25,
      if (cursor != null) 'cursor': identifier(cursor),
    };
    final Object? data;
    if (public) {
      try {
        data = (await publicApi.get<dynamic>(
          '/public/organizations/${identifier(org)}/knowledge',
          queryParameters: query,
          options: Options(followRedirects: false, maxRedirects: 0),
        )).data;
      } on DioException catch (e) {
        throw ApiFailure.fromDio(e);
      }
    } else {
      data = await api.get('${root(org)}/catalog', queryParameters: query);
    }
    return decode(
      () => PageBatch.fromJson(object(data), KnowledgeItem.fromJson),
    );
  }

  Future<KnowledgeItem> detail(
    String org,
    String id, {
    bool public = false,
  }) async {
    final Object? data;
    if (public) {
      try {
        data = (await publicApi.get<dynamic>(
          '/public/organizations/${identifier(org)}/knowledge/${identifier(id)}',
          options: Options(followRedirects: false, maxRedirects: 0),
        )).data;
      } on DioException catch (e) {
        throw ApiFailure.fromDio(e);
      }
    } else {
      data = await api.get('${root(org)}/catalog/${identifier(id)}');
    }
    return decode(() {
      final item = KnowledgeItem.fromJson(object(data));
      if (item.id != id) throw const FormatException();
      return item;
    });
  }

  Future<KnowledgeMine> mine(
    String org, {
    String? savedCursor,
    String? interestCursor,
    String? caseCursor,
  }) async {
    final data = await api.get(
      '${root(org)}/mine',
      queryParameters: {
        'limit': 25,
        'saved_cursor': ?savedCursor,
        'interest_cursor': ?interestCursor,
        'case_cursor': ?caseCursor,
      },
    );
    return decode(() => KnowledgeMine.fromJson(object(data)));
  }

  Future<void> save(String org, String id, {required bool saved}) async {
    final path = '${root(org)}/saved/${identifier(id)}';
    if (saved) {
      await api.delete(path);
    } else {
      await api.post(path);
    }
  }

  Future<void> interest(String org, String id) async {
    await api.post('${root(org)}/interests/${identifier(id)}');
  }

  Future<FundingCase> createCase(String org, String id) async {
    final data = await api.post(
      '${root(org)}/funding-cases',
      data: {'item_id': identifier(id)},
    );
    return decode(() {
      final value = FundingCase.fromJson(object(data));
      if (value.itemId != id) throw const FormatException();
      return value;
    }, command: true);
  }

  Future<FundingCase> transition(
    String org,
    FundingCase item,
    String target,
    String reason,
  ) async {
    if (!(fundingTransitions[item.status] ?? []).contains(target) ||
        reason.trim().isEmpty ||
        reason.length > 500) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await api.post(
      '${root(org)}/funding-cases/${item.id}/status',
      data: {
        'expected_version': item.version,
        'status': target,
        'reason': reason,
      },
    );
    return decode(() {
      final result = FundingCase.fromJson(object(data));
      if (result.id != item.id || result.itemId != item.itemId) {
        throw const FormatException();
      }
      return result;
    }, command: true);
  }
}

class KnowledgeController extends ChangeNotifier with SupportRetry {
  final KnowledgeRepository repository;
  final String organizationId;
  final bool public;
  List<KnowledgeItem> catalog = [];
  List<SavedKnowledge> saved = [];
  List<OpportunityInterest> interests = [];
  List<FundingCase> cases = [];
  Map<String, String> filters = {'locale': 'en', 'availability': 'active'};
  String? cursor, savedCursor, interestCursor, caseCursor;
  String? pendingCaseId, pendingItemId;
  final Map<String, String> reasons = {};
  ApiFailure? failure;
  bool busy = false, requiresReadback = false, _disposed = false;
  int _generation = 0;
  KnowledgeController(
    this.repository,
    this.organizationId, {
    this.public = false,
  });
  Future<void> load({
    bool more = false,
    Map<String, String>? nextFilters,
  }) async {
    if (_disposed ||
        (busy && nextFilters == null) ||
        (more && cursor == null)) {
      return;
    }
    final generation = ++_generation;
    if (nextFilters != null) {
      filters = Map.of(nextFilters);
      catalog = [];
      cursor = null;
    }
    busy = true;
    failure = null;
    notifyListeners();
    try {
      final result = await repository.catalog(
        organizationId,
        filters,
        cursor: more ? cursor : null,
        public: public,
      );
      if (_disposed || generation != _generation) return;
      if (more && result.cursor == cursor && cursor != null) {
        throw const ApiFailure(
          'invalid_response',
          kind: ApiFailureKind.invalidResponse,
        );
      }
      catalog = more
          ? [
              ...catalog,
              ...result.items.where(
                (item) => !catalog.any((old) => old.id == item.id),
              ),
            ]
          : result.items;
      cursor = result.cursor;
    } catch (e) {
      if (!_disposed && generation == _generation) failure = failureOf(e);
      recordFailure(failure!);
    } finally {
      if (!_disposed && generation == _generation) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadMine({String? more}) async {
    if (public || busy || retryDelayed || _disposed) return;
    busy = true;
    failure = null;
    notifyListeners();
    try {
      FundingCase? recovered;
      if (requiresReadback &&
          (pendingCaseId != null || pendingItemId != null)) {
        String? next;
        final seen = <String>{};
        var pages = 0;
        do {
          final batch = await repository.mine(organizationId, caseCursor: next);
          if (_disposed) return;
          recovered = batch.cases
              .where(
                (c) => pendingCaseId != null
                    ? c.id == pendingCaseId
                    : c.itemId == pendingItemId,
              )
              .firstOrNull;
          next = batch.caseCursor;
          if (next != null && (!seen.add(next) || ++pages > 200)) {
            throw const ApiFailure(
              'invalid_response',
              kind: ApiFailureKind.invalidResponse,
            );
          }
        } while (recovered == null && next != null);
        if (recovered == null && pendingCaseId != null) {
          throw const ApiFailure('not_found', kind: ApiFailureKind.notFound);
        }
      }
      final result = await repository.mine(
        organizationId,
        savedCursor: more == 'saved' ? savedCursor : null,
        interestCursor: more == 'interests' ? interestCursor : null,
        caseCursor: more == 'cases' ? caseCursor : null,
      );
      if (_disposed) return;
      if (more == null || more == 'saved') {
        saved = more == null ? result.saved : [...saved, ...result.saved];
        savedCursor = result.savedCursor;
      }
      if (more == null || more == 'interests') {
        interests = more == null
            ? result.interests
            : [...interests, ...result.interests];
        interestCursor = result.interestCursor;
      }
      if (more == null || more == 'cases') {
        cases = more == null ? result.cases : [...cases, ...result.cases];
        caseCursor = result.caseCursor;
      }
      if (recovered != null) {
        cases = [...cases.where((c) => c.id != recovered!.id), recovered];
      }
      requiresReadback = false;
      pendingCaseId = null;
      pendingItemId = null;
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

  Future<void> saveItem(KnowledgeItem item) async => _write(
    () => repository.save(
      organizationId,
      item.id,
      saved: saved.any((s) => s.itemId == item.id),
    ),
  );
  Future<void> unsaveItem(String id) async =>
      _write(() => repository.save(organizationId, id, saved: true));
  Future<void> interestIn(KnowledgeItem item) async =>
      _write(() => repository.interest(organizationId, item.id));
  Future<void> createCase(KnowledgeItem item) async {
    if (public || busy || retryDelayed || requiresReadback || _disposed) return;
    pendingItemId = item.id;
    await _write(() async {
      await repository.createCase(organizationId, item.id);
    });
  }

  Future<void> transition(FundingCase item, String target) async {
    if (public || busy || retryDelayed || requiresReadback || _disposed) return;
    pendingCaseId = item.id;
    await _write(() async {
      final updated = await repository.transition(
        organizationId,
        item,
        target,
        reasons[item.id] ?? '',
      );
      if (!_disposed) {
        cases = [
          for (final old in cases)
            if (old.id == updated.id) updated else old,
        ];
        reasons.remove(item.id);
      }
    });
  }

  Future<void> _write(Future<void> Function() command) async {
    if (public || busy || retryDelayed || requiresReadback || _disposed) return;
    busy = true;
    failure = null;
    notifyListeners();
    try {
      await command();
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
        requiresReadback =
            failure!.uncertain || failure!.kind == ApiFailureKind.conflict;
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
    if (!_disposed && failure == null) await loadMine();
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    catalog = [];
    saved = [];
    cases = [];
    interests = [];
    reasons.clear();
    super.dispose();
  }
}
