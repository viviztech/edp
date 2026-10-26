import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/core/files/file_transport.dart';
import 'package:edp_mobile/core/files/private_files.dart';
import 'package:edp_mobile/features/applications/application_documents.dart';
import 'package:edp_mobile/features/applications/application_documents_panel.dart';
import 'package:edp_mobile/features/applications/documents_controller.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'application_documents_test.dart' show document, documentRequirement;
import 'file_transport_test.dart'
    show FileTestScope, FileTestSnapshot, FileTestTokens;
import 'fixtures/application_fixture.dart';

class _Controller extends DocumentsController {
  final snapshot = FileTestSnapshot([1, 2, 3]);
  ApplicationDocument? currentDownloadDocument;
  int downloads = 0;
  _Controller()
    : super(
        ApplicationDocumentsRepository(
          DomainApi(AuthRepository(Dio(), FileTestTokens())),
          FileTransport(AuthRepository(Dio(), FileTestTokens())),
        ),
        FileTestScope(),
        organizationId: applicationOrg,
        applicationId: applicationId,
        applicationVersion: 5,
        requirements: [documentRequirement()],
        collectionEnabled: true,
        maxUploadBytes: 256,
      ) {
    loaded = true;
    items = [
      document(state: 'clean', usable: true, fileVersion: 9, frozen: true),
    ];
  }
  @override
  Future<PrivateSnapshot?> download(ApplicationDocument document) async {
    downloads++;
    final current = currentDownloadDocument;
    return current == null
        ? snapshot
        : VerifiedApplicationDownload(snapshot, current);
  }
}

Future<void> _show(
  WidgetTester tester,
  _Controller controller, {
  String locale = 'en',
  bool nativeSupported = true,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      locale: Locale(locale),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: ApplicationDocumentsPanel(
            controller: controller,
            nativeSupported: nativeSupported,
            commandsEnabled: true,
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _tap(WidgetTester tester, String label) async {
  final target = find.text(label);
  await tester.ensureVisible(target);
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
  });

  testWidgets(
    'disabled collection shows policy and status without byte controls',
    (tester) async {
      final controller = _Controller()..collectionEnabled = false;
      await _show(tester, controller);
      expect(
        find.text(
          'Document collection is unavailable. Existing document status remains visible.',
        ),
        findsOneWidget,
      );
      expect(find.text('Synthetic files only'), findsOneWidget);
      for (final label in [
        'Choose document',
        'Replace document',
        'Remove document',
        'Verify private download',
        'Upload selected bytes',
      ]) {
        expect(find.text(label), findsNothing);
      }
      expect(find.text('Scan complete'), findsOneWidget);
      expect(controller.downloads, 0);
      await tester.pumpWidget(const SizedBox.shrink());
      await controller.close();
    },
  );

  testWidgets(
    'unsupported native platform keeps evidence visible with no private byte controls',
    (tester) async {
      final controller = _Controller();
      await _show(tester, controller, nativeSupported: false);
      expect(
        find.text(
          'Document selection and private downloads require the Android or iOS app.',
        ),
        findsOneWidget,
      );
      expect(find.text('Choose document'), findsNothing);
      expect(find.text('Verify private download'), findsNothing);
      expect(find.text('Submitted document proof'), findsOneWidget);
      await tester.pumpWidget(const SizedBox.shrink());
      await controller.close();
    },
  );

  testWidgets(
    'unusable clean evidence has no download and submitted proof uses frozen version',
    (tester) async {
      final controller = _Controller()
        ..items = [
          document(state: 'clean', usable: false, fileVersion: 9, frozen: true),
        ]
        ..editable = false;
      await _show(tester, controller);
      expect(find.text('Scan complete'), findsOneWidget);
      expect(
        find.text('This document is not currently usable for submission.'),
        findsOneWidget,
      );
      expect(find.text('text/plain · 3 bytes · version 4'), findsOneWidget);
      expect(find.text('text/plain · 3 bytes · version 9'), findsNothing);
      expect(find.text('Verify private download'), findsNothing);
      expect(find.text('Submitted document proof'), findsOneWidget);
      await tester.pumpWidget(const SizedBox.shrink());
      await controller.close();
    },
  );

  testWidgets(
    'verified download receipt closes and releases only the private copy',
    (tester) async {
      final controller = _Controller()..editable = false;
      await _show(tester, controller);
      await _tap(tester, 'Verify private download');
      expect(find.text('Private download verified'), findsOneWidget);
      expect(controller.downloads, 1);
      expect(controller.snapshot.disposed, isFalse);
      await _tap(tester, 'Close and delete private copy');
      expect(find.text('Private download verified'), findsNothing);
      expect(controller.snapshot.disposed, isTrue);
      expect(controller.snapshot.releases, 1);
      expect(controller.items.single.active, isTrue);
      await tester.pumpWidget(const SizedBox.shrink());
      await controller.close();
    },
  );

  testWidgets(
    'backgrounding and unmounting each release an open private receipt',
    (tester) async {
      final controller = _Controller()..editable = false;
      await _show(tester, controller);
      await _tap(tester, 'Verify private download');
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      await tester.pumpAndSettle();
      expect(controller.snapshot.disposed, isTrue);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pumpAndSettle();
      expect(find.text('Private download verified'), findsNothing);
      await tester.pumpWidget(const SizedBox.shrink());
      await controller.close();
      final second = _Controller()..editable = false;
      await _show(tester, second);
      await _tap(tester, 'Verify private download');
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
      expect(second.snapshot.disposed, isTrue);
      await second.close();
    },
  );

  testWidgets(
    'download receipt shows the freshly authorized document version',
    (tester) async {
      final controller = _Controller()
        ..editable = false
        ..items = [document(state: 'clean', usable: true, fileVersion: 3)]
        ..currentDownloadDocument = document(
          state: 'clean',
          usable: true,
          fileVersion: 9,
        );
      await _show(tester, controller);
      await _tap(tester, 'Verify private download');
      expect(find.text('Private download verified'), findsOneWidget);
      expect(find.text('text/plain · 3 bytes · version 9'), findsOneWidget);
      await tester.pumpWidget(const SizedBox.shrink());
      await controller.close();
    },
  );

  testWidgets(
    'Tamil private document policy fits 320 pixels with enlarged text',
    (tester) async {
      tester.view.physicalSize = const Size(320, 900);
      tester.view.devicePixelRatio = 1;
      tester.platformDispatcher.textScaleFactorTestValue = 1.4;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
      final controller = _Controller()..editable = false;
      await _show(tester, controller, locale: 'ta');
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/m02-tamil-320.png'),
      );
      final text = AppLocalizations.of(
        tester.element(find.byType(ApplicationDocumentsPanel)),
      )!;
      await tester.ensureVisible(find.text(text.fileDownload));
      await tester.pumpAndSettle();
      expect(find.text(text.fileDownload).hitTestable(), findsOneWidget);
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/m02-tamil-320-bottom.png'),
      );
      await tester.pumpWidget(const SizedBox.shrink());
      await controller.close();
    },
  );
}
