import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../features/identity/providers.dart';
import '../../l10n/app_localizations.dart';
import 'destinations.dart';

/// Unmount private feature state when the account or its session changes.
class SignedInGate extends ConsumerWidget {
  final String destination;
  final WidgetBuilder builder;
  const SignedInGate({
    super.key,
    required this.destination,
    required this.builder,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionStateProvider);
    final text = AppLocalizations.of(context)!;
    if (session.status == SessionStatus.authenticated &&
        session.profile != null) {
      return KeyedSubtree(
        key: ValueKey(
          '${session.profile!.id}:${session.generation}:$destination',
        ),
        child: Builder(builder: builder),
      );
    }
    return Scaffold(
      appBar: AppBar(title: Text(text.authTitle)),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: session.status == SessionStatus.restoring
              ? const CircularProgressIndicator()
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      session.status == SessionStatus.unavailable
                          ? text.mobileSessionUnavailable
                          : text.authSessionExpired,
                    ),
                    const SizedBox(height: 16),
                    if (session.status == SessionStatus.unavailable)
                      TextButton(
                        onPressed: ref
                            .read(sessionStateProvider.notifier)
                            .retryRestore,
                        child: Text(text.cmsRetry),
                      ),
                    FilledButton(
                      onPressed: () {
                        final next = MobileDestination.parse(destination);
                        context.push(
                          Uri(
                            path: '/account',
                            queryParameters: next == null
                                ? null
                                : {'next': next.toString()},
                          ).toString(),
                        );
                      },
                      child: Text(text.authLogin),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}
