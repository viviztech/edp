import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../core/api/api_failure.dart';
import 'application_models.dart';
import 'application_repository.dart';

/// In-memory feature state. Consequential requests are sent once and reconciled explicitly.
class ApplicationEditor extends ChangeNotifier {
  final ApplicationRepository repository;
  final String organizationId;
  final String? requestedApplicationId;
  String? cycleId;
  List<ApplicationCycle> cycles = [];
  ApplicationRecord? record, latest;
  Map<String, String> values = {};
  Set<String> accepted = {};
  ApiFailure? failure;
  bool busy = false,
      cyclesLoaded = false,
      needsReview = false,
      documentsReady = false;
  bool documentWorkPending = false;
  String? notice;
  int historyRevision = 0, _generation = 0;
  int? _pendingDocumentVersion;
  bool _disposed = false;
  DateTime? _retryUntil;
  Timer? _retryTimer;

  ApplicationEditor(
    this.repository, {
    required this.organizationId,
    this.cycleId,
    String? applicationId,
  }) : requestedApplicationId = applicationId;

  bool get open {
    final now = DateTime.now().toUtc();
    return cyclesLoaded &&
        cycleId != null &&
        cycles.any(
          (item) =>
              item.id == cycleId &&
              !item.opensAt.isAfter(now) &&
              item.closesAt.isAfter(now),
        );
  }

  bool get editable => record?.isDraft == true && open;
  bool get dirtyAnswers =>
      record?.isDraft == true &&
      record!.form.fields.any(
        (field) =>
            (values[field.id] ?? '') != (record!.answers[field.id] ?? ''),
      );
  bool get dirty =>
      dirtyAnswers || (record?.isDraft == true && accepted.isNotEmpty);
  bool get blocksNavigation => busy || needsReview || dirty;
  bool get retryDelayed => _retryUntil?.isAfter(DateTime.now().toUtc()) == true;
  bool get canWrite =>
      editable &&
      !busy &&
      !needsReview &&
      !retryDelayed &&
      !documentWorkPending;
  bool get canSubmit =>
      canWrite &&
      !dirtyAnswers &&
      documentsReady &&
      record!.form.fields.every(
        (field) =>
            (!field.isRequired || (values[field.id] ?? '').trim().isNotEmpty) &&
            applicationAnswerIsValid(field, values[field.id] ?? ''),
      ) &&
      record!.form.acknowledgements.every(
        (item) => !item.isRequired || accepted.contains(item.id),
      );

  void _emit() {
    if (_disposed) return;
    notifyListeners();
    final pending = _pendingDocumentVersion;
    if (!busy && pending != null) {
      _pendingDocumentVersion = null;
      Future.microtask(() => documentVersionChanged(pending));
    }
  }

  bool _current(int operation) => !_disposed && operation == _generation;
  ApiFailure _failure(Object error, {bool command = false}) =>
      error is ApiFailure
      ? error
      : ApiFailure(
          'service_unavailable',
          kind: ApiFailureKind.unavailable,
          outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
        );

  void _adopt(ApplicationRecord value, {bool keepAnswers = false}) {
    record = value;
    if (!keepAnswers || !value.isDraft) values = Map.of(value.answers);
    if (!value.isDraft) {
      accepted = value.accepted.map((item) => item.id).toSet();
    } else {
      accepted = accepted.intersection(
        value.form.acknowledgements.map((item) => item.id).toSet(),
      );
    }
    latest = null;
    needsReview = false;
    documentsReady = value.form.documents.isEmpty;
  }

  Future<ApplicationRecord> _read() async {
    final result = requestedApplicationId != null && cycleId == null
        ? await repository.readLegacy(organizationId, requestedApplicationId!)
        : await repository.read(organizationId, cycleId!);
    final expectedId = record?.id ?? requestedApplicationId;
    if (expectedId != null && result.id != expectedId) {
      throw const ApiFailure(
        'application_unavailable',
        kind: ApiFailureKind.notFound,
      );
    }
    return result;
  }

