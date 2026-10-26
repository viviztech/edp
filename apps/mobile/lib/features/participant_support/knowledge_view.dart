import 'support_labels.dart';
import '../../l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/links/external_links.dart';
import 'knowledge.dart';
import 'support_common.dart';

class KnowledgeView extends ConsumerStatefulWidget {
  final String organizationId;
  final bool public;
  final void Function(bool, bool)? onState;
  const KnowledgeView({
    super.key,
    required this.organizationId,
    this.public = false,
    this.onState,
  });
  @override
  ConsumerState<KnowledgeView> createState() => _KnowledgeViewState();
}

class _KnowledgeViewState extends ConsumerState<KnowledgeView> {
  late KnowledgeController controller;
  String? _locale;
  bool opening = false;
  final filterControllers = {
    for (final key in ['q', 'sector', 'geography', 'tag'])
      key: TextEditingController(),
  };
  String kind = '', availability = 'active';
  @override
  void initState() {
    super.initState();
    controller = KnowledgeController(
      ref.read(knowledgeRepositoryProvider),
      widget.organizationId,
      public: widget.public,
    )..addListener(changed);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final locale = Localizations.localeOf(context).languageCode;
    if (_locale != locale) {
      _locale = locale;
      Future.microtask(() async {
        await controller.load(
          nextFilters: {'locale': locale, 'availability': availability},
        );
        if (!widget.public) await controller.loadMine();
      });
    }
  }

  void changed() {
    if (mounted) {
      widget.onState?.call(
        controller.reasons.values.any((r) => r.isNotEmpty) ||
            controller.requiresReadback,
        controller.busy,
      );
      setState(() {});
    }
  }

  @override
  void dispose() {
    controller.removeListener(changed);
    controller.dispose();
    for (final input in filterControllers.values) {
      input.dispose();
    }
    super.dispose();
  }

