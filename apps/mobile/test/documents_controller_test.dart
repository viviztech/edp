import 'dart:async';

import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/core/files/file_transport.dart';
import 'package:edp_mobile/core/files/private_files.dart';
import 'package:edp_mobile/features/applications/application_documents.dart';
import 'package:edp_mobile/features/applications/application_models.dart';
import 'package:edp_mobile/features/applications/documents_controller.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import 'application_documents_test.dart'
    show
        document,
        documentResult,
        documentRequirement,
        documentRequirementJson,
        documentRequirementId,
        documentOtherId,
        documentId;
import 'file_transport_test.dart'
    show FileTestScope, FileTestSnapshot, FileTestTokens;
import 'fixtures/application_fixture.dart';

class _Repository extends ApplicationDocumentsRepository {
  _Repository()
    : super(
        DomainApi(AuthRepository(Dio(), FileTestTokens())),
        FileTransport(AuthRepository(Dio(), FileTestTokens())),
      );
  int lists = 0, registers = 0, uploads = 0, details = 0, removals = 0;
  List<ApplicationDocument> items = [];
  List<ApplicationDocumentRequirement> requirements = [documentRequirement()];
  int version = 1;
  bool enabled = true;
  Object? registerFailure, uploadFailure, removeFailure, listFailure;
  final intents = <DocumentIntent>[];
  final operations = <String>[];
  ApplicationDocumentResult? detailResult, uploadResult, removeResult;
  Completer<ApplicationDocumentsBatch>? delayedList;
  @override
  Future<ApplicationDocumentsBatch> list(String org, String app) async {
    lists++;
    operations.add('list');
    if (listFailure != null) throw listFailure!;
    if (delayedList != null) return delayedList!.future;
    return ApplicationDocumentsBatch(
      applicationId: app,
      applicationVersion: version,
      maxUploadBytes: 256,
      collectionEnabled: enabled,
      requirements: requirements,
      items: items,
    );
  }

  @override
  Future<ApplicationDocumentResult> register(
    String org,
    String app,
    DocumentIntent intent,
  ) async {
    registers++;
    operations.add('register');
    intents.add(intent);
    if (registerFailure != null) throw registerFailure!;
    return documentResult(version: ++version, requestId: intent.requestId);
  }

  @override
  Future<ApplicationDocumentResult> upload(
    String org,
    String app,
    ApplicationDocument value,
    PrivateSnapshot snapshot, {
    CancelToken? cancelToken,
  }) async {
    uploads++;
    operations.add('upload');
    if (uploadFailure != null) throw uploadFailure!;
    return uploadResult ??
        documentResult(version: version, state: 'quarantined', fileVersion: 2);
  }

  @override
  Future<ApplicationDocumentResult> detail(
    String org,
    String app,
    String id,
  ) async {
    details++;
    operations.add('detail');
    return detailResult ?? documentResult(version: version);
  }

  @override
  Future<ApplicationDocumentResult> remove(
    String org,
    String app,
    ApplicationDocument value,
    int expectedVersion,
  ) async {
    removals++;
    operations.add('remove');
    expect(expectedVersion, version);
    if (removeFailure != null) throw removeFailure!;
    return removeResult ?? documentResult(version: ++version, removed: true);
  }
}

DocumentsController _controller(_Repository repository, FileTestScope scope) =>
    DocumentsController(
      repository,
      scope,
      organizationId: applicationOrg,
      applicationId: applicationId,
      applicationVersion: 1,
      requirements: repository.requirements,
      collectionEnabled: true,
      maxUploadBytes: 256,
    );

const _uncertain = ApiFailure(
  'request_timeout',
  kind: ApiFailureKind.timeout,
  outcome: CommandOutcome.uncertain,
);

