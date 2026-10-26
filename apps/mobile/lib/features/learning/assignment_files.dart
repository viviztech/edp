import 'dart:async';
import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../../core/files/file_transport.dart';
import '../../core/files/private_files.dart';
import '../identity/providers.dart';
import 'learning_models.dart';
import 'learning_repository.dart';

String learningRequestId() {
  final bytes = List.generate(16, (_) => Random.secure().nextInt(256));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  final hex = bytes.map((n) => n.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}

class AssignmentAttachment {
  final String id, state, fileId, fileState, mediaType, sha256, requestId;
  final int revision, version, fileVersion, byteSize;
  final bool usable;
  final int? frozenVersion;
  final DateTime? frozenAt;
  AssignmentAttachment(Map<String, dynamic> data, String org)
    : id = learningId(data['id']),
      state = data['state'] as String,
      revision = learningInt(data['target_revision'], min: 1, max: 10),
      version = learningInt(data['version'], min: 1),
      fileId = learningId(learningObject(data['file'])['id']),
      fileState = learningObject(data['file'])['state'] as String,
      mediaType = learningObject(data['file'])['media_type'] as String,
      sha256 = learningObject(data['file'])['sha256'] as String,
      byteSize = learningInt(
        learningObject(data['file'])['byte_size'],
        min: 1,
        max: 104857600,
      ),
      fileVersion = learningInt(
        learningObject(data['file'])['version'],
        min: 1,
      ),
      requestId = learningId(learningObject(data['file'])['client_request_id']),
      usable = data['usable'] as bool,
      frozenVersion = data['evidence'] == null
          ? null
          : learningInt(
              learningObject(data['evidence'])['file_version'],
              min: 1,
            ),
      frozenAt = data['evidence'] == null
          ? null
          : learningDate(learningObject(data['evidence'])['frozen_at']) {
    final file = learningObject(data['file']);
    if (file['organization_id'] != org ||
        file['purpose'] != 'assignment_submission' ||
        file['resource_id'] != id ||
        !{'active', 'removed', 'submitted'}.contains(state) ||
        !privateMediaTypes.contains(mediaType) ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256)) {
      throw const FormatException();
    }
    if (data['evidence'] != null) {
      final proof = learningObject(data['evidence']);
      if (proof['file_id'] != fileId ||
          proof['sha256'] != sha256 ||
          proof['byte_size'] != byteSize) {
        throw const FormatException();
      }
    }
  }
  bool get waiting =>
      {'uploading', 'quarantined', 'scanning'}.contains(fileState);
}

class AssignmentFileRule {
  final int minimum, maximum, maxBytes;
  final Set<String> types;
  final LearningLabel notice;
  AssignmentFileRule(Map<String, dynamic> data)
    : minimum = learningInt(data['minimum_files'], max: 100),
      maximum = learningInt(data['maximum_files'], min: 1, max: 100),
      maxBytes = learningInt(data['max_file_bytes'], min: 1, max: 104857600),
      types = (data['allowed_mime_types'] as List).cast<String>().toSet(),
      notice = LearningLabel(data, 'notice') {
    if (minimum > maximum ||
        types.isEmpty ||
        !types.every(privateMediaTypes.contains)) {
      throw const FormatException();
    }
  }
}

class AssignmentFileBatch {
  final bool collectionEnabled;
  final int nextRevision, maxBytes;
  final AssignmentFileRule? rule;
  final List<AssignmentAttachment> items;
  AssignmentFileBatch(Map<String, dynamic> data, String org)
    : collectionEnabled = data['collection_enabled'] as bool,
      nextRevision = learningInt(data['next_revision'], min: 1, max: 11),
      maxBytes = learningInt(data['max_upload_bytes'], min: 1, max: 104857600),
      rule = data['rule'] == null
          ? null
          : AssignmentFileRule(learningObject(data['rule'])),
      items = learningObjects(
        data['items'],
      ).map((item) => AssignmentAttachment(item, org)).toList() {
    if (items.length > 1000 ||
        items.map((item) => item.id).toSet().length != items.length) {
      throw const FormatException();
    }
  }
  List<AssignmentAttachment> get staged => items
      .where((item) => item.state == 'active' && item.revision == nextRevision)
      .toList();
  List<String> get usableIds =>
      staged.where((item) => item.usable).map((item) => item.id).toList();
  bool get ready =>
      staged.every((item) => item.usable) &&
      staged.length >= (rule?.minimum ?? 0) &&
      staged.length <= (rule?.maximum ?? 0);
  int get effectiveBytes =>
      [maxBytes, rule?.maxBytes ?? maxBytes, clientMaxFileBytes].reduce(min);
}

