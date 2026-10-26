import 'dart:async';

import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/features/applications/application_editor.dart';
import 'package:edp_mobile/features/applications/application_models.dart';
import 'package:edp_mobile/features/applications/application_repository.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fixtures/application_fixture.dart';

class _NoTokens implements TokenStore {
  @override
  Future<void> clear() async {}
  @override
  Future<String?> read() async => null;
  @override
  Future<void> write(String value) async {}
}

class EditorRepository extends ApplicationRepository {
  EditorRepository() : super(DomainApi(AuthRepository(Dio(), _NoTokens())));
  ApplicationRecord? server = applicationRecord();
  bool closed = false, lostSave = false, lostSubmit = false, lostStart = false;
  ApiFailure? readFailure, saveFailure;
  Completer<void>? saveGate;
  int saves = 0, submits = 0, starts = 0, reads = 0;

  @override
  Future<List<ApplicationCycle>> cycles(String org) async =>
      closed ? [] : [ApplicationCycle.fromJson(applicationCycleJson())];
  @override
  Future<ApplicationRecord> read(String org, String cycle) async {
    reads++;
    if (readFailure != null) throw readFailure!;
    if (server == null) {
      throw const ApiFailure(
        'not_found',
        kind: ApiFailureKind.notFound,
        statusCode: 404,
      );
    }
    return server!;
  }

  @override
  Future<ApplicationRecord> start(String org, String cycle) async {
    starts++;
    if (lostStart) {
      throw const ApiFailure(
        'request_timeout',
        kind: ApiFailureKind.timeout,
        outcome: CommandOutcome.uncertain,
      );
    }
    return server = applicationRecord();
  }

  @override
  Future<ApplicationRecord> save(
    String org,
    ApplicationRecord record,
    Map<String, String> answers,
  ) async {
    saves++;
    if (saveGate != null) await saveGate!.future;
    if (saveFailure != null) throw saveFailure!;
    if (server!.version != record.version) {
      throw const ApiFailure('version_conflict', kind: ApiFailureKind.conflict);
    }
    server = applicationRecord(
      version: record.version + 1,
      answer: answers[applicationField] ?? '',
    );
    if (lostSave) {
      throw const ApiFailure(
        'request_timeout',
        kind: ApiFailureKind.timeout,
        outcome: CommandOutcome.uncertain,
      );
    }
    return server!;
  }

  @override
  Future<ApplicationRecord> submit(
    String org,
    ApplicationRecord record,
    Set<String> accepted,
  ) async {
    submits++;
    server = applicationRecord(
      version: record.version + 1,
      answer: record.answers[applicationField] ?? '',
      state: 'submitted',
    );
    if (lostSubmit) {
      throw const ApiFailure(
        'request_timeout',
        kind: ApiFailureKind.timeout,
        outcome: CommandOutcome.uncertain,
      );
    }
    return server!;
  }

  @override
  Future<ApplicationReadiness> readiness(
    String org,
    ApplicationRecord record,
  ) async => ApplicationReadiness(record.version, true);
}

