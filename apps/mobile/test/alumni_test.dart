import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/features/alumni/alumni_models.dart';
import 'package:edp_mobile/features/alumni/alumni_page.dart';
import 'package:edp_mobile/features/alumni/alumni_repository.dart';
import 'package:edp_mobile/features/alumni/updates_page.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'file_transport_test.dart' show FileTestTokens;

const org = '11111111-1111-4111-8111-111111111111';
const enrollment = '22222222-2222-4222-8222-222222222222';
const profileId = '33333333-3333-4333-8333-333333333333';
const definitionId = '44444444-4444-4444-8444-444444444444';
const noticeId = '55555555-5555-4555-8555-555555555555';
const followId = '66666666-6666-4666-8666-666666666666';
const recordId = '77777777-7777-4777-8777-777777777777';
Map<String, dynamic> profileFields() => {
  'name': 'Saved bakery',
  'sector': 'Food',
  'products_services': 'Baked goods',
  'stage': 'idea',
  'registration_info': null,
  'started_on': null,
  'team_size': 0,
  'investment_band': 'undisclosed',
  'funding_status': 'none',
  'revenue_band': 'undisclosed',
  'support_needs': null,
  'public_opt_in': false,
};
Map<String, dynamic> profileJson() => {
  ...profileFields(),
  'id': profileId,
  'enrollment_id': enrollment,
  'version': 1,
  'revisions': [],
  'follow_ups': [
    {
      'id': followId,
      'offset_days': 47,
      'due_on': '2026-09-30',
      'status': 'pending',
      'outcome': null,
    },
  ],
};
Map<String, dynamic> entryJson({bool profile = false}) => {
  'enrollment_id': enrollment,
  'program_id': org,
  'profile': profile ? profileJson() : null,
};
Map<String, dynamic> impactJson({
  List<Map<String, dynamic>> records = const [],
}) => {
  'enrollments': [
    {
      'id': enrollment,
      'name_en': 'Synthetic cohort',
      'name_ta': 'சோதனை குழு',
      'status': 'completed',
    },
  ],
  'definitions': [
    {
      'id': definitionId,
      'edition': 2,
      'title_en': 'Self report',
      'title_ta': 'சுய அறிக்கை',
      'definition_en': 'Participant reported business and jobs observations.',
      'definition_ta':
          'பங்கேற்பாளர் தெரிவித்த தொழில் மற்றும் வேலைக் கவனிப்புகள்.',
      'state': 'published',
    },
  ],
  'records': records,
  'enrollment_next_cursor': null,
  'definition_next_cursor': null,
  'record_next_cursor': null,
};
Map<String, dynamic> observationJson(Map<String, dynamic> command) => {
  ...command,
  'id': recordId,
  'revision': (command['expected_revision'] as int) + 1,
};
Map<String, dynamic> noticeJson() => {
  'id': noticeId,
  'enrollment_id': enrollment,
  'version': 1,
  'topic': 'enrollment_created',
  'template_version': 'enrollment-created-v1',
  'action_kind': 'schedule',
  'created_at': '2026-10-23T10:00:00Z',
  'expires_at': '2030-10-23T10:00:00Z',
  'read_at': null,
};

class _Api extends DomainApi {
  final calls = <(String, Map<String, dynamic>?)>[];
  Object? response;
  Object? Function(String, Map<String, dynamic>?)? read;
  int writes = 0;
  _Api() : super(AuthRepository(Dio(), FileTestTokens()));
  @override
  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    calls.add((path, queryParameters));
    return read?.call(path, queryParameters) ?? response;
  }

  @override
  Future<dynamic> post(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    writes++;
    return response;
  }
}

class _Repository extends AlumniRepository {
  int profileSaves = 0, impactSaves = 0, businessReads = 0;
  bool uncertainProfile = true, uncertainImpact = true;
  final impactCommands = <Map<String, dynamic>>[];
  BusinessProfile? previous;
  Map<String, dynamic>? savedFields;
  _Repository() : super(_Api());
  @override
  Future<List<BusinessEntry>> businesses(String organization) async {
    businessReads++;
    return [BusinessEntry.fromJson(entryJson(profile: profileSaves > 0))];
  }

  @override
  Future<BusinessProfile> saveProfile(
    String organization,
    String selected,
    Map<String, dynamic> fields, {
    BusinessProfile? previous,
  }) async {
    profileSaves++;
    this.previous = previous;
    savedFields = Map.of(fields);
    if (uncertainProfile) {
      uncertainProfile = false;
      throw const ApiFailure(
        'request_timeout',
        kind: ApiFailureKind.timeout,
        outcome: CommandOutcome.uncertain,
      );
    }
    return BusinessProfile.fromJson(profileJson());
  }