void main() {
  test(
    'disabled collection and missing native scope prevent picking or issuing commands',
    () async {
      final repository = _Repository()..enabled = false;
      final scope = FileTestScope()..selected = FileTestSnapshot([1, 2, 3]);
      final controller = _controller(repository, scope);
      await controller.load();
      await controller.pick(documentRequirement());
      expect(controller.canCollect, isFalse);
      expect(scope.picks, 0);
      expect(repository.registers, 0);
      await controller.close();
      final unsupported = DocumentsController(
        repository,
        null,
        organizationId: applicationOrg,
        applicationId: applicationId,
        applicationVersion: 1,
        requirements: repository.requirements,
        collectionEnabled: true,
        maxUploadBytes: 256,
      );
      await unsupported.load();
      expect(unsupported.canCollect, isFalse);
      await unsupported.close();
    },
  );

  test(
    'intent loss requires explicit recovery of the identical body, never an automatic upload',
    () async {
      final repository = _Repository()..registerFailure = _uncertain;
      final snapshot = FileTestSnapshot([1, 2, 3]);
      final controller = _controller(
        repository,
        FileTestScope()..selected = snapshot,
      );
      await controller.load();
      await controller.pick(documentRequirement());
      final intent = controller.pendingIntent!;
      expect(repository.registers, 1);
      expect(repository.uploads, 0);
      expect(controller.blocksNavigation, isTrue);
      expect(controller.canCollect, isFalse);
      repository.registerFailure = null;
      await controller.recoverRegistration();
      expect(repository.registers, 2);
      expect(identical(repository.intents[0], repository.intents[1]), isTrue);
      expect(identical(repository.intents.last.body, intent.body), isTrue);
      expect(controller.canUpload, isTrue);
      expect(repository.uploads, 0);
      await controller.close();
      expect(snapshot.disposed, isTrue);
    },
  );

  test(
    'lost PUT must read current pending state before an explicit continuation',
    () async {
      final repository = _Repository()..uploadFailure = _uncertain;
      final snapshot = FileTestSnapshot([1, 2, 3]);
      final controller = _controller(
        repository,
        FileTestScope()..selected = snapshot,
      );
      await controller.load();
      await controller.pick(documentRequirement());
      await controller.uploadPending();
      expect(repository.uploads, 1);
      expect(controller.requiresReadback, isTrue);
      await controller.uploadPending();
      expect(repository.uploads, 1);
      await controller.reconcileUpload();
      expect(repository.details, 1);
      expect(controller.canUpload, isTrue);
      expect(repository.uploads, 1);
      repository.uploadFailure = null;
      await controller.uploadPending();
      expect(
        repository.operations.where((c) => c == 'upload' || c == 'detail'),
        ['upload', 'detail', 'upload'],
      );
      expect(snapshot.disposed, isTrue);
      expect(controller.hasPending, isFalse);
      await controller.close();
    },
  );

  test(
    'quarantined readback after a lost PUT releases bytes without sending a second PUT',
    () async {
      final repository = _Repository()..uploadFailure = _uncertain;
      final snapshot = FileTestSnapshot([1, 2, 3]);
      final controller = _controller(
        repository,
        FileTestScope()..selected = snapshot,
      );
      await controller.load();
      await controller.pick(documentRequirement());
      await controller.uploadPending();
      repository.detailResult = documentResult(
        version: 2,
        state: 'quarantined',
        fileVersion: 2,
      );
      await controller.reconcileUpload();
      expect(repository.uploads, 1);
      expect(controller.canUpload, isFalse);
      expect(controller.hasPending, isFalse);
      expect(snapshot.disposed, isTrue);
      expect(controller.ready, isFalse);
      await controller.close();
    },
  );

  test(
    'clean state without usable evidence never marks required documents ready',
    () async {
      final repository = _Repository()
        ..items = [document(state: 'clean', usable: false)];
      final controller = _controller(repository, FileTestScope());
      await controller.load();
      expect(controller.ready, isFalse);
      repository.items = [document(state: 'clean', usable: true)];
      await controller.load();
      expect(controller.ready, isTrue);
      await controller.close();
    },
  );

  test(
    'policy count ceiling blocks collection and submission readiness',
    () async {
      final repository = _Repository()
        ..requirements = [documentRequirement(maxFiles: 2, policyMaxFiles: 1)]
        ..items = [document(state: 'clean', usable: true)];
      final scope = FileTestScope()..selected = FileTestSnapshot([1, 2, 3]);
      final controller = _controller(repository, scope);
      await controller.load();
      await controller.pick(repository.requirements.single);
      expect(scope.picks, 0);
      expect(repository.registers, 0);
      repository.items = [
        document(state: 'clean', usable: true),
        document(
          id: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
          state: 'clean',
          usable: true,
        ),
      ];
      await controller.load();
      expect(controller.ready, isFalse);
      await controller.close();
    },
  );

  test(
    'picker result while backgrounded waits for foreground before registering once',
    () async {
      final selected = Completer<PrivateSnapshot?>();
      final entered = Completer<void>();
      final scope = FileTestScope()
        ..picker = () {
          entered.complete();
          return selected.future;
        };
      final repository = _Repository();
      final controller = _controller(repository, scope);
      await controller.load();
      final picking = controller.pick(documentRequirement());
      await entered.future;
      controller.pause();
      final snapshot = FileTestSnapshot([1, 2, 3]);
      selected.complete(snapshot);
      await Future<void>.delayed(Duration.zero);
      expect(repository.registers, 0);
      expect(snapshot.disposed, isFalse);
      expect(controller.hasPending, isFalse);
      await controller.resume();
      await picking;
      expect(repository.registers, 1);
      expect(repository.uploads, 0);
      expect(controller.canUpload, isTrue);
      await controller.close();
      expect(snapshot.disposed, isTrue);
    },
  );

  test(
    'a shared file policy count ceiling applies across different requirements',
    () async {
      final first = documentRequirement(maxFiles: 2, policyMaxFiles: 1);
      final second = ApplicationDocumentRequirement.fromJson(
        documentRequirementJson(
          maxFiles: 2,
          policyMaxFiles: 1,
          id: documentOtherId,
        ),
      );
      final repository = _Repository()
        ..requirements = [first, second]
        ..items = [document(state: 'clean', usable: true)];
      final scope = FileTestScope()..selected = FileTestSnapshot([1, 2, 3]);
      final controller = _controller(repository, scope);
      await controller.load();
      expect(repository.items.single.requirementId, documentRequirementId);
      expect(first.policyId, second.policyId);
      await controller.pick(second);
      expect(scope.picks, 0);
      expect(repository.registers, 0);
      expect(controller.ready, isFalse);
      await controller.close();
    },
  );

  test(
    'closing releases a picker waiting for foreground and disposes its private copy',
    () async {
      final selected = Completer<PrivateSnapshot?>();
      final entered = Completer<void>();
      final scope = FileTestScope()
        ..picker = () {
          entered.complete();
          return selected.future;
        };
      final repository = _Repository();
      final controller = _controller(repository, scope);
      await controller.load();
      final picking = controller.pick(documentRequirement());
      await entered.future;
      controller.pause();
      final snapshot = FileTestSnapshot([1, 2, 3]);
      selected.complete(snapshot);
      await Future<void>.delayed(Duration.zero);
      expect(snapshot.disposed, isFalse);
      await controller.close();
      await picking;
      expect(snapshot.disposed, isTrue);
      expect(repository.registers, 0);
      expect(repository.uploads, 0);
    },
  );

  test(
    'closing during picker disposes late bytes and never restores feature state',
    () async {
      final selected = Completer<PrivateSnapshot?>();
      final entered = Completer<void>();
      final scope = FileTestScope()
        ..picker = () {
          entered.complete();
          return selected.future;
        };
      final repository = _Repository();
      final controller = _controller(repository, scope);
      await controller.load();
      final picking = controller.pick(documentRequirement());
      await entered.future;
      await controller.close();
      final snapshot = FileTestSnapshot([1, 2, 3]);
      selected.complete(snapshot);
      await picking;
      expect(scope.closed, isTrue);
      expect(snapshot.disposed, isTrue);
      expect(repository.registers, 0);
      expect(controller.items, isEmpty);
    },
  );

  test(
    'uncertain removal allows only read reconciliation before a new removal decision',
    () async {
      final original = document(state: 'clean', usable: true);
      final repository = _Repository()
        ..items = [original]
        ..removeFailure = _uncertain;
      final controller = _controller(repository, FileTestScope());
      await controller.load();
      await controller.remove(original);
      expect(repository.removals, 1);
      expect(controller.uncertainRemoval?.id, documentId);
      await controller.remove(original);
      expect(repository.removals, 1);
      repository.detailResult = documentResult(version: 2, removed: true);
      await controller.reconcileRemoval();
      expect(repository.details, 1);
      expect(controller.items, isEmpty);
      expect(controller.uncertainRemoval, isNull);
      expect(repository.removals, 1);
      await controller.close();
    },
  );

  test(
    'regressed command aggregate version cannot replace already displayed document state',
    () async {
      final repository = _Repository();
      final controller = _controller(
        repository,
        FileTestScope()..selected = FileTestSnapshot([1, 2, 3]),
      );
      await controller.load();
      await controller.pick(documentRequirement());
      expect(controller.version, 2);
      repository.uploadResult = documentResult(
        version: 1,
        state: 'quarantined',
        fileVersion: 2,
      );
      await controller.uploadPending();
      expect(controller.failure?.kind, ApiFailureKind.conflict);
      expect(controller.items.single.file.state, 'pending');
      expect(controller.requiresReadback, isTrue);
      await controller.close();
    },
  );

  test(
    'process restart reselects only identical bytes for a current pending binding',
    () async {
      final repository = _Repository()..items = [document()];
      final snapshot = FileTestSnapshot([9, 9, 9]);
      final scope = FileTestScope()..selected = snapshot;
      final controller = _controller(repository, scope);
      await controller.load();
      await controller.reselectPending(repository.items.single);
      expect(repository.details, 1);
      expect(repository.registers, 0);
      expect(repository.uploads, 0);
      expect(controller.failure?.code, 'file_proof_mismatch');
      expect(controller.hasPending, isFalse);
      expect(snapshot.disposed, isTrue);
      await controller.close();
    },
  );

  testWidgets(
    'scan polling is bounded and pauses while the application is backgrounded',
    (tester) async {
      final repository = _Repository()
        ..items = [document(state: 'quarantined')];
      final controller = _controller(repository, FileTestScope());
      await controller.load();
      for (var index = 0; index < 8; index++) {
        await tester.pump(const Duration(seconds: 2));
      }
      expect(repository.lists, 6);
      controller.pause();
      await tester.pump(const Duration(seconds: 20));
      expect(repository.lists, 6);
      await controller.resume();
      expect(repository.lists, 7);
      controller.pause();
      await tester.pump(const Duration(seconds: 20));
      expect(repository.lists, 7);
      await controller.close();
    },
  );

  test(
    'a scalar version advance received during document load is retained and refreshed',
    () async {
      final repository = _Repository();
      final gate = Completer<ApplicationDocumentsBatch>();
      repository.delayedList = gate;
      final controller = _controller(repository, FileTestScope());
      final initial = controller.load();
      expect(controller.busy, isTrue);
      controller.syncApplicationVersion(3, editable: true);
      controller.syncApplicationVersion(2, editable: true);
      repository.delayedList = null;
      repository.version = 3;
      gate.complete(
        ApplicationDocumentsBatch(
          applicationId: applicationId,
          applicationVersion: 1,
          maxUploadBytes: 256,
          collectionEnabled: true,
          requirements: repository.requirements,
          items: [],
        ),
      );
      await initial;
      await Future<void>.delayed(Duration.zero);
      expect(controller.version, 3);
      expect(controller.loaded, isTrue);
      expect(repository.lists, 2);
      expect(controller.failure, isNull);
      await controller.close();
    },
  );
}