void main() {
  late EditorRepository repository;
  late ApplicationEditor editor;
  setUp(() {
    repository = EditorRepository();
    editor = ApplicationEditor(
      repository,
      organizationId: applicationOrg,
      cycleId: applicationCycle,
    );
  });
  tearDown(() => editor.dispose());

  test(
    'partial draft save and resume remain independent from acknowledgements',
    () async {
      await editor.load();
      expect(editor.canSubmit, isFalse);
      editor.setAnswer(applicationField, 'Partial proposal');
      expect(editor.blocksNavigation, isTrue);
      await editor.save();
      expect(editor.dirtyAnswers, isFalse);
      expect(editor.record!.version, 2);
      expect(editor.values[applicationField], 'Partial proposal');
      expect(editor.canSubmit, isFalse);
      editor.acknowledge(applicationDeclaration, true);
      editor.acknowledge(applicationConsent, true);
      expect(editor.canSubmit, isTrue);
    },
  );

  test(
    'lost save preserves text, reads exact state, and waits for explicit reconciliation',
    () async {
      await editor.load();
      editor.setAnswer(applicationField, 'My unsaved proposal');
      repository.lostSave = true;
      await editor.save();
      expect(editor.needsReview, isTrue);
      expect(editor.values[applicationField], 'My unsaved proposal');
      await editor.save();
      expect(repository.saves, 1);
      // Calling load must read back, never overwrite the pending local text.
      await editor.load();
      expect(editor.latest!.version, 2);
      expect(editor.values[applicationField], 'My unsaved proposal');
      expect(editor.canWrite, isFalse);
      await editor.chooseSaved(keepEdits: true);
      expect(editor.record!.version, 2);
      expect(editor.dirtyAnswers, isFalse);
      expect(repository.saves, 1);
    },
  );

  test(
    'second device conflict preserves both versions until explicit keep or discard',
    () async {
      await editor.load();
      editor.setAnswer(applicationField, 'Local proposal');
      repository.server = applicationRecord(
        version: 2,
        answer: 'Second device proposal',
      );
      await editor.save();
      expect(editor.failure!.kind, ApiFailureKind.conflict);
      await editor.reconcile();
      expect(editor.values[applicationField], 'Local proposal');
      expect(
        editor.latest!.answers[applicationField],
        'Second device proposal',
      );
      await editor.chooseSaved(keepEdits: true);
      expect(editor.record!.version, 2);
      expect(editor.dirtyAnswers, isTrue);
      await editor.save();
      expect(repository.server!.version, 3);
      expect(repository.server!.answers[applicationField], 'Local proposal');
    },
  );

  test(
    'lost submit becomes the authoritative receipt without a second submission',
    () async {
      repository.server = applicationRecord(
        version: 2,
        answer: 'Saved proposal',
      );
      await editor.load();
      editor.acknowledge(applicationDeclaration, true);
      editor.acknowledge(applicationConsent, true);
      repository.lostSubmit = true;
      await editor.submit();
      expect(editor.needsReview, isTrue);
      await editor.submit();
      expect(repository.submits, 1);
      await editor.reconcile();
      expect(editor.record!.state, 'submitted');
      expect(editor.record!.number, 'EDP-2026-00000001');
      expect(editor.record!.history.last.state, 'submitted');
      expect(editor.record!.accepted, hasLength(2));
      expect(editor.blocksNavigation, isFalse);
      expect(repository.submits, 1);
    },
  );

  test(
    'uncertain start requires readback; confirmed absence permits explicit retry',
    () async {
      repository.server = null;
      await editor.load();
      repository.lostStart = true;
      await editor.start();
      expect(editor.needsReview, isTrue);
      repository.readFailure = const ApiFailure(
        'offline',
        kind: ApiFailureKind.offline,
      );
      await editor.reconcile();
      expect(editor.needsReview, isTrue);
      await editor.start();
      expect(repository.starts, 1);
      repository.readFailure = null;
      await editor.reconcile();
      expect(editor.needsReview, isFalse);
      repository.lostStart = false;
      await editor.start();
      expect(repository.starts, 2);
      expect(editor.record!.id, applicationId);
    },
  );

  test('closed cycle remains readable but cannot save or submit', () async {
    repository.closed = true;
    await editor.load();
    expect(editor.record!.id, applicationId);
    expect(editor.editable, isFalse);
    editor.setAnswer(applicationField, 'Blocked');
    await editor.save();
    await editor.submit();
    expect(repository.saves, 0);
    expect(repository.submits, 0);
  });

  test(
    'requested history ID mismatch cannot silently open another draft',
    () async {
      editor.dispose();
      editor = ApplicationEditor(
        repository,
        organizationId: applicationOrg,
        cycleId: applicationCycle,
        applicationId: '99999999-9999-4999-8999-999999999999',
      );
      await editor.load();
      expect(editor.record, isNull);
      expect(editor.failure!.kind, ApiFailureKind.notFound);
    },
  );

  test(
    'double save sends one command and late completion cannot restore disposed data',
    () async {
      await editor.load();
      editor.setAnswer(applicationField, 'Private text');
      repository.saveGate = Completer<void>();
      final pending = editor.save();
      await editor.save();
      expect(repository.saves, 1);
      editor.dispose();
      repository.saveGate!.complete();
      await pending;
      expect(editor.values, isEmpty);
      // Supply a new controller for the common teardown.
      editor = ApplicationEditor(repository, organizationId: applicationOrg);
    },
  );

  testWidgets(
    'Retry-After blocks writes until the indicated delay has elapsed',
    (tester) async {
      await editor.load();
      editor.setAnswer(applicationField, 'Retained text');
      repository.saveFailure = const ApiFailure(
        'rate_limited',
        kind: ApiFailureKind.rateLimited,
        statusCode: 429,
        retryAfter: Duration(seconds: 2),
      );
      await editor.save();
      expect(editor.retryDelayed, isTrue);
      await editor.save();
      expect(repository.saves, 1);
      await tester.pump(const Duration(seconds: 3));
      // Widget fake time advances timers; wall-clock comparison is separately
      // guarded by the timer clearing its deadline.
      expect(editor.retryDelayed, isFalse);
      expect(editor.values[applicationField], 'Retained text');
    },
  );
}