  @override
  Future<ImpactPage> impact(
    String organization, {
    String? enrollmentCursor,
    String? definitionCursor,
    String? recordCursor,
    String? enrollmentId,
    String? stage,
    String? observedOn,
    int limit = 25,
  }) async => ImpactPage.fromJson(impactJson());
  @override
  Future<ImpactObservation> recordImpact(
    String organization,
    Map<String, dynamic> body,
  ) async {
    impactSaves++;
    impactCommands.add(Map.of(body));
    if (uncertainImpact) {
      uncertainImpact = false;
      throw const ApiFailure(
        'request_timeout',
        kind: ApiFailureKind.timeout,
        outcome: CommandOutcome.uncertain,
      );
    }
    return ImpactObservation.fromJson(observationJson(body));
  }

  @override
  Future<EnrollmentNoticePage> notices(
    String organization, {
    String? cursor,
  }) async => EnrollmentNoticePage.fromJson({
    'items': [noticeJson()],
    'next_cursor': null,
  });
  @override
  Future<EnrollmentNoticePreference> preference(String organization) async =>
      EnrollmentNoticePreference.fromJson({
        'topic': 'enrollment_created',
        'enabled': true,
        'version': 0,
      });
}

Widget _app(
  AlumniRepository repository,
  Widget child, {
  Locale locale = const Locale('en'),
  double scale = 1,
}) => ProviderScope(
  overrides: [alumniRepositoryProvider.overrideWithValue(repository)],
  child: MaterialApp(
    locale: locale,
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    supportedLocales: const [Locale('en'), Locale('ta')],
    builder: (context, child) => MediaQuery(
      data: MediaQuery.of(
        context,
      ).copyWith(textScaler: TextScaler.linear(scale)),
      child: child!,
    ),
    home: child,
  ),
);
Finder input(String field) => find.descendant(
  of: find.byKey(ValueKey(field)),
  matching: find.byType(TextField),
);
DateTime _fixtureNow() => DateTime.utc(2026, 10, 24);
Future<void> tapVisible(WidgetTester tester, String text) async {
  final target = find.text(text).last;
  await tester.ensureVisible(target);
  await tester.pumpAndSettle();
  await tester.tap(target);
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() async {
    for (final family in ['Roboto', 'NotoSansTamil']) {
      await (FontLoader(
            family,
          )..addFont(rootBundle.load('assets/fonts/NotoSansTamil-Regular.ttf')))
          .load();
    }
    await (FontLoader(
      'MaterialIcons',
    )..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'))).load();
  });
  test(
    'profile policy dates and opaque IDs decode without recalculating schedules',
    () {
      final profile = BusinessProfile.fromJson(profileJson());
      expect(profile.followUps.single.dueOn, '2026-09-30');
      expect(profile.followUps.single.offsetDays, 47);
      expect(
        () => BusinessProfile.fromJson({
          ...profileJson(),
          'enrollment_id': '../other',
        }),
        throwsFormatException,
      );
      expect(
        () => validateProfile({...profileFields(), 'stage': 'operating'}),
        throwsA(isA<ApiFailure>()),
      );
      expect(
        () => validateOutcome({
          'reported_on': '2999-01-01',
          'business_started': false,
          'business_active': true,
          'jobs_created': 0,
          'funding_band': 'none',
          'revenue_band': 'none',
        }),
        throwsA(isA<ApiFailure>()),
      );
    },
  );
  test(
    'malformed successful profile is uncertain after exactly one command',
    () async {
      final api = _Api()..response = {...profileJson(), 'enrollment_id': org};
      await expectLater(
        AlumniRepository(api).saveProfile(org, enrollment, profileFields()),
        throwsA(
          isA<ApiFailure>().having((e) => e.uncertain, 'uncertain', true),
        ),
      );
      expect(api.writes, 1);
    },
  );
  test('impact cursors and exact filters stay independent and typed', () async {
    final api = _Api()..response = impactJson();
    await AlumniRepository(api).impact(
      org,
      enrollmentCursor: enrollment,
      definitionCursor: definitionId,
      recordCursor: recordId,
      enrollmentId: enrollment,
      stage: 'baseline',
      observedOn: '2026-10-01',
    );
    expect(api.calls.single.$2, {
      'limit': 25,
      'enrollment_cursor': enrollment,
      'definition_cursor': definitionId,
      'record_cursor': recordId,
      'enrollment_id': enrollment,
      'stage': 'baseline',
      'observed_on': '2026-10-01',
    });
    await expectLater(
      AlumniRepository(
        api,
      ).impact(org, recordCursor: 'https://outside.invalid'),
      throwsA(isA<ApiFailure>()),
    );
    expect(api.calls, hasLength(1));
  });
  test(
    'schedule target is freshly authorized through participant inbox and owned timeline',
    () async {
      final api = _Api()
        ..read = (path, query) => path.contains('participant-notifications')
            ? {
                'items': [noticeJson()],
                'next_cursor': null,
              }
            : {
                'enrollments': [
                  {'id': enrollment, 'status': 'completed'},
                ],
              };
      expect(
        await AlumniRepository(api).scheduleTarget(org, noticeId),
        enrollment,
      );
      expect(api.calls.map((c) => c.$1), [
        '/participant-notifications/organizations/$org/mine',
        '/programs/organizations/$org/my-timeline',
      ]);
      api.read = (path, query) => path.contains('participant-notifications')
          ? {
              'items': [noticeJson()],
              'next_cursor': null,
            }
          : {'enrollments': []};
      await expectLater(
        AlumniRepository(api).scheduleTarget(org, noticeId),
        throwsA(
          isA<ApiFailure>().having(
            (e) => e.kind,
            'kind',
            ApiFailureKind.notFound,
          ),
        ),
      );
    },
  );
  testWidgets(
    'lost profile creation keeps input and requires explicit saved-state decision',
    (tester) async {
      final repository = _Repository();
      tester.view.physicalSize = const Size(900, 2600);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        _app(repository, const AlumniPage(organizationId: org)),
      );
      await tester.pumpAndSettle();
      await tester.enterText(input('name'), 'My unsaved bakery');
      await tester.enterText(input('sector'), 'Food');
      await tester.enterText(input('products_services'), 'Baked goods');
      await tapVisible(tester, 'Save private profile');
      expect(repository.profileSaves, 1);
      expect(
        (tester.widget<TextField>(input('name'))).controller!.text,
        'My unsaved bakery',
      );
      await tapVisible(tester, 'Read saved state');
      expect(repository.profileSaves, 1);
      await tapVisible(tester, 'Keep my edits for explicit save');
      await tapVisible(tester, 'Save private profile');
      expect(repository.profileSaves, 2);
      expect(repository.previous?.version, 1);
      expect(repository.savedFields!['name'], 'My unsaved bakery');
    },
  );
  testWidgets(
    'uncertain impact replay keeps identical request UUID and command body',
    (tester) async {
      final repository = _Repository();
      tester.view.physicalSize = const Size(900, 2600);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        _app(
          repository,
          const AlumniPage(organizationId: org, initialSection: 'impact'),
        ),
      );
      await tester.pumpAndSettle();
      await tester.enterText(input('reason'), 'Synthetic self report');
      await tapVisible(tester, 'Submit self-report');
      expect(repository.impactSaves, 1);
      await tapVisible(tester, 'Read exact observation state');
      expect(repository.impactSaves, 1);
      await tapVisible(tester, 'Explicitly retry unchanged request');
      expect(repository.impactSaves, 2);
      expect(repository.impactCommands[1], repository.impactCommands[0]);
    },
  );
  testWidgets('new impact observations use the current injected UTC date', (
    tester,
  ) async {
    var now = DateTime.parse('2026-10-24T01:00:00+05:30');
    await tester.pumpWidget(
      _app(
        _Repository(),
        AlumniPage(
          organizationId: org,
          initialSection: 'impact',
          now: () => now,
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(
      tester.widget<TextField>(input('observed_on')).controller!.text,
      '2026-10-23',
    );
    await tester.enterText(input('observed_on'), '2026-10-01');
    await tester.pumpAndSettle();
    now = DateTime.utc(2026, 10, 25, 23, 59);
    final workspaceScroll = find
        .descendant(
          of: find.byType(ListView),
          matching: find.byType(Scrollable),
        )
        .first;
    await tester.scrollUntilVisible(
      find.text('Start another observation'),
      300,
      scrollable: workspaceScroll,
    );
    await tapVisible(tester, 'Start another observation');
    await tester.scrollUntilVisible(
      input('observed_on'),
      -300,
      scrollable: workspaceScroll,
    );
    expect(
      tester.widget<TextField>(input('observed_on')).controller!.text,
      '2026-10-25',
    );
    expect(tester.takeException(), isNull);
  });
  testWidgets(
    'Tamil updates wraps at 320 pixels with enlarged text and semantics',
    (tester) async {
      tester.view.physicalSize = const Size(320, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        _app(
          _Repository(),
          const UpdatesPage(organizationId: org),
          locale: const Locale('ta'),
          scale: 1.4,
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('சேர்க்கைப் புதுப்பிப்புகள்'), findsOneWidget);
      expect(tester.takeException(), isNull);
      expect(find.byType(SwitchListTile), findsOneWidget);
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/m05-updates-tamil-320.png'),
      );
    },
  );
  for (final section in ['business', 'impact']) {
    testWidgets('Tamil $section forms support 320 pixels and enlarged text', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(320, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        _app(
          _Repository(),
          AlumniPage(
            organizationId: org,
            initialSection: section,
            now: _fixtureNow,
          ),
          locale: const Locale('ta'),
          scale: 1.4,
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/m05-$section-tamil-320.png'),
      );
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  }
}
