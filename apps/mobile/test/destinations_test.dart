import 'package:edp_mobile/core/navigation/destinations.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const id = '11111111-1111-4111-8111-111111111111';
  test(
    'domain destinations preserve only explicit organization and supported section',
    () {
      for (final path in [
        '/learning?organization=$id&section=attendance',
        '/support?organization=$id&section=mentoring',
        '/alumni?organization=$id&section=impact',
        '/updates?organization=$id',
        '/resources?organization=$id',
      ]) {
        expect(MobileDestination.parse(path)?.toString(), path);
      }
      for (final path in [
        '/learning',
        '/support?section=plans',
        '/learning?organization=$id&section=staff',
        '/alumni?organization=$id&section=support',
        '/updates?organization=$id&token=secret',
        '/support?organization=$id&section=plans&section=support',
      ]) {
        expect(MobileDestination.parse(path), isNull);
      }
    },
  );
  test('preserves a known intake without accepting redirect or token data', () {
    const destination = '/applications?organization=$id&cycle=$id';
    expect(MobileDestination.parse(destination).toString(), destination);
    for (final value in [
      'https://example.com/applications',
      '//example.com/applications',
      '/applications?organization=$id&organization=$id',
      '/applications?token=private',
      '/applications?organization=invalid',
      '/applications?cycle=$id',
      '/applications?application=$id',
      '/applications/../account',
      '/applications%2f..%2faccount',
      '/account?next=https://example.com',
      '/support#private',
      '/learn?organization=$id',
    ]) {
      expect(MobileDestination.parse(value), isNull, reason: value);
    }
  });
  test(
    'object destinations pin their parent context and reject unrelated parameters',
    () {
      for (final destination in [
        '/learning?organization=$id&course=$id&lesson=$id',
        '/support?organization=$id&ticket=$id',
        '/alumni?organization=$id&enrollment=$id&follow_up=$id',
        '/resources?organization=$id&item=$id',
        '/certificate?code=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
      ]) {
        expect(MobileDestination.parse(destination)?.toString(), destination);
      }
      for (final destination in [
        '/learning?organization=$id&lesson=$id',
        '/learning?organization=$id&section=attendance&course=$id',
        '/support?organization=$id&section=plans&ticket=$id',
        '/alumni?organization=$id&follow_up=$id',
        '/alumni?organization=$id&section=impact&enrollment=$id',
        '/resources?item=$id',
        '/certificate',
        '/certificate?code=short',
        '/certificate?code=AAAAAAAAAAAAAAAAAAAA&token=secret',
        '/support?organization=$id%0A&ticket=$id',
      ]) {
        expect(
          MobileDestination.parse(destination),
          isNull,
          reason: destination,
        );
      }
    },
  );
}
