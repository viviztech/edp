import 'dart:async';

import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/core/files/file_transport.dart';
import 'package:edp_mobile/core/files/private_files.dart';
import 'package:edp_mobile/features/applications/application_documents.dart';
import 'package:edp_mobile/features/applications/application_models.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import 'file_transport_test.dart'
    show FileTestSnapshot, FileTestScope, FileTestTokens, cryptoHash;
import 'fixtures/application_fixture.dart';

const documentRequirementId = '99999999-9999-4999-8999-999999999999';
const documentId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const documentFileId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const documentRequestId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
const documentOtherId = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';

Map<String, Object> documentRequirementJson({
  int maxFiles = 2,
  int policyMaxFiles = 2,
  String id = documentRequirementId,
  String policyId = applicationFormId,
}) => {
  'id': id,
  'label_en': 'Synthetic document',
  'label_ta': 'சோதனை ஆவணம்',
  'instructions_en': 'Synthetic only',
  'instructions_ta': 'சோதனை மட்டும்',
  'min_files': 1,
  'max_files': maxFiles,
  'file_policy': {
    'id': policyId,
    'notice_en': 'Synthetic files only',
    'notice_ta': 'சோதனைக் கோப்புகள் மட்டும்',
    'max_file_bytes': 1024,
    'max_upload_bytes': 512,
    'max_files': policyMaxFiles,
    'retention_days': 30,
    'rejected_retention_days': 2,
    'allowed_mime_types': ['text/plain'],
  },
};

ApplicationDocumentRequirement documentRequirement({
  int maxFiles = 2,
  int policyMaxFiles = 2,
}) => ApplicationDocumentRequirement.fromJson(
  documentRequirementJson(maxFiles: maxFiles, policyMaxFiles: policyMaxFiles),
);

Map<String, dynamic> documentJson({
  String id = documentId,
  String state = 'pending',
  bool usable = false,
  int fileVersion = 1,
  String org = applicationOrg,
  String requestId = documentRequestId,
  bool removed = false,
  bool frozen = false,
}) => {
  'id': id,
  'requirement_id': documentRequirementId,
  'usable': usable,
  'removed_at': removed ? '2026-10-24T01:00:00Z' : null,
  'replaced_by_id': null,
  'file': {
    'id': documentFileId,
    'organization_id': org,
    'resource_id': id,
    'client_request_id': requestId,
    'media_type': 'text/plain',
    'sha256': cryptoHash([1, 2, 3]),
    'state': state,
    'byte_size': 3,
    'version': fileVersion,
    'scan_attempts': 0,
    'failure_code': null,
    'retention_until': '2026-11-24T00:00:00Z',
    'legal_hold': false,
    'evidence_frozen': frozen,
    'purpose': 'application_document',
  },
  'submitted_evidence': frozen
      ? {
          'file_id': documentFileId,
          'file_version': 4,
          'byte_size': 3,
          'sha256': cryptoHash([1, 2, 3]),
          'frozen_at': '2026-10-24T02:00:00Z',
        }
      : null,
};

ApplicationDocument document({
  String id = documentId,
  String state = 'pending',
  bool usable = false,
  int fileVersion = 1,
  bool removed = false,
  bool frozen = false,
}) => ApplicationDocument.fromJson(
  documentJson(
    id: id,
    state: state,
    usable: usable,
    fileVersion: fileVersion,
    removed: removed,
    frozen: frozen,
  ),
);

ApplicationDocumentResult documentResult({
  int version = 2,
  String state = 'pending',
  bool removed = false,
  bool usable = false,
  int fileVersion = 1,
  String requestId = documentRequestId,
}) => ApplicationDocumentResult.fromJson({
  'application_version': version,
  'document': documentJson(
    state: state,
    removed: removed,
    usable: usable,
    fileVersion: fileVersion,
    requestId: requestId,
  ),
});

Map<String, Object?> _page({
  int version = 1,
  List<Map<String, dynamic>> items = const [],
  String? cursor,
  List<Map<String, Object>>? requirements,
}) => {
  'application_id': applicationId,
  'application_version': version,
  'max_upload_bytes': 256,
  'collection_enabled': true,
  'document_requirements': requirements ?? [documentRequirementJson()],
  'items': items,
  'next_cursor': cursor,
};

class _Api extends DomainApi {
  _Api() : super(AuthRepository(Dio(), FileTestTokens()));
  final calls = <(String, String, Object?)>[];
  late FutureOr<Object?> Function(String, String, Object?) handler;
  @override
  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    calls.add(('GET', path, queryParameters));
    return handler('GET', path, queryParameters);
  }

  @override
  Future<dynamic> post(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    calls.add(('POST', path, data));
    return handler('POST', path, data);
  }

  @override
  Future<dynamic> delete(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    calls.add(('DELETE', path, data));
    return handler('DELETE', path, data);
  }
}

