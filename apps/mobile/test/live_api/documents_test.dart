import 'dart:async';
import 'dart:convert';

import 'package:crypto/crypto.dart' as crypto;
import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/files/file_transport.dart';
import 'package:edp_mobile/core/files/private_files.dart';
import 'package:edp_mobile/features/applications/application_documents.dart';
import 'package:edp_mobile/features/applications/application_models.dart';
import 'package:edp_mobile/features/applications/application_repository.dart';
import 'package:edp_mobile/features/applications/documents_controller.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

// A deliberately test-only byte adapter. The network/repositories are real;
// these small known synthetic bytes supply no file-provider/device evidence.
class _Snapshot implements PrivateSnapshot {
  @override
  final String mediaType;
  final List<int> bytes;
  bool disposed = false;
  _Snapshot(this.mediaType, List<int> source)
    : bytes = List.unmodifiable(source);
  @override
  String get id => '11111111-1111-4111-8111-111111111111';
  @override
  int get byteSize => bytes.length;
  @override
  String get sha256 => crypto.sha256.convert(bytes).toString();
  @override
  Future<void> verify() async {
    if (disposed) throw StateError('Synthetic snapshot closed');
  }

  @override
  Stream<List<int>> openRead() async* {
    await verify();
    yield bytes;
  }

  @override
  Future<void> dispose() async => disposed = true;
}

class _Scope implements PrivateFileScope {
  @override
  bool closed = false;
  _Snapshot? selection;
  @override
  Future<PrivateSnapshot?> pick({
    required Set<String> allowedMediaTypes,
    required int maxBytes,
  }) async {
    if (closed) throw StateError('Synthetic scope closed');
    final selected = selection;
    selection = null;
    if (selected == null) return null;
    expect(allowedMediaTypes, contains(selected.mediaType));
    expect(selected.byteSize, lessThanOrEqualTo(maxBytes));
    return selected;
  }

  @override
  Future<PrivateSink> beginDownload({
    required String mediaType,
    required int maxBytes,
    required int expectedByteSize,
    required String expectedSha256,
  }) async => _Sink(mediaType, expectedByteSize, expectedSha256);
  @override
  Future<void> close() async => closed = true;
}

class _Sink implements PrivateSink {
  final String mediaType, expectedSha256;
  final int expectedByteSize;
  final List<int> bytes = [];
  bool terminal = false;
  _Sink(this.mediaType, this.expectedByteSize, this.expectedSha256);
  @override
  Future<void> append(List<int> chunk) async {
    expect(terminal, isFalse);
    expect(chunk.length, lessThanOrEqualTo(channelChunkBytes));
    bytes.addAll(chunk);
    expect(bytes.length, lessThanOrEqualTo(expectedByteSize));
  }

  @override
  Future<PrivateSnapshot> finish() async {
    terminal = true;
    expect(bytes.length, expectedByteSize);
    expect(crypto.sha256.convert(bytes).toString(), expectedSha256);
    return _Snapshot(mediaType, bytes);
  }

  @override
  Future<void> abort() async {
    terminal = true;
    bytes.clear();
  }
}

ApplicationDocumentsRepository _documents(LiveApiClient client) =>
    ApplicationDocumentsRepository(client.api, FileTransport(client.identity));

_Snapshot _payload(LiveApiFixture fixture, String type) => _Snapshot(
  type,
  base64Decode(jsonObject(fixture.documentIntake['payloads'])[type] as String),
);

Future<ApplicationDocument> _scan(
  LiveApiFixture fixture,
  ApplicationDocumentsRepository repository,
  ApplicationRecord app,
  ApplicationDocument document, {
  bool infected = false,
}) async {
  await fixture.requestSyntheticScan(document.file.id, infected: infected);
  final deadline = DateTime.now().add(const Duration(seconds: 10));
  while (DateTime.now().isBefore(deadline)) {
    final current = (await repository.detail(
      fixture.organizationId,
      app.id,
      document.id,
    )).document;
    if (current.file.state == (infected ? 'infected' : 'clean')) return current;
    await Future<void>.delayed(const Duration(milliseconds: 100));
  }
  throw StateError('Controlled synthetic scan timeout');
}

Future<ApplicationRecord> _start(
  LiveApiFixture fixture,
  LiveApiClient client,
  String name,
) async {
  final repository = ApplicationRepository(client.api);
  final app = await repository.start(
    fixture.organizationId,
    fixture.documentIntake['${name}_cycle_id'] as String,
  );
  return repository.save(fixture.organizationId, app, {
    app.form.fields.single.id: 'Synthetic proposal',
  });
}

