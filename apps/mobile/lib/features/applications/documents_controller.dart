import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../core/api/api_failure.dart';
import '../../core/files/private_files.dart';
import 'application_documents.dart';
import 'application_models.dart';

/// Screen-owned state. It never persists a document, queues bytes or resends a PUT.
class DocumentsController extends ChangeNotifier {
  final ApplicationDocumentsRepository repository;
  final PrivateFileScope? scope;
  final String organizationId, applicationId;
  final Future<void> Function(int)? onChanged;
  int version, maxUploadBytes;
  List<ApplicationDocumentRequirement> requirements;
  List<ApplicationDocument> items = [];
  bool collectionEnabled, editable, busy = false, loaded = false;
  bool requiresReadback = false, needsReview = false;
  bool _disposed = false, _foreground = true;
  ApiFailure? failure;
  DocumentIntent? pendingIntent;
  ApplicationDocument? pendingDocument, uncertainRemoval;
  CancelToken? _transfer;
  Timer? _poll, _backoff;
  DateTime? _retryUntil;
  int _generation = 0, _pollsLeft = 0;
  Future<void>? _closing;
  Completer<void>? _foregroundSignal;
  int? _pendingApplicationVersion;

  DocumentsController(
    this.repository,
    this.scope, {
    required this.organizationId,
    required this.applicationId,
    required int applicationVersion,
    required this.requirements,
    required this.collectionEnabled,
    required this.maxUploadBytes,
    this.editable = true,
    this.onChanged,
  }) : version = applicationVersion;

  bool get retryDelayed => _retryUntil?.isAfter(DateTime.now().toUtc()) == true;
  bool get hasPending =>
      pendingIntent != null ||
      pendingDocument != null ||
      uncertainRemoval != null;
  bool get blocksNavigation =>
      busy || hasPending || requiresReadback || needsReview;
  bool get canCollect =>
      !_disposed &&
      loaded &&
      editable &&
      collectionEnabled &&
      scope != null &&
      !scope!.closed &&
      _foreground &&
      !busy &&
      !hasPending &&
      !needsReview &&
      !retryDelayed;
  bool get canUpload =>
      !_disposed &&
      editable &&
      collectionEnabled &&
      scope != null &&
      !scope!.closed &&
      _foreground &&
      !busy &&
      !retryDelayed &&
      !needsReview &&
      !requiresReadback &&
      pendingIntent != null &&
      pendingDocument?.file.state == 'pending';
  bool get ready =>
      loaded &&
      !busy &&
      !hasPending &&
      !needsReview &&
      !requiresReadback &&
      requirements.every((rule) {
        final active = items
            .where((item) => item.active && item.requirementId == rule.id)
            .toList();
        return active.length >= rule.minFiles &&
            active.length <= effectiveMaxFiles(rule) &&
            policyCount(rule) <= rule.policyMaxFiles &&
            active.every((item) => item.usable);
      });
  int effectiveLimit(ApplicationDocumentRequirement rule) =>
      rule.effectiveUploadLimit(maxUploadBytes).clamp(0, applicationFileLimit);
  int effectiveMaxFiles(ApplicationDocumentRequirement rule) =>
      rule.maxFiles < rule.policyMaxFiles ? rule.maxFiles : rule.policyMaxFiles;
  int policyCount(ApplicationDocumentRequirement rule, {String? excluding}) =>
      items
          .where(
            (item) =>
                item.active &&
                item.id != excluding &&
                requirements.any(
                  (other) =>
                      other.id == item.requirementId &&
                      other.policyId == rule.policyId,
                ),
          )
          .length;
  bool hasCapacity(ApplicationDocumentRequirement rule, {String? excluding}) =>
      items
              .where(
                (item) =>
                    item.active &&
                    item.requirementId == rule.id &&
                    item.id != excluding,
              )
              .length <
          rule.maxFiles &&
      policyCount(rule, excluding: excluding) < rule.policyMaxFiles;

  void _emit() {
    if (_disposed) return;
    final pendingVersion = _pendingApplicationVersion;
    if (!busy && pendingVersion != null) {
      _pendingApplicationVersion = null;
      if (pendingVersion > version) {
        version = pendingVersion;
        loaded = false;
        Future.microtask(load);
      }
    }
    notifyListeners();
  }

  Future<bool> _visible(int operation) async {
    if (!_current(operation)) return false;
    if (!_foreground) {
      final signal = _foregroundSignal ??= Completer<void>();
      await signal.future;
    }
    return _current(operation) && _foreground && editable && collectionEnabled;
  }

