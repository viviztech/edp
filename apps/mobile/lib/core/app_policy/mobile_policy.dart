import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/identity/providers.dart';
import '../../l10n/app_localizations.dart';
import '../links/external_links.dart';

const appVersion = String.fromEnvironment('APP_VERSION', defaultValue: '0.1.0');

List<int> _version(String value) {
  if (!RegExp(
    r'^(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})$',
  ).hasMatch(value)) {
    throw const FormatException('Invalid app version');
  }
  return value.split('.').map(int.parse).toList();
}

int compareAppVersions(String left, String right) {
  final a = _version(left), b = _version(right);
  for (var index = 0; index < 3; index++) {
    final order = a[index].compareTo(b[index]);
    if (order != 0) return order;
  }
  return 0;
}

class MobilePolicy {
  final bool enabled;
  final String minimum, latest;
  final String? downloadUrl;
  MobilePolicy.fromJson(Map<String, dynamic> data, String platform)
    : enabled = data['updates_enabled'] as bool,
      minimum = data['minimum_version'] as String,
      latest = data['latest_version'] as String,
      downloadUrl = data['download_url'] as String? {
    if (!{'android', 'ios', 'web'}.contains(platform) ||
        data['platform'] != platform ||
        compareAppVersions(latest, minimum) < 0 ||
        (downloadUrl != null &&
            (validatePublicLink(downloadUrl!)?.scheme != 'https')) ||
        (enabled && (platform == 'web' || downloadUrl == null))) {
      throw const FormatException('Invalid app policy');
    }
  }
  bool updateAvailable(String current) =>
      enabled && compareAppVersions(current, latest) < 0;
  bool updateRequired(String current) =>
      enabled && compareAppVersions(current, minimum) < 0;
}

class MobilePolicyRepository {
  final Dio dio;
  MobilePolicyRepository(this.dio);
  Future<MobilePolicy?> read(String platform) async {
    try {
      final response = await dio.get<dynamic>(
        '/public/mobile-policy',
        queryParameters: {'platform': platform},
        options: Options(followRedirects: false, maxRedirects: 0),
      );
      return MobilePolicy.fromJson(
        Map<String, dynamic>.from(response.data as Map),
        platform,
      );
    } catch (_) {
      // Missing/offline/malformed metadata never locks a participant out.
      return null;
    }
  }
}

final mobilePolicyProvider = FutureProvider<MobilePolicy?>((ref) async {
  final platform = kIsWeb
      ? 'web'
      : switch (defaultTargetPlatform) {
          TargetPlatform.android => 'android',
          TargetPlatform.iOS => 'ios',
          _ => 'web',
        };
  if (platform == 'web') return null;
  return MobilePolicyRepository(
    ref.watch(authRepositoryProvider).dio,
  ).read(platform);
});

class MobilePolicyBanner extends ConsumerStatefulWidget {
  final Widget child;
  const MobilePolicyBanner({super.key, required this.child});
  @override
  ConsumerState<MobilePolicyBanner> createState() => _MobilePolicyBannerState();
}

class _MobilePolicyBannerState extends ConsumerState<MobilePolicyBanner>
    with WidgetsBindingObserver {
  String? dismissed;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      ref.invalidate(mobilePolicyProvider);
    }
  }

  @override
  Widget build(BuildContext context) {
    final policy = ref.watch(mobilePolicyProvider).asData?.value;
    var available = false, mandatory = false;
    try {
      available = policy?.updateAvailable(appVersion) ?? false;
      mandatory = policy?.updateRequired(appVersion) ?? false;
    } catch (_) {}
    if (!available ||
        policy == null ||
        (!mandatory && dismissed == policy.latest)) {
      return widget.child;
    }
    final text = AppLocalizations.of(context)!;
    return Column(
      children: [
        Material(
          color: Theme.of(context).colorScheme.surfaceContainer,
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Semantics(
                    liveRegion: true,
                    child: Text(
                      mandatory
                          ? text.mobileUpdateRequired
                          : text.mobileUpdateAvailable,
                    ),
                  ),
                  Wrap(
                    spacing: 8,
                    children: [
                      TextButton(
                        onPressed: () => ref
                            .read(externalLinksProvider)
                            .open(policy.downloadUrl!),
                        child: Text(text.mobileUpdateOpen),
                      ),
                      if (!mandatory)
                        TextButton(
                          onPressed: () =>
                              setState(() => dismissed = policy.latest),
                          child: Text(text.mobileUpdateDismiss),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
        Expanded(child: widget.child),
      ],
    );
  }
}
