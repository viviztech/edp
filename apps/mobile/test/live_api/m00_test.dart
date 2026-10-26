import 'package:edp_mobile/features/applications/application_history.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

void main() {
  group('M00 synthetic Flutter/API acceptance', () {
    late LiveApiFixture fixture;

    setUpAll(() {
      fixture = LiveApiFixture.load();
    });

    test(
      'identity maps real locale and organization grants and restores a session',
      () async {
        final client = await fixture.signIn('owner');
        addTearDown(client.close);
        expect(client.profile.id, fixture.accountUserId('owner'));
        expect(client.profile.locale, 'ta');
        expect(client.profile.grants, hasLength(2));
        expect(
          client.profile.hasPermission(
            fixture.organizationId,
            'participant.self',
          ),
          isTrue,
        );
        expect(
          client.profile.hasPermission(fixture.organizationId, 'lms.learn'),
          isTrue,
        );
        expect(
          client.profile.hasPermission(fixture.organizationId, 'crm.lead.view'),
          isFalse,
        );
        expect(
          client.profile.hasPermission(
            fixture.otherOrganizationId,
            'crm.lead.view',
          ),
          isTrue,
        );
        expect(
          client.profile.hasPermission(
            fixture.otherOrganizationId,
            'participant.self',
          ),
          isFalse,
        );
        expect(client.tokens.hasRefreshToken, isTrue);

        final restored = await client.restoreInNewRepository();
        expect(restored?.id, fixture.accountUserId('owner'));
        expect(restored?.locale, 'ta');
        expect(restored?.grants, hasLength(2));
        final profile = jsonObject(await client.api.get('/auth/me'));
        expect(profile['id'], fixture.accountUserId('owner'));
      },
    );

    test(
      'zero-grant applicant can read owned history without a staff or participant role',
      () async {
        final client = await fixture.signIn('applicant');
        addTearDown(client.close);
        expect(client.profile.grants, isEmpty);
        final history = await ApplicationHistoryRepository(client.api).list();
        expect(history.items, isEmpty);
        expect(history.nextCursor, isNull);
        await expectLater(
          client.api.get(
            '/participant-notifications/organizations/${fixture.organizationId}/mine',
          ),
          throwsA(apiFailureWithStatus(403)),
        );
      },
    );

    test(
      'owner reads enrollment inbox and reconciles versioned read and preferences',
      () async {
        final client = await fixture.signIn('owner');
        addTearDown(client.close);
        final prefix =
            '/participant-notifications/organizations/${fixture.organizationId}';
        final inbox = jsonObject(await client.api.get('$prefix/mine'));
        final notices = jsonItems(inbox);
        expect(notices, hasLength(1));
        expect(inbox['next_cursor'], isNull);
        final notice = notices.single;
        expect(notice['id'], fixture.enrollment('owner')['notice_id']);
        expect(
          notice['enrollment_id'],
          fixture.enrollment('owner')['enrollment_id'],
        );
        expect(notice['topic'], 'enrollment_created');
        expect(notice['action_kind'], 'schedule');
        expect(notice['read_at'], isNull);
        expect(notice.containsKey('recipient_user_id'), isFalse);
        expect(notice.containsKey('body'), isFalse);
        final read = jsonObject(
          await client.api.post(
            '$prefix/${notice['id']}/read',
            data: {'expected_version': notice['version']},
          ),
        );
        expect(read['read_at'], isNotNull);
        expect(read['version'], (notice['version'] as int) + 1);
        final reread = jsonItems(await client.api.get('$prefix/mine')).single;
        expect(reread['read_at'], read['read_at']);
        await expectLater(
          client.api.post(
            '$prefix/${notice['id']}/read',
            data: {'expected_version': notice['version']},
          ),
          throwsA(apiFailureWithStatus(409)),
        );

        final preference = jsonObject(
          await client.api.get('$prefix/preference'),
        );
        expect(preference['enabled'], isTrue);
        final disabled = jsonObject(
          await client.api.post(
            '$prefix/preference',
            data: {'enabled': false, 'expected_version': preference['version']},
          ),
        );
        expect(disabled['enabled'], isFalse);
        await expectLater(
          client.api.post(
            '$prefix/preference',
            data: {'enabled': true, 'expected_version': preference['version']},
          ),
          throwsA(apiFailureWithStatus(409)),
        );
        expect(
          jsonObject(await client.api.get('$prefix/preference'))['enabled'],
          isFalse,
        );
        final enabled = jsonObject(
          await client.api.post(
            '$prefix/preference',
            data: {'enabled': true, 'expected_version': disabled['version']},
          ),
        );
        expect(enabled['enabled'], isTrue);
      },
    );

    test(
      'server denies peer reads and cross-organization or CRM-derived participant access',
      () async {
        final owner = await fixture.signIn('owner');
        final peer = await fixture.signIn('peer');
        final outsider = await fixture.signIn('outsider');
        addTearDown(owner.close);
        addTearDown(peer.close);
        addTearDown(outsider.close);
        final primary =
            '/participant-notifications/organizations/${fixture.organizationId}';
        final other =
            '/participant-notifications/organizations/${fixture.otherOrganizationId}';
        final peers = jsonItems(await peer.api.get('$primary/mine'));
        expect(peers, hasLength(1));
        expect(peers.single['id'], fixture.enrollment('peer')['notice_id']);
        expect(
          peers.single['id'],
          isNot(fixture.enrollment('owner')['notice_id']),
        );
        await expectLater(
          peer.api.post(
            '$primary/${fixture.enrollment('owner')['notice_id']}/read',
            data: {'expected_version': 1},
          ),
          throwsA(apiFailureWithStatus(404)),
        );
        await expectLater(
          owner.api.get('$other/mine'),
          throwsA(apiFailureWithStatus(403)),
        );
        await expectLater(
          outsider.api.get('$primary/mine'),
          throwsA(apiFailureWithStatus(403)),
        );
        await expectLater(
          owner.api.get('$primary/operations/health'),
          throwsA(apiFailureWithStatus(403)),
        );
        await expectLater(
          owner.api.get(
            '/notifications/organizations/${fixture.organizationId}/mine',
          ),
          throwsA(apiFailureWithStatus(403)),
        );
        // The same identity legitimately has CRM access in the second organization;
        // that grant is distinct from a participant profile and recipient scope.
        final crm = jsonObject(
          await owner.api.get(
            '/notifications/organizations/${fixture.otherOrganizationId}/mine',
          ),
        );
        expect(jsonItems(crm), isEmpty);
      },
    );

    test(
      'application history contains owned enrollment evidence only',
      () async {
        final client = await fixture.signIn('owner');
        addTearDown(client.close);
        final history = await ApplicationHistoryRepository(client.api).list();
        expect(history.items, hasLength(1));
        expect(
          history.items.single.id,
          fixture.enrollment('owner')['application_id'],
        );
        expect(history.items.single.organizationId, fixture.organizationId);
        expect(history.items.single.state, 'enrolled');
        expect(
          history.items.single.id,
          isNot(fixture.enrollment('peer')['application_id']),
        );
        expect(
          history.items.single.id,
          isNot(fixture.enrollment('outsider')['application_id']),
        );
      },
    );
  }, skip: liveAcceptanceSkipReason);
}
