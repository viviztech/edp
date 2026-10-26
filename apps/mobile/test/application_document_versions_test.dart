import 'dart:async';

import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/features/applications/application_editor.dart';
import 'package:edp_mobile/features/applications/application_models.dart';
import 'package:flutter_test/flutter_test.dart';

import 'application_editor_test.dart' show EditorRepository;
import 'fixtures/application_fixture.dart';

class _BusyScalarRepository extends EditorRepository {
  final entered = Completer<void>(), release = Completer<void>();
  bool uncertain = false;

  @override
  Future<ApplicationRecord> save(
    String org,
    ApplicationRecord record,
    Map<String, String> answers,
  ) async {
    saves++;
    entered.complete();
    await release.future;
    if (uncertain) {
      throw const ApiFailure(
        'request_timeout',
        kind: ApiFailureKind.timeout,
        outcome: CommandOutcome.uncertain,
      );
    }
    return applicationRecord(
      version: record.version + 1,
      answer: answers[applicationField] ?? '',
    );
  }
}

Future<void> _settleQueuedAcknowledgement(ApplicationEditor editor) async {
  for (var i = 0; i < 10; i++) {
    await Future<void>.delayed(Duration.zero);
    if (!editor.busy) return;
  }
  fail('Document acknowledgement did not settle');
}

void main() {
  test(
    'document versions received during scalar save reconcile highest acknowledgement after save',
    () async {
      final repository = _BusyScalarRepository();
      final editor = ApplicationEditor(
        repository,
        organizationId: applicationOrg,
        cycleId: applicationCycle,
      );
      addTearDown(editor.dispose);
      await editor.load();
      editor.setAnswer(applicationField, 'Saved local proposal');
      final saving = editor.save();
      await repository.entered.future;
      await editor.documentVersionChanged(3);
      await editor.documentVersionChanged(4);
      expect(editor.busy, isTrue);
      expect(repository.reads, 1);
      repository.server = applicationRecord(
        version: 4,
        answer: 'Saved local proposal',
      );
      repository.release.complete();
      await saving;
      await _settleQueuedAcknowledgement(editor);
      expect(editor.record!.version, 4);
      expect(editor.values[applicationField], 'Saved local proposal');
      expect(editor.needsReview, isFalse);
      expect(editor.dirtyAnswers, isFalse);
      expect(repository.reads, 2);
      expect(repository.saves, 1);
    },
  );

  test(
    'queued document acknowledgement never clears an uncertain scalar command even with equal answers',
    () async {
      final repository = _BusyScalarRepository()
        ..server = applicationRecord(answer: 'Same saved proposal')
        ..uncertain = true;
      final editor = ApplicationEditor(
        repository,
        organizationId: applicationOrg,
        cycleId: applicationCycle,
      );
      addTearDown(editor.dispose);
      await editor.load();
      final saving = editor.save();
      await repository.entered.future;
      await editor.documentVersionChanged(3);
      repository.server = applicationRecord(
        version: 3,
        answer: 'Same saved proposal',
      );
      repository.release.complete();
      await saving;
      await _settleQueuedAcknowledgement(editor);
      expect(editor.record!.version, 1);
      expect(editor.latest!.version, 3);
      expect(editor.values[applicationField], 'Same saved proposal');
      expect(editor.failure!.uncertain, isTrue);
      expect(editor.needsReview, isTrue);
      expect(editor.canWrite, isFalse);
      await editor.save();
      expect(repository.saves, 1);
      await editor.chooseSaved(keepEdits: true);
      expect(editor.needsReview, isFalse);
      expect(editor.record!.version, 3);
      expect(editor.canWrite, isTrue);
      expect(repository.saves, 1);
    },
  );
}
