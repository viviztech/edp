import 'support_labels.dart';
import '../../l10n/app_localizations.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/files/private_files.dart';
import '../../core/api/api_failure.dart';
import '../../core/files/providers.dart';
import 'helpdesk.dart';
import 'helpdesk_files.dart';
import 'support_common.dart';

class HelpdeskView extends ConsumerStatefulWidget {
  final String organizationId;
  final String? initialTicketId;
  final void Function(bool, bool) onState;
  const HelpdeskView({
    super.key,
    required this.organizationId,
    required this.onState,
    this.initialTicketId,
  });
  @override
  ConsumerState<HelpdeskView> createState() => _HelpdeskViewState();
}

class _HelpdeskViewState extends ConsumerState<HelpdeskView>
    with WidgetsBindingObserver {
  late HelpdeskController controller;
  HelpdeskFilesController? files;
  PrivateSnapshot? receipt;
  int scopeGeneration = 0;
  String? requestedTicket;
  ApiFailure? scopeFailure;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    controller = HelpdeskController(
      ref.read(helpdeskRepositoryProvider),
      widget.organizationId,
    )..addListener(changed);
    Future.microtask(() async {
      await controller.list();
      await controller.loadNotices();
      if (mounted && widget.initialTicketId != null) {
        await controller.open(widget.initialTicketId!);
      }
    });
  }

  void changed() {
    if (!mounted) return;
    syncFiles();
    widget.onState(
      controller.dirty ||
          controller.requiresReadback ||
          files?.hasPending == true ||
          files?.selected.isNotEmpty == true,
      controller.busy || files?.busy == true,
    );
    setState(() {});
  }

  void fileChanged() {
    if (!mounted) return;
    widget.onState(
      controller.dirty ||
          controller.requiresReadback ||
          files?.hasPending == true ||
          files?.selected.isNotEmpty == true,
      controller.busy || files?.busy == true,
    );
    setState(() {});
  }

  void syncFiles() {
    final id = controller.ticket?.id;
    if (id == requestedTicket) return;
    requestedTicket = id;
    final generation = ++scopeGeneration;
    files?.removeListener(fileChanged);
    files?.dispose();
    files = null;
    scopeFailure = null;
    unawaited(closeReceipt());
    if (id == null) return;
    Future<void>(() async {
      PrivateFileScope? scope;
      ApiFailure? storageFailure;
      try {
        final store = ref.read(privateFilesProvider);
        if (store.supported) scope = await store.createScope();
      } catch (error) {
        storageFailure = failureOf(error);
        /* Metadata remains available. */
      }
      if (!mounted || generation != scopeGeneration) {
        await scope?.close();
        return;
      }
      files = HelpdeskFilesController(
        ref.read(helpdeskFilesRepositoryProvider),
        widget.organizationId,
        id,
        scope,
      )..addListener(fileChanged);
      scopeFailure = storageFailure;
      setState(() {});
      await files!.refresh();
    });
  }

  Future<void> closeReceipt() async {
    final current = receipt;
    receipt = null;
    if (mounted) setState(() {});
    try {
      await current?.dispose();
    } catch (_) {
      /* Store fails closed. */
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if ({
      AppLifecycleState.hidden,
      AppLifecycleState.paused,
      AppLifecycleState.detached,
    }.contains(state)) {
      files?.pause();
      unawaited(closeReceipt());
    }
    if (state == AppLifecycleState.resumed) {
      unawaited(files?.resume());
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    scopeGeneration++;
    controller.removeListener(changed);
    controller.dispose();
    files?.removeListener(fileChanged);
    files?.dispose();
    final copy = receipt;
    receipt = null;
    unawaited(copy?.dispose().catchError((Object _) {}) ?? Future.value());
    super.dispose();
  }

  Future<bool> canChangeTicket() async {
    if (controller.busy ||
        files?.busy == true ||
        controller.creationIntent != null) {
      return false;
    }
    if (controller.reply.isNotEmpty ||
        controller.reason.isNotEmpty ||
        controller.legacyText.isNotEmpty ||
        files?.hasPending == true ||
        files?.selected.isNotEmpty == true) {
      return confirmAction(
        context,
        AppLocalizations.of(context)!.domainDiscardThisTicketSUnsentText23075b,
      );
    }
    return true;
  }

  Future<void> choose(String id) async {
    if (controller.ticket?.id == id) {
      await controller.open(id);
      return;
    }
    if (await canChangeTicket()) await controller.open(id);
  }

  Future<void> download(SupportFile file) async {
    final result = await files?.download(file);
    if (result == null) return;
    if (!mounted) {
      await result.dispose();
      return;
    }
    await closeReceipt();
    if (mounted) {
      setState(() => receipt = result);
    } else {
      await result.dispose();
    }
  }

  Future<void> legacy(LegacyAttachment file) async {
    final ticket = controller.ticket;
    if (ticket == null) return;
    try {
      final content = await controller.repository.legacyDownload(
        widget.organizationId,
        ticket.id,
        file,
      );
      if (!mounted || controller.ticket?.id != ticket.id) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(file.name),
          content: SingleChildScrollView(child: SelectableText(content)),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(AppLocalizations.of(context)!.domainClose7d9eb7),
            ),
          ],
        ),
      );
    } catch (e) {
      if (mounted) setState(() => controller.failure = failureOf(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final model = controller, ticket = model.ticket, attachments = files;
    final enabled = !model.busy && !model.requiresReadback;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          AppLocalizations.of(context)!.domainMySupportTicketsbca759,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        if (model.busy) const LinearProgressIndicator(),
        SupportError(model.failure),
        DropdownButtonFormField<String>(
          isExpanded: true,
          initialValue: model.statusFilter ?? '',
          decoration: InputDecoration(
            labelText: AppLocalizations.of(
              context,
            )!.domainTicketStatusFiltere21337,
          ),
          items: [
            for (final status in [
              '',
              'open',
              'assigned',
              'in_progress',
              'waiting_for_user',
              'resolved',
              'closed',
            ])
              DropdownMenuItem(
                value: status,
                child: Text(
                  status.isEmpty
                      ? AppLocalizations.of(context)!.domainAllStatuses8ee573
                      : supportLabel(context, status),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
          ],
          onChanged: model.busy
              ? null
              : (v) {
                  model.statusFilter = v == '' ? null : v;
                  model.list();
                },
        ),
        TextButton(
          onPressed: model.busy ? null : () => model.list(),
          child: Text(AppLocalizations.of(context)!.domainRefreshTickets1c30a6),
        ),
        if (model.tickets.isEmpty && !model.busy)
          Text(AppLocalizations.of(context)!.domainNoSupportTickets72f5d9),
        for (final row in model.tickets)
          ListTile(
            title: Text('${row.number} · ${row.subject}'),
            subtitle: Text(
              '${supportLabel(context, row.status)} · ${supportLabel(context, row.priority)}',
            ),
            selected: ticket?.id == row.id,
            onTap: model.busy ? null : () => choose(row.id),
          ),
        if (model.cursor != null)
          TextButton(
            onPressed: model.busy ? null : () => model.list(more: true),
            child: Text(AppLocalizations.of(context)!.domainMoreTickets0e480f),
          ),
        ExpansionTile(
          title: Text(
            AppLocalizations.of(context)!.domainCreateASupportTicket9709e0,
          ),
          children: [
            DropdownButtonFormField<String>(
              isExpanded: true,
              initialValue: model.category,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.domainCategory292c06,
              ),
              items: [
                for (final category in ticketCategories)
                  DropdownMenuItem(
                    value: category,
                    child: Text(
                      supportLabel(context, category),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: model.busy || model.creationIntent != null
                  ? null
                  : (v) => model.category = v ?? 'general',
            ),
            DropdownButtonFormField<String>(
              isExpanded: true,
              initialValue: model.priority,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.domainPriorityd60dbb,
              ),
              items: [
                for (final priority in ticketPriorities)
                  DropdownMenuItem(
                    value: priority,
                    child: Text(
                      supportLabel(context, priority),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: model.busy || model.creationIntent != null
                  ? null
                  : (v) => model.priority = v ?? 'normal',
            ),
            TextFormField(
              key: ValueKey(
                'subject:${model.creationIntent?['request_id']}:${model.subject.isEmpty}',
              ),
              initialValue: model.subject,
              maxLength: 200,
              enabled: !model.busy && model.creationIntent == null,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.domainSubject689712,
              ),
              onChanged: (v) {
                model.subject = v;
                fileChanged();
              },
            ),
            TextFormField(
              key: ValueKey(
                'body:${model.creationIntent?['request_id']}:${model.body.isEmpty}',
              ),
              initialValue: model.body,
              maxLength: 8000,
              minLines: 3,
              maxLines: 8,
              enabled: !model.busy && model.creationIntent == null,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(
                  context,
                )!.domainQuestionRequestba73e0,
              ),
              onChanged: (v) {
                model.body = v;
                fileChanged();
              },
            ),
            FilledButton(
              onPressed: model.busy ? null : model.create,
              child: Text(
                model.creationIntent == null
                    ? AppLocalizations.of(context)!.domainCreateTickete836fc
                    : AppLocalizations.of(
                        context,
                      )!.domainRecoverThisExactTicketRequestdf25ad,
              ),
            ),
          ],
        ),
        if (ticket != null) ...[
          const Divider(),
          Text(
            '${ticket.number} · ${ticket.subject}',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          Text('${supportLabel(context, ticket.status)} · v${ticket.version}'),
          TextButton(
            onPressed: model.busy ? null : () => model.open(ticket.id),
            child: Text(
              AppLocalizations.of(context)!.domainRefreshThisConversation6b5a20,
            ),
          ),
          for (final message in model.messages)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(dateText(context, message.createdAt)),
                    Text(message.body),
                    for (final file in message.attachments)
                      TextButton(
                        onPressed: model.busy ? null : () => legacy(file),
                        child: Text('${file.name} · ${file.size} bytes'),
                      ),
                    for (final file in message.files) ...[
                      Text(
                        '${file.mediaType} · ${file.byteSize} · v${file.frozenVersion ?? file.fileVersion}',
                      ),
                      SelectableText(file.sha256),
                      if (file.frozenAt != null)
                        Text(dateText(context, file.frozenAt!)),
                      if (file.usable && attachments?.enabled == true)
                        TextButton(
                          onPressed: attachments!.busy
                              ? null
                              : () => download(file),
                          child: Text(
                            AppLocalizations.of(
                              context,
                            )!.domainVerifyPrivateDownload3a2d36,
                          ),
                        ),
                    ],
                  ],
                ),
              ),
            ),
          if (model.messageCursor != null)
            TextButton(
              onPressed: model.busy
                  ? null
                  : () => model.open(ticket.id, moreMessages: true),
              child: Text(
                AppLocalizations.of(context)!.domainMoreMessages9b4a40,
              ),
            ),
          if (ticket.status != 'closed') ...[
            TextFormField(
              key: ValueKey('reply:${ticket.id}:${model.reply.isEmpty}'),
              initialValue: model.reply,
              maxLength: 8000,
              minLines: 3,
              maxLines: 8,
              enabled: !model.busy,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(
                  context,
                )!.domainSharedReply4d437b,
              ),
              onChanged: (v) {
                model.reply = v;
                fileChanged();
              },
            ),
            ExpansionTile(
              title: Text(
                AppLocalizations.of(
                  context,
                )!.domainOptionalPlainTextAttachment030a73,
              ),
              children: [
                TextFormField(
                  key: ValueKey(
                    'legacy:${ticket.id}:${model.legacyText.isEmpty}',
                  ),
                  initialValue: model.legacyText,
                  maxLength: 32768,
                  minLines: 2,
                  maxLines: 6,
                  enabled: !model.busy,
                  decoration: InputDecoration(
                    labelText: AppLocalizations.of(
                      context,
                    )!.domainUtf8TextMaximum32768ded21d,
                  ),
                  onChanged: (v) {
                    model.legacyText = v;
                    fileChanged();
                  },
                ),
              ],
            ),
            if (attachments != null) filePanel(context, attachments),
            FilledButton(
              onPressed:
                  enabled &&
                      attachments?.busy != true &&
                      attachments?.hasPending != true
                  ? () async {
                      await model.send(
                        fileIds: attachments?.replyFileIds ?? [],
                      );
                      if (model.failure == null) {
                        attachments?.selected.clear();
                        await attachments?.refresh();
                      }
                    }
                  : null,
              child: Text(
                AppLocalizations.of(context)!.domainSendSharedReplyf121d3,
              ),
            ),
          ],
          if ({'resolved', 'closed'}.contains(ticket.status)) ...[
            TextFormField(
              key: ValueKey('status:${ticket.id}:${model.reason.isEmpty}'),
              initialValue: model.reason,
              maxLength: 500,
              enabled: !model.busy,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(
                  context,
                )!.domainReasonForClosingReopening5e3744,
              ),
              onChanged: (v) {
                model.reason = v;
                fileChanged();
              },
            ),
            if (ticket.status == 'resolved')
              TextButton(
                onPressed: enabled
                    ? () async {
                        if (await confirmAction(
                          context,
                          AppLocalizations.of(
                            context,
                          )!.domainCloseThisResolvedTicket3edf38,
                        )) {
                          await model.changeStatus(reopen: false);
                        }
                      }
                    : null,
                child: Text(
                  AppLocalizations.of(context)!.domainCloseResolvedTicketf3687f,
                ),
              ),
            TextButton(
              onPressed: enabled
                  ? () => model.changeStatus(reopen: true)
                  : null,
              child: Text(
                AppLocalizations.of(context)!.domainReopenTickete6b8d8,
              ),
            ),
          ],
          ExpansionTile(
            title: Text(
              AppLocalizations.of(context)!.domainTicketHistory183fea,
            ),
            children: [
              for (final event in model.history)
                ListTile(
                  title: Text(
                    '${supportLabel(context, event.event)} · ${supportLabel(context, event.status)} · v${event.version}',
                  ),
                  subtitle: Text(
                    '${dateText(context, event.createdAt)}\n${event.reason ?? ''}',
                  ),
                ),
              if (model.historyCursor != null)
                TextButton(
                  onPressed: model.busy
                      ? null
                      : () => model.open(ticket.id, moreHistory: true),
                  child: Text(
                    AppLocalizations.of(context)!.domainMoreHistory7e2113,
                  ),
                ),
            ],
          ),
        ],
        if (receipt case final copy?)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    AppLocalizations.of(
                      context,
                    )!.domainPrivateDownloadVerified22d5aa,
                  ),
                  Text('${copy.mediaType} · ${copy.byteSize}'),
                  SelectableText(copy.sha256),
                  TextButton(
                    onPressed: closeReceipt,
                    child: Text(
                      AppLocalizations.of(
                        context,
                      )!.domainCloseAndDeletePrivateCopy3f2b2d,
                    ),
                  ),
                ],
              ),
            ),
          ),
        const Divider(),
        Text(
          AppLocalizations.of(context)!.domainSupportNotifications3a8090,
          style: Theme.of(context).textTheme.titleLarge,
        ),
        TextButton(
          onPressed: model.busy ? null : () => model.loadNotices(),
          child: Text(
            AppLocalizations.of(
              context,
            )!.domainRefreshNotificationsAndPreferencef9bb90,
          ),
        ),
        if (model.preference case final pref?)
          SwitchListTile(
            title: Text(
              AppLocalizations.of(
                context,
              )!.domainInAppSupportNotificationsd81899,
            ),
            value: pref.enabled,
            onChanged: enabled ? model.setPreference : null,
          ),
        for (final notice in model.notices)
          ListTile(
            title: Text('${notice.event}${notice.read ? '' : ' •'}'),
            subtitle: Text(notice.ticketId),
            onTap: model.busy
                ? null
                : () async {
                    if (await canChangeTicket()) await model.openNotice(notice);
                  },
          ),
        if (model.noticeCursor != null)
          TextButton(
            onPressed: model.busy ? null : () => model.loadNotices(more: true),
            child: Text(
              AppLocalizations.of(context)!.domainMoreNotifications9e58f9,
            ),
          ),
      ],
    );
  }

  Widget filePanel(
    BuildContext context,
    HelpdeskFilesController model,
  ) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text(
        AppLocalizations.of(context)!.domainSecureSharedAttachmentsff80f8,
        style: Theme.of(context).textTheme.titleMedium,
      ),
      SupportError(model.failure),
      SupportError(scopeFailure),
      if (model.scope == null && ref.read(privateFilesProvider).supported)
        TextButton(
          onPressed: model.busy
              ? null
              : () {
                  requestedTicket = null;
                  syncFiles();
                },
          child: Text(AppLocalizations.of(context)!.fileRetryProtection),
        ),
      if (model.busy) const LinearProgressIndicator(),
      if (!model.enabled)
        Text(
          AppLocalizations.of(context)!.domainFileCollectionIsUnavailable1eb8de,
        ),
      if (model.policy case final policy?) ...[
        Text(tr(context, policy.noticeEn, policy.noticeTa)),
        Text(
          '${policy.mediaTypes.join(', ')} · ${model.effectiveLimit} bytes · ${policy.maxFiles}',
        ),
        Text(
          '${AppLocalizations.of(context)!.domainRetentionDays51de08}: ${policy.retentionDays} / ${policy.rejectedDays}',
        ),
      ],
      TextButton(
        onPressed: model.busy ? null : () => model.refresh(),
        child: Text(
          AppLocalizations.of(context)!.domainRefreshAttachmentStatusd7974f,
        ),
      ),
      for (final file in model.items)
        ListTile(
          title: Text(
            '${file.mediaType} · ${file.byteSize} · ${supportLabel(context, file.state)} / ${supportLabel(context, file.fileState)}',
          ),
          subtitle: Text(
            file.usable
                ? AppLocalizations.of(context)!.domainUsableb4d1bf
                : AppLocalizations.of(context)!.domainNotUsabled7464d,
          ),
          leading: file.selectable
              ? Checkbox(
                  value: model.selected.contains(file.id),
                  onChanged: model.busy
                      ? null
                      : (v) {
                          setState(() {
                            if (v == true) {
                              model.selected.add(file.id);
                            } else {
                              model.selected.remove(file.id);
                            }
                          });
                          fileChanged();
                        },
                )
              : null,
          trailing: file.state == 'staged' && model.enabled
              ? IconButton(
                  tooltip: AppLocalizations.of(
                    context,
                  )!.domainRemoveStagedFilea50773,
                  icon: const Icon(Icons.delete_outline),
                  onPressed: model.busy || model.hasPending
                      ? null
                      : () async {
                          if (await confirmAction(
                            context,
                            AppLocalizations.of(
                              context,
                            )!.domainRemoveThisStagedAttachmentf4b57b,
                          )) {
                            await model.remove(file);
                          }
                        },
                )
              : null,
        ),
      if (model.cursor != null)
        TextButton(
          onPressed: model.busy ? null : () => model.refresh(more: true),
          child: Text(
            AppLocalizations.of(context)!.domainMoreAttachments1f9e79,
          ),
        ),
      if (model.enabled && model.scope != null)
        OutlinedButton(
          onPressed: model.canPick ? model.pick : null,
          child: Text(
            AppLocalizations.of(context)!.domainChooseSharedAttachment971b66,
          ),
        ),
      if (model.intent != null && model.pending == null)
        TextButton(
          onPressed: model.busy ? null : model.recoverRegistration,
          child: Text(
            AppLocalizations.of(
              context,
            )!.domainRecoverExactFileRegistrationa8a032,
          ),
        ),
      if (model.pending != null && model.enabled)
        FilledButton(
          onPressed:
              model.busy ||
                  model.requiresReadback ||
                  model.pending?.fileState != 'pending'
              ? null
              : model.upload,
          child: Text(
            AppLocalizations.of(context)!.domainUploadSelectedBytes08b1dc,
          ),
        ),
      if (model.hasPending)
        TextButton(
          onPressed: model.busy
              ? null
              : () async {
                  await model.discard();
                  fileChanged();
                },
          child: Text(
            AppLocalizations.of(
              context,
            )!.domainDiscardSelectedPrivateCopy449966,
          ),
        ),
      Text(
        AppLocalizations.of(context)!.domainAnUploadedFileIsAttachedOnly99c018,
      ),
    ],
  );
}
