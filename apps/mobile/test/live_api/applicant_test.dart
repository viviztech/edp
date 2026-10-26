import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/features/applications/application_editor.dart';
import 'package:edp_mobile/features/applications/application_history.dart';
import 'package:edp_mobile/features/applications/application_models.dart';
import 'package:edp_mobile/features/applications/application_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

Map<String, String> completeAnswers(ApplicationRecord record, String idea) => {
  for (final field in record.form.fields)
    field.id: switch (field.type) {
      'number' => '2',
      'date' => '2026-10-24',
      'boolean' => 'true',
      'textarea' => idea,
      _ => 'Synthetic enterprise',
    },
};

void main() {
  group('M01 synthetic applicant/API acceptance', () {
    late LiveApiFixture fixture;
    setUpAll(() => fixture = LiveApiFixture.load());

    test(
      'fresh zero-grant applicant registers, verifies locally, saves/resumes and receives immutable receipt',
      () async {
        final client = await fixture.registerApplicant();
        addTearDown(client.close);
        expect(client.profile.grants, isEmpty);
        expect(client.profile.locale, 'ta');
        final repository = ApplicationRepository(client.api);
        final cycle = fixture.applicationIntake['open_cycle_id'] as String;
        final opportunities = await repository.cycles(fixture.organizationId);
        expect(opportunities.any((item) => item.id == cycle), isTrue);
        final draft = await repository.start(fixture.organizationId, cycle);
        expect(draft.form.collectionEnabled, isFalse);
        expect(draft.form.fields.map((field) => field.type).toSet(), {
          'text',
          'textarea',
          'number',
          'date',
          'boolean',
        });
        expect(
          draft.form.fields.every(
            (field) =>
                field.labelEn.isNotEmpty &&
                field.labelTa.isNotEmpty &&
                field.labelEn != field.labelTa,
          ),
          isTrue,
        );
        final firstField = draft.form.fields.first;
        final partial = await repository.save(fixture.organizationId, draft, {
          firstField.id: 'Synthetic enterprise',
        });
        expect(partial.completionPercent, lessThan(100));
        final resumed = await repository.read(fixture.organizationId, cycle);
        expect(resumed.answers[firstField.id], 'Synthetic enterprise');
        final saved = await repository.save(
          fixture.organizationId,
          resumed,
          completeAnswers(resumed, 'Community enterprise proposal'),
        );
        expect(saved.completionPercent, 100);
        final ack = saved.form.acknowledgements.map((item) => item.id).toSet();
        await expectLater(
          repository.submit(fixture.organizationId, saved, {ack.first}),
          throwsA(apiFailureWithStatus(422)),
        );
        final receipt = await repository.submit(
          fixture.organizationId,
          saved,
          ack,
        );
        expect(receipt.state, 'submitted');
        expect(receipt.number, startsWith('EDP-'));
        expect(receipt.accepted, hasLength(2));
        expect(receipt.history.map((item) => item.state), [
          'draft',
          'submitted',
        ]);
        final recovered = await repository.read(fixture.organizationId, cycle);
        expect(recovered.number, receipt.number);
        // Existing server successful-submission semantics return the same receipt.
        final repeat = await repository.submit(
          fixture.organizationId,
          saved,
          ack,
        );
        expect(repeat.number, receipt.number);
        final history = await ApplicationHistoryRepository(client.api).list();
        expect(history.items.single.id, receipt.id);
        expect(history.items.single.organizationId, fixture.organizationId);
      },
    );

    test(
      'two signed-in devices reconcile stale writes without losing local edits',
      () async {
        final first = await fixture.signIn('applicant');
        final second = await fixture.signIn('applicant');
        addTearDown(first.close);
        addTearDown(second.close);
        final cycle = fixture.applicationIntake['second_cycle_id'] as String;
        final repository = ApplicationRepository(first.api);
        await repository.start(fixture.organizationId, cycle);
        final editor = ApplicationEditor(
          repository,
          organizationId: fixture.organizationId,
          cycleId: cycle,
        );
        addTearDown(editor.dispose);
        await editor.load();
        final field = editor.record!.form.fields.first;
        editor.setAnswer(field.id, 'First device retained text');
        final otherRepository = ApplicationRepository(second.api);
        final otherDraft = await otherRepository.read(
          fixture.organizationId,
          cycle,
        );
        await otherRepository.save(fixture.organizationId, otherDraft, {
          field.id: 'Second device saved text',
        });
        await editor.save();
        expect(editor.failure!.kind, ApiFailureKind.conflict);
        await editor.reconcile();
        expect(editor.values[field.id], 'First device retained text');
        expect(editor.latest!.answers[field.id], 'Second device saved text');
        await editor.chooseSaved(keepEdits: true);
        expect(editor.dirtyAnswers, isTrue);
        await editor.save();
        expect(editor.failure, isNull);
        expect(
          (await otherRepository.read(
            fixture.organizationId,
            cycle,
          )).answers[field.id],
          'First device retained text',
        );
      },
    );

    test(
      'lost real save/submit responses trigger readback and exactly one command each',
      () async {
        final client = await fixture.signIn('applicant');
        addTearDown(client.close);
        final cycle = fixture.applicationIntake['lost_cycle_id'] as String;
        final repository = ApplicationRepository(client.api);
        await repository.start(fixture.organizationId, cycle);
        final editor = ApplicationEditor(
          repository,
          organizationId: fixture.organizationId,
          cycleId: cycle,
        );
        addTearDown(editor.dispose);
        await editor.load();
        for (final entry in completeAnswers(
          editor.record!,
          'Recovered submission proposal',
        ).entries) {
          editor.setAnswer(entry.key, entry.value);
        }
        var saves = 0, submits = 0;
        var dropSave = true, dropSubmit = true;
        client.dio.interceptors.add(
          InterceptorsWrapper(
            onRequest: (options, handler) {
              if (options.method == 'PATCH') saves++;
              if (options.method == 'POST' &&
                  options.path.endsWith('/submit')) {
                submits++;
              }
              handler.next(options);
            },
            onResponse: (response, handler) {
              final request = response.requestOptions;
              if ((request.method == 'PATCH' && dropSave) ||
                  (request.method == 'POST' &&
                      request.path.endsWith('/submit') &&
                      dropSubmit)) {
                if (request.method == 'PATCH') {
                  dropSave = false;
                } else {
                  dropSubmit = false;
                }
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
        await editor.save();
        expect(editor.needsReview, isTrue);
        await editor.save();
        expect(saves, 1);
        await editor.reconcile();
        expect(editor.latest!.version, 2);
        await editor.chooseSaved(keepEdits: true);
        expect(editor.dirtyAnswers, isFalse);
        for (final item in editor.record!.form.acknowledgements) {
          editor.acknowledge(item.id, true);
        }
        await editor.submit();
        expect(editor.needsReview, isTrue);
        await editor.submit();
        expect(submits, 1);
        await editor.reconcile();
        expect(editor.record!.state, 'submitted');
        expect(editor.record!.number, isNotNull);
        expect(editor.record!.accepted, hasLength(2));
        expect(submits, 1);
        expect(saves, 1);
      },
    );

    test(
      'closed intake draft reads by exact history identity and refuses server scalar edits',
      () async {
        final client = await fixture.signIn('applicant');
        addTearDown(client.close);
        final repository = ApplicationRepository(client.api);
        final cycle = fixture.applicationIntake['closed_cycle_id'] as String;
        final draft = await repository.read(fixture.organizationId, cycle);
        expect(draft.id, fixture.applicationIntake['closed_application_id']);
        final editor = ApplicationEditor(
          repository,
          organizationId: fixture.organizationId,
          cycleId: cycle,
          applicationId: draft.id,
        );
        addTearDown(editor.dispose);
        await editor.load();
        expect(editor.record!.id, draft.id);
        expect(editor.editable, isFalse);
        await expectLater(
          repository.save(
            fixture.organizationId,
            draft,
            completeAnswers(draft, 'Blocked after close'),
          ),
          throwsA(apiFailureWithStatus(404)),
        );
        expect(
          (await repository.read(fixture.organizationId, cycle)).version,
          draft.version,
        );
      },
    );

    test(
      'peer and wrong organization cannot read or write another applicant application',
      () async {
        final owner = await fixture.signIn('applicant');
        final peer = await fixture.signIn('peer');
        addTearDown(owner.close);
        addTearDown(peer.close);
        final cycle = fixture.applicationIntake['closed_cycle_id'] as String;
        final draft = await ApplicationRepository(
          owner.api,
        ).read(fixture.organizationId, cycle);
        final peerRepository = ApplicationRepository(peer.api);
        await expectLater(
          peerRepository.read(fixture.organizationId, cycle),
          throwsA(apiFailureWithStatus(404)),
        );
        await expectLater(
          peerRepository.save(
            fixture.organizationId,
            draft,
            completeAnswers(draft, 'Peer forbidden'),
          ),
          throwsA(apiFailureWithStatus(404)),
        );
        await expectLater(
          owner.api.get(
            '/applications/organizations/${fixture.otherOrganizationId}/cycles/$cycle/application',
          ),
          throwsA(apiFailureWithStatus(404)),
        );
        await expectLater(
          owner.api.patch(
            '/applications/organizations/${fixture.otherOrganizationId}/draft/${draft.id}',
            data: {'expected_version': draft.version, 'answers': <Object>[]},
          ),
          throwsA(apiFailureWithStatus(404)),
        );
      },
    );

    test(
      'owner history paginates without dropping entries or including another person',
      () async {
        final client = await fixture.signIn('applicant');
        addTearDown(client.close);
        final repository = ApplicationHistoryRepository(client.api);
        final first = await repository.list();
        expect(first.items, hasLength(25));
        expect(first.nextCursor, isNotNull);
        final second = await repository.list(cursor: first.nextCursor);
        expect(second.items, isNotEmpty);
        final ids = [
          ...first.items,
          ...second.items,
        ].map((item) => item.id).toList();
        expect(ids.toSet().length, ids.length);
        expect(
          ids,
          contains(fixture.applicationIntake['closed_application_id']),
        );
        expect(
          ids,
          isNot(contains(fixture.enrollment('peer')['application_id'])),
        );
        expect(second.nextCursor, isNull);
      },
    );
  }, skip: liveAcceptanceSkipReason);
}
