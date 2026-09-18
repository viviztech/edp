import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('native refresh storage persists, replaces and deletes', (
    tester,
  ) async {
    expect(
      kIsWeb,
      isFalse,
      reason: 'Run this acceptance test on Android or iOS.',
    );
    const storage = FlutterSecureStorage();
    final first = SecureTokenStore(storage);
    // Refuse to replace an existing account session on a developer device.
    expect(
      await first.read(),
      isNull,
      reason: 'Use a dedicated test installation with no signed-in account.',
    );
    addTearDown(first.clear);

    await first.write('synthetic-native-refresh-one');
    final recreated = SecureTokenStore(const FlutterSecureStorage());
    expect(await recreated.read(), 'synthetic-native-refresh-one');

    await recreated.write('synthetic-native-refresh-two');
    expect(await first.read(), 'synthetic-native-refresh-two');
    final entries = await storage.readAll();
    expect(entries[SecureTokenStore.key], 'synthetic-native-refresh-two');
    expect(entries.values, isNot(contains('synthetic-native-refresh-one')));

    await recreated.clear();
    expect(await first.read(), isNull);
    await recreated.clear();
    expect(await recreated.read(), isNull);
  });
}