void main() {
  group('M02 synthetic documents/API acceptance', () {
    late LiveApiFixture fixture;
    setUpAll(() => fixture = LiveApiFixture.load());

    test(
      'five allowed formats stay quarantined until controlled scan, replace/remove, freeze and download exact evidence',
      () async {
        final client = await fixture.signIn('applicant');
        addTearDown(client.close);
        final applications = ApplicationRepository(client.api);
        final documents = _documents(client);
        var app = await _start(fixture, client, 'workflow');
        final org = fixture.organizationId, rule = app.form.documents.single;
        expect(app.form.collectionEnabled, isTrue);
        expect(rule.mimeTypes.toSet(), privateMediaTypes);
        expect(rule.effectiveUploadLimit(app.form.maxUploadBytes), 1024);
        final accepted = app.form.acknowledgements
            .map((item) => item.id)
            .toSet();
        await expectLater(
          applications.submit(org, app, accepted),
          throwsA(apiFailureWithStatus(422)),
        );
        final uploaded = <ApplicationDocument>[];
        for (final type in privateMediaTypes) {
          final snapshot = _payload(fixture, type);
          final batch = await documents.list(org, app.id);
          final intent = DocumentIntent(
            snapshot: snapshot,
            expectedVersion: batch.applicationVersion,
            requirementId: rule.id,
          );
          final registered = await documents.register(org, app.id, intent);
          expect(registered.document.file.state, 'pending');
          final result = await documents.upload(
            org,
            app.id,
            registered.document,
            snapshot,
          );
          expect(result.document.file.state, 'quarantined');
          expect(result.document.usable, isFalse);
          final scope = _Scope();
          await expectLater(
            documents.download(org, app.id, result.document, scope),
            throwsA(isA<ApiFailure>()),
          );
          uploaded.add(result.document);
        }
        app = await applications.read(org, app.cycleId!);
        expect((await applications.readiness(org, app)).ready, isFalse);
        await expectLater(
          applications.submit(org, app, accepted),
          throwsA(apiFailureWithStatus(422)),
        );
        for (var i = 0; i < uploaded.length; i++) {
          uploaded[i] = await _scan(fixture, documents, app, uploaded[i]);
          expect(uploaded[i].usable, isTrue);
        }
        var batch = await documents.list(org, app.id);
        expect((await applications.readiness(org, app)).ready, isTrue);
        final removed = await documents.remove(
          org,
          app.id,
          uploaded.removeLast(),
          batch.applicationVersion,
        );
        expect(removed.document.active, isFalse);
        final old = uploaded.removeLast();
        batch = await documents.list(org, app.id);
        final replacementBytes = _payload(fixture, old.file.mediaType);
        final replacementIntent = DocumentIntent(
          snapshot: replacementBytes,
          expectedVersion: batch.applicationVersion,
          requirementId: rule.id,
          replacesId: old.id,
        );
        final replacement = await documents.register(
          org,
          app.id,
          replacementIntent,
        );
        final superseded = (await documents.detail(
          org,
          app.id,
          old.id,
        )).document;
        expect(superseded.active, isFalse);
        expect(superseded.replacedById, replacement.document.id);
        final replacementUpload = await documents.upload(
          org,
          app.id,
          replacement.document,
          replacementBytes,
        );
        uploaded.add(
          await _scan(fixture, documents, app, replacementUpload.document),
        );
        app = await applications.read(org, app.cycleId!);
        final receipt = await applications.submit(org, app, accepted);
        expect(receipt.state, 'submitted');
        batch = await documents.list(org, app.id);
        final active = batch.items.where((item) => item.active).toList();
        expect(active.length, 4);
        for (final document in active) {
          expect(document.evidence, isNotNull);
          expect(document.file.evidenceFrozen, isTrue);
          expect(document.evidence!.sha256, document.file.sha256);
          expect(document.evidence!.byteSize, document.file.byteSize);
          final snapshot = await documents.download(
            org,
            app.id,
            document,
            _Scope(),
          );
          final bytes = await snapshot
              .openRead()
              .expand((chunk) => chunk)
              .toList();
          expect(bytes, _payload(fixture, document.file.mediaType).bytes);
          await snapshot.dispose();
        }
        await expectLater(
          documents.remove(org, app.id, active.first, batch.applicationVersion),
          throwsA(apiFailureWithStatus(409)),
        );
        final frozen = (await documents.detail(
          org,
          app.id,
          active.first.id,
        )).document;
        expect(
          frozen.evidence!.fileVersion,
          active.first.evidence!.fileVersion,
        );
        expect(frozen.evidence!.frozenAt, active.first.evidence!.frozenAt);
      },
    );

    test(
      'lost real intent, PUT and removal responses require explicit recovery and one byte write',
      () async {
        final client = await fixture.signIn('applicant');
        addTearDown(client.close);
        final app = await _start(fixture, client, 'lost');
        final documents = _documents(client), scope = _Scope();
        final controller = DocumentsController(
          documents,
          scope,
          organizationId: fixture.organizationId,
          applicationId: app.id,
          applicationVersion: app.version,
          requirements: app.form.documents,
          collectionEnabled: app.form.collectionEnabled,
          maxUploadBytes: app.form.maxUploadBytes,
        );
        addTearDown(controller.close);
        await controller.load();
        var intents = 0, puts = 0, removals = 0;
        var dropIntent = true, dropPut = true, dropRemoval = true;
        client.dio.interceptors.add(
          InterceptorsWrapper(
            onRequest: (options, handler) {
              if (options.method == 'POST' &&
                  options.path.endsWith('/documents')) {
                intents++;
              }
              if (options.method == 'PUT') puts++;
              if (options.method == 'DELETE') removals++;
              handler.next(options);
            },
            onResponse: (response, handler) {
              final request = response.requestOptions;
              final isIntent =
                  request.method == 'POST' &&
                  request.path.endsWith('/documents');
              if ((isIntent && dropIntent) ||
                  (request.method == 'PUT' && dropPut) ||
                  (request.method == 'DELETE' && dropRemoval)) {
                if (isIntent) dropIntent = false;
                if (request.method == 'PUT') dropPut = false;
                if (request.method == 'DELETE') dropRemoval = false;
                handler.reject(
                  DioException(
                    requestOptions: request,
                    type: DioExceptionType.receiveTimeout,
                  ),
                );
              } else {
                handler.next(response);
              }
            },
          ),
        );
        scope.selection = _payload(fixture, 'application/pdf');
        await controller.pick(app.form.documents.single);
        expect(controller.pendingIntent, isNotNull);
        expect(controller.pendingDocument, isNull);
        expect(controller.failure!.uncertain, isTrue);
        final request = controller.pendingIntent!.requestId;
        await controller.uploadPending();
        expect(puts, 0);
        await controller.recoverRegistration();
        expect(controller.pendingDocument!.file.clientRequestId, request);
        expect(intents, 2);
        expect(
          (await documents.list(fixture.organizationId, app.id)).items,
          hasLength(1),
        );
        await controller.uploadPending();
        expect(controller.requiresReadback, isTrue);
        await controller.uploadPending();
        expect(puts, 1);
        await controller.reconcileUpload();
        expect(controller.pendingIntent, isNull);
        expect(controller.items.single.file.state, 'quarantined');
        await controller.resume();
        expect(puts, 1);
        final current = await _scan(
          fixture,
          documents,
          app,
          controller.items.single,
        );
        await controller.load();
        await controller.remove(current);
        expect(controller.uncertainRemoval, isNotNull);
        await controller.remove(current);
        expect(removals, 1);
        await controller.reconcileRemoval();
        expect(controller.uncertainRemoval, isNull);
        expect(controller.items.where((item) => item.active), isEmpty);
        expect(removals, 1);
        expect(puts, 1);
      },
    );

    test(
      'server rejects stale versions, changed request UUID reuse and mismatched raw bytes; unsafe scan remains unusable',
      () async {
        final client = await fixture.signIn('applicant');
        addTearDown(client.close);
        final app = await _start(fixture, client, 'bounds');
        final documents = _documents(client), org = fixture.organizationId;
        final bytes = _payload(fixture, 'application/pdf');
        final intent = DocumentIntent(
          snapshot: bytes,
          expectedVersion: app.version,
          requirementId: app.form.documents.single.id,
        );
        final first = await documents.register(org, app.id, intent);
        final root =
            '/applications/organizations/$org/applications/${app.id}/documents';
        await expectLater(
          client.api.post(
            root,
            data: {...intent.body, 'byte_size': bytes.byteSize + 1},
          ),
          throwsA(apiFailureWithStatus(409)),
        );
        final stale = DocumentIntent(
          snapshot: bytes,
          expectedVersion: app.version,
          requirementId: app.form.documents.single.id,
        );
        await expectLater(
          documents.register(org, app.id, stale),
          throwsA(apiFailureWithStatus(409)),
        );
        await expectLater(
          documents.upload(
            org,
            app.id,
            first.document,
            _Snapshot('application/pdf', [1, 2, 3]),
          ),
          throwsA(
            isA<ApiFailure>().having(
              (e) => e.outcome,
              'outcome',
              CommandOutcome.notSent,
            ),
          ),
        );
        final content = '$root/${first.document.id}/content';
        await expectLater(
          client.identity.authenticatedRequest(
            content,
            method: 'PUT',
            data: Stream<List<int>>.value(bytes.bytes),
            bodyLength: bytes.byteSize,
            headers: {'content-type': 'image/png', 'if-match': '"1"'},
          ),
          throwsA(apiFailureWithStatus(415)),
        );
        final uploaded = await documents.upload(
          org,
          app.id,
          first.document,
          bytes,
        );
        final infected = await _scan(
          fixture,
          documents,
          app,
          uploaded.document,
          infected: true,
        );
        expect(infected.usable, isFalse);
        expect(infected.file.failureCode, 'malware_detected');
        expect(
          (await ApplicationRepository(client.api).readiness(org, app)).ready,
          isFalse,
        );
        await expectLater(
          documents.download(org, app.id, infected, _Scope()),
          throwsA(isA<ApiFailure>()),
        );
      },
    );

    test(
      'peer and other organization cannot list, register, read, upload, remove or download owner documents',
      () async {
        final owner = await fixture.signIn('applicant'),
            peer = await fixture.signIn('peer');
        addTearDown(owner.close);
        addTearDown(peer.close);
        final app = await _start(fixture, owner, 'scope');
        final documents = _documents(owner), org = fixture.organizationId;
        final bytes = _payload(fixture, 'text/plain');
        final intent = DocumentIntent(
          snapshot: bytes,
          expectedVersion: app.version,
          requirementId: app.form.documents.single.id,
        );
        final registered = await documents.register(org, app.id, intent);
        final uploaded = await documents.upload(
          org,
          app.id,
          registered.document,
          bytes,
        );
        final clean = await _scan(fixture, documents, app, uploaded.document);
        for (final entry in [
          (peer, org),
          (owner, fixture.otherOrganizationId),
        ]) {
          final repository = _documents(entry.$1), organization = entry.$2;
          await expectLater(
            repository.list(organization, app.id),
            throwsA(apiFailureWithStatus(404)),
          );
          await expectLater(
            repository.detail(organization, app.id, clean.id),
            throwsA(apiFailureWithStatus(404)),
          );
          await expectLater(
            repository.register(organization, app.id, intent),
            throwsA(apiFailureWithStatus(404)),
          );
          await expectLater(
            repository.upload(organization, app.id, clean, bytes),
            throwsA(apiFailureWithStatus(404)),
          );
          await expectLater(
            repository.remove(
              organization,
              app.id,
              clean,
              uploaded.applicationVersion,
            ),
            throwsA(apiFailureWithStatus(404)),
          );
          await expectLater(
            repository.download(organization, app.id, clean, _Scope()),
            throwsA(apiFailureWithStatus(404)),
          );
        }
      },
    );

    test('revoked session cannot initiate another private download', () async {
      final client = await fixture.signIn('applicant');
      final second = await fixture.signIn('applicant');
      addTearDown(client.close);
      addTearDown(second.close);
      final app = await _start(fixture, client, 'revoked');
      final documents = _documents(client), org = fixture.organizationId;
      final bytes = _payload(fixture, 'text/plain');
      final intent = DocumentIntent(
        snapshot: bytes,
        expectedVersion: app.version,
        requirementId: app.form.documents.single.id,
      );
      final registered = await documents.register(org, app.id, intent);
      final uploaded = await documents.upload(
        org,
        app.id,
        registered.document,
        bytes,
      );
      final clean = await _scan(fixture, documents, app, uploaded.document);
      final sessions = await second.identity.sessions();
      final old = sessions.where((item) => !item.current).toList();
      expect(old, isNotEmpty);
      for (final session in old) {
        await second.identity.revoke(session.id);
      }
      await expectLater(
        documents.download(org, app.id, clean, _Scope()),
        throwsA(isA<ApiFailure>()),
      );
      expect(client.tokens.hasRefreshToken, isFalse);
    });
  }, skip: liveAcceptanceSkipReason);
}
