import 'api_failure.dart';

void validateApiPath(String path) {
  final uri = Uri.tryParse(path);
  if (path.isEmpty ||
      path.length > 2048 ||
      !path.startsWith('/') ||
      path.startsWith('//') ||
      path.contains('\\') ||
      path.contains('%') ||
      path.contains('?') ||
      path.contains('#') ||
      !RegExp(r'^/[A-Za-z0-9_./~:-]+$').hasMatch(path) ||
      uri == null ||
      uri.hasScheme ||
      uri.hasAuthority ||
      uri.pathSegments.any(
        (part) => part == '.' || part == '..' || part.isEmpty,
      )) {
    throw const ApiFailure(
      'unsafe_request',
      kind: ApiFailureKind.unsafeRequest,
      outcome: CommandOutcome.notSent,
    );
  }
}

Map<String, String> validateApiHeaders(Map<String, String>? headers) {
  final safe = <String, String>{};
  for (final entry in (headers ?? const <String, String>{}).entries) {
    if (!{
          'content-type',
          'if-match',
          'accept',
        }.contains(entry.key.toLowerCase()) ||
        entry.value.length > 256 ||
        entry.value.contains(RegExp(r'[\r\n]'))) {
      throw const ApiFailure(
        'unsafe_request',
        kind: ApiFailureKind.unsafeRequest,
        outcome: CommandOutcome.notSent,
      );
    }
    safe[entry.key] = entry.value;
  }
  return safe;
}
