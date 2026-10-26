import 'package:edp_mobile/main.dart';
import 'package:edp_mobile/features/identity/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'fixtures/guest_session.dart';

class TamilLocale extends LocaleController {
  @override
  Locale build() => const Locale('ta');
}

void main() {
  setUpAll(() async {
    for (final family in ['Roboto', 'NotoSansTamil']) {
      await (FontLoader(
            family,
          )..addFont(rootBundle.load('assets/fonts/NotoSansTamil-Regular.ttf')))
          .load();
    }
  });
  testWidgets('Tamil home supports a narrow screen and enlarged text', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 760);
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.textScaleFactorTestValue = 1.4;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          localeProvider.overrideWith(TamilLocale.new),
          sessionStateProvider.overrideWith(GuestSession.new),
        ],
        child: const EdpApp(),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Read in English'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await expectLater(
      find.byType(EdpApp),
      matchesGoldenFile('goldens/m00-tamil-320.png'),
    );
  });
}
