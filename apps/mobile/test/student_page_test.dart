import 'package:edp_mobile/core/files/private_files.dart';
import 'package:edp_mobile/core/files/providers.dart';
import 'package:edp_mobile/core/attendance/attendance_scanner.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/features/learning/assignment_files.dart';
import 'package:edp_mobile/features/learning/learning_repository.dart';
import 'package:edp_mobile/features/learning/student_page.dart';
import 'package:edp_mobile/l10n/app_localizations.dart';
import 'package:edp_mobile/theme/edp_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'learning_test.dart';
import 'file_transport_test.dart' show FileTestScope;

Future<void> showStudent(
  WidgetTester tester, {
  bool tamil = false,
  String section = 'learning',
  LearningTestRepository? repository,
  AttendanceScanner? scanner,
  String? course,
  PrivateFiles? privateFiles,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        learningRepositoryProvider.overrideWithValue(
          repository ?? LearningTestRepository(),
        ),
        assignmentFilesRepositoryProvider.overrideWithValue(
          LearningFileTestRepository(),
        ),
        privateFilesProvider.overrideWithValue(
          privateFiles ?? NativePrivateFiles(supported: false),
        ),
        if (scanner != null)
          attendanceScannerProvider.overrideWithValue(scanner),
      ],
      child: MaterialApp(
        locale: Locale(tamil ? 'ta' : 'en'),
        supportedLocales: AppLocalizations.supportedLocales,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        theme: EdpTheme.light(),
        home: StudentPage(
          organizationId: learningOrg,
          initialSection: section,
          initialCourseId: course,
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

class _TestScanner extends AttendanceScanner {
  @override
  Future<String?> scan({
    required String instruction,
    required String cancel,
  }) async => 'edp-attendance:${'A'.padRight(43, 'A')}';
}

class _AttendanceRepository extends LearningTestRepository {
  @override
  Future<void> checkIn(String organization, String entered) async {
    writes++;
  }
}

class _ProtectedTestStore extends NativePrivateFiles {
  bool denied = true;
  _ProtectedTestStore() : super(supported: true);
  @override
  Future<PrivateFileScope> createScope() async {
    if (denied) {
      throw const ApiFailure(
        'private_storage_unavailable',
        kind: ApiFailureKind.unavailable,
      );
    }
    return FileTestScope();
  }
}

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
  testWidgets(
    'student learning renders server ordering, quiz choices and assignment controls without staff actions',
    (tester) async {
      await showStudent(tester);
      expect(find.text('Business foundations'), findsOneWidget);
      await tester.tap(find.text('First module'));
      await tester.pumpAndSettle();
      expect(find.text('Who is the customer?'), findsOneWidget);
      expect(find.text('Buyer'), findsOneWidget);
      expect(find.text('Issue certificate'), findsNothing);
      expect(find.text('Grade assignment'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'attendance manual payload form is available when camera is absent',
    (tester) async {
      await showStudent(tester, section: 'attendance');
      expect(
        find.text('Attendance code or edp-attendance payload'),
        findsOneWidget,
      );
      expect(find.text('Check in'), findsOneWidget);
      expect(find.text('Scan attendance QR'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets('Tamil student page supports 320 pixels and enlarged text', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 760);
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.textScaleFactorTestValue = 1.4;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await showStudent(tester, tamil: true);
    expect(tester.takeException(), isNull);
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/m03-tamil-320.png'),
    );
  });
  testWidgets(
    'a camera result fills the code but requires a separate explicit check-in',
    (tester) async {
      final repository = _AttendanceRepository();
      await showStudent(
        tester,
        section: 'attendance',
        repository: repository,
        scanner: _TestScanner(),
      );
      await tester.tap(find.text('Scan attendance QR'));
      await tester.pumpAndSettle();
      expect(repository.writes, 0);
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        startsWith('edp-attendance:'),
      );
      await tester.tap(find.text('Check in'));
      await tester.pumpAndSettle();
      expect(repository.writes, 1);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'an unavailable linked course does not fall back to a different owned course',
    (tester) async {
      await showStudent(tester, course: '99999999-9999-4999-8999-999999999999');
      expect(find.text('Business foundations'), findsNothing);
      expect(
        find.textContaining('linked record is unavailable'),
        findsOneWidget,
      );
    },
  );
  testWidgets(
    'storage protection reason is visible and explicit retry preserves assignment input',
    (tester) async {
      final store = _ProtectedTestStore();
      await showStudent(tester, privateFiles: store);
      await tester.tap(find.text('First module'));
      await tester.pumpAndSettle();
      expect(
        find.textContaining('Private files require encrypted device storage'),
        findsOneWidget,
      );
      await tester.enterText(
        find.byType(TextField),
        'Retained assignment text',
      );
      await tester.pumpAndSettle();
      store.denied = false;
      final retry = find.text('Retry protected storage');
      await tester.ensureVisible(retry);
      await tester.pumpAndSettle();
      expect(retry.hitTestable(), findsOneWidget);
      await tester.tap(retry);
      await tester.pumpAndSettle();
      expect(
        find.textContaining('Private files require encrypted device storage'),
        findsNothing,
      );
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'Retained assignment text',
      );
      expect(tester.takeException(), isNull);
    },
  );
}
