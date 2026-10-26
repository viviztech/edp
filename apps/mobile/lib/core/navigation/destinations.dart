/// Only known internal destinations survive an authentication transition.
/// Server authorization remains authoritative when each destination opens.
class MobileDestination {
  final Uri uri;
  const MobileDestination._(this.uri);

  static final uuid = RegExp(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
  );
  static const _parameters = {
    '/applications': {'organization', 'cycle', 'application'},
    '/account': <String>{},
    '/learning': {'organization', 'section', 'course', 'lesson'},
    '/support': {'organization', 'section', 'ticket'},
    '/alumni': {'organization', 'section', 'enrollment', 'follow_up'},
    '/updates': {'organization'},
    '/resources': {'organization', 'item'},
    '/certificate': {'code'},
  };
  static const _sections = {
    '/learning': {'learning', 'schedule', 'attendance'},
    '/support': {'support', 'mentoring', 'plans', 'resources'},
    '/alumni': {'business', 'impact'},
  };

  static MobileDestination? parse(String? value) {
    if (value == null ||
        value.length > 512 ||
        value.contains('\\') ||
        value.codeUnits.any((c) => c <= 32 || c == 127)) {
      return null;
    }
    final rawPath = value.split('?').first;
    if (rawPath.contains('%') ||
        rawPath.split('/').any((part) => part == '.' || part == '..')) {
      return null;
    }
    final uri = Uri.tryParse(value);
    if (uri == null || uri.hasScheme || uri.hasAuthority || uri.hasFragment) {
      return null;
    }
    final allowed = _parameters[uri.path];
    if (allowed == null) return null;
    for (final entry in uri.queryParametersAll.entries) {
      if (!allowed.contains(entry.key) ||
          entry.value.length != 1 ||
          entry.value.single.codeUnits.any((c) => c <= 32 || c == 127) ||
          (entry.key == 'section'
              ? _sections[uri.path]?.contains(entry.value.single) != true
              : entry.key == 'code'
              ? !RegExp(r'^[A-Za-z0-9_-]{20,48}$').hasMatch(entry.value.single)
              : !uuid.hasMatch(entry.value.single))) {
        return null;
      }
    }
    if ({'/learning', '/support', '/alumni', '/updates'}.contains(uri.path) &&
        !uri.queryParameters.containsKey('organization')) {
      return null;
    }
    final query = uri.queryParameters;
    if ((uri.path == '/certificate' && !query.containsKey('code')) ||
        (uri.path == '/resources' &&
            query.containsKey('item') &&
            !query.containsKey('organization')) ||
        (uri.path == '/learning' &&
            (query.containsKey('course') || query.containsKey('lesson')) &&
            (query['section'] != null && query['section'] != 'learning' ||
                query.containsKey('lesson') && !query.containsKey('course'))) ||
        (uri.path == '/support' &&
            query.containsKey('ticket') &&
            query['section'] != null &&
            query['section'] != 'support') ||
        (uri.path == '/alumni' &&
            query.containsKey('follow_up') &&
            !query.containsKey('enrollment')) ||
        (uri.path == '/alumni' &&
            query.containsKey('enrollment') &&
            query['section'] != null &&
            query['section'] != 'business')) {
      return null;
    }
    if (uri.path == '/applications' &&
        (uri.queryParameters.containsKey('cycle') ||
            uri.queryParameters.containsKey('application')) &&
        !uri.queryParameters.containsKey('organization')) {
      return null;
    }
    return MobileDestination._(uri);
  }

  @override
  String toString() => uri.toString();
}
