import 'support_labels.dart';
import '../../l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'helpdesk_view.dart';
import 'knowledge_view.dart';
import 'mentoring_view.dart';
import 'plans_view.dart';
import 'support_common.dart';

class ParticipantSupportPage extends StatefulWidget {
  final String organizationId, initialSection;
  final String? initialTicketId;
  const ParticipantSupportPage({
    super.key,
    required this.organizationId,
    this.initialSection = 'support',
    this.initialTicketId,
  });
  @override
  State<ParticipantSupportPage> createState() => _ParticipantSupportPageState();
}

class _ParticipantSupportPageState extends State<ParticipantSupportPage> {
  late String section;
  bool dirty = false, busy = false, leaving = false;
  @override
  void initState() {
    super.initState();
    identifier(widget.organizationId);
    section =
        {
          'support',
          'mentoring',
          'plans',
          'resources',
        }.contains(widget.initialSection)
        ? widget.initialSection
        : 'support';
  }

  void stateChanged(bool nextDirty, bool nextBusy) {
    if (!mounted || dirty == nextDirty && busy == nextBusy) return;
    setState(() {
      dirty = nextDirty;
      busy = nextBusy;
    });
  }

  Future<void> select(String next) async {
    if (section == next || busy) return;
    if (dirty &&
        !await confirmAction(
          context,
          AppLocalizations.of(
            context,
          )!.domainDiscardUnsavedTextAndSelectedPrivatea3487b,
        )) {
      return;
    }
    if (mounted) {
      setState(() {
        section = next;
        dirty = false;
        busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !dirty && !busy || leaving,
    onPopInvokedWithResult: (didPop, result) async {
      if (didPop || busy || leaving) return;
      if (await confirmAction(
            context,
            AppLocalizations.of(
              context,
            )!.domainLeaveThisPageAndDiscardUnsavedcb9eed,
          ) &&
          mounted) {
        setState(() => leaving = true);
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) context.pop();
        });
      }
    },
    child: Scaffold(
      appBar: AppBar(
        title: Text(
          AppLocalizations.of(context)!.domainParticipantSupporte5a040,
        ),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(8),
            child: Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                for (final item in [
                  'support',
                  'mentoring',
                  'plans',
                  'resources',
                ])
                  ChoiceChip(
                    label: Text(supportLabel(context, item)),
                    selected: section == item,
                    onSelected: busy ? null : (_) => select(item),
                  ),
              ],
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: KeyedSubtree(
                key: ValueKey('${widget.organizationId}:$section'),
                child: switch (section) {
                  'mentoring' => MentoringView(
                    organizationId: widget.organizationId,
                    onState: stateChanged,
                  ),
                  'plans' => PlansView(
                    organizationId: widget.organizationId,
                    onState: stateChanged,
                  ),
                  'resources' => KnowledgeView(
                    organizationId: widget.organizationId,
                    onState: stateChanged,
                  ),
                  _ => HelpdeskView(
                    organizationId: widget.organizationId,
                    initialTicketId: widget.initialTicketId,
                    onState: stateChanged,
                  ),
                },
              ),
            ),
          ),
        ],
      ),
    ),
  );
}