  bool _current(int operation) => !_disposed && operation == _generation;
  ApiFailure _safe(Object error, {bool command = false}) => error is ApiFailure
      ? error
      : ApiFailure(
          'file_runtime_unavailable',
          kind: ApiFailureKind.unavailable,
          outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
        );
  void _fail(Object error, {bool command = false}) {
    failure = _safe(error, command: command);
    if (failure!.kind == ApiFailureKind.conflict ||
        failure!.kind == ApiFailureKind.invalidSession) {
      needsReview = true;
    }
    final delay = failure!.retryAfter;
    if (delay != null && delay > Duration.zero) {
      _backoff?.cancel();
      _retryUntil = DateTime.now().toUtc().add(delay);
      _backoff = Timer(delay, () {
        _retryUntil = null;
        _emit();
      });
    }
  }

  void _upsert(ApplicationDocument document) {
    items = [
      for (final item in items)
        if (item.id != document.id && item.id != pendingIntent?.replacesId)
          item,
      if (document.active) document,
    ];
  }

  Future<void> _version(int value) async {
    if (value < version) {
      throw const ApiFailure('version_conflict', kind: ApiFailureKind.conflict);
    }
    version = value;
    await onChanged?.call(value);
  }

  Future<void> _result(ApplicationDocumentResult result) async {
    if (result.applicationVersion < version) {
      throw const ApiFailure('version_conflict', kind: ApiFailureKind.conflict);
    }
    _upsert(result.document);
    await _version(result.applicationVersion);
  }

  Future<void> load({bool poll = false}) async {
    if (busy || _disposed || !_foreground || retryDelayed) return;
    final operation = ++_generation;
    if (!poll) _pollsLeft = 5;
    _poll?.cancel();
    busy = true;
    failure = null;
    _emit();
    try {
      final batch = await repository.list(organizationId, applicationId);
      if (!_current(operation)) return;
      if (batch.applicationVersion < version) {
        throw const ApiFailure(
          'version_conflict',
          kind: ApiFailureKind.conflict,
        );
      }
      items = batch.items;
      requirements = batch.requirements;
      collectionEnabled = batch.collectionEnabled;
      maxUploadBytes = batch.maxUploadBytes;
      loaded = true;
      needsReview = false;
      await _version(batch.applicationVersion);
    } catch (error) {
      if (_current(operation)) {
        loaded = false;
        _fail(error);
      }
    } finally {
      if (_current(operation)) {
        busy = false;
        _emit();
        _schedulePoll();
      }
    }
  }

  void _schedulePoll() {
    _poll?.cancel();
    if (_disposed ||
        !_foreground ||
        !loaded ||
        failure != null ||
        _pollsLeft < 1 ||
        !items.any((item) => item.waiting)) {
      return;
    }
    _pollsLeft--;
    _poll = Timer(
      const Duration(seconds: 2),
      () => unawaited(load(poll: true)),
    );
  }

  Future<void> pick(
    ApplicationDocumentRequirement rule, {
    ApplicationDocument? replaces,
  }) async {
    if (!canCollect || !requirements.any((value) => value.id == rule.id)) {
      return;
    }
    final active = items
        .where(
          (item) =>
              item.active &&
              item.requirementId == rule.id &&
              item.id != replaces?.id,
        )
        .length;
    if (active >= effectiveMaxFiles(rule) ||
        !hasCapacity(rule, excluding: replaces?.id) ||
        (replaces != null &&
            (!replaces.active || replaces.requirementId != rule.id))) {
      _fail(
        const ApiFailure('file_count_exceeded', kind: ApiFailureKind.conflict),
      );
      _emit();
      return;
    }
    final operation = ++_generation;
    busy = true;
    failure = null;
    _poll?.cancel();
    _emit();
    PrivateSnapshot? selected;
    try {
      selected = await scope!.pick(
        allowedMediaTypes: rule.mimeTypes.toSet().intersection(
          applicationFileTypes,
        ),
        maxBytes: effectiveLimit(rule),
      );
      if (!await _visible(operation)) {
        await selected?.dispose();
        selected = null;
        return;
      }
      if (selected == null) return;
      await selected.verify();
      if (!await _visible(operation)) {
        await selected.dispose();
        selected = null;
        return;
      }
      if (!rule.mimeTypes.contains(selected.mediaType) ||
          selected.byteSize < 1 ||
          selected.byteSize > effectiveLimit(rule)) {
        throw const ApiFailure(
          'invalid_file',
          kind: ApiFailureKind.validation,
          outcome: CommandOutcome.notSent,
        );
      }
      pendingIntent = DocumentIntent(
        snapshot: selected,
        expectedVersion: version,
        requirementId: rule.id,
        replacesId: replaces?.id,
        mayRegister: () =>
            !_disposed && _foreground && editable && collectionEnabled,
      );
      selected = null;
      await _register(operation);
    } catch (error) {
      if (_current(operation)) _fail(error);
    } finally {
      await selected?.dispose();
      if (_current(operation)) {
        busy = false;
        _emit();
      }
    }
  }

