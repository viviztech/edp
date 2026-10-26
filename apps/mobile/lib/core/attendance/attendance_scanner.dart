import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_failure.dart';

/// Camera frames remain with the platform scanner. A scan only fills a form;
/// the participant must separately submit the code to the authorized API.
class AttendanceScanner {
  final MethodChannel channel;
  final bool supported;
  const AttendanceScanner({
    this.channel = const MethodChannel('edp/attendance_scanner'),
    this.supported = !kIsWeb,
  });

  Future<String?> scan({
    required String instruction,
    required String cancel,
  }) async {
    if (!supported) {
      throw const ApiFailure(
        'scanner_unavailable',
        kind: ApiFailureKind.unavailable,
      );
    }
    try {
      final value = await channel.invokeMethod<String>('scan', {
        'instruction': instruction,
        'cancel': cancel,
      });
      if (value == null) return null;
      // Accept only our bounded QR payload. Foreign URLs are never opened.
      if (value.contains(RegExp(r'[\r\n]')) ||
          !RegExp(r'^edp-attendance:[A-Za-z0-9_-]{32,128}$').hasMatch(value)) {
        throw const ApiFailure(
          'invalid_attendance_token',
          kind: ApiFailureKind.validation,
        );
      }
      return value;
    } on MissingPluginException {
      throw const ApiFailure(
        'scanner_unavailable',
        kind: ApiFailureKind.unavailable,
      );
    } on PlatformException catch (error) {
      if (error.code == 'invalid_payload') {
        throw const ApiFailure(
          'invalid_attendance_token',
          kind: ApiFailureKind.validation,
        );
      }
      throw ApiFailure(
        error.code == 'denied' ? 'camera_denied' : 'scanner_unavailable',
        kind: error.code == 'denied'
            ? ApiFailureKind.forbidden
            : ApiFailureKind.unavailable,
      );
    }
  }
}

final attendanceScannerProvider = Provider((ref) => const AttendanceScanner());
