import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'l10n/app_localizations.dart';
import 'theme/edp_theme.dart';
import 'features/identity/account_page.dart';
import 'features/cms/public_pages.dart';
import 'features/cms/public_editorial.dart';

final localeProvider = NotifierProvider<LocaleController, Locale>(
  LocaleController.new,
);

class LocaleController extends Notifier<Locale> {
  @override
  Locale build() => const Locale('en');

  void toggle() {
    state = Locale(state.languageCode == 'en' ? 'ta' : 'en');
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, _) => const PublicHome()),
      GoRoute(path: '/pages', builder: (_, _) => const PublicPages()),
      GoRoute(
        path: '/pages/:slug',
        builder: (_, state) => PublicPages(slug: state.pathParameters['slug']),
      ),
      GoRoute(
        path: '/news',
        builder: (_, _) => const PublicEditorial(kind: 'news'),
      ),
      GoRoute(
        path: '/events',
        builder: (_, _) => const PublicEditorial(kind: 'event'),
      ),
      GoRoute(
        path: '/faq',
        builder: (_, _) => const PublicEditorial(kind: 'faq'),
      ),
      GoRoute(
        path: '/testimonials',
        builder: (_, _) => const PublicEditorial(kind: 'testimonial'),
      ),
      GoRoute(path: '/account', builder: (_, _) => const AccountPage()),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});

void main() => runApp(const ProviderScope(child: EdpApp()));

class EdpApp extends ConsumerWidget {
  const EdpApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      locale: ref.watch(localeProvider),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      onGenerateTitle: (context) => AppLocalizations.of(context)!.title,
      theme: EdpTheme.light(),
      routerConfig: ref.watch(routerProvider),
    );
  }
}

class PublicHome extends ConsumerWidget {
  const PublicHome({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(text.title)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(
              text.welcome,
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            const SizedBox(height: 24),
            Text(text.availability),
            TextButton(
              onPressed: () => context.push('/pages'),
              child: Text(text.cmsPages),
            ),
            TextButton(
              onPressed: () => context.push('/account'),
              child: Text(text.authTitle),
            ),
            const SizedBox(height: 24),
            TextButton(
              onPressed: ref.read(localeProvider.notifier).toggle,
              child: Text(text.language),
            ),
          ],
        ),
      ),
    );
  }
}