  Future<void> load() async {
    if (busy) return;
    // A retry/rebuild must not discard unsaved text or an unresolved command.
    if (dirty || needsReview) {
      await reconcile();
      return;
    }
    final operation = ++_generation;
    busy = true;
    failure = null;
    _emit();
    try {
      cycles = await repository.cycles(organizationId);
      if (!_current(operation)) return;
      cyclesLoaded = true;
    } catch (error) {
      if (!_current(operation)) return;
      failure = _failure(error);
      cycles = [];
      cyclesLoaded = false;
    }
    if (cycleId == null &&
        requestedApplicationId == null &&
        cycles.isNotEmpty) {
      cycleId = cycles.first.id;
    }
    if (cycleId != null || requestedApplicationId != null) {
      try {
        final value = await _read();
        if (!_current(operation)) return;
        if (requestedApplicationId != null &&
            value.id != requestedApplicationId) {
          throw const ApiFailure(
            'application_unavailable',
            kind: ApiFailureKind.notFound,
          );
        }
        _adopt(value);
        await _readiness(operation);
      } catch (error) {
        if (!_current(operation)) return;
        final result = _failure(error);
        // A missing draft in an explicitly open cycle permits starting that exact cycle.
        if (!(result.kind == ApiFailureKind.notFound &&
            requestedApplicationId == null &&
            open)) {
          failure = result;
        }
      }
    }
    if (_current(operation)) {
      busy = false;
      _emit();
    }
  }

  Future<void> _readiness(int operation) async {
    final value = record;
    if (value == null) return;
    try {
      final status = await repository.readiness(organizationId, value);
      if (!_current(operation)) return;
      documentsReady = status.ready;
      if (status.version != value.version) {
        needsReview = true;
        failure = const ApiFailure(
          'version_conflict',
          kind: ApiFailureKind.conflict,
        );
      }
    } catch (error) {
      if (_current(operation)) {
        documentsReady = false;
        failure = _failure(error);
      }
    }
  }

  Future<void> start() async {
    if (busy || needsReview || retryDelayed || !open || record != null) return;
    final operation = ++_generation;
    busy = true;
    failure = null;
    notice = null;
    _emit();
    try {
      final value = await repository.start(organizationId, cycleId!);
      if (!_current(operation)) return;
      _adopt(value);
      historyRevision++;
      await _readiness(operation);
    } catch (error) {
      if (_current(operation)) _commandFailure(error);
    } finally {
      if (_current(operation)) {
        busy = false;
        _emit();
      }
    }
  }

  void setAnswer(String id, String value) {
    if (!canWrite || !record!.form.fields.any((field) => field.id == id)) {
      return;
    }
    values = {...values, id: value};
    notice = null;
    _emit();
  }

  void acknowledge(String id, bool enabled) {
    if (!canWrite ||
        !record!.form.acknowledgements.any((item) => item.id == id)) {
      return;
    }
    accepted = {...accepted};
    if (enabled) {
      accepted.add(id);
    } else {
      accepted.remove(id);
    }
    _emit();
  }

  void _commandFailure(Object error) {
    failure = _failure(error, command: true);
    final delay = failure!.retryAfter;
    if (delay != null && delay > Duration.zero) {
      _retryTimer?.cancel();
      _retryUntil = DateTime.now().toUtc().add(delay);
      _retryTimer = Timer(delay, () {
        _retryUntil = null;
        _emit();
      });
    }
    needsReview =
        failure!.uncertain ||
        failure!.kind == ApiFailureKind.conflict ||
        failure!.kind == ApiFailureKind.invalidSession;
    latest = null;
  }

  Future<void> save() async {
    if (!canWrite) return;
    final operation = ++_generation;
    final original = record!;
    final submitted = Map<String, String>.of(values);
    busy = true;
    failure = null;
    notice = null;
    _emit();
    try {
      final saved = await repository.save(organizationId, original, submitted);
      if (!_current(operation)) return;
      _adopt(saved);
      notice = 'saved';
      historyRevision++;
      await _readiness(operation);
    } catch (error) {
      if (_current(operation)) _commandFailure(error);
    } finally {
      if (_current(operation)) {
        busy = false;
        _emit();
      }
    }
  }

