import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/features/participant_support/helpdesk.dart';
import 'package:edp_mobile/features/participant_support/knowledge.dart';
import 'package:edp_mobile/features/participant_support/mentoring.dart';
import 'package:edp_mobile/features/participant_support/plans.dart';
import 'package:flutter_test/flutter_test.dart';
import 'fixtures/support_fixture.dart';

void main() {
  test(
    'lost plan save cannot be acknowledged until authoritative read succeeds and keeps dirty text',
    () async {
      final api = SupportFixtureApi()..lostPlan = true;
      final model = PlansController(PlansRepository(api), supportOrg);
      addTearDown(model.dispose);
      await model.load();
      model.edit('problem', 'Retained description');
      await model.save('problem');
      expect(api.writes, 1);
      expect(model.requiresReview, isTrue);
      model.resolve(keepEdits: true);
      expect(model.requiresReview, isTrue);
      api.readFailure = const ApiFailure(
        'offline',
        kind: ApiFailureKind.offline,
      );
      await model.load();
      model.resolve(keepEdits: true);
      expect(model.requiresReview, isTrue);
      expect(model.edits['problem'], 'Retained description');
      api.readFailure = null;
      await model.load();
      expect(model.readbackReady, isTrue);
      model.resolve(keepEdits: true);
      expect(model.plan!.version, 2);
      expect(model.canWrite, isTrue);
      expect(api.writes, 1);
    },
  );
  test('acknowledged plan save survives a later failed refresh', () async {
    final api = SupportFixtureApi();
    final model = PlansController(PlansRepository(api), supportOrg);
    addTearDown(model.dispose);
    await model.load();
    model.edit('problem', 'Saved text');
    await model.save('problem');
    api.readFailure = const ApiFailure('offline', kind: ApiFailureKind.offline);
    await model.load();
    expect(model.plan!.version, 2);
    expect(model.edits, isEmpty);
    expect(api.writes, 1);
  });
  test(
    'helpdesk retries exactly the same ticket request after an unknown result',
    () async {
      final api = SupportFixtureApi()..lostCreate = true;
      final model = HelpdeskController(HelpdeskRepository(api), supportOrg);
      addTearDown(model.dispose);
      model.subject = 'Synthetic request';
      model.body = 'Retained question';
      await model.create();
      expect(model.requiresReadback, isTrue);
      expect(model.creationIntent, isNotNull);
      model.subject = 'New input cannot change an existing request';
      await model.create();
      expect(api.bodies[1], api.bodies[0]);
      expect(model.creationIntent, isNull);
      expect(model.ticket!.id, supportTicket);
      expect(model.messages.single.body, 'Synthetic shared message');
    },
  );
  test(
    'definitive ticket validation failure preserves editable user text',
    () async {
      final api = SupportFixtureApi()
        ..writeFailure = const ApiFailure(
          'invalid',
          kind: ApiFailureKind.validation,
        );
      final model = HelpdeskController(HelpdeskRepository(api), supportOrg);
      addTearDown(model.dispose);
      model.subject = 'Synthetic request';
      model.body = 'Retained question';
      await model.create();
      expect(model.creationIntent, isNull);
      expect(model.subject, 'Synthetic request');
      expect(model.body, 'Retained question');
    },
  );
  test(
    'private mentoring notes fail closed and uncertain feedback cannot replay before readback',
    () async {
      final private = supportMentoringJson();
      (private['notes'] as List).first['visibility'] = 'mentor_private';
      expect(() => MyMentoring.fromJson(private), throwsFormatException);
      final api = SupportFixtureApi()
        ..writeFailure = const ApiFailure(
          'timeout',
          kind: ApiFailureKind.timeout,
          outcome: CommandOutcome.uncertain,
        );
      final model = MentoringController(MentoringRepository(api), supportOrg);
      addTearDown(model.dispose);
      await model.refresh();
      model.comment = 'Keep this feedback';
      await model.send(supportSession);
      await model.send(supportSession);
      expect(api.writes, 1);
      expect(model.comment, 'Keep this feedback');
      expect(model.requiresReadback, isTrue);
    },
  );
  test(
    'knowledge saved, interests and funding pagination advance independently',
    () async {
      final api = SupportFixtureApi();
      final model = KnowledgeController(
        KnowledgeRepository(api, api.identity.dio),
        supportOrg,
      );
      addTearDown(model.dispose);
      await model.loadMine();
      await model.loadMine(more: 'saved');
      expect(api.queries.last!['saved_cursor'], supportItem);
      expect(api.queries.last!.containsKey('interest_cursor'), isFalse);
      expect(model.interestCursor, supportAssignment);
      expect(model.caseCursor, supportCase);
    },
  );
  test(
    'support controllers clear participant prose and records on disposal',
    () async {
      final api = SupportFixtureApi();
      final help = HelpdeskController(HelpdeskRepository(api), supportOrg);
      await help.open(supportTicket);
      help.reply = 'Private unsent text';
      help.dispose();
      expect(help.ticket, isNull);
      expect(help.reply, isEmpty);
      expect(help.messages, isEmpty);
      final mentor = MentoringController(MentoringRepository(api), supportOrg);
      await mentor.refresh();
      mentor.comment = 'Private feedback';
      mentor.dispose();
      expect(mentor.data, isNull);
      expect(mentor.comment, isEmpty);
    },
  );
}
