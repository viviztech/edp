import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/attendance/attendance_scanner.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('edp/test_attendance_scanner');
  const scanner = AttendanceScanner(channel: channel);
  tearDown(
    () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null),
  );
  test(
    'only a bounded attendance payload is returned and scanning never submits it',
    () async {
      final payload = 'edp-attendance:${'A' * 43}';
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (call) async {
            expect(call.method, 'scan');
            expect(call.arguments, {'instruction': 'Scan', 'cancel': 'Cancel'});
            return payload;
          });
      expect(
        await scanner.scan(instruction: 'Scan', cancel: 'Cancel'),
        payload,
      );
    },
  );
  for (final value in [
    'https://example.org/attendance',
    'edp-attendance:short',
    'edp-attendance:${'A' * 129}',
    'edp-attendance:${'A' * 43}\n',
  ]) {
    test('unsupported scan payload fails closed ${value.length}', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (_) async => value);
      await expectLater(
        scanner.scan(instruction: 'Scan', cancel: 'Cancel'),
        throwsA(
          isA<ApiFailure>().having(
            (f) => f.kind,
            'validation',
            ApiFailureKind.validation,
          ),
        ),
      );
    });
  }
  test(
    'camera denial maps to a safe manual-entry state and cancel returns no code',
    () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
            channel,
            (_) async => throw PlatformException(code: 'denied'),
          );
      await expectLater(
        scanner.scan(instruction: 'Scan', cancel: 'Cancel'),
        throwsA(
          isA<ApiFailure>().having(
            (f) => f.kind,
            'forbidden',
            ApiFailureKind.forbidden,
          ),
        ),
      );
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (_) async => null);
      expect(await scanner.scan(instruction: 'Scan', cancel: 'Cancel'), isNull);
    },
  );
}
