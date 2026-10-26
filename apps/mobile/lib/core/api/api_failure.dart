import 'package:dio/dio.dart';

enum ApiFailureKind {
  offline,
  timeout,
  invalidSession,
  forbidden,
  notFound,
  validation,
  conflict,
  rateLimited,
  unavailable,
  invalidResponse,
  unsafeRequest,
  oversized,
  cancelled,
  unknown,
}

/// Whether a consequential command needs server reconciliation before retry.
enum CommandOutcome { notSent, rejected, uncertain }

class ApiFailure implements Exception {
  final String code;
  final ApiFailureKind kind;
  final CommandOutcome outcome;
  final int? statusCode;
  final Duration? retryAfter;

  const ApiFailure(
    this.code, {
    this.kind = ApiFailureKind.unknown,
    this.outcome = CommandOutcome.rejected,
    this.statusCode,
    this.retryAfter,
  });

  bool get uncertain => outcome == CommandOutcome.uncertain;

  factory ApiFailure.fromDio(DioException error, {bool command = false}) {
    final response = error.response;
    final status = response?.statusCode;
    final retryAfter = parseRetryAfter(response?.headers.value('retry-after'));
    if (status != null) {
      final (kind, fallback) = switch (status) {
        401 => (ApiFailureKind.invalidSession, 'invalid_session'),
        403 => (ApiFailureKind.forbidden, 'forbidden'),
        404 => (ApiFailureKind.notFound, 'not_found'),
        400 || 422 => (ApiFailureKind.validation, 'validation_failed'),
        409 || 412 => (ApiFailureKind.conflict, 'version_conflict'),
        413 => (ApiFailureKind.oversized, 'response_too_large'),
        429 => (ApiFailureKind.rateLimited, 'rate_limited'),
        >= 300 && < 400 => (ApiFailureKind.unsafeRequest, 'redirect_rejected'),
        >= 500 => (ApiFailureKind.unavailable, 'service_unavailable'),
        _ => (ApiFailureKind.unknown, 'request_failed'),
      };
      final body = response?.data;
      final serverError = body is Map ? body['error'] : null;
      final value = serverError is Map ? serverError['code'] : null;
      // Only stable codes cross this boundary, never bodies, paths or messages.
      final code =
          value is String && RegExp(r'^[a-z][a-z0-9_]{0,79}$').hasMatch(value)
          ? value
          : fallback;
      return ApiFailure(
        code,
        kind: kind,
        outcome: command && (status >= 500 || (status >= 200 && status < 300))
            ? CommandOutcome.uncertain
            : CommandOutcome.rejected,
        statusCode: status,
        retryAfter: retryAfter,
      );
    }
    final (kind, code) = switch (error.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.sendTimeout ||
      DioExceptionType.receiveTimeout => (
        ApiFailureKind.timeout,
        'request_timeout',
      ),
      DioExceptionType.connectionError => (ApiFailureKind.offline, 'offline'),
      DioExceptionType.cancel => (
        ApiFailureKind.cancelled,
        'request_cancelled',
      ),
      DioExceptionType.badCertificate => (
        ApiFailureKind.unavailable,
        'service_unavailable',
      ),
      _ => (ApiFailureKind.unavailable, 'service_unavailable'),
    };
    return ApiFailure(
      code,
      kind: kind,
      outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
    );
  }

  @override
  String toString() => 'ApiFailure($code, ${outcome.name})';
}

/// Surface backoff to the caller; the transport never sleeps or replays writes.
Duration? parseRetryAfter(String? value, {DateTime? now}) {
  if (value == null) return null;
  final seconds = int.tryParse(value.trim());
  if (seconds != null) return Duration(seconds: seconds < 0 ? 0 : seconds);
  final match = RegExp(
    r'^[A-Za-z]{3}, (\d{2}) ([A-Za-z]{3}) (\d{4}) (\d{2}):(\d{2}):(\d{2}) GMT$',
  ).firstMatch(value.trim());
  if (match == null) return null;
  const months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  final month = months.indexOf(match[2]!) + 1;
  if (month == 0) return null;
  final date = DateTime.utc(
    int.parse(match[3]!),
    month,
    int.parse(match[1]!),
    int.parse(match[4]!),
    int.parse(match[5]!),
    int.parse(match[6]!),
  );
  final duration = date.difference(now ?? DateTime.now().toUtc());
  return duration.isNegative ? Duration.zero : duration;
}
