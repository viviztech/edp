import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../../core/navigation/destinations.dart';
import '../identity/providers.dart';
import '../../l10n/app_localizations.dart';

class ApplicationHistoryEntry {
  final String id, organizationId, organizationName, state;
  final String? cycleId, number, cycleNameEn, cycleNameTa;
  final int version;
  ApplicationHistoryEntry.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      organizationId = json['organization_id'] as String,
      organizationName = json['organization_name'] as String,
      state = json['state'] as String,
      cycleId = json['cycle_id'] as String?,
      number = json['application_number'] as String?,
      cycleNameEn = json['cycle_name_en'] as String?,
      cycleNameTa = json['cycle_name_ta'] as String?,
      version = json['version'] as int;
}

class ApplicationHistoryBatch {
  final List<ApplicationHistoryEntry> items;
  final String? nextCursor;
  ApplicationHistoryBatch.fromJson(Map<String, dynamic> json)
    : items = List.unmodifiable(
        (json['items'] as List)
            .map(
              (item) => ApplicationHistoryEntry.fromJson(
                Map<String, dynamic>.from(item as Map),
              ),
            )
            .toList(),
      ),
      nextCursor = json['next_cursor'] as String?;
}

class ApplicationHistoryRepository {
  final DomainApi api;
  ApplicationHistoryRepository(this.api);
  Future<ApplicationHistoryBatch> list({String? cursor}) async {
    if (cursor != null && !MobileDestination.uuid.hasMatch(cursor)) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await api.get(
      '/applications/mine',
      queryParameters: {'limit': 25, 'cursor': ?cursor},
    );
    try {
      final batch = ApplicationHistoryBatch.fromJson(
        Map<String, dynamic>.from(data as Map),
      );
      if (batch.items.length > 25 ||
          batch.items.map((item) => item.id).toSet().length !=
              batch.items.length ||
          batch.items.any(
            (item) =>
                !MobileDestination.uuid.hasMatch(item.id) ||
                !MobileDestination.uuid.hasMatch(item.organizationId) ||
                (item.cycleId != null &&
                    !MobileDestination.uuid.hasMatch(item.cycleId!)) ||
                item.version < 1,
          ) ||
          (batch.nextCursor != null &&
              (!MobileDestination.uuid.hasMatch(batch.nextCursor!) ||
                  batch.nextCursor == cursor))) {
        throw const FormatException();
      }
      return batch;
    } catch (_) {
      throw const ApiFailure(
        'invalid_response',
        kind: ApiFailureKind.invalidResponse,
      );
    }
  }
}

final applicationHistoryRepositoryProvider = Provider(
  (ref) => ApplicationHistoryRepository(ref.watch(domainApiProvider)),
);

class ApplicationHistory extends ConsumerStatefulWidget {
  final void Function(ApplicationHistoryEntry)? onOpen;
  const ApplicationHistory({super.key, this.onOpen});
  @override
  ConsumerState<ApplicationHistory> createState() => _ApplicationHistoryState();
}

class _ApplicationHistoryState extends ConsumerState<ApplicationHistory> {
  List<ApplicationHistoryEntry> items = [];
  String? cursor;
  bool loading = true, failed = false;
  int generation = 0;
  bool failedMore = false;
  final Set<String> previousCursors = {};
  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  Future<void> load({bool more = false}) async {
    if (!mounted || (more && cursor == null)) return;
    final request = ++generation;
    setState(() {
      loading = true;
      failed = false;
    });
    try {
      final batch = await ref
          .read(applicationHistoryRepositoryProvider)
          .list(cursor: more ? cursor : null);
      if (!mounted || request != generation) return;
      if ((more &&
              batch.items.any(
                (item) => items.any((old) => old.id == item.id),
              )) ||
          (more &&
              batch.nextCursor != null &&
              previousCursors.contains(batch.nextCursor))) {
        throw const ApiFailure(
          'invalid_response',
          kind: ApiFailureKind.invalidResponse,
        );
      }
      setState(() {
        if (!more) previousCursors.clear();
        if (cursor != null && more) previousCursors.add(cursor!);
        items = more ? [...items, ...batch.items] : batch.items;
        cursor = batch.nextCursor;
      });
    } catch (_) {
      if (mounted && request == generation) {
        setState(() {
          failed = true;
          failedMore = more;
        });
      }
    } finally {
      if (mounted && request == generation) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = AppLocalizations.of(context)!;
    final tamil = Localizations.localeOf(context).languageCode == 'ta';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          text.mobileApplications,
          style: Theme.of(context).textTheme.titleLarge,
        ),
        if (loading) const LinearProgressIndicator(),
        if (failed) ...[
          Text(text.cmsError),
          TextButton(
            onPressed: loading ? null : () => load(more: failedMore),
            child: Text(text.cmsRetry),
          ),
        ],
        if (!loading && !failed && items.isEmpty)
          Text(text.mobileNoApplications),
        for (final item in items)
          Card(
            child: ListTile(
              title: Text(
                item.number ??
                    (tamil ? item.cycleNameTa : item.cycleNameEn) ??
                    item.organizationName,
              ),
              subtitle: Text(
                '${item.organizationName} · ${applicationStateLabel(text, item.state)}',
              ),
              trailing: widget.onOpen == null
                  ? null
                  : const Icon(Icons.chevron_right),
              onTap: widget.onOpen == null ? null : () => widget.onOpen!(item),
            ),
          ),
        if (cursor != null)
          TextButton(
            onPressed: loading ? null : () => load(more: true),
            child: Text(text.cmsMore),
          ),
      ],
    );
  }
}

String applicationStateLabel(AppLocalizations text, String state) =>
    switch (state) {
      'draft' => text.mobileDraft,
      'submitted' => text.mobileSubmitted,
      'under_review' => text.mobileUnderReview,
      'shortlisted' => text.mobileShortlisted,
      'interview_scheduled' => text.mobileInterview,
      'selected' => text.mobileSelected,
      'waitlisted' => text.mobileWaitlisted,
      'rejected' => text.mobileRejected,
      'enrolled' => text.mobileEnrolled,
      _ => text.cmsUnavailable,
    };
