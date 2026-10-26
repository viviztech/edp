import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_failure.dart';
import '../../core/files/private_files.dart';
import '../../l10n/app_localizations.dart';
import 'application_documents.dart';
import 'application_models.dart';
import 'documents_controller.dart';

/// Private files stay in the controller's scope. No path or export reaches UI.
class ApplicationDocumentsPanel extends StatefulWidget {
  final DocumentsController controller;
  final bool nativeSupported, commandsEnabled;
  final ApiFailure? storageFailure;
  final VoidCallback? retryStorage;
  const ApplicationDocumentsPanel({
    super.key,
    required this.controller,
    required this.nativeSupported,
    required this.commandsEnabled,
    this.storageFailure,
    this.retryStorage,
  });

  @override
  State<ApplicationDocumentsPanel> createState() =>
      _ApplicationDocumentsPanelState();
}

class _ApplicationDocumentsPanelState extends State<ApplicationDocumentsPanel>
    with WidgetsBindingObserver {
  PrivateSnapshot? receipt;
  int receiptVersion = 0;
  DocumentsController get controller => widget.controller;
  bool get commandsEnabled => widget.commandsEnabled;
  bool get nativeSupported => widget.nativeSupported;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    final copy = receipt;
    receipt = null;
    if (copy != null) unawaited(_release(copy));
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.hidden ||
        state == AppLifecycleState.detached) {
      unawaited(_closeReceipt());
    }
  }

  Future<void> _closeReceipt() async {
    final copy = receipt;
    if (mounted) setState(() => receipt = null);
    if (copy != null) await _release(copy);
  }

  @override
  Widget build(BuildContext context) {
    final text = AppLocalizations.of(context)!;
    final tamil = Localizations.localeOf(context).languageCode == 'ta';
    final model = controller;
    final enabled = commandsEnabled && model.canCollect && nativeSupported;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          text.mobileDocuments,
          style: Theme.of(context).textTheme.titleLarge,
        ),
        if (model.busy) const LinearProgressIndicator(),
        if (!model.collectionEnabled) Text(text.fileCollectionDisabled),
        if (!nativeSupported) Text(text.fileNativeRequired),
        if (nativeSupported && model.scope == null) ...[
          Text(
            widget.storageFailure == null
                ? text.fileUnavailable
                : _failure(text, widget.storageFailure!),
          ),
          if (widget.retryStorage != null)
            TextButton(
              onPressed: commandsEnabled && !model.busy
                  ? widget.retryStorage
                  : null,
              child: Text(text.fileRetryProtection),
            ),
        ],
        if (model.failure case final failure?)
          Semantics(liveRegion: true, child: Text(_failure(text, failure))),
        TextButton(
          onPressed: commandsEnabled && !model.busy && !model.retryDelayed
              ? model.load
              : null,
          child: Text(text.fileRefresh),
        ),
        for (final rule in model.requirements) ...[
          const SizedBox(height: 12),
          Text(
            tamil ? rule.labelTa : rule.labelEn,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text(tamil ? rule.instructionsTa : rule.instructionsEn),
          Text(tamil ? rule.noticeTa : rule.noticeEn),
          Text(
            text.fileLimits(
              rule.minFiles,
              model.effectiveMaxFiles(rule),
              model.effectiveLimit(rule),
            ),
          ),
          Text(rule.mimeTypes.join(', ')),
          Text(text.filePolicyCount(rule.policyMaxFiles)),
          Text(
            text.fileRetention(rule.retentionDays, rule.rejectedRetentionDays),
          ),
          for (final item in model.items.where(
            (item) => item.requirementId == rule.id,
          ))
            _document(context, text, item, rule, enabled),
          if (model.editable && model.collectionEnabled && nativeSupported)
            OutlinedButton.icon(
              onPressed:
                  enabled &&
                      model.hasCapacity(rule) &&
                      model.effectiveLimit(rule) > 0
                  ? () => model.pick(rule)
                  : null,
              icon: const Icon(Icons.attach_file),
              label: Text(text.fileChoose),
            ),
        ],
        if (model.pendingIntent case final intent?) ...[
          const SizedBox(height: 12),
          Text(
            text.fileSelected,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text('${intent.snapshot.mediaType} · ${intent.snapshot.byteSize}'),
          SelectableText(intent.snapshot.sha256),
          if (model.pendingDocument == null && model.collectionEnabled)
            TextButton(
              onPressed:
                  commandsEnabled &&
                      !model.busy &&
                      !model.retryDelayed &&
                      model.editable
                  ? model.recoverRegistration
                  : null,
              child: Text(text.fileRecoverIntent),
            ),
          if (model.requiresReadback)
            TextButton(
              onPressed: commandsEnabled && !model.busy && !model.retryDelayed
                  ? model.reconcileUpload
                  : null,
              child: Text(text.fileReadBeforeRetry),
            ),
          if (model.pendingDocument != null && model.collectionEnabled)
            FilledButton(
              onPressed: commandsEnabled && model.canUpload
                  ? model.uploadPending
                  : null,
              child: Text(text.fileUpload),
            ),
          TextButton(
            onPressed: !model.busy ? model.discardPending : null,
            child: Text(text.fileDiscard),
          ),
        ],
        if (model.uncertainRemoval != null)
          TextButton(
            onPressed: commandsEnabled && !model.busy && !model.retryDelayed
                ? model.reconcileRemoval
                : null,
            child: Text(text.fileReadBeforeRetry),
          ),
        if (receipt case final copy?)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    text.fileDownloadReceipt,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text(
                    text.fileProof(
                      copy.mediaType,
                      copy.byteSize,
                      receiptVersion,
                    ),
                  ),
                  SelectableText(copy.sha256),
                  TextButton(
                    onPressed: _closeReceipt,
                    child: Text(text.fileCloseReceipt),
                  ),
                ],
              ),
            ),
          ),
        Semantics(
          liveRegion: true,
          child: Text(
            model.ready
                ? text.mobileDocumentsReady
                : text.mobileDocumentsPending,
          ),
        ),
      ],
    );
  }

  Widget _document(
    BuildContext context,
    AppLocalizations text,
    ApplicationDocument item,
    ApplicationDocumentRequirement rule,
    bool enabled,
  ) {
    final model = controller;
    final evidence = item.evidence;
    final version = evidence?.fileVersion ?? item.file.version;
    final bytes = evidence?.byteSize ?? item.file.byteSize;
    final hash = evidence?.sha256 ?? item.file.sha256;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(_state(text, item.file.state)),
            if (!item.active || !item.usable) Text(text.fileUnusable),
            Text(text.fileProof(item.file.mediaType, bytes, version)),
            SelectableText(hash),
            if (evidence != null) ...[
              Text(text.fileFrozenEvidence),
              Text(
                DateFormat.yMMMd(
                  Localizations.localeOf(context).languageCode,
                ).add_jm().format(evidence.frozenAt.toLocal()),
              ),
            ],
            if (model.collectionEnabled && nativeSupported)
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (item.usable && item.active)
                    TextButton(
                      onPressed:
                          commandsEnabled && !model.busy && !model.retryDelayed
                          ? () => _download(context, item)
                          : null,
                      child: Text(text.fileDownload),
                    ),
                  if (model.editable && item.active) ...[
                    if (item.file.state == 'pending')
                      TextButton(
                        onPressed: enabled
                            ? () => model.reselectPending(item)
                            : null,
                        child: Text(text.fileReselect),
                      ),
                    TextButton(
                      onPressed: enabled
                          ? () => model.pick(rule, replaces: item)
                          : null,
                      child: Text(text.fileReplace),
                    ),
                    TextButton(
                      onPressed: enabled ? () => _remove(context, item) : null,
                      child: Text(text.fileRemove),
                    ),
                  ],
                ],
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _remove(
    BuildContext context,
    ApplicationDocument document,
  ) async {
    final text = AppLocalizations.of(context)!;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(text.fileConfirmRemove),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(text.mobileStay),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(text.fileRemove),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) await controller.remove(document);
  }

  Future<void> _download(
    BuildContext context,
    ApplicationDocument document,
  ) async {
    final snapshot = await controller.download(document);
    if (snapshot == null) return;
    if (!mounted) {
      await _release(snapshot);
      return;
    }
    await _closeReceipt();
    if (!mounted || controller.scope?.closed == true) {
      await _release(snapshot);
      return;
    }
    setState(() {
      receipt = snapshot;
      final current = snapshot is VerifiedApplicationDownload
          ? snapshot.document
          : document;
      receiptVersion = current.evidence?.fileVersion ?? current.file.version;
    });
  }
}