  Future<void> _register(int operation) async {
    final intent = pendingIntent;
    if (intent == null ||
        !_foreground ||
        !editable ||
        !collectionEnabled ||
        scope?.closed != false) {
      return;
    }
    try {
      final result = await repository.register(
        organizationId,
        applicationId,
        intent,
      );
      if (!_current(operation)) return;
      pendingDocument = result.document;
      requiresReadback = false;
      needsReview = false;
      await _result(result);
      if (pendingDocument!.file.state != 'pending') await _clearPending();
    } catch (error) {
      if (_current(operation)) _fail(error, command: true);
    }
  }

  Future<void> recoverRegistration() async {
    if (_disposed ||
        busy ||
        !editable ||
        !collectionEnabled ||
        !_foreground ||
        retryDelayed ||
        pendingIntent == null ||
        pendingDocument != null) {
      return;
    }
    final operation = ++_generation;
    busy = true;
    failure = null;
    _emit();
    await _register(operation);
    if (_current(operation)) {
      busy = false;
      _emit();
    }
  }

  Future<void> uploadPending() async {
    if (!canUpload) return;
    final operation = ++_generation;
    final document = pendingDocument!, snapshot = pendingIntent!.snapshot;
    busy = true;
    failure = null;
    _poll?.cancel();
    _transfer = CancelToken();
    _emit();
    try {
      final result = await repository.upload(
        organizationId,
        applicationId,
        document,
        snapshot,
        cancelToken: _transfer,
      );
      if (!_current(operation)) return;
      await _result(result);
      await _clearPending();
      _pollsLeft = 5;
    } catch (error) {
      if (_current(operation)) {
        _fail(error, command: true);
        requiresReadback = true;
      }
    } finally {
      if (_current(operation)) {
        busy = false;
        _transfer = null;
        _emit();
        _schedulePoll();
      }
    }
  }

  Future<void> reconcileUpload() async {
    final known = pendingDocument;
    if (_disposed || busy || known == null || !_foreground || retryDelayed) {
      return;
    }
    final operation = ++_generation;
    busy = true;
    failure = null;
    _emit();
    try {
      final result = await repository.detail(
        organizationId,
        applicationId,
        known.id,
      );
      if (!_current(operation)) return;
      if (result.document.file.version < known.file.version) {
        throw const ApiFailure(
          'version_conflict',
          kind: ApiFailureKind.conflict,
        );
      }
      pendingDocument = result.document;
      requiresReadback = false;
      needsReview = false;
      await _result(result);
      if (!result.document.active || result.document.file.state != 'pending') {
        await _clearPending();
      }
      _pollsLeft = 5;
    } catch (error) {
      if (_current(operation)) {
        _fail(error);
        requiresReadback = true;
      }
    } finally {
      if (_current(operation)) {
        busy = false;
        _emit();
        _schedulePoll();
      }
    }
  }

  /// After process death, only a registered pending binding can accept re-selection.
  Future<void> reselectPending(ApplicationDocument document) async {
    if (!canCollect || document.file.state != 'pending' || !document.active) {
      return;
    }
    final rule = requirements
        .where((value) => value.id == document.requirementId)
        .firstOrNull;
    if (rule == null) return;
    final operation = ++_generation;
    busy = true;
    failure = null;
    _emit();
    PrivateSnapshot? selected;
    try {
      final current = await repository.detail(
        organizationId,
        applicationId,
        document.id,
      );
      if (!_current(operation)) return;
      await _result(current);
      if (!current.document.active ||
          current.document.file.state != 'pending') {
        throw const ApiFailure(
          'file_upload_unavailable',
          kind: ApiFailureKind.conflict,
        );
      }
      if (!await _visible(operation)) return;
      selected = await scope!.pick(
        allowedMediaTypes: {document.file.mediaType},
        maxBytes: effectiveLimit(rule),
      );
      if (!await _visible(operation)) {
        await selected?.dispose();
        selected = null;
        return;
      }
      if (selected == null) return;
      await selected.verify();
      if (!await _visible(operation)) {
        await selected.dispose();
        selected = null;
        return;
      }
      if (selected.byteSize != current.document.file.byteSize ||
          selected.sha256 != current.document.file.sha256 ||
          selected.mediaType != current.document.file.mediaType) {
        throw const ApiFailure(
          'file_proof_mismatch',
          kind: ApiFailureKind.validation,
          outcome: CommandOutcome.notSent,
        );
      }
      pendingIntent = DocumentIntent(
        snapshot: selected,
        expectedVersion: version,
        requirementId: rule.id,
      );
      pendingDocument = current.document;
      requiresReadback = false;
      selected = null;
    } catch (error) {
      if (_current(operation)) _fail(error);
    } finally {
      await selected?.dispose();
      if (_current(operation)) {
        busy = false;
        _emit();
      }
    }
  }