final assignmentFilesRepositoryProvider = Provider(
  (ref) => AssignmentFilesRepository(
    ref.watch(domainApiProvider),
    FileTransport(ref.watch(authRepositoryProvider)),
  ),
);

class AssignmentFilesRepository {
  final DomainApi api;
  final FileTransport transport;
  AssignmentFilesRepository(this.api, this.transport);
  String root(String org, String course, String assignment) {
    learningId(course);
    learningId(assignment);
    return '${learningRoot(org)}/my-learning/$course/assignments/$assignment/files';
  }

  Future<AssignmentFileBatch> list(
    String org,
    String course,
    String assignment,
  ) async {
    final data = await api.get(root(org, course, assignment));
    return learningDecode(() => AssignmentFileBatch(learningObject(data), org));
  }

  Future<AssignmentAttachment> detail(
    String org,
    String course,
    String assignment,
    String id,
  ) async {
    learningId(id);
    final data = await api.get('${root(org, course, assignment)}/$id');
    return learningDecode(() => _file(data, org, id));
  }

  AssignmentAttachment _file(Object? data, String org, [String? id]) {
    final file = AssignmentAttachment(learningObject(data), org);
    if (id != null && file.id != id) throw const FormatException();
    return file;
  }

  Future<AssignmentAttachment> register(
    String org,
    String course,
    String assignment,
    Map<String, Object> intent,
    PrivateSnapshot snapshot,
  ) async {
    await snapshot.verify();
    final data = await api.post(root(org, course, assignment), data: intent);
    return learningDecode(() {
      final result = _file(data, org);
      if (result.requestId != intent['client_request_id'] ||
          result.revision != intent['expected_revision'] ||
          result.byteSize != snapshot.byteSize ||
          result.sha256 != snapshot.sha256 ||
          result.mediaType != snapshot.mediaType) {
        throw const FormatException();
      }
      return result;
    }, command: true);
  }

