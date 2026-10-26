import 'support_labels.dart';
import '../../l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'mentoring.dart';
import 'support_common.dart';

class MentoringView extends ConsumerStatefulWidget {
  final String organizationId;
  final void Function(bool, bool) onState;
  const MentoringView({
    super.key,
    required this.organizationId,
    required this.onState,
  });
  @override
  ConsumerState<MentoringView> createState() => _MentoringViewState();
}

class _MentoringViewState extends ConsumerState<MentoringView> {
  late MentoringController controller;
  String? sessionId;
  @override
  void initState() {
    super.initState();
    controller = MentoringController(
      ref.read(mentoringRepositoryProvider),
      widget.organizationId,
    )..addListener(changed);
    Future.microtask(controller.refresh);
  }

  void changed() {
    if (mounted) {
      widget.onState(
        controller.comment.isNotEmpty || controller.requiresReadback,
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
    final model = controller, data = model.data;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          AppLocalizations.of(context)!.domainMyMentoringb93152,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        if (model.busy) const LinearProgressIndicator(),
        SupportError(model.failure),
        TextButton(
          onPressed: model.busy ? null : model.refresh,
          child: Text(
            AppLocalizations.of(context)!.domainRefreshMentoringeee9c0,
          ),
        ),
        if (data != null) ...[
          if (data.assignments.isEmpty)
            Text(
              AppLocalizations.of(
                context,
              )!.domainNoMentoringAssignmentsAreAvailable4ebb99,
            ),
          for (final assignment in data.assignments)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      assignment.mentorName,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    Text(
                      '${supportLabel(context, assignment.state)} · ${dateText(context, assignment.startsOn, dateOnly: true)}',
                    ),
                    if (assignment.endsOn != null)
                      Text(
                        dateText(context, assignment.endsOn!, dateOnly: true),
                      ),
                    for (final session in data.sessions.where(
                      (s) => s.assignmentId == assignment.id,
                    )) ...[
                      Text(
                        '${session.topic} · ${supportLabel(context, session.status)}',
                      ),
                      Text(
                        '${dateText(context, session.startsAt)} – ${dateText(context, session.endsAt)}',
                      ),
                      Text(
                        supportLabel(context, session.mode),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (session.location != null)
                        SelectableText(session.location!),
                      for (final feedback in data.feedback.where(
                        (f) => f.sessionId == session.id,
                      ))
                        Text(
                          '${feedback.rating}/5 · ${feedback.comment ?? ''}',
                        ),
                    ],
                    for (final note in data.notes.where(
                      (n) => n.assignmentId == assignment.id,
                    ))
                      Text(note.body),
                    for (final work in [
                      ...data.goals,
                      ...data.actions,
                      ...data.followUps,
                    ].where((w) => w.assignmentId == assignment.id)) ...[
                      Text(
                        '${work.title} · ${supportLabel(context, work.state)}${work.progress == null ? '' : ' · ${work.progress}%'}',
                      ),
                      if (work.description != null) Text(work.description!),
                      if (work.due != null) Text(dateText(context, work.due!)),
                    ],
                  ],
                ),
              ),
            ),
          if (data.sessions.any(
            (s) =>
                s.status == 'completed' &&
                !data.feedback.any((f) => f.sessionId == s.id),
          )) ...[
            DropdownButtonFormField<String>(
              initialValue: sessionId,
              isExpanded: true,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(
                  context,
                )!.domainCompletedSessionfca593,
              ),
              items: [
                for (final s in data.sessions.where(
                  (s) =>
                      s.status == 'completed' &&
                      !data.feedback.any((f) => f.sessionId == s.id),
                ))
                  DropdownMenuItem(value: s.id, child: Text(s.topic)),
              ],
              onChanged: model.busy || model.requiresReadback
                  ? null
                  : (v) => setState(() => sessionId = v),
            ),
            DropdownButtonFormField<int>(
              initialValue: model.rating,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.domainRating15b4690a,
              ),
              items: [
                for (var i = 1; i <= 5; i++)
                  DropdownMenuItem(value: i, child: Text('$i')),
              ],
              onChanged: model.busy ? null : (v) => model.rating = v ?? 5,
            ),
            TextFormField(
              key: ValueKey('feedback:${model.comment.isEmpty}'),
              initialValue: model.comment,
              maxLength: 2000,
              maxLines: 3,
              enabled: !model.busy,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(
                  context,
                )!.domainFeedbackCommentbf4a27,
              ),
              onChanged: (v) {
                model.comment = v;
                widget.onState(v.isNotEmpty, model.busy);
              },
            ),
            FilledButton(
              onPressed:
                  sessionId == null || model.busy || model.requiresReadback
                  ? null
                  : () => model.send(sessionId!),
              child: Text(
                AppLocalizations.of(context)!.domainSendSessionFeedbacke07582,
              ),
            ),
          ],
        ],
      ],
    );
  }
}
