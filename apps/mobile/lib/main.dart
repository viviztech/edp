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
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('EDP')),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                Text(
                  text.title,
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: theme.colorScheme.primary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                Text(text.welcome, style: theme.textTheme.headlineLarge),
                const SizedBox(height: 28),
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: const BoxDecoration(
                    color: EdpColors.paper,
                    border: Border(
                      left: BorderSide(color: EdpColors.highlight, width: 4),
                    ),
                  ),
                  child: Text(text.availability),
                ),
                const SizedBox(height: 28),
                _HomeLink(
                  title: text.cmsPages,
                  icon: Icons.menu_book_outlined,
                  onTap: () => context.push('/pages'),
                ),
                const SizedBox(height: 12),
                _HomeLink(
                  title: text.authTitle,
                  icon: Icons.person_outline,
                  onTap: () => context.push('/account'),
                ),
                const SizedBox(height: 24),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    onPressed: ref.read(localeProvider.notifier).toggle,
                    child: Text(text.language),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HomeLink extends StatelessWidget {
  const _HomeLink({
    required this.title,
    required this.icon,
    required this.onTap,
  });

  final String title;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      color: EdpColors.paper,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(4),
        side: const BorderSide(color: EdpColors.line),
      ),
      clipBehavior: Clip.antiAlias,
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 18,
          vertical: 12,
        ),
        leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
        title: Text(title),
        trailing: const Icon(Icons.arrow_forward),
        onTap: onTap,
      ),
    );
  }
}
