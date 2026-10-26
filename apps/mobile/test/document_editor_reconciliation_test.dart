import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/features/applications/application_editor.dart';
import 'package:flutter_test/flutter_test.dart';

import 'application_editor_test.dart' show EditorRepository;
import 'fixtures/application_fixture.dart';

void main() {
  late EditorRepository repository;
  late ApplicationEditor editor;
  setUp(() {
    repository = EditorRepository()
      ..server = applicationRecord(answer: 'Saved original');
    editor = ApplicationEditor(
      repository,
      organizationId: applicationOrg,
      cycleId: applicationCycle,
    );
  });
  tearDown(() => editor.dispose());

  test(
    'acknowledged document-only version advance keeps unsaved scalar input and baseline',
    () async {
      await editor.load();
      editor.setAnswer(applicationField, 'Private unsaved edit');
      repository.server = applicationRecord(
        version: 2,
        answer: 'Saved original',
      );
      await editor.documentVersionChanged(2);
      expect(editor.record!.version, 2);
      expect(editor.record!.answers[applicationField], 'Saved original');
      expect(editor.values[applicationField], 'Private unsaved edit');
      expect(editor.dirtyAnswers, isTrue);
      expect(editor.needsReview, isFalse);
      expect(repository.saves, 0);
      expect(repository.submits, 0);
    },
  );

  test(
    'concurrent scalar change after document acknowledgement requires an explicit review',
    () async {
      await editor.load();
      editor.setAnswer(applicationField, 'Private unsaved edit');
      repository.server = applicationRecord(
        version: 3,
        answer: 'Other device saved',
      );
      await editor.documentVersionChanged(2);
      expect(editor.record!.version, 1);
      expect(editor.values[applicationField], 'Private unsaved edit');
      expect(editor.latest!.answers[applicationField], 'Other device saved');
      expect(editor.needsReview, isTrue);
      expect(editor.canWrite, isFalse);
      expect(repository.saves, 0);
    },
  );

  test(
    'read older than acknowledged document version fails closed without discarding edits',
    () async {
      await editor.load();
      editor.setAnswer(applicationField, 'Private unsaved edit');
      await editor.documentVersionChanged(2);
      expect(editor.failure?.kind, ApiFailureKind.conflict);
      expect(editor.values[applicationField], 'Private unsaved edit');
      expect(editor.record!.version, 1);
      expect(editor.needsReview, isTrue);
    },
  );
}
