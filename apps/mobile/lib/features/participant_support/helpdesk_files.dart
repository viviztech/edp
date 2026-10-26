import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../../core/files/file_transport.dart';
import '../../core/files/private_files.dart';
import 'support_common.dart';

class SupportFilePolicy {
  final String id, noticeEn, noticeTa;
  final int maxBytes, maxFiles, retentionDays, rejectedDays;
  final Set<String> mediaTypes;
  SupportFilePolicy.fromJson(Map<String, dynamic> d)
    : id = identifier(d['id']),
      noticeEn = d['notice_en'] as String,
      noticeTa = d['notice_ta'] as String,
      maxBytes = (d['max_file_bytes'] as int) < (d['max_upload_bytes'] as int)
          ? d['max_file_bytes'] as int
          : d['max_upload_bytes'] as int,
      maxFiles = d['max_files'] as int,
      retentionDays = d['retention_days'] as int,
      rejectedDays = d['rejected_retention_days'] as int,
      mediaTypes = Set.unmodifiable(
        (d['allowed_mime_types'] as List).cast<String>(),
      ) {
    if (maxBytes < 1 || maxFiles < 1 || mediaTypes.isEmpty) {
      throw const FormatException();
    }
  }
}

class SupportFile {
  final String id,
      state,
      fileState,
      organizationId,
      fileId,
      mediaType,
      sha256,
      requestId;
  final int version, fileVersion, byteSize;
  final int? frozenVersion;
  final DateTime? frozenAt;
  final bool usable;
  final SupportFilePolicy policy;
  SupportFile.fromJson(Map<String, dynamic> d)
    : id = identifier(d['id']),
      state = d['state'] as String,
      version = versionOf(d['version']),
      usable = d['usable'] as bool,
      fileState = object(d['file'])['state'] as String,
      organizationId = identifier(object(d['file'])['organization_id']),
      fileId = identifier(object(d['file'])['id']),
      requestId = identifier(object(d['file'])['client_request_id']),
      mediaType = object(d['file'])['media_type'] as String,
      sha256 =
          (d['evidence'] == null
                  ? object(d['file'])['sha256']
                  : object(d['evidence'])['sha256'])
              as String,
      byteSize =
          (d['evidence'] == null
                  ? object(d['file'])['byte_size']
                  : object(d['evidence'])['byte_size'])
              as int,
      fileVersion = versionOf(object(d['file'])['version']),
      frozenVersion = d['evidence'] == null
          ? null
          : versionOf(object(d['evidence'])['file_version']),
      frozenAt = d['evidence'] == null
          ? null
          : DateTime.parse(object(d['evidence'])['frozen_at'] as String),
      policy = SupportFilePolicy.fromJson(object(d['policy'])) {
    if (d['internal'] != false ||
        object(d['file'])['purpose'] != 'helpdesk_attachment' ||
        object(d['file'])['resource_id'] != id ||
        byteSize < 1 ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256) ||
        !privateMediaTypes.contains(mediaType) ||
        !{'staged', 'removed', 'posted'}.contains(state)) {
      throw const FormatException();
    }
  }
  bool get selectable => state == 'staged' && usable;
}

class SupportFilesBatch {
  final bool enabled;
  final int maxBytes;
  final SupportFilePolicy? policy;
  final PageBatch<SupportFile> page;
  SupportFilesBatch.fromJson(Map<String, dynamic> d)
    : enabled = d['collection_enabled'] as bool,
      maxBytes = d['max_upload_bytes'] as int,
      policy = d['policy'] == null
          ? null
          : SupportFilePolicy.fromJson(object(d['policy'])),
      page = PageBatch.fromJson(d, SupportFile.fromJson);
}

class HelpdeskFilesRepository {
  final DomainApi api;
  final FileTransport transport;
  HelpdeskFilesRepository(this.api, this.transport);
  String root(String org, String ticket) =>
      '/helpdesk/organizations/${identifier(org)}/tickets/${identifier(ticket)}/files';
  SupportFile _file(
    Object? data,
    String org, {
    String? id,
    bool command = false,
  }) => decode(() {
    final file = SupportFile.fromJson(object(data));
    if (file.organizationId != org || (id != null && file.id != id)) {
      throw const FormatException();
    }
    return file;
  }, command: command);
  Future<SupportFilesBatch> list(
    String org,
    String ticket, {
    String? cursor,
  }) async {
    final data = await api.get(
      root(org, ticket),
      queryParameters: {'limit': 25, 'cursor': ?cursor},
    );
    return decode(() {
      final batch = SupportFilesBatch.fromJson(object(data));
      if (batch.page.items.any((f) => f.organizationId != org)) {
        throw const FormatException();
      }
      return batch;
    });
  }