  Future<void> remove(ApplicationDocument document) async {
    if (!canCollect || !document.active) return;
    final operation = ++_generation;
    busy = true;
    failure = null;
    _emit();
    try {
      final result = await repository.remove(
        organizationId,
        applicationId,
        document,
        version,
      );
      if (!_current(operation)) return;
      await _result(result);
    } catch (error) {
      if (_current(operation)) {
        _fail(error, command: true);
        if (failure!.uncertain) uncertainRemoval = document;
      }
    } finally {
      if (_current(operation)) {
        busy = false;
        _emit();
      }
    }
  }

  Future<void> reconcileRemoval() async {
    final document = uncertainRemoval;
    if (_disposed || busy || document == null || !_foreground || retryDelayed) {
      return;
    }
    final operation = ++_generation;
    busy = true;
    failure = null;
    _emit();
    try {
      final result = await repository.detail(
        organizationId,
        applicationId,
        document.id,
      );
      if (!_current(operation)) return;
      await _result(result);
      uncertainRemoval = null;
      needsReview = false;
    } catch (error) {
      if (_current(operation)) _fail(error);
    } finally {
      if (_current(operation)) {
        busy = false;
        _emit();
      }
    }
  }

  Future<PrivateSnapshot?> download(ApplicationDocument document) async {
    if (_disposed ||
        busy ||
        retryDelayed ||
        scope == null ||
        scope!.closed ||
        !_foreground ||
        !collectionEnabled ||
        !document.usable) {
      return null;
    }
    final operation = ++_generation;
    busy = true;
    failure = null;
    _transfer = CancelToken();
    _emit();
    try {
      final result = await repository.download(
        organizationId,
        applicationId,
        document,
        scope!,
        cancelToken: _transfer,
      );
      if (!_current(operation) || !_foreground) {
        await result.dispose();
        return null;
      }
      return result;
    } catch (error) {
      if (_current(operation)) _fail(error);
      return null;
    } finally {
      if (_current(operation)) {
        busy = false;
        _transfer = null;
        _emit();
      }
    }
  }

  Future<void> _clearPending() async {
    final intent = pendingIntent;
    pendingIntent = null;
    pendingDocument = null;
    requiresReadback = false;
    await intent?.snapshot.dispose();
  }

  Future<void> discardPending() async {
    if (_disposed || busy) return;
    await _clearPending();
    needsReview = false;
    failure = null;
    _emit();
  }

  void syncApplicationVersion(int value, {required bool editable}) {
    if (_disposed) return;
    this.editable = editable;
    if (busy && value > (_pendingApplicationVersion ?? version)) {
      _pendingApplicationVersion = value;
    } else if (!busy && value > version) {
      version = value;
      loaded = false;
    }
    if (!editable) {
      _transfer?.cancel();
      _poll?.cancel();
      if (!busy) unawaited(_clearPending().then((_) => _emit()));
    }
  }

  void pause() {
    _foreground = false;
    _poll?.cancel();
    _transfer?.cancel();
    _emit();
  }

  Future<void> resume() async {
    if (_disposed) return;
    _foreground = true;
    final signal = _foregroundSignal;
    _foregroundSignal = null;
    signal?.complete();
    _emit();
    if (pendingDocument != null && requiresReadback) {
      await reconcileUpload();
    } else {
      await load();
    }
  }

  Future<void> close() {
    dispose();
    return _closing ?? Future.value();
  }

  Future<void> _cleanupScope() async {
    try {
      await _clearPending();
    } finally {
      await scope?.close();
    }
  }

  @override
  void dispose() {
    if (_disposed) return;
    _disposed = true;
    final signal = _foregroundSignal;
    _foregroundSignal = null;
    signal?.complete();
    _generation++;
    _poll?.cancel();
    _backoff?.cancel();
    _transfer?.cancel();
    items = [];
    super.dispose();
    _closing = _cleanupScope();
    unawaited(
      _closing!.catchError((Object error) {
        failure = _safe(error);
      }),
    );
  }
}
