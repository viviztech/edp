import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Public source links are opened only after an explicit user action, without
/// bearer credentials, API capabilities, headers or in-app script execution.
Uri? validatePublicLink(String value) {
  if (value.length > 2048 ||
      value.contains('\\') ||
      value.codeUnits.any((c) => c <= 32 || c == 127)) {
    return null;
  }
  final uri = Uri.tryParse(value);
  if (uri == null ||
      !{'https', 'http'}.contains(uri.scheme) ||
      uri.host.isEmpty ||
      uri.userInfo.isNotEmpty) {
    return null;
  }
  try {
    if (uri.port < 1 || uri.port > 65535) return null;
  } on FormatException {
    return null;
  }
  return uri;
}

class ExternalLinks {
  final MethodChannel channel;
  const ExternalLinks({
    this.channel = const MethodChannel('edp/external_links'),
  });
  Future<bool> open(String value) async {
    final uri = validatePublicLink(value);
    if (uri == null) return false;
    try {
      return await channel.invokeMethod<bool>('open', {
            'url': uri.toString(),
          }) ==
          true;
    } on PlatformException {
      return false;
    } on MissingPluginException {
      return false;
    }
  }
}

final externalLinksProvider = Provider((ref) => const ExternalLinks());
