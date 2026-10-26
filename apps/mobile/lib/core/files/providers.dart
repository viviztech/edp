import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/identity/providers.dart';
import 'private_files.dart';

final privateFilesProvider = Provider<PrivateFiles>((ref) {
  final store = NativePrivateFiles();
  final identity = ref.watch(authRepositoryProvider);
  void close() {
    // The store fails closed after cleanup failure; never log native paths.
    unawaited(store.closeScopes().catchError((Object _) {}));
  }

  final remove = identity.onInvalidated(close);
  ref.onDispose(() {
    remove();
    close();
  });
  return store;
});
