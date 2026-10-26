import 'support_labels.dart';
import '../../l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'plans.dart';
import 'support_common.dart';

class PlansView extends ConsumerStatefulWidget {
  final String organizationId;
  final void Function(bool, bool) onState;
  const PlansView({
    super.key,
    required this.organizationId,
    required this.onState,
  });
  @override
  ConsumerState<PlansView> createState() => _PlansViewState();
}

class _PlansViewState extends ConsumerState<PlansView> {
  late PlansController controller;
  @override
  void initState() {
    super.initState();
    controller = PlansController(
      ref.read(plansRepositoryProvider),
      widget.organizationId,
    )..addListener(changed);
    Future.microtask(controller.load);
  }

  void changed() {
    if (mounted) {
      widget.onState(
        controller.dirty || controller.requiresReview,
        controller.busy,
      );
      setState(() {});
    }
  }

  @override
  void dispose() {
    controller.removeListener(changed);
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final model = controller, plan = model.plan;
    String label(String code) => supportLabel(context, code);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          AppLocalizations.of(context)!.domainMyBusinessPlanf1ef69,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        if (model.busy) const LinearProgressIndicator(),
        SupportError(model.failure),
        TextButton(
          onPressed: model.busy ? null : () => model.load(),
          child: Text(AppLocalizations.of(context)!.domainRefreshPlanscbc510),
        ),
        if (model.entries.isEmpty && !model.busy)
          Text(
            AppLocalizations.of(
              context,
            )!.domainNoActiveEnrollmentIsAvailableFor2f3a04,
          ),
        if (model.entries.isNotEmpty)
          DropdownButtonFormField<String>(
            key: ValueKey(model.selectedEnrollment),
            initialValue: model.selectedEnrollment,
            isExpanded: true,
            decoration: InputDecoration(
              labelText: AppLocalizations.of(
                context,
              )!.domainActiveEnrollmentebb2ab,
            ),
            items: [
              for (final entry in model.entries)
                DropdownMenuItem(
                  value: entry.enrollmentId,
                  child: Text(entry.enrollmentId),
                ),
            ],
            onChanged: model.busy
                ? null
                : (v) async {
                    if (v == null || v == model.selectedEnrollment) return;
                    if (model.dirty &&
                        !await confirmAction(
                          context,
                          AppLocalizations.of(
                            context,
                          )!.domainDiscardEditsBeforeChangingEnrollment28e2f9,
                        )) {
                      return;
                    }
                    model.edits.clear();
                    model.requiresReview = false;
                    await model.load(enrollment: v);
                  },
          ),
        if (model.requiresReview && model.readbackReady) ...[
          Text(
            AppLocalizations.of(
              context,
            )!.domainReviewTheCurrentSavedPlanBefore514269,
          ),
          TextButton(
            onPressed: model.busy || !model.readbackReady
                ? null
                : () => model.resolve(keepEdits: true),
            child: Text(
              AppLocalizations.of(
                context,
              )!.domainUseCurrentVersionAndKeepMybb6388,
            ),
          ),
          TextButton(
            onPressed: model.busy || !model.readbackReady
                ? null
                : () => model.resolve(keepEdits: false),
            child: Text(AppLocalizations.of(context)!.domainUseSavedPlanfee405),
          ),
        ],
        if (plan == null &&
            model.selectedEnrollment != null &&
            !model.requiresReview)
          FilledButton(
            onPressed: model.busy ? null : model.create,
            child: Text(AppLocalizations.of(context)!.domainCreatePlan4e207a),
          ),
        if (plan != null) ...[
          Text(
            '${supportLabel(context, plan.status)} · ${plan.completed}/${plan.total} · v${plan.version}',
          ),
          for (final code in planSections)
            ExpansionTile(
              key: ValueKey('${plan.id}:$code'),
              title: Text(label(code)),
              children: [
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: TextFormField(
                    key: ValueKey(
                      '${plan.id}:$code:${plan.version}:${model.requiresReview}',
                    ),
                    initialValue:
                        model.edits[code] ?? plan.sections[code] ?? '',
                    enabled: model.canWrite,
                    maxLength: 10000,
                    minLines: 3,
                    maxLines: 8,
                    decoration: InputDecoration(labelText: label(code)),
                    onChanged: (v) => model.edit(code, v),
                  ),
                ),
                if (plan.editable)
                  TextButton(
                    onPressed: model.canWrite && model.edits.containsKey(code)
                        ? () => model.save(code)
                        : null,
                    child: Text(
                      AppLocalizations.of(context)!.domainSaveThisSection1e6c91,
                    ),
                  ),
              ],
            ),
          if (plan.editable)
            FilledButton(
              onPressed: model.canWrite && !model.dirty && plan.completed == 20
                  ? () async {
                      if (await confirmAction(
                        context,
                        AppLocalizations.of(
                          context,
                        )!.domainSubmitThisSavedPlanForReview262665,
                      )) {
                        await model.submit();
                      }
                    }
                  : null,
              child: Text(
                AppLocalizations.of(context)!.domainSubmitSavedPlan231cac,
              ),
            ),
          for (final submission in plan.submissions)
            ExpansionTile(
              title: Text(
                '${AppLocalizations.of(context)!.domainSubmission8d11f7} ${submission.number} · v${submission.version}',
              ),
              children: [
                Text(dateText(context, submission.createdAt)),
                for (final section in submission.snapshot.entries)
                  ListTile(
                    title: Text(label(section.key)),
                    subtitle: Text(section.value),
                  ),
                if (submission.review case final review?) ...[
                  Text('${review.decision} · ${review.reason}'),
                  for (final comment in review.comments.entries)
                    ListTile(
                      title: Text(label(comment.key)),
                      subtitle: Text(comment.value),
                    ),
                ],
              ],
            ),
        ],
      ],
    );
  }
}
