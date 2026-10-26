import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../../core/files/file_transport.dart';
import '../../core/files/private_files.dart';
import '../../core/navigation/destinations.dart';
import '../identity/providers.dart';
import 'application_models.dart';

final applicationDocumentsRepositoryProvider = Provider(
  (ref) => ApplicationDocumentsRepository(
    ref.watch(domainApiProvider),
    FileTransport(ref.watch(authRepositoryProvider)),
  ),
);

const applicationFileLimit = 10 * 1024 * 1024;
const applicationFileTypes = {
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/webp',
  'text/plain',
};

bool _uuid(Object? value) =>
    value is String && MobileDestination.uuid.hasMatch(value);
bool _digest(String value) => RegExp(r'^[0-9a-f]{64}$').hasMatch(value);

class ApplicationDocumentFile {
  final String id,
      organizationId,
      resourceId,
      clientRequestId,
      mediaType,
      sha256,
      state;
  final int byteSize, version, scanAttempts;
  final String? failureCode;
  final DateTime retentionUntil;
  final bool legalHold, evidenceFrozen;
  ApplicationDocumentFile.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      organizationId = json['organization_id'] as String,
      resourceId = json['resource_id'] as String,
      clientRequestId = json['client_request_id'] as String,
      mediaType = json['media_type'] as String,
      sha256 = json['sha256'] as String,
      state = json['state'] as String,
      byteSize = json['byte_size'] as int,
      version = json['version'] as int,
      scanAttempts = json['scan_attempts'] as int,
      failureCode = json['failure_code'] as String?,
      retentionUntil = DateTime.parse(json['retention_until'] as String),
      legalHold = json['legal_hold'] as bool,
      evidenceFrozen = json['evidence_frozen'] as bool {
    if (!_uuid(id) ||
        !_uuid(organizationId) ||
        !_uuid(resourceId) ||
        !_uuid(clientRequestId) ||
        !applicationFileTypes.contains(mediaType) ||
        !_digest(sha256) ||
        byteSize < 1 ||
        byteSize > 104857600 ||
        version < 1 ||
        version > 2147483647 ||
        scanAttempts < 0 ||
        !{
          'pending',
          'uploading',
          'quarantined',
          'scanning',
          'clean',
          'infected',
          'rejected',
          'deleted',
        }.contains(state) ||
        json['purpose'] != 'application_document') {
      throw const FormatException('Invalid document metadata');
    }
  }
}

class ApplicationDocumentEvidence {
  final String fileId, sha256;
  final int fileVersion, byteSize;
  final DateTime frozenAt;
  ApplicationDocumentEvidence.fromJson(Map<String, dynamic> json)
    : fileId = json['file_id'] as String,
      sha256 = json['sha256'] as String,
      fileVersion = json['file_version'] as int,
      byteSize = json['byte_size'] as int,
      frozenAt = DateTime.parse(json['frozen_at'] as String) {
    if (!_uuid(fileId) || !_digest(sha256) || fileVersion < 1 || byteSize < 1) {
      throw const FormatException('Invalid document evidence');
    }
  }
}

class ApplicationDocument {
  final String id, requirementId;
  final ApplicationDocumentFile file;
  final bool usable;
  final DateTime? removedAt;
  final String? replacedById;
  final ApplicationDocumentEvidence? evidence;
  bool get active => removedAt == null && replacedById == null;
  bool get waiting =>
      {'uploading', 'quarantined', 'scanning'}.contains(file.state);
  ApplicationDocument.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      requirementId = json['requirement_id'] as String,
      file = ApplicationDocumentFile.fromJson(applicationObject(json['file'])),
      usable = json['usable'] as bool,
      removedAt = json['removed_at'] == null
          ? null
          : DateTime.parse(json['removed_at'] as String),
      replacedById = json['replaced_by_id'] as String?,
      evidence = json['submitted_evidence'] == null
          ? null
          : ApplicationDocumentEvidence.fromJson(
              applicationObject(json['submitted_evidence']),
            ) {
    if (!_uuid(id) ||
        !_uuid(requirementId) ||
        file.resourceId != id ||
        (replacedById != null && !_uuid(replacedById)) ||
        (evidence != null &&
            (evidence!.fileId != file.id ||
                evidence!.sha256 != file.sha256 ||
                evidence!.byteSize != file.byteSize))) {
      throw const FormatException('Invalid document binding');
    }
  }
}