  Future<SupportFile> detail(String org, String ticket, String id) async =>
      _file(
        await api.get('${root(org, ticket)}/${identifier(id)}'),
        org,
        id: id,
      );
  Future<SupportFile> register(
    String org,
    String ticket,
    Map<String, Object> intent,
  ) async => _file(
    await api.post(root(org, ticket), data: intent),
    org,
    command: true,
  );
  Future<SupportFile> upload(
    String org,
    String ticket,
    SupportFile file,
    PrivateSnapshot snapshot,
    CancelToken cancel,
  ) async {
    if (file.mediaType != snapshot.mediaType ||
        file.byteSize != snapshot.byteSize ||
        file.sha256 != snapshot.sha256) {
      throw const ApiFailure(
        'file_proof_mismatch',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    return _file(
      await transport.upload(
        '${root(org, ticket)}/${file.id}/content',
        snapshot: snapshot,
        expectedVersion: file.fileVersion,
        cancelToken: cancel,
      ),
      org,
      id: file.id,
      command: true,
    );
  }

  Future<SupportFile> remove(
    String org,
    String ticket,
    SupportFile file,
  ) async => _file(
    await api.delete(
      '${root(org, ticket)}/${file.id}',
      data: {'expected_version': file.version},
    ),
    org,
    id: file.id,
    command: true,
  );
  Future<PrivateSnapshot> download(
    String org,
    String ticket,
    SupportFile file,
    PrivateFileScope scope,
    CancelToken cancel,
  ) async {
    final current = await detail(org, ticket, file.id);
    if (!current.usable || current.state == 'removed') {
      throw const ApiFailure('file_unavailable', kind: ApiFailureKind.conflict);
    }
    return transport.download(
      '${root(org, ticket)}/${file.id}/content',
      scope: scope,
      proof: FileProof(
        mediaType: current.mediaType,
        byteSize: current.byteSize,
        sha256: current.sha256,
      ),
      cancelToken: cancel,
    );
  }
}

class HelpdeskFilesController extends ChangeNotifier with SupportRetry {
  final HelpdeskFilesRepository repository;
  final String organizationId, ticketId;
  final PrivateFileScope? scope;
  List<SupportFile> items = [];
  final Set<String> selected = {};
  SupportFilePolicy? policy;
  int maxBytes = 0;
  bool enabled = false,
      busy = false,
      requiresReadback = false,
      _disposed = false,
      _foreground = true;
  String? cursor;
  ApiFailure? failure;
  Map<String, Object>? intent;
  PrivateSnapshot? snapshot;
  SupportFile? pending;
  CancelToken? _transfer;
  Completer<void>? _foregroundSignal;
  HelpdeskFilesController(
    this.repository,
    this.organizationId,
    this.ticketId,
    this.scope,
  );
  bool get hasPending => intent != null || pending != null || requiresReadback;
  int get effectiveLimit => [
    maxBytes,
    policy?.maxBytes ?? 0,
    clientMaxFileBytes,
  ].reduce((a, b) => a < b ? a : b);
  bool get canPick =>
      !_disposed &&
      !busy &&
      !retryDelayed &&
      _foreground &&
      enabled &&
      policy != null &&
      scope != null &&
      !scope!.closed &&
      !hasPending &&
      effectiveLimit > 0;
  List<String> get replyFileIds => items
      .where((f) => f.selectable && selected.contains(f.id))
      .map((f) => f.id)
      .toList();
  Future<void> refresh({bool more = false}) async {
    if (busy || retryDelayed || _disposed || !_foreground) return;
    busy = true;
    failure = null;
    notifyListeners();
    try {
      final result = await repository.list(
        organizationId,
        ticketId,
        cursor: more ? cursor : null,
      );
      if (_disposed) return;
      enabled = result.enabled;
      maxBytes = result.maxBytes;
      policy = result.policy;
      items = more ? [...items, ...result.page.items] : result.page.items;
      cursor = result.page.cursor;
      selected.removeWhere(
        (id) => !items.any((f) => f.id == id && f.selectable),
      );
      if (pending != null) {
        final current = await repository.detail(
          organizationId,
          ticketId,
          pending!.id,
        );
        if (_disposed) return;
        pending = current;
        requiresReadback = false;
        if (current.fileState != 'pending') await discard();
      } else if (intent == null) {
        requiresReadback = false;
      }
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e);
        recordFailure(failure!);
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> pick() async {
    if (!canPick ||
        items.where((f) => f.state == 'staged').length >= policy!.maxFiles) {
      return;
    }
    busy = true;
    failure = null;
    notifyListeners();
    PrivateSnapshot? selectedFile;
    try {
      selectedFile = await scope!.pick(
        allowedMediaTypes: policy!.mediaTypes.intersection(privateMediaTypes),
        maxBytes: effectiveLimit,
      );
      if (!await _visible()) return;
      if (selectedFile == null) return;
      await selectedFile.verify();
      if (!await _visible()) return;
      if (!policy!.mediaTypes.contains(selectedFile.mediaType) ||
          selectedFile.byteSize < 1 ||
          selectedFile.byteSize > effectiveLimit) {
        throw const ApiFailure(
          'invalid_file',
          kind: ApiFailureKind.validation,
          outcome: CommandOutcome.notSent,
        );
      }
      snapshot = selectedFile;
      selectedFile = null;
      intent = Map.unmodifiable({
        'client_request_id': uuid(),
        'policy_id': policy!.id,
        'internal': false,
        'media_type': snapshot!.mediaType,
        'byte_size': snapshot!.byteSize,
        'sha256': snapshot!.sha256,
      });
      await _register();
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
      }
    } finally {
      await selectedFile?.dispose();
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> _register() async {
    await snapshot!.verify();
    if (!await _visible()) return;
    final result = await repository.register(organizationId, ticketId, intent!);
    if (_disposed) return;
    if (result.requestId != intent!['client_request_id'] ||
        result.sha256 != snapshot!.sha256 ||
        result.byteSize != snapshot!.byteSize ||
        result.mediaType != snapshot!.mediaType) {
      throw const ApiFailure(
        'invalid_response',
        kind: ApiFailureKind.invalidResponse,
        outcome: CommandOutcome.uncertain,
      );
    }
    pending = result;
    items = [...items.where((f) => f.id != result.id), result];
  }

  Future<void> recoverRegistration() async {
    if (busy ||
        retryDelayed ||
        _disposed ||
        intent == null ||
        pending != null ||
        !_foreground) {
      return;
    }
    busy = true;
    failure = null;
    notifyListeners();
    try {
      await _register();
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> upload() async {
    if (busy ||
        retryDelayed ||
        _disposed ||
        requiresReadback ||
        pending?.fileState != 'pending' ||
        snapshot == null ||
        !enabled ||
        !_foreground) {
      return;
    }
    busy = true;
    failure = null;
    _transfer = CancelToken();
    notifyListeners();
    try {
      final result = await repository.upload(
        organizationId,
        ticketId,
        pending!,
        snapshot!,
        _transfer!,
      );
      if (_disposed) return;
      items = [...items.where((f) => f.id != result.id), result];
      await discard();
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
        requiresReadback = true;
      }
    } finally {
      if (!_disposed) {
        busy = false;
        _transfer = null;
        notifyListeners();
      }
    }
  }

  Future<void> remove(SupportFile file) async {
    if (busy ||
        retryDelayed ||
        _disposed ||
        !enabled ||
        hasPending ||
        file.state != 'staged') {
      return;
    }
    busy = true;
    failure = null;
    notifyListeners();
    try {
      final result = await repository.remove(organizationId, ticketId, file);
      if (_disposed) return;
      items = [
        for (final f in items)
          if (f.id == result.id) result else f,
      ];
      selected.remove(file.id);
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
        requiresReadback = failure!.uncertain;
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<PrivateSnapshot?> download(SupportFile file) async {
    if (busy ||
        retryDelayed ||
        _disposed ||
        !_foreground ||
        !enabled ||
        scope == null ||
        scope!.closed) {
      return null;
    }
    busy = true;
    failure = null;
    _transfer = CancelToken();
    notifyListeners();
    try {
      final result = await repository.download(
        organizationId,
        ticketId,
        file,
        scope!,
        _transfer!,
      );
      if (_disposed || !_foreground) {
        await result.dispose();
        return null;
      }
      return result;
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e);
        recordFailure(failure!);
      }
      return null;
    } finally {
      if (!_disposed) {
        busy = false;
        _transfer = null;
        notifyListeners();
      }
    }
  }

  Future<void> discard() async {
    final copy = snapshot;
    snapshot = null;
    intent = null;
    pending = null;
    requiresReadback = false;
    await copy?.dispose();
  }

  void pause() {
    _foreground = false;
    _transfer?.cancel();
  }

  Future<void> resume() async {
    _foreground = true;
    _foregroundSignal?.complete();
    _foregroundSignal = null;
    await refresh();
  }

  Future<bool> _visible() async {
    if (_disposed) return false;
    if (!_foreground) await (_foregroundSignal ??= Completer<void>()).future;
    return !_disposed && _foreground && enabled;
  }

  @override
  void dispose() {
    if (_disposed) return;
    _disposed = true;
    _foregroundSignal?.complete();
    _foregroundSignal = null;
    _transfer?.cancel();
    unawaited(discard().then((_) => scope?.close()).catchError((Object _) {}));
    items = [];
    selected.clear();
    super.dispose();
  }
}
