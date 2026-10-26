import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/features/participant_support/helpdesk.dart';
import 'package:edp_mobile/features/participant_support/helpdesk_files.dart';
import 'package:edp_mobile/features/participant_support/knowledge.dart';
import 'package:edp_mobile/features/participant_support/mentoring.dart';
import 'package:edp_mobile/features/participant_support/plans.dart';
import 'package:flutter_test/flutter_test.dart';
import 'helpers.dart';
import '../file_transport_test.dart' show FileTestSnapshot, FileTestScope;
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:edp_mobile/core/files/file_transport.dart';

import 'package:edp_mobile/features/participant_support/support_common.dart'
    show uuid;

void main() {
  group('M04 real synthetic Flutter API acceptance', () {
    late LiveApiFixture fixture;
    setUpAll(() => fixture = LiveApiFixture.load());
    test(
      'plan retains stale text, reads current version and submits an immutable complete snapshot',
      () async {
        final owner = await fixture.signIn('owner'),
            peer = await fixture.signIn('peer');
        addTearDown(owner.close);
        addTearDown(peer.close);
        final org = fixture.organizationId,
            repository = PlansRepository(owner.api);
        final enrollment =
            fixture.enrollment('owner')['enrollment_id'] as String;
        var plan = await repository.create(org, enrollment);
        final stale = plan;
        plan = await repository.save(
          org,
          plan,
          planSections.first,
          'Synthetic executive summary',
        );
        await expectLater(
          repository.save(org, stale, 'problem', 'Retain this stale text'),
          throwsA(apiFailureWithStatus(409)),
        );
        expect(
          (await repository.mine(
            org,
          )).single.plan!.sections[planSections.first],
          'Synthetic executive summary',
        );
        for (final section in planSections.skip(1)) {
          plan = await repository.save(
            org,
            plan,
            section,
            'Synthetic $section evidence',
          );
        }
        plan = await repository.submit(org, plan);
        expect(plan.editable, isFalse);
        expect(plan.submissions.single.snapshot.length, 20);
        await expectLater(
          repository.save(org, plan, 'problem', 'Forbidden mutation'),
          throwsA(apiFailureWithStatus(409)),
        );
        await expectLater(
          PlansRepository(peer.api).create(org, enrollment),
          throwsA(apiFailureWithStatus(404)),
        );
        await expectLater(
          repository.mine(fixture.otherOrganizationId),
          throwsA(apiFailureWithStatus(403)),
        );
      },
    );

    test(
      'mentoring excludes private notes and accepts one feedback only for completed owned sessions',
      () async {
        final director = await fixture.signIn('director'),
            owner = await fixture.signIn('owner'),
            peer = await fixture.signIn('peer');
        addTearDown(director.close);
        addTearDown(owner.close);
        addTearDown(peer.close);
        final org = fixture.organizationId,
            root = '/mentoring/organizations/${fixture.organizationId}';
        Future<Map<String, dynamic>> create(
          String path,
          Map<String, Object?> body,
        ) async =>
            jsonObject(await director.api.post('$root$path', data: body));
        final profile = await create('/profiles', {
          'user_id': fixture.accountUserId('director'),
          'headline': 'Synthetic mentor',
        });
        final now = DateTime.now().toUtc();
        final assignment = await create('/assignments', {
          'mentor_profile_id': profile['id'],
          'enrollment_id': fixture.enrollment('owner')['enrollment_id'],
          'starts_on': now.toIso8601String().substring(0, 10),
          'reason': 'Synthetic mentor assignment',
        });
        final session = await create('/sessions', {
          'assignment_id': assignment['id'],
          'starts_at': now.add(const Duration(days: 1)).toIso8601String(),
          'ends_at': now
              .add(const Duration(days: 1, hours: 1))
              .toIso8601String(),
          'mode': 'phone',
          'topic': 'Synthetic customer discovery',
        });
        for (final visibility in [
          'mentor_private',
          'shared_with_participant',
        ]) {
          await create('/notes', {
            'assignment_id': assignment['id'],
            'session_id': session['id'],
            'visibility': visibility,
            'body': 'Synthetic $visibility note',
          });
        }
        await create('/sessions/${session['id']}/state', {
          'expected_version': 1,
          'target': 'completed',
          'reason': 'Synthetic session completed',
        });
        final repository = MentoringRepository(owner.api);
        final mine = await repository.read(org);
        expect(
          mine.notes.single.body,
          'Synthetic shared_with_participant note',
        );
        expect(
          (await MentoringRepository(peer.api).read(org)).assignments,
          isEmpty,
        );
        expect(
          (await repository.feedback(
            org,
            session['id'] as String,
            5,
            'Useful synthetic guidance',
          )).rating,
          5,
        );
        await expectLater(
          repository.feedback(org, session['id'] as String, 4, 'Duplicate'),
          throwsA(apiFailureWithStatus(409)),
        );
        await expectLater(
          MentoringRepository(
            peer.api,
          ).feedback(org, session['id'] as String, 5, ''),
          throwsA(apiFailureWithStatus(404)),
        );
      },
    );

    test(
      'published resource, saved item and all funding transitions use owner contracts',
      () async {
        final director = await fixture.signIn('director'),
            owner = await fixture.signIn('owner'),
            peer = await fixture.signIn('peer');
        addTearDown(director.close);
        addTearDown(owner.close);
        addTearDown(peer.close);
        final org = fixture.organizationId,
            root = '/knowledge/organizations/${fixture.organizationId}';
        var resource = jsonObject(
          await director.api.post(
            '$root/items',
            data: {
              'kind': 'funding',
              'locale': 'ta',
              'slug': 'mobile-synthetic-funding',
              'title': 'சோதனை நிதி',
              'provider': 'Synthetic provider',
              'type': 'Grant',
              'description': 'Synthetic funding information',
              'eligibility': 'Official criteria',
              'benefits': 'Official benefit',
              'sector': 'Food',
              'geography': 'Tamil Nadu',
              'tags': ['enterprise'],
              'application_process': 'Use the official source',
              'documents': ['Business registration'],
              'official_url': 'https://example.org/funding',
              'last_verified_at': DateTime.now()
                  .toUtc()
                  .toIso8601String()
                  .substring(0, 10),
              'visibility': 'public',
              'funding_amount_min': '100.01',
              'funding_amount_max': '200.02',
            },
          ),
        );
        resource = jsonObject(
          await director.api.post(
            '$root/items/${resource['id']}/publish',
            data: {
              'expected_version': resource['version'],
              'reason': 'Synthetic verified resource',
            },
          ),
        );
        final repository = KnowledgeRepository(owner.api, owner.dio);
        final catalog = await repository.catalog(org, {'locale': 'ta'});
        expect(catalog.items.single.id, resource['id']);
        expect(
          (await repository.catalog(org, {
            'locale': 'ta',
          }, public: true)).items.single.id,
          resource['id'],
        );
        await repository.save(org, resource['id'] as String, saved: false);
        expect(
          (await repository.mine(org)).saved.single.item!.title,
          'சோதனை நிதி',
        );
        var funding = await repository.createCase(
          org,
          resource['id'] as String,
        );
        await expectLater(
          repository.transition(org, funding, 'approved', 'Invalid shortcut'),
          throwsA(
            isA<ApiFailure>().having(
              (f) => f.outcome,
              'not sent',
              CommandOutcome.notSent,
            ),
          ),
        );
        for (final target in [
          'eligibility_check',
          'document_preparation',
          'applied',
          'under_review',
          'approved',
          'disbursed',
        ]) {
          funding = await repository.transition(
            org,
            funding,
            target,
            'Synthetic $target evidence',
          );
        }
        expect(funding.status, 'disbursed');
        expect(funding.history.length, 7);
        expect(
          (await KnowledgeRepository(peer.api, peer.dio).mine(org)).cases,
          isEmpty,
        );
        await repository.save(org, resource['id'] as String, saved: true);
        expect((await repository.mine(org)).saved, isEmpty);
      },
    );

    test(
      'helpdesk create replay, private note exclusion, reply, close/reopen, notices and preferences',
      () async {
        final director = await fixture.signIn('director'),
            owner = await fixture.signIn('owner'),
            peer = await fixture.signIn('peer');
        addTearDown(director.close);
        addTearDown(owner.close);
        addTearDown(peer.close);
        final org = fixture.organizationId,
            repository = HelpdeskRepository(owner.api);
        final intent = <String, Object>{
          'request_id': uuid(),
          'category': 'funding',
          'priority': 'normal',
          'subject': 'Synthetic funding support',
          'body': 'Please review the synthetic question.',
        };
        var ticket = await repository.create(org, intent);
        expect((await repository.create(org, intent)).id, ticket.id);
        final root = '/helpdesk/organizations/$org/tickets/${ticket.id}';
        await expectLater(
          HelpdeskRepository(peer.api).detail(org, ticket.id),
          throwsA(apiFailureWithStatus(403)),
        );
        await director.api.post(
          '$root/assignment',
          data: {
            'expected_version': ticket.version,
            'assignee_user_id': fixture.accountUserId('director'),
            'reason': 'Synthetic support assignment',
          },
        );
        ticket = await repository.detail(org, ticket.id);
        await director.api.post(
          '$root/messages',
          data: {
            'expected_version': ticket.version,
            'body': 'Synthetic private staff note',
            'internal': true,
          },
        );
        ticket = await repository.detail(org, ticket.id);
        final files = HelpdeskFilesRepository(
          owner.api,
          FileTransport(owner.identity),
        );
        final bytes = FileTestSnapshot(
          base64Decode(
            jsonObject(fixture.domainIntake['payloads'])['text/plain']
                as String,
          ),
        );
        addTearDown(bytes.dispose);
        var file = await files.register(org, ticket.id, {
          'client_request_id': uuid(),
          'policy_id': fixture.domainIntake['policy_id'] as String,
          'internal': false,
          'media_type': bytes.mediaType,
          'byte_size': bytes.byteSize,
          'sha256': bytes.sha256,
        });
        file = await files.upload(org, ticket.id, file, bytes, CancelToken());
        expect(
          (await repository.messages(
            org,
            ticket.id,
          )).items.expand((m) => m.files),
          isEmpty,
        );
        await fixture.requestSyntheticScan(file.fileId);
        final deadline = DateTime.now().add(const Duration(seconds: 10));
        while (!file.usable && DateTime.now().isBefore(deadline)) {
          await Future<void>.delayed(const Duration(milliseconds: 100));
          file = await files.detail(org, ticket.id, file.id);
        }
        expect(file.usable, isTrue);
        await expectLater(
          HelpdeskFilesRepository(
            peer.api,
            FileTransport(peer.identity),
          ).detail(org, ticket.id, file.id),
          throwsA(apiFailureWithStatus(403)),
        );
        final scope = FileTestScope();
        final copy = await files.download(
          org,
          ticket.id,
          file,
          scope,
          CancelToken(),
        );
        expect(copy.sha256, bytes.sha256);
        await copy.dispose();
        await scope.close();
        ticket = await repository.reply(
          org,
          ticket,
          'Synthetic shared reply',
          legacyText: 'Synthetic text evidence',
          fileIds: [file.id],
        );
        var messages = await repository.messages(org, ticket.id);
        expect(
          messages.items.expand((m) => m.files).single.frozenVersion,
          isNotNull,
        );
        expect(
          messages.items.any((m) => m.body.contains('private staff note')),
          isFalse,
        );
        final attachment = messages.items.expand((m) => m.attachments).single;
        expect(
          await repository.legacyDownload(org, ticket.id, attachment),
          'Synthetic text evidence',
        );
        for (final status in ['in_progress', 'waiting_for_user', 'resolved']) {
          await director.api.post(
            '$root/status',
            data: {
              'expected_version': ticket.version,
              'status': status,
              'reason': 'Synthetic $status evidence',
            },
          );
          ticket = await repository.detail(org, ticket.id);
        }
        ticket = await repository.status(
          org,
          ticket,
          'Synthetic owner close',
          reopen: false,
        );
        expect(ticket.status, 'closed');
        ticket = await repository.status(
          org,
          ticket,
          'Synthetic owner reopen',
          reopen: true,
        );
        expect(ticket.status, 'open');
        expect((await repository.history(org, ticket.id)).items, isNotEmpty);
        final notices = await repository.notices(org);
        expect(notices.items, isNotEmpty);
        await repository.readNotice(org, notices.items.first);
        var preference = await repository.preference(org);
        preference = await repository.setPreference(org, preference, false);
        expect(preference.enabled, isFalse);
      },
    );
  }, skip: liveAcceptanceSkipReason);
}