class ApplicationDocumentsBatch {
  final String applicationId;
  final int applicationVersion, maxUploadBytes;
  final bool collectionEnabled;
  final List<ApplicationDocumentRequirement> requirements;
  final List<ApplicationDocument> items;
  const ApplicationDocumentsBatch({
    required this.applicationId,
    required this.applicationVersion,
    required this.maxUploadBytes,
    required this.collectionEnabled,
    required this.requirements,
    required this.items,
  });
}

class ApplicationDocumentResult {
  final int applicationVersion;
  final ApplicationDocument document;
  ApplicationDocumentResult.fromJson(Map<String, dynamic> json)
    : applicationVersion = json['application_version'] as int,
      document = ApplicationDocument.fromJson(
        applicationObject(json['document']),
      ) {
    if (applicationVersion < 1) {
      throw const FormatException('Invalid application version');
    }
  }
}

/// The fresh authorized metadata labels the bytes verified by this download.
class VerifiedApplicationDownload implements PrivateSnapshot {
  final PrivateSnapshot snapshot;
  final ApplicationDocument document;
  const VerifiedApplicationDownload(this.snapshot, this.document);
  @override
  String get id => snapshot.id;
  @override
  String get mediaType => snapshot.mediaType;
  @override
  String get sha256 => snapshot.sha256;
  @override
  int get byteSize => snapshot.byteSize;
  @override
  Future<void> verify() => snapshot.verify();
  @override
  Stream<List<int>> openRead() => snapshot.openRead();
  @override
  Future<void> dispose() => snapshot.dispose();
}

/// An in-memory immutable command: no names, provider URIs or paths are retained.
class DocumentIntent {
  final Map<String, Object> body;
  final PrivateSnapshot snapshot;
  final bool Function()? mayRegister;
  String get requestId => body['client_request_id'] as String;
  String get requirementId => body['requirement_id'] as String;
  String? get replacesId => body['replaces_document_id'] as String?;
  DocumentIntent({
    required this.snapshot,
    required int expectedVersion,
    required String requirementId,
    String? replacesId,
    this.mayRegister,
  }) : body = Map.unmodifiable({
         'expected_version': expectedVersion,
         'client_request_id': _newRequestId(),
         'requirement_id': requirementId,
         'media_type': snapshot.mediaType,
         'byte_size': snapshot.byteSize,
         'sha256': snapshot.sha256,
         'replaces_document_id': ?replacesId,
       });
  static String _newRequestId() {
    final random = Random.secure();
    final bytes = List.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    final hex = bytes
        .map((value) => value.toRadixString(16).padLeft(2, '0'))
        .join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }
}

class ApplicationDocumentsRepository {
  final DomainApi api;
  final FileTransport transport;
  ApplicationDocumentsRepository(this.api, this.transport);
  String _root(String org, String app) {
    if (!_uuid(org) || !_uuid(app)) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    return '/applications/organizations/$org/applications/$app/documents';
  }

  T _decode<T>(T Function() read, {bool command = false}) {
    try {
      return read();
    } catch (_) {
      throw ApiFailure(
        'invalid_response',
        kind: ApiFailureKind.invalidResponse,
        outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
      );
    }
  }

  ApplicationDocumentResult _result(
    Object? value,
    String org, {
    String? documentId,
    bool command = false,
  }) => _decode(() {
    final result = ApplicationDocumentResult.fromJson(applicationObject(value));
    if (result.document.file.organizationId != org ||
        (documentId != null && result.document.id != documentId)) {
      throw const FormatException();
    }
    return result;
  }, command: command);