  Future<void> submit() async {
    if (!canSubmit) return;
    final operation = ++_generation;
    busy = true;
    failure = null;
    notice = null;
    _emit();
    try {
      final result = await repository.submit(
        organizationId,
        record!,
        Set.of(accepted),
      );
      if (!_current(operation)) return;
      _adopt(result);
      notice = 'submitted';
      historyRevision++;
    } catch (error) {
      if (_current(operation)) _commandFailure(error);
    } finally {
      if (_current(operation)) {
        busy = false;
        _emit();
      }
    }
  }

  /// Read that exact object without discarding local text or replaying a command.
  Future<void> reconcile() async {
    if (busy || (cycleId == null && requestedApplicationId == null)) return;
    final operation = ++_generation;
    busy = true;
    failure = null;
    notice = null;
    _emit();
    try {
      // A closed intake stays readable, and stale discovery cannot enable writes.
      try {
        final currentCycles = await repository.cycles(organizationId);
        if (!_current(operation)) return;
        cycles = currentCycles;
        cyclesLoaded = true;
      } catch (error) {
        if (!_current(operation)) return;
        cycles = [];
        cyclesLoaded = false;
        failure = _failure(error);
      }
      final saved = await _read();
      if (!_current(operation)) return;
      if ((record != null && saved.id != record!.id) ||
          (requestedApplicationId != null &&
              saved.id != requestedApplicationId)) {
        throw const ApiFailure(
          'application_unavailable',
          kind: ApiFailureKind.notFound,
        );
      }
      if (!saved.isDraft) {
        _adopt(saved);
        notice = 'submitted';
        historyRevision++;
      } else if (record == null) {
        _adopt(saved);
        historyRevision++;
      } else {
        latest = saved;
        needsReview = true;
      }
    } catch (error) {
      if (_current(operation)) {
        failure = _failure(error);
        needsReview = true;
        // Starting is scoped uniquely to this owner/cycle. An authoritative
        // absence permits another explicit start without inventing a new intake.
        if (record == null &&
            requestedApplicationId == null &&
            open &&
            failure!.kind == ApiFailureKind.notFound) {
          needsReview = false;
          notice = 'not_started';
        }
      }
    } finally {
      if (_current(operation)) {
        busy = false;
        _emit();
      }
    }
  }

  Future<void> chooseSaved({required bool keepEdits}) async {
    final saved = latest;
    if (busy || saved == null) return;
    final operation = ++_generation;
    _adopt(saved, keepAnswers: keepEdits);
    failure = null;
    busy = true;
    _emit();
    await _readiness(operation);
    if (_current(operation)) {
      busy = false;
      _emit();
    }
  }

  /// A document command changes the aggregate version, never the local answers.
  /// Adopt only a read matching the acknowledged version and unchanged scalar
  /// baseline; another device's scalar changes still require an explicit choice.
  Future<void> documentVersionChanged(int acknowledgedVersion) async {
    final previous = record;
    if (!_disposed && busy) {
      if (acknowledgedVersion > (_pendingDocumentVersion ?? 0)) {
        _pendingDocumentVersion = acknowledgedVersion;
      }
      return;
    }
    if (_disposed ||
        previous == null ||
        acknowledgedVersion <= previous.version) {
      return;
    }
    final operation = ++_generation;
    busy = true;
    documentsReady = false;
    _emit();
    try {
      final saved = await _read();
      if (!_current(operation)) return;
      if (saved.version < acknowledgedVersion) {
        throw const ApiFailure(
          'version_conflict',
          kind: ApiFailureKind.conflict,
        );
      }
      if (!saved.isDraft) {
        _adopt(saved);
      } else if (!needsReview &&
          saved.version == acknowledgedVersion &&
          mapEquals(saved.answers, previous.answers) &&
          saved.form.id == previous.form.id) {
        _adopt(saved, keepAnswers: true);
      } else {
        latest = saved;
        needsReview = true;
      }
    } catch (error) {
      if (_current(operation)) {
        failure = _failure(error);
        needsReview = true;
      }
    } finally {
      if (_current(operation)) {
        busy = false;
        _emit();
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    _retryTimer?.cancel();
    values.clear();
    accepted.clear();
    super.dispose();
  }
}