class _Transport extends FileTransport {
  _Transport() : super(AuthRepository(Dio(), FileTestTokens()));
  int downloads = 0;
  FileProof? proof;
  String? path;
  @override
  Future<PrivateSnapshot> download(
    String typedPath, {
    required PrivateFileScope scope,
    required FileProof proof,
    CancelToken? cancelToken,
  }) async {
    downloads++;
    this.proof = proof;
    path = typedPath;
    return FileTestSnapshot([1, 2, 3]);
  }
}

void main() {
  test(
    'document list follows bounded cursor pages and enforces immutable aggregate identity',
    () async {
      final api = _Api();
      api.handler = (_, _, query) => (query as Map)['cursor'] == null
          ? _page(items: [documentJson()], cursor: documentOtherId)
          : _page(items: [documentJson(id: documentOtherId)]);
      final batch = await ApplicationDocumentsRepository(
        api,
        _Transport(),
      ).list(applicationOrg, applicationId);
      expect(batch.items.map((d) => d.id), [documentId, documentOtherId]);
      expect(api.calls.map((c) => (c.$3 as Map)['limit']), [100, 100]);
      expect(() => batch.items.clear(), throwsUnsupportedError);
      expect(() => batch.requirements.clear(), throwsUnsupportedError);
    },
  );

  test(
    'list rejects foreign organization, unknown requirement and repeated page cursor',
    () async {
      final api = _Api();
      final repository = ApplicationDocumentsRepository(api, _Transport());
      for (final value in [
        _page(items: [documentJson(org: applicationOtherOrg)]),
        _page(
          items: [
            {...documentJson(), 'requirement_id': documentOtherId},
          ],
        ),
        {..._page(), 'application_id': applicationOtherOrg},
        _page(cursor: documentOtherId),
      ]) {
        api.handler = (_, _, _) => value;
        await expectLater(
          repository.list(applicationOrg, applicationId),
          throwsA(isA<ApiFailure>()),
        );
      }
    },
  );

  test(
    'valid requirements can paginate more than one hundred owned bindings',
    () async {
      String id(int index) =>
          '00000000-0000-4000-8000-${index.toRadixString(16).padLeft(12, '0')}';
      final rules = [
        documentRequirementJson(maxFiles: 100, policyMaxFiles: 100),
        documentRequirementJson(
          maxFiles: 100,
          policyMaxFiles: 100,
          id: documentOtherId,
          policyId: documentOtherId,
        ),
      ];
      final bindings = List.generate(101, (index) {
        final value = documentJson(id: id(index + 1));
        value['requirement_id'] = index < 100
            ? documentRequirementId
            : documentOtherId;
        final file = value['file'] as Map<String, dynamic>;
        file['id'] = id(index + 1001);
        file['client_request_id'] = id(index + 2001);
        return value;
      });
      final api = _Api()
        ..handler = (_, _, query) => (query as Map)['cursor'] == null
            ? _page(
                items: bindings.take(100).toList(),
                requirements: rules,
                cursor: id(100),
              )
            : _page(items: bindings.skip(100).toList(), requirements: rules);
      final batch = await ApplicationDocumentsRepository(
        api,
        _Transport(),
      ).list(applicationOrg, applicationId);
      expect(batch.items, hasLength(101));
      expect(batch.items.last.requirementId, documentOtherId);
      expect(api.calls, hasLength(2));
    },
  );

  test(
    'pagination refuses a version change and duplicate document IDs',
    () async {
      final api = _Api();
      final repository = ApplicationDocumentsRepository(api, _Transport());
      var second = _page(version: 2);
      api.handler = (_, _, query) => (query as Map)['cursor'] == null
          ? _page(items: [documentJson()], cursor: documentOtherId)
          : second;
      await expectLater(
        repository.list(applicationOrg, applicationId),
        throwsA(isA<ApiFailure>()),
      );
      second = _page(items: [documentJson()]);
      await expectLater(
        repository.list(applicationOrg, applicationId),
        throwsA(isA<ApiFailure>()),
      );
    },
  );

  test(
    'idempotent registration preserves exact command body and request UUID on explicit recovery',
    () async {
      final api = _Api();
      final snapshot = FileTestSnapshot([1, 2, 3]);
      final intent = DocumentIntent(
        snapshot: snapshot,
        expectedVersion: 1,
        requirementId: documentRequirementId,
      );
      var dropped = true;
      api.handler = (_, _, data) {
        if (dropped) {
          dropped = false;
          throw const ApiFailure(
            'request_timeout',
            kind: ApiFailureKind.timeout,
            outcome: CommandOutcome.uncertain,
          );
        }
        return {
          'application_version': 2,
          'document': documentJson(
            requestId: (data as Map)['client_request_id'] as String,
          ),
        };
      };
      final repository = ApplicationDocumentsRepository(api, _Transport());
      await expectLater(
        repository.register(applicationOrg, applicationId, intent),
        throwsA(isA<ApiFailure>()),
      );
      expect(api.calls, hasLength(1));
      final recovered = await repository.register(
        applicationOrg,
        applicationId,
        intent,
      );
      expect(recovered.document.file.clientRequestId, intent.requestId);
      expect(identical(api.calls[0].$3, api.calls[1].$3), isTrue);
      expect(snapshot.verifications, 2);
      expect(() => intent.body['byte_size'] = 4, throwsUnsupportedError);
      expect(
        api.calls.first.$2,
        '/applications/organizations/$applicationOrg/applications/$applicationId/documents',
      );
    },
  );

  test(
    'malformed or foreign successful command response is uncertain',
    () async {
      final api = _Api();
      final repository = ApplicationDocumentsRepository(api, _Transport());
      final intent = DocumentIntent(
        snapshot: FileTestSnapshot([1, 2, 3]),
        expectedVersion: 1,
        requirementId: documentRequirementId,
      );
      for (final value in [
        {
          'application_version': 2,
          'document': documentJson(requestId: documentRequestId),
        },
        {
          'application_version': 2,
          'document': documentJson(org: applicationOtherOrg),
        },
        {'invalid': true},
      ]) {
        api.handler = (_, _, _) => value;
        await expectLater(
          repository.register(applicationOrg, applicationId, intent),
          throwsA(
            isA<ApiFailure>().having((e) => e.uncertain, 'uncertain', isTrue),
          ),
        );
      }
      expect(api.calls, hasLength(3));
    },
  );

  test(
    'removal pins the application version and exact typed document identity',
    () async {
      final api = _Api()
        ..handler = (_, _, _) => {
          'application_version': 8,
          'document': documentJson(removed: true),
        };
      final result = await ApplicationDocumentsRepository(
        api,
        _Transport(),
      ).remove(applicationOrg, applicationId, document(), 7);
      expect(api.calls.single.$1, 'DELETE');
      expect(
        api.calls.single.$2,
        '/applications/organizations/$applicationOrg/applications/$applicationId/documents/$documentId',
      );
      expect(api.calls.single.$3, {'expected_version': 7});
      expect(result.document.active, isFalse);
    },
  );

  test(
    'download reauthorizes detail and uses frozen evidence after file version advances',
    () async {
      final api = _Api()
        ..handler = (_, _, _) => {
          'application_version': 8,
          'document': documentJson(
            state: 'clean',
            usable: true,
            fileVersion: 9,
            frozen: true,
          ),
        };
      final transport = _Transport();
      final repository = ApplicationDocumentsRepository(api, transport);
      final stale = document(
        state: 'clean',
        usable: true,
        fileVersion: 4,
        frozen: true,
      );
      await repository.download(
        applicationOrg,
        applicationId,
        stale,
        FileTestScope(),
      );
      expect(api.calls.single.$1, 'GET');
      expect(api.calls.single.$2.endsWith('/$documentId'), isTrue);
      expect(
        transport.path,
        '/applications/organizations/$applicationOrg/applications/$applicationId/documents/$documentId/content',
      );
      expect(transport.proof!.sha256, stale.evidence!.sha256);
      expect(transport.proof!.byteSize, stale.evidence!.byteSize);
      final current = ApplicationDocument.fromJson(
        documentJson(
          state: 'clean',
          usable: true,
          fileVersion: 9,
          frozen: true,
        ),
      );
      expect(current.evidence!.fileVersion, 4);
      expect(current.file.version, 9);
    },
  );

  test(
    'clean label without current usable authorization never opens byte transport',
    () async {
      final api = _Api()
        ..handler = (_, _, _) => {
          'application_version': 2,
          'document': documentJson(state: 'clean', usable: false),
        };
      final transport = _Transport();
      await expectLater(
        ApplicationDocumentsRepository(api, transport).download(
          applicationOrg,
          applicationId,
          document(state: 'clean', usable: true),
          FileTestScope(),
        ),
        throwsA(isA<ApiFailure>()),
      );
      expect(transport.downloads, 0);
    },
  );
}