  Future<ApplicationDocumentsBatch> list(String org, String app) async {
    final root = _root(org, app);
    int? version, ceiling;
    bool? enabled;
    List<ApplicationDocumentRequirement>? requirements;
    final items = <ApplicationDocument>[],
        ids = <String>{},
        cursors = <String>{};
    String? cursor;
    do {
      final value = await api.get(
        root,
        queryParameters: {'limit': 100, 'cursor': ?cursor},
      );
      final data = _decode(() => applicationObject(value));
      _decode(() {
        final pageVersion = data['application_version'] as int;
        final pageCeiling = data['max_upload_bytes'] as int;
        final pageEnabled = data['collection_enabled'] as bool;
        if (data['application_id'] != app ||
            pageVersion < 1 ||
            pageCeiling < 1 ||
            (version != null &&
                (version != pageVersion ||
                    ceiling != pageCeiling ||
                    enabled != pageEnabled))) {
          throw const FormatException();
        }
        version = pageVersion;
        ceiling = pageCeiling;
        enabled = pageEnabled;
        requirements ??= (data['document_requirements'] as List)
            .map(
              (value) => ApplicationDocumentRequirement.fromJson(
                applicationObject(value),
              ),
            )
            .toList();
        if (requirements!.length > 20 ||
            requirements!.any(
              (rule) => !_uuid(rule.id) || !_uuid(rule.policyId),
            ) ||
            requirements!.map((rule) => rule.id).toSet().length !=
                requirements!.length) {
          throw const FormatException();
        }
        for (final value in data['items'] as List) {
          final item = ApplicationDocument.fromJson(applicationObject(value));
          final maximumBindings = requirements!.fold<int>(
            0,
            (sum, rule) => sum + rule.maxFiles,
          );
          if (items.length >= maximumBindings ||
              !ids.add(item.id) ||
              item.file.organizationId != org ||
              !requirements!.any((rule) => rule.id == item.requirementId)) {
            throw const FormatException();
          }
          items.add(item);
        }
        cursor = data['next_cursor'] as String?;
        if (cursor != null && (!_uuid(cursor) || !cursors.add(cursor!))) {
          throw const FormatException();
        }
      });
    } while (cursor != null);
    return ApplicationDocumentsBatch(
      applicationId: app,
      applicationVersion: version!,
      maxUploadBytes: ceiling!,
      collectionEnabled: enabled!,
      requirements: List.unmodifiable(requirements!),
      items: List.unmodifiable(items),
    );
  }

  Future<ApplicationDocumentResult> detail(
    String org,
    String app,
    String documentId,
  ) async {
    if (!_uuid(documentId)) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    return _result(
      await api.get('${_root(org, app)}/$documentId'),
      org,
      documentId: documentId,
    );
  }

  Future<ApplicationDocumentResult> register(
    String org,
    String app,
    DocumentIntent intent,
  ) async {
    await intent.snapshot.verify();
    if (intent.mayRegister?.call() == false) {
      throw const ApiFailure(
        'private_file_cancelled',
        kind: ApiFailureKind.cancelled,
        outcome: CommandOutcome.notSent,
      );
    }
    final result = _result(
      await api.post(_root(org, app), data: intent.body),
      org,
      command: true,
    );
    final file = result.document.file;
    if (file.clientRequestId != intent.requestId ||
        result.document.requirementId != intent.requirementId ||
        file.mediaType != intent.snapshot.mediaType ||
        file.sha256 != intent.snapshot.sha256 ||
        file.byteSize != intent.snapshot.byteSize) {
      throw const ApiFailure(
        'invalid_response',
        kind: ApiFailureKind.invalidResponse,
        outcome: CommandOutcome.uncertain,
      );
    }
    return result;
  }

  Future<ApplicationDocumentResult> upload(
    String org,
    String app,
    ApplicationDocument document,
    PrivateSnapshot snapshot, {
    CancelToken? cancelToken,
  }) async {
    if (snapshot.mediaType != document.file.mediaType ||
        snapshot.sha256 != document.file.sha256 ||
        snapshot.byteSize != document.file.byteSize) {
      throw const ApiFailure(
        'file_proof_mismatch',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    return _result(
      await transport.upload(
        '${_root(org, app)}/${document.id}/content',
        snapshot: snapshot,
        expectedVersion: document.file.version,
        cancelToken: cancelToken,
      ),
      org,
      documentId: document.id,
      command: true,
    );
  }

  Future<ApplicationDocumentResult> remove(
    String org,
    String app,
    ApplicationDocument document,
    int expectedVersion,
  ) async => _result(
    await api.delete(
      '${_root(org, app)}/${document.id}',
      data: {'expected_version': expectedVersion},
    ),
    org,
    documentId: document.id,
    command: true,
  );
  Future<PrivateSnapshot> download(
    String org,
    String app,
    ApplicationDocument document,
    PrivateFileScope scope, {
    CancelToken? cancelToken,
  }) async {
    final current = (await detail(org, app, document.id)).document;
    if (!current.active || !current.usable) {
      throw const ApiFailure(
        'file_not_available',
        kind: ApiFailureKind.conflict,
      );
    }
    final evidence = current.evidence;
    final snapshot = await transport.download(
      '${_root(org, app)}/${current.id}/content',
      scope: scope,
      proof: FileProof(
        mediaType: current.file.mediaType,
        byteSize: evidence?.byteSize ?? current.file.byteSize,
        sha256: evidence?.sha256 ?? current.file.sha256,
      ),
      cancelToken: cancelToken,
    );
    return VerifiedApplicationDownload(snapshot, current);
  }
}
