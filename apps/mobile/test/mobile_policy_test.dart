import 'package:dio/dio.dart';
import 'package:edp_mobile/core/app_policy/mobile_policy.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:edp_mobile/l10n/app_localizations.dart';
import 'core_api_test.dart' show ControlledAdapter, jsonResponse;

void main() {
  Map<String, dynamic> policy() => {
    'platform': 'android',
    'updates_enabled': true,
    'minimum_version': '0.1.1',
    'latest_version': '0.2.0',
    'download_url': 'https://example.org/approved-download',
  };
  test(
    'version comparison is numeric, bounded and rejects malformed versions',
    () {
      expect(compareAppVersions('1.10.0', '1.9.9'), greaterThan(0));
      expect(compareAppVersions('0.1.0', '0.1.0'), 0);
      for (final invalid in ['1.0', '01.0.0', '1.0.0-beta', '9999999.0.0']) {
        expect(
          () => compareAppVersions(invalid, '0.1.0'),
          throwsFormatException,
        );
      }
    },
  );
  test(
    'only enabled valid platform policy and HTTPS download produce an update prompt',
    () {
      final valid = MobilePolicy.fromJson(policy(), 'android');
      expect(valid.updateRequired('0.1.0'), isTrue);
      expect(valid.updateAvailable('0.1.1'), isTrue);
      expect(valid.updateAvailable('0.2.0'), isFalse);
      for (final changed in [
        {'platform': 'ios'},
        {'download_url': 'https://user:password@example.org/app'},
        {'download_url': 'http://example.org/app'},
        {'download_url': null},
        {'latest_version': '0.0.1'},
      ]) {
        expect(
          () => MobilePolicy.fromJson({...policy(), ...changed}, 'android'),
          throwsFormatException,
        );
      }
      expect(
        MobilePolicy.fromJson({
          ...policy(),
          'updates_enabled': false,
          'download_url': null,
        }, 'android').updateRequired('0.0.1'),
        isFalse,
      );
    },
  );
  test(
    'missing, offline or malformed policy fails open without sending bearer credentials',
    () async {
      for (final body in [
        null,
        {'platform': 'android'},
      ]) {
        final dio = Dio(BaseOptions(baseUrl: 'https://example.invalid/api/v1'));
        dio.httpClientAdapter = ControlledAdapter((options) {
          expect(options.headers.containsKey('Authorization'), isFalse);
          return jsonResponse(body);
        });
        expect(await MobilePolicyRepository(dio).read('android'), isNull);
        dio.close();
      }
    },
  );
  testWidgets(
    'required update metadata shows a localized prompt while preserving the workspace',
    (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            mobilePolicyProvider.overrideWith(
              (ref) async => MobilePolicy.fromJson(policy(), 'android'),
            ),
          ],
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: const MobilePolicyBanner(
              child: Scaffold(body: Text('Owned workspace')),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(
        find.text(
          'Please update this app to continue using the supported version.',
        ),
        findsOneWidget,
      );
      expect(find.text('Owned workspace'), findsOneWidget);
      expect(find.text('Later'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
}
