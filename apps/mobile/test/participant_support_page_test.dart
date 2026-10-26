import 'package:edp_mobile/core/files/file_transport.dart';
import 'package:edp_mobile/core/files/private_files.dart';
import 'package:edp_mobile/core/files/providers.dart';
import 'package:edp_mobile/features/participant_support/helpdesk.dart';
import 'package:edp_mobile/features/participant_support/helpdesk_files.dart';
import 'package:edp_mobile/features/participant_support/knowledge.dart';
import 'package:edp_mobile/features/participant_support/mentoring.dart';
import 'package:edp_mobile/features/participant_support/participant_support_page.dart';
import 'package:edp_mobile/features/participant_support/plans.dart';
import 'package:edp_mobile/l10n/app_localizations.dart';
import 'package:edp_mobile/theme/edp_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fixtures/support_fixture.dart';

void main() {
  setUpAll(() async {
    await (FontLoader(
      'MaterialIcons',
    )..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'))).load();
    for (final family in ['Roboto', 'NotoSansTamil']) {
      await (FontLoader(
            family,
          )..addFont(rootBundle.load('assets/fonts/NotoSansTamil-Regular.ttf')))
          .load();
    }
  });
  for (final section in ['support', 'mentoring', 'plans', 'resources']) {
    testWidgets(
      'Tamil $section supports 320 pixels, enlarged text and safe disposal',
      (tester) async {
        tester.view.physicalSize = const Size(320, 900);
        tester.view.devicePixelRatio = 1;
        tester.platformDispatcher.textScaleFactorTestValue = 1.4;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
        final api = SupportFixtureApi();
        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              helpdeskRepositoryProvider.overrideWithValue(
                HelpdeskRepository(api),
              ),
              helpdeskFilesRepositoryProvider.overrideWithValue(
                HelpdeskFilesRepository(api, FileTransport(api.identity)),
              ),
              plansRepositoryProvider.overrideWithValue(PlansRepository(api)),
              mentoringRepositoryProvider.overrideWithValue(
                MentoringRepository(api),
              ),
              knowledgeRepositoryProvider.overrideWithValue(
                KnowledgeRepository(api, api.identity.dio),
              ),
              privateFilesProvider.overrideWithValue(
                NativePrivateFiles(supported: false),
              ),
            ],
            child: MaterialApp(
              locale: const Locale('ta'),
              supportedLocales: AppLocalizations.supportedLocales,
              localizationsDelegates: AppLocalizations.localizationsDelegates,
              theme: EdpTheme.light(),
              home: ParticipantSupportPage(
                organizationId: supportOrg,
                initialSection: section,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        expect(find.text('Issue certificate'), findsNothing);
        expect(find.text('Synthetic private staff note'), findsNothing);
        await expectLater(
          find.byType(MaterialApp),
          matchesGoldenFile('goldens/m04-$section-tamil-320.png'),
        );
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      },
    );
  }
}
