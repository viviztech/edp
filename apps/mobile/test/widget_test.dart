import 'package:edp_mobile/main.dart';
import 'package:edp_mobile/features/identity/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'fixtures/guest_session.dart';

void main() {
  testWidgets('guest can switch to Tamil without authentication', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [sessionStateProvider.overrideWith(GuestSession.new)],
        child: const EdpApp(),
      ),
    );
    await tester.pumpAndSettle();
    expect(
      find.text('Build your skills. Shape your business.'),
      findsOneWidget,
    );
    await tester.ensureVisible(find.byType(TextButton).last);
    await tester.tap(find.byType(TextButton).last);
    await tester.pumpAndSettle();
    // The language control can be below the viewport on a small device.
    expect(find.text('Read in English', skipOffstage: false), findsOneWidget);
    expect(find.text('Build your skills. Shape your business.'), findsNothing);
  });
}