  Future<AssignmentAttachment> upload(
    String org,
    String course,
    String assignment,
    AssignmentAttachment file,
    PrivateSnapshot snapshot,
    CancelToken token,
  ) async {
    if (snapshot.sha256 != file.sha256 ||
        snapshot.byteSize != file.byteSize ||
        snapshot.mediaType != file.mediaType) {
      throw const ApiFailure(
        'file_proof_mismatch',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await transport.upload(
      '${root(org, course, assignment)}/${file.id}/content',
      snapshot: snapshot,
      expectedVersion: file.fileVersion,
      cancelToken: token,
    );
    return learningDecode(() => _file(data, org, file.id), command: true);
  }

  Future<AssignmentAttachment> remove(
    String org,
    String course,
    String assignment,
    AssignmentAttachment file,
  ) async {
    final data = await api.delete(
      '${root(org, course, assignment)}/${file.id}',
      data: {'expected_version': file.version},
    );
    return learningDecode(() => _file(data, org, file.id), command: true);
  }

  Future<PrivateSnapshot> download(
    String org,
    String course,
    String assignment,
    AssignmentAttachment file,
    PrivateFileScope scope,
    CancelToken token,
  ) async {
    final current = await detail(org, course, assignment, file.id);
    if (!current.usable || current.state == 'removed') {
      throw const ApiFailure(
        'file_not_available',
        kind: ApiFailureKind.conflict,
      );
    }
    return transport.download(
      '${root(org, course, assignment)}/${file.id}/content',
      scope: scope,
      proof: FileProof(
        mediaType: current.mediaType,
        byteSize: current.byteSize,
        sha256: current.sha256,
      ),
      cancelToken: token,
    );
  }
}

/// One assignment and one revision own their immutable selection/recovery state.
class AssignmentFilesController extends ChangeNotifier {
  final AssignmentFilesRepository repository;
  final PrivateFileScope? scope;
  final String org, course, assignment;
  AssignmentFileBatch? batch;
  ApiFailure? failure;
  bool busy = false, needsReadback = false, _closed = false, _foreground = true;
  String? operation;
  PrivateSnapshot? selected;
  Map<String, Object>? intent;
  AssignmentAttachment? pending;
  CancelToken? _transfer;
  Timer? _poll;
  int _polls = 0;
  DateTime? _retryUntil;
  AssignmentFilesController(
    this.repository,
    this.scope, {
    required this.org,
    required this.course,
    required this.assignment,
  });
  bool get hasPending => intent != null || pending != null || needsReadback;
  bool get retryDelayed => _retryUntil?.isAfter(DateTime.now().toUtc()) == true;
  bool get canPick =>
      !_closed &&
      _foreground &&
      !busy &&
      !hasPending &&
      !retryDelayed &&
      batch?.collectionEnabled == true &&
      batch?.rule != null &&
      scope?.closed == false;
  bool get ready => batch != null && batch!.ready && !busy && !hasPending;
  void _emit() {
    if (!_closed) notifyListeners();
  }

  void _fail(Object error, {bool command = false}) {
    failure = error is ApiFailure
        ? error
        : ApiFailure(
            'file_unavailable',
            kind: ApiFailureKind.unavailable,
            outcome: command
                ? CommandOutcome.uncertain
                : CommandOutcome.rejected,
          );
    if (failure!.retryAfter case final delay?) {
      _retryUntil = DateTime.now().toUtc().add(delay);
    }
  }

  Future<void> load() async {
    if (_closed || busy || !_foreground || retryDelayed) return;
    busy = true;
    failure = null;
    _emit();
    try {
      final value = await repository.list(org, course, assignment);
      if (_closed) return;
      batch = value;
    } catch (error) {
      if (!_closed) _fail(error);
    } finally {
      if (!_closed) {
        busy = false;
        _emit();
        _schedule();
      }
    }
  }

  void _schedule() {
    _poll?.cancel();
    if (!_foreground ||
        _closed ||
        _polls >= 5 ||
        failure != null ||
        batch?.items.any((file) => file.waiting) != true) {
      return;
    }
    _polls++;
    _poll = Timer(const Duration(seconds: 2), () => unawaited(load()));
  }

  Future<void> pick({AssignmentAttachment? existing}) async {
    if (!canPick ||
        (existing == null && batch!.staged.length >= batch!.rule!.maximum) ||
        (existing != null &&
            (existing.state != 'active' || existing.fileState != 'pending'))) {
      return;
    }
    busy = true;
    failure = null;
    _poll?.cancel();
    _emit();
    PrivateSnapshot? copy;
    try {
      if (existing != null) {
        existing = await repository.detail(
          org,
          course,
          assignment,
          existing.id,
        );
        if (existing.state != 'active' ||
            existing.fileState != 'pending' ||
            existing.revision != batch!.nextRevision) {
          throw const ApiFailure(
            'version_conflict',
            kind: ApiFailureKind.conflict,
          );
        }
      }
      if (_closed || !_foreground) return;
      copy = await scope!.pick(
        allowedMediaTypes: existing == null
            ? batch!.rule!.types
            : {existing.mediaType},
        maxBytes: batch!.effectiveBytes,
      );
      if (copy == null) return;
      if (_closed || !_foreground) return;
      await copy.verify();
      if (_closed || !_foreground) return;
      if (!batch!.rule!.types.contains(copy.mediaType) ||
          copy.byteSize > batch!.effectiveBytes ||
          copy.byteSize < 1) {
        throw const ApiFailure('invalid_file', kind: ApiFailureKind.validation);
      }
      if (existing != null &&
          (copy.sha256 != existing.sha256 ||
              copy.byteSize != existing.byteSize ||
              copy.mediaType != existing.mediaType)) {
        throw const ApiFailure(
          'file_proof_mismatch',
          kind: ApiFailureKind.validation,
        );
      }
      selected = copy;
      copy = null;
      pending = existing;
      intent = Map.unmodifiable({
        'client_request_id': existing?.requestId ?? learningRequestId(),
        'expected_revision': batch!.nextRevision,
        'media_type': selected!.mediaType,
        'byte_size': selected!.byteSize,
        'sha256': selected!.sha256,
      });
      if (existing == null) await _register();
    } catch (error) {
      if (!_closed) _fail(error, command: intent != null);
    } finally {
      await copy?.dispose();
      if (!_closed) {
        busy = false;
        _emit();
      }
    }
  }

  Future<void> _register() async {
    operation = 'intent';
    final result = await repository.register(
      org,
      course,
      assignment,
      intent!,
      selected!,
    );
    if (_closed) return;
    pending = result;
    operation = null;
    needsReadback = false;
  }

  Future<void> recoverIntent() async {
    if (_closed ||
        busy ||
        !_foreground ||
        retryDelayed ||
        intent == null ||
        pending != null) {
      return;
    }
    busy = true;
    failure = null;
    _emit();
    try {
      await _register();
    } catch (error) {
      if (!_closed) _fail(error, command: true);
    } finally {
      if (!_closed) {
        busy = false;
        _emit();
      }
    }
  }

  Future<void> upload() async {
    if (_closed ||
        busy ||
        !_foreground ||
        retryDelayed ||
        needsReadback ||
        selected == null ||
        pending?.fileState != 'pending' ||
        scope?.closed != false) {
      return;
    }
    busy = true;
    failure = null;
    operation = 'upload';
    _transfer = CancelToken();
    _emit();
    try {
      await repository.upload(
        org,
        course,
        assignment,
        pending!,
        selected!,
        _transfer!,
      );
      if (_closed) return;
      await _clear();
      _polls = 0;
    } catch (error) {
      if (!_closed) {
        _fail(error, command: true);
        needsReadback = true;
      }
    } finally {
      if (!_closed) {
        busy = false;
        _transfer = null;
        _emit();
        if (!needsReadback) await load();
      }
    }
  }

  Future<void> remove(AssignmentAttachment file) async {
    if (_closed ||
        busy ||
        !_foreground ||
        retryDelayed ||
        hasPending ||
        file.state != 'active') {
      return;
    }
    busy = true;
    failure = null;
    operation = 'remove';
    pending = file;
    _emit();
    try {
      await repository.remove(org, course, assignment, file);
      if (!_closed) await _clear();
    } catch (error) {
      if (!_closed) {
        _fail(error, command: true);
        if (failure!.uncertain || failure!.kind == ApiFailureKind.conflict) {
          needsReadback = true;
        } else {
          pending = null;
          operation = null;
        }
      }
    } finally {
      if (!_closed) {
        busy = false;
        _emit();
        if (!needsReadback) await load();
      }
    }
  }

  Future<void> reconcile() async {
    if (_closed || busy || !_foreground || retryDelayed || pending == null) {
      return;
    }
    busy = true;
    failure = null;
    _emit();
    try {
      final current = await repository.detail(
        org,
        course,
        assignment,
        pending!.id,
      );
      if (_closed) return;
      pending = current;
      if (operation == 'remove' ||
          current.state != 'active' ||
          current.fileState != 'pending') {
        await _clear();
      } else {
        needsReadback = false;
        operation = null;
      }
    } catch (error) {
      if (!_closed) {
        _fail(error);
        needsReadback = true;
      }
    } finally {
      if (!_closed) {
        busy = false;
        _emit();
        if (!needsReadback) await load();
      }
    }
  }

  Future<void> _clear() async {
    final copy = selected;
    selected = null;
    intent = null;
    pending = null;
    needsReadback = false;
    operation = null;
    await copy?.dispose();
  }

  Future<void> discard() async {
    if (_closed || busy) return;
    await _clear();
    if (!_closed) {
      failure = null;
      _emit();
      await load();
    }
  }

  void pause() {
    _foreground = false;
    _poll?.cancel();
    _transfer?.cancel();
  }

  Future<void> resume() async {
    if (_closed) return;
    _foreground = true;
    _polls = 0;
    if (needsReadback && pending != null) {
      await reconcile();
    } else {
      await load();
    }
  }

  @override
  void dispose() {
    if (_closed) return;
    _closed = true;
    _poll?.cancel();
    _transfer?.cancel();
    super.dispose();
    unawaited(_cleanup());
  }

  Future<void> _cleanup() async {
    try {
      await _clear();
    } finally {
      try {
        await scope?.close();
      } catch (_) {
        /* Private store fails closed. */
      }
    }
  }
}