  Future<void> openItem(KnowledgeItem item, {bool external = false}) async {
    if (opening) return;
    setState(() => opening = true);
    try {
      final current = await controller.repository.detail(
        widget.organizationId,
        item.id,
        public: widget.public,
      );
      if (!mounted) return;
      if (external) {
        final opened = await ref
            .read(externalLinksProvider)
            .open(current.officialUrl);
        if (!opened && mounted) {
          await Clipboard.setData(ClipboardData(text: current.officialUrl));
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(
                  AppLocalizations.of(context)!.domainOfficialLinkCopiede5a1aa,
                ),
              ),
            );
          }
        }
      } else {
        await showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(current.title),
            content: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(current.provider),
                  Text(current.description),
                  Text(current.eligibility),
                  Text(current.benefits),
                  Text(current.process),
                  for (final name in current.documents) Text(name),
                  Text(current.contact),
                  SelectableText(current.officialUrl),
                  Text(
                    '${AppLocalizations.of(context)!.domainVerified4f7838}: ${dateText(context, current.verifiedAt, dateOnly: true)}',
                  ),
                  if (current.closesOn != null)
                    Text(
                      '${AppLocalizations.of(context)!.domainCloses74c21a}: ${dateText(context, current.closesOn!, dateOnly: true)}',
                    ),
                  if (current.minimum != null || current.maximum != null)
                    Text(
                      'INR ${current.minimum ?? '—'} – ${current.maximum ?? '—'}',
                    ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: Text(AppLocalizations.of(context)!.domainClose7d9eb7),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        controller.failure = failureOf(e);
        setState(() {});
      }
    } finally {
      if (mounted) setState(() => opening = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final model = controller;
    Widget moreButton(String title, String? cursor, VoidCallback action) =>
        cursor == null
        ? const SizedBox.shrink()
        : TextButton(onPressed: model.busy ? null : action, child: Text(title));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          AppLocalizations.of(
            context,
          )!.domainResourcesOpportunitiesAndFunding0ba4d7,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        if (model.busy || opening) const LinearProgressIndicator(),
        SupportError(model.failure),
        for (final field in ['q', 'sector', 'geography', 'tag'])
          TextField(
            controller: filterControllers[field],
            maxLength: field == 'tag' ? 200 : 120,
            decoration: InputDecoration(
              labelText: supportLabel(context, field),
            ),
          ),
        DropdownButtonFormField<String>(
          isExpanded: true,
          initialValue: kind,
          decoration: InputDecoration(
            labelText: AppLocalizations.of(context)!.domainResourceTypec9bf2e,
          ),
          items: [
            for (final code in ['', 'scheme', 'funding', 'opportunity'])
              DropdownMenuItem(
                value: code,
                child: Text(
                  code.isEmpty
                      ? AppLocalizations.of(context)!.domainAllTypesf10988
                      : supportLabel(context, code),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
          ],
          onChanged: (v) => kind = v ?? '',
        ),
        DropdownButtonFormField<String>(
          isExpanded: true,
          initialValue: availability,
          decoration: InputDecoration(
            labelText: AppLocalizations.of(context)!.domainAvailability12f67f,
          ),
          items: [
            for (final code in ['active', 'all', 'upcoming', 'open', 'closed'])
              DropdownMenuItem(
                value: code,
                child: Text(
                  supportLabel(context, code),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
          ],
          onChanged: (v) => availability = v ?? 'active',
        ),
        FilledButton(
          onPressed: model.busy
              ? null
              : () => model.load(
                  nextFilters: {
                    'locale': _locale ?? 'en',
                    'availability': availability,
                    if (kind.isNotEmpty) 'kind': kind,
                    for (final item in filterControllers.entries)
                      if (item.value.text.trim().isNotEmpty)
                        item.key: item.value.text.trim(),
                  },
                ),
          child: Text(AppLocalizations.of(context)!.domainApplyFiltersd80ab1),
        ),
        if (model.catalog.isEmpty && !model.busy)
          Text(AppLocalizations.of(context)!.domainNoMatchingResourcesfee1b1),
        for (final item in model.catalog)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    item.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text(
                    '${item.provider} · ${supportLabel(context, item.availability)}',
                  ),
                  Text('${item.sector} · ${item.geography}'),
                  Text(
                    '${AppLocalizations.of(context)!.domainVerified4f7838}: ${dateText(context, item.verifiedAt, dateOnly: true)}',
                  ),
                  if (item.closesOn != null)
                    Text(
                      '${AppLocalizations.of(context)!.domainCloses74c21a}: ${dateText(context, item.closesOn!, dateOnly: true)}',
                    ),
                  Wrap(
                    spacing: 8,
                    children: [
                      TextButton(
                        onPressed: opening ? null : () => openItem(item),
                        child: Text(
                          AppLocalizations.of(context)!.domainDetails45989d,
                        ),
                      ),
                      TextButton(
                        onPressed: opening
                            ? null
                            : () => openItem(item, external: true),
                        child: Text(
                          AppLocalizations.of(
                            context,
                          )!.domainOpenOfficialSource7bd352,
                        ),
                      ),
                      if (!widget.public) ...[
                        TextButton(
                          onPressed: model.busy || model.requiresReadback
                              ? null
                              : () => model.saveItem(item),
                          child: Text(
                            model.saved.any((s) => s.itemId == item.id)
                                ? AppLocalizations.of(
                                    context,
                                  )!.domainUnsave51883b
                                : AppLocalizations.of(
                                    context,
                                  )!.domainSave1509f5,
                          ),
                        ),
                        if (item.kind == 'opportunity')
                          TextButton(
                            onPressed: model.busy || model.requiresReadback
                                ? null
                                : () => model.interestIn(item),
                            child: Text(
                              AppLocalizations.of(
                                context,
                              )!.domainExpressInterest97c8c3,
                            ),
                          ),
                        if (item.kind == 'funding')
                          TextButton(
                            onPressed: model.busy || model.requiresReadback
                                ? null
                                : () => model.createCase(item),
                            child: Text(
                              AppLocalizations.of(
                                context,
                              )!.domainTrackMyFundingApplicationb7f857,
                            ),
                          ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
          ),
        moreButton(
          AppLocalizations.of(context)!.domainMoreResources3f990f,
          model.cursor,
          () => model.load(more: true),
        ),
        if (!widget.public) ...[
          TextButton(
            onPressed: model.busy ? null : () => model.loadMine(),
            child: Text(
              AppLocalizations.of(
                context,
              )!.domainRefreshSavedItemsAndFundingStatusea7e93,
            ),
          ),
          Text(
            AppLocalizations.of(context)!.domainSavedResources5d702b,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          for (final saved in model.saved)
            ListTile(
              title: Text(
                saved.item?.title ??
                    AppLocalizations.of(
                      context,
                    )!.domainResourceNoLongerAvailable008112,
              ),
              onTap: saved.item == null ? null : () => openItem(saved.item!),
              trailing: IconButton(
                tooltip: AppLocalizations.of(context)!.domainUnsave51883b,
                icon: const Icon(Icons.bookmark_remove),
                onPressed: model.busy || model.requiresReadback
                    ? null
                    : () => model.unsaveItem(saved.itemId),
              ),
            ),
          moreButton(
            AppLocalizations.of(context)!.domainMoreSavedItems5862e9,
            model.savedCursor,
            () => model.loadMine(more: 'saved'),
          ),
          Text(
            AppLocalizations.of(context)!.domainOpportunityInterests68b05b,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          for (final interest in model.interests) Text(interest.title),
          moreButton(
            AppLocalizations.of(context)!.domainMoreInterests5eaef0,
            model.interestCursor,
            () => model.loadMine(more: 'interests'),
          ),
          Text(
            AppLocalizations.of(
              context,
            )!.domainSelfReportedFundingProgress81e27b,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          for (final item in model.cases)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(item.title),
                    Text(
                      '${supportLabel(context, item.status)} · v${item.version}',
                    ),
                    for (final event in item.history)
                      Text(
                        '${dateText(context, event.createdAt)} · ${supportLabel(context, event.status)} · ${event.reason}',
                      ),
                    if ((fundingTransitions[item.status] ?? []).isNotEmpty) ...[
                      TextFormField(
                        key: ValueKey('reason:${item.id}:${item.version}'),
                        initialValue: model.reasons[item.id] ?? '',
                        maxLength: 500,
                        decoration: InputDecoration(
                          labelText: AppLocalizations.of(
                            context,
                          )!.domainReasonUpdate49c0dc,
                        ),
                        onChanged: (v) {
                          model.reasons[item.id] = v;
                          widget.onState?.call(
                            model.reasons.values.any((r) => r.isNotEmpty),
                            model.busy,
                          );
                        },
                      ),
                      for (final target in fundingTransitions[item.status]!)
                        TextButton(
                          onPressed: model.busy || model.requiresReadback
                              ? null
                              : () async {
                                  if (await confirmAction(
                                    context,
                                    AppLocalizations.of(
                                      context,
                                    )!.domainRecordThisFundingStatusUpdate888dec,
                                  )) {
                                    await model.transition(item, target);
                                  }
                                },
                          child: Text(
                            supportLabel(context, target),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                    ],
                  ],
                ),
              ),
            ),
          moreButton(
            AppLocalizations.of(context)!.domainMoreFundingCases3e9368,
            model.caseCursor,
            () => model.loadMine(more: 'cases'),
          ),
        ],
      ],
    );
  }
}
