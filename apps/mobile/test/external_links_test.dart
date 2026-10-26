import 'package:edp_mobile/core/links/external_links.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('only bounded explicit public HTTP links pass without credentials', () {
    for (final raw in [
      'https://example.org/resource?q=one#part',
      'http://example.org/',
    ]) {
      expect(validatePublicLink(raw), isNotNull);
    }
    for (final raw in [
      'javascript:alert(1)',
      'file:///private',
      '//example.org',
      'https://account:secret@example.org',
      'https://example.org/\nnext',
      'https:\\example.org',
      'https://example.org:70000',
      'https://',
      'https://example.org/${'x' * 2048}',
    ]) {
      expect(validatePublicLink(raw), isNull);
    }
  });
  test('native action receives only the validated public URL', () async {
    const channel = MethodChannel('test/external_links');
    final calls = <MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          calls.add(call);
          return true;
        });
    addTearDown(
      () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null),
    );
    final links = ExternalLinks(channel: channel);
    expect(await links.open('javascript:alert(1)'), isFalse);
    expect(calls, isEmpty);
    expect(await links.open('https://example.org/source'), isTrue);
    expect(calls.single.arguments, {'url': 'https://example.org/source'});
  });
}