Future<void> _release(PrivateSnapshot snapshot) async {
  try {
    await snapshot.dispose();
  } on ApiFailure {
    /* Store fails closed on native cleanup errors. */
  }
}

String _state(AppLocalizations text, String state) => switch (state) {
  'pending' => text.filePending,
  'uploading' => text.fileUploading,
  'quarantined' => text.fileQuarantined,
  'scanning' => text.fileScanning,
  'clean' => text.fileClean,
  'infected' => text.fileInfected,
  'rejected' => text.fileRejected,
  'deleted' => text.fileDeleted,
  _ => text.fileUnavailable,
};

String _failure(AppLocalizations text, ApiFailure failure) {
  if (failure.code == 'private_storage_unavailable') {
    return text.fileProtectionRequired;
  }
  if (failure.uncertain) return text.fileReadBeforeRetry;
  return switch (failure.kind) {
    ApiFailureKind.invalidSession => text.authSessionExpired,
    ApiFailureKind.conflict => text.mobileConflict,
    ApiFailureKind.oversized => text.fileTooLarge,
    ApiFailureKind.validation ||
    ApiFailureKind.invalidResponse => text.fileInvalid,
    ApiFailureKind.rateLimited => text.mobileWaitAndRetry,
    _ => text.fileUnavailable,
  };
}
