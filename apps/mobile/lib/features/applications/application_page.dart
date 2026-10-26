import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_failure.dart';
import '../../core/files/private_files.dart';
import '../../core/files/providers.dart';
import '../../core/navigation/destinations.dart';
import '../../l10n/app_localizations.dart';
import '../identity/providers.dart';
import 'application_editor.dart';
import 'application_documents.dart';
import 'application_documents_panel.dart';
import 'documents_controller.dart';
import 'application_history.dart';
import 'application_models.dart';
import 'application_repository.dart';

/// A route owns its private editor. Session/context gates dispose it on change.
class ApplicationPage extends ConsumerStatefulWidget {
  final MobileDestination destination;
  const ApplicationPage({super.key, required this.destination});

  @override
  ConsumerState<ApplicationPage> createState() => _ApplicationPageState();
}

class _ApplicationPageState extends ConsumerState<ApplicationPage>
    with WidgetsBindingObserver {
  ApplicationEditor? editor;
  DocumentsController? documents;
  ApiFailure? privateStorageFailure;
  bool creatingDocuments = false;
  bool leaving = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    final query = widget.destination.uri.queryParameters;
    final organization = query['organization'];
    if (organization != null) {
      editor = ApplicationEditor(
        ref.read(applicationRepositoryProvider),
        organizationId: organization,
        cycleId: query['cycle'],
        applicationId: query['application'],
      )..addListener(_changed);
      Future.microtask(editor!.load);
    }
  }

  void _changed() {
    if (!mounted) return;
    _syncDocuments();
    setState(() {});
  }

  void _documentsChanged() {
    if (!mounted) return;
    final model = editor, files = documents;
    if (model != null && files != null) {
      model.documentWorkPending = files.blocksNavigation;
      model.documentsReady =
          files.ready && files.version == model.record?.version;
    }
    setState(() {});
  }

  void _syncDocuments() {
    final model = editor, record = editor?.record;
    if (model == null || record == null || record.form.documents.isEmpty) {
      return;
    }
    final current = documents;
    if (current != null && current.applicationId == record.id) {
      final previous = current.version;
      current.syncApplicationVersion(record.version, editable: model.editable);
      if (previous < record.version && !current.busy && !current.hasPending) {
        Future.microtask(current.load);
      }
      return;
    }
    if (creatingDocuments) return;
    creatingDocuments = true;
    Future<void>(() async {
      if (!mounted) return;
      PrivateFileScope? scope;
      ApiFailure? scopeFailure;
      try {
        final store = ref.read(privateFilesProvider);
        if (store.supported) scope = await store.createScope();
      } on ApiFailure catch (error) {
        scopeFailure = error;
        // Metadata remains readable when local private storage is unavailable.
      }
      if (!mounted || editor != model || model.record?.id != record.id) {
        await scope?.close();
        return;
      }
      current?.removeListener(_documentsChanged);
      current?.dispose();
      final next = DocumentsController(
        ref.read(applicationDocumentsRepositoryProvider),
        scope,
        organizationId: model.organizationId,
        applicationId: record.id,
        applicationVersion: record.version,
        requirements: record.form.documents,
        collectionEnabled: record.form.collectionEnabled,
        maxUploadBytes: record.form.maxUploadBytes,
        editable: model.editable,
        onChanged: model.documentVersionChanged,
      );
      documents = next;
      privateStorageFailure = scopeFailure;
      creatingDocuments = false;
      next.addListener(_documentsChanged);
      _documentsChanged();
      await next.load();
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    editor?.removeListener(_changed);
    editor?.dispose();
    documents?.removeListener(_documentsChanged);
    documents?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.hidden ||
        state == AppLifecycleState.detached) {
      documents?.pause();
    }
    final resumingFileAction =
        state == AppLifecycleState.resumed &&
        (documents?.busy == true || documents?.hasPending == true);
    if (state == AppLifecycleState.resumed) unawaited(documents?.resume());
    // A platform picker can return before the host's resumed event. Its exact
    // document acknowledgement performs the aggregate read without replacing
    // dirty scalar answers or opening an unrelated scalar review concurrently.
    if (resumingFileAction) return;
    if (state == AppLifecycleState.resumed && editor?.busy == false) {
      if (editor!.record != null || editor!.needsReview) {
        editor!.reconcile();
      } else {
        editor!.load();
      }
    }
  }

  Future<bool> _mayLeave() async {
    if (editor?.busy == true || documents?.busy == true) return false;
    if (editor?.blocksNavigation != true &&
        documents?.blocksNavigation != true) {
      return true;
    }
    final text = AppLocalizations.of(context)!;
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            content: Text(
              editor?.needsReview == true || documents?.blocksNavigation == true
                  ? text.mobileUncertainLeave
                  : text.mobileUnsaved,
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: Text(text.mobileStay),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(text.mobileLeave),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _open(Map<String, String> query) async {
    if (!await _mayLeave() || !mounted) return;
    context.pushReplacement(
      Uri(path: '/applications', queryParameters: query).toString(),
    );
  }

  Future<void> _submit() async {
    if (editor?.canSubmit != true) return;
    final text = AppLocalizations.of(context)!;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(text.mobileConfirmSubmit),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(text.mobileStay),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(text.mobileSubmit),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) await editor!.submit();
  }

  @override
  Widget build(BuildContext context) {
    final text = AppLocalizations.of(context)!;
    final profile = ref.watch(sessionProvider);
    final model = editor;
    final query = widget.destination.uri.queryParameters;
    final organizations = <String, String>{
      for (final grant in profile?.grants ?? [])
        grant.organizationId: grant.organizationName,
    };
    const configuredOrganization = String.fromEnvironment(
      'PUBLIC_ORGANIZATION_ID',
    );
    if (MobileDestination.uuid.hasMatch(configuredOrganization)) {
      organizations.putIfAbsent(
        configuredOrganization,
        () => text.mobileProgramIntake,
      );
    }
    return PopScope(
      canPop:
          leaving ||
          (model?.blocksNavigation != true &&
              documents?.blocksNavigation != true),
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop || leaving) return;
        if (await _mayLeave() && mounted) {
          setState(() => leaving = true);
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) context.pop();
          });
        }
      },
      child: Scaffold(
        appBar: AppBar(
          toolbarHeight: 76,
          title: Text(
            text.mobileApplications,
            maxLines: 2,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          actions: [
            IconButton(
              tooltip: text.mobileHome,
              icon: const Icon(Icons.home_outlined),
              onPressed: () async {
                if (await _mayLeave() && context.mounted) context.go('/');
              },
            ),
          ],
        ),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  if (model == null) Text(text.mobileChooseOrganization),
                  for (final organization in organizations.entries)
                    if (organization.key != query['organization'])
                      TextButton(
                        onPressed: model?.busy == true
                            ? null
                            : () => _open({'organization': organization.key}),
                        child: Text(organization.value),
                      ),
                  if (model != null) ..._workspace(model, text),
                  const SizedBox(height: 28),
                  ApplicationHistory(
                    key: ValueKey(model?.historyRevision ?? 0),
                    onOpen: (entry) => _open({
                      'organization': entry.organizationId,
                      if (entry.cycleId != null) 'cycle': entry.cycleId!,
                      'application': entry.id,
                    }),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _workspace(ApplicationEditor model, AppLocalizations text) {
    final record = model.record;
    final tamil = Localizations.localeOf(context).languageCode == 'ta';
    return [
      if (model.busy) const LinearProgressIndicator(),
      if (model.failure != null)
        Semantics(
          liveRegion: true,
          child: Text(applicationFailureLabel(text, model.failure!)),
        ),
      if (model.notice == 'saved' || model.notice == 'submitted')
        Semantics(
          liveRegion: true,
          child: Text(
            model.notice == 'submitted'
                ? text.mobileSubmitSuccess
                : text.mobileSaved,
          ),
        ),
      if (model.needsReview) ...[
        if (model.failure == null) Text(text.mobileReviewSaved),
        TextButton(
          onPressed: model.busy ? null : model.reconcile,
          child: Text(text.mobileRefreshRecord),
        ),
        if (model.latest case final saved?) ...[
          Text(text.mobileSavedVersion(saved.version)),
          for (final field in saved.form.fields)
            Text(
              '${tamil ? field.labelTa : field.labelEn}: ${saved.answers[field.id] ?? ''}',
            ),
          Wrap(
            spacing: 12,
            children: [
              TextButton(
                onPressed: () => model.chooseSaved(keepEdits: false),
                child: Text(text.mobileUseSaved),
              ),
              TextButton(
                onPressed: () => model.chooseSaved(keepEdits: true),
                child: Text(text.mobileKeepEdits),
              ),
            ],
          ),
        ],
      ],
      if (!model.needsReview)
        TextButton(
          onPressed: model.busy
              ? null
              : record == null
              ? model.load
              : model.reconcile,
          child: Text(
            record == null ? text.cmsRetry : text.mobileRefreshRecord,
          ),
        ),
      if (record == null) ...[
        Text(text.mobileIntakes, style: Theme.of(context).textTheme.titleLarge),
        if (model.cyclesLoaded && model.cycles.isEmpty)
          Text(text.mobileNoIntakes),
        for (final cycle in model.cycles)
          ListTile(
            leading: Icon(
              cycle.id == model.cycleId
                  ? Icons.radio_button_checked
                  : Icons.radio_button_unchecked,
            ),
            title: Text(tamil ? cycle.nameTa : cycle.nameEn),
            subtitle: Text(
              '${_date(cycle.opensAt)} – ${_date(cycle.closesAt)}',
            ),
            onTap: model.busy
                ? null
                : () => _open({
                    'organization': model.organizationId,
                    'cycle': cycle.id,
                  }),
          ),
        if (model.requestedApplicationId == null && model.open)
          FilledButton(
            onPressed: model.busy || model.needsReview ? null : model.start,
            child: Text(text.mobileStartApplication),
          ),
      ] else ...[
        Text(
          tamil ? record.form.titleTa : record.form.titleEn,
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        Text(applicationStateLabel(text, record.state)),
        Text(text.mobileCompletion(record.completionPercent)),
        if (!record.isDraft) ...[
          SelectableText(
            record.number ?? '',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          if (record.submittedAt != null) Text(_date(record.submittedAt!)),
          Text(
            text.mobileSubmitSuccess,
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ],
        if (!model.editable) Text(text.mobileReadOnly),
        for (final field in record.form.fields)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: ApplicationAnswerInput(
              key: ValueKey('${record.id}:${field.id}'),
              field: field,
              value: model.values[field.id] ?? '',
              label:
                  '${tamil ? field.labelTa : field.labelEn}${field.isRequired ? ' *' : ''}',
              enabled: model.canWrite,
              onChanged: (value) => model.setAnswer(field.id, value),
            ),
          ),
        if (record.form.documents.isNotEmpty) ...[
          if (documents case final files?)
            ApplicationDocumentsPanel(
              controller: files,
              nativeSupported: ref.read(privateFilesProvider).supported,
              commandsEnabled: !model.busy && !model.needsReview,
              storageFailure: privateStorageFailure,
              retryStorage: () {
                if (creatingDocuments || files.busy || files.hasPending) return;
                files.removeListener(_documentsChanged);
                files.dispose();
                documents = null;
                privateStorageFailure = null;
                _syncDocuments();
                setState(() {});
              },
            )
          else
            Text(text.cmsLoading),
        ],
        for (final acknowledgement in record.form.acknowledgements)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            title: Text(
              '${tamil ? acknowledgement.labelTa : acknowledgement.labelEn}${acknowledgement.isRequired ? ' *' : ''}',
            ),
            subtitle:
                record.accepted
                    .where((item) => item.id == acknowledgement.id)
                    .isEmpty
                ? null
                : Text(
                    _date(
                      record.accepted
                          .firstWhere((item) => item.id == acknowledgement.id)
                          .acceptedAt,
                    ),
                  ),
            value: model.accepted.contains(acknowledgement.id),
            onChanged: model.canWrite
                ? (value) =>
                      model.acknowledge(acknowledgement.id, value == true)
                : null,
          ),
        if (model.editable)
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              OutlinedButton(
                onPressed: model.canWrite ? model.save : null,
                child: Text(text.mobileSave),
              ),
              FilledButton(
                onPressed: model.canSubmit ? _submit : null,
                child: Text(text.mobileSubmit),
              ),
            ],
          ),
        if (record.history.isNotEmpty) ...[
          const SizedBox(height: 20),
          Text(
            text.mobileStatusHistory,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          for (final event in record.history)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(applicationStateLabel(text, event.state)),
              subtitle: Text(_date(event.createdAt)),
            ),
        ],
      ],
    ];
  }

  String _date(DateTime value) => DateFormat.yMMMd(
    Localizations.localeOf(context).languageCode,
  ).add_jm().format(value.toLocal());
}

class ApplicationAnswerInput extends StatefulWidget {
  final ApplicationField field;
  final String value, label;
  final bool enabled;
  final ValueChanged<String> onChanged;
  const ApplicationAnswerInput({
    super.key,
    required this.field,
    required this.value,
    required this.label,
    required this.enabled,
    required this.onChanged,
  });
  @override
  State<ApplicationAnswerInput> createState() => _ApplicationAnswerInputState();
}

class _ApplicationAnswerInputState extends State<ApplicationAnswerInput> {
  late final controller = TextEditingController(text: widget.value);
  @override
  void didUpdateWidget(ApplicationAnswerInput oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (controller.text != widget.value) controller.text = widget.value;
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.field.type == 'boolean') {
      return CheckboxListTile(
        contentPadding: EdgeInsets.zero,
        title: Text(widget.label),
        tristate: true,
        value: widget.value.isEmpty ? null : widget.value == 'true',
        onChanged: widget.enabled
            ? (value) => widget.onChanged(value == null ? '' : value.toString())
            : null,
      );
    }
    return TextField(
      controller: controller,
      enabled: widget.enabled,
      maxLength: 5000,
      minLines: widget.field.type == 'textarea' ? 3 : 1,
      maxLines: widget.field.type == 'textarea' ? 8 : 1,
      keyboardType: widget.field.type == 'number'
          ? const TextInputType.numberWithOptions(signed: true, decimal: true)
          : widget.field.type == 'date'
          ? TextInputType.datetime
          : TextInputType.text,
      decoration: InputDecoration(
        labelText: widget.label,
        helperText: widget.field.type == 'date'
            ? AppLocalizations.of(context)!.mobileDateFormat
            : null,
        counterText: '',
      ),
      onChanged: widget.onChanged,
    );
  }
}

String applicationFailureLabel(AppLocalizations text, ApiFailure failure) {
  if (failure.uncertain) return text.mobileCommandUncertain;
  return switch (failure.kind) {
    ApiFailureKind.invalidSession => text.authSessionExpired,
    ApiFailureKind.conflict => text.mobileConflict,
    ApiFailureKind.forbidden ||
    ApiFailureKind.notFound => text.mobileApplicationUnavailable,
    ApiFailureKind.offline ||
    ApiFailureKind.timeout => text.mobileConnectionInterrupted,
    ApiFailureKind.validation => text.mobileCheckAnswers,
    ApiFailureKind.rateLimited => text.mobileWaitAndRetry,
    _ => text.cmsError,
  };
}
