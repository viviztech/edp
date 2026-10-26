import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'l10n/app_localizations.dart';
import 'theme/edp_theme.dart';
import 'features/identity/account_page.dart';
import 'features/cms/public_pages.dart';
import 'features/cms/public_editorial.dart';
import 'features/identity/providers.dart';
import 'features/applications/application_page.dart';
import 'core/navigation/session_gate.dart';
import 'core/navigation/destinations.dart';
import 'core/app_policy/mobile_policy.dart';
import 'features/learning/student_page.dart';
import 'features/learning/public_certificate_page.dart';
import 'features/participant_support/participant_support_page.dart';
import 'features/participant_support/public_resources_page.dart';
import 'features/participant_support/public_resource_detail.dart';
import 'features/alumni/alumni_page.dart';
import 'features/alumni/updates_page.dart';

final localeProvider = NotifierProvider<LocaleController, Locale>(
  LocaleController.new,
);

class LocaleController extends Notifier<Locale> {
  @override
  Locale build() => const Locale('en');

  void toggle() {
    state = Locale(state.languageCode == 'en' ? 'ta' : 'en');
  }

  void useLanguage(String language) {
    if (language == 'en' || language == 'ta') state = Locale(language);
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
      GoRoute(
        path: '/account',
        builder: (_, state) => _AccountDestination(
          next: MobileDestination.parse(state.uri.queryParameters['next']),
        ),
      ),
      GoRoute(
        path: '/applications',
        builder: (_, state) => SignedInGate(
          destination: state.uri.toString(),
          builder: (context) {
            final destination = MobileDestination.parse(state.uri.toString());
            if (destination == null) {
              return Scaffold(
                body: Center(
                  child: Text(
                    AppLocalizations.of(context)!.mobileApplicationUnavailable,
                  ),
                ),
              );
            }
            return ApplicationPage(destination: destination);
          },
        ),
      ),
      for (final path in ['/learning', '/support', '/alumni', '/updates'])
        GoRoute(
          path: path,
          builder: (_, state) => SignedInGate(
            destination: state.uri.toString(),
            builder: (context) {
              final destination = MobileDestination.parse(state.uri.toString());
              final organization =
                  destination?.uri.queryParameters['organization'];
              if (destination == null || organization == null) {
                return _unavailable(context);
              }
              final section = destination.uri.queryParameters['section'];
              return switch (path) {
                '/learning' => StudentPage(
                  organizationId: organization,
                  initialSection: section ?? 'learning',
                  initialCourseId: destination.uri.queryParameters['course'],
                  initialLessonId: destination.uri.queryParameters['lesson'],
                ),
                '/support' => ParticipantSupportPage(
                  organizationId: organization,
                  initialSection: section ?? 'support',
                  initialTicketId: destination.uri.queryParameters['ticket'],
                ),
                '/alumni' => AlumniPage(
                  organizationId: organization,
                  initialSection: section ?? 'business',
                  initialEnrollmentId:
                      destination.uri.queryParameters['enrollment'],
                  initialFollowUpId:
                      destination.uri.queryParameters['follow_up'],
                ),
                _ => UpdatesPage(organizationId: organization),
              };
            },
          ),
        ),
      GoRoute(
        path: '/resources',
        builder: (context, state) {
          final destination = MobileDestination.parse(state.uri.toString());
          final organization = destination?.uri.queryParameters['organization'];
          final item = destination?.uri.queryParameters['item'];
          return organization == null
              ? _unavailable(context)
              : item != null
              ? PublicResourceDetail(
                  key: ValueKey('$organization:$item'),
                  organizationId: organization,
                  itemId: item,
                )
              : PublicResourcesPage(
                  key: ValueKey(organization),
                  organizationId: organization,
                );
        },
      ),
      GoRoute(
        path: '/certificate',
        builder: (context, state) {
          final destination = MobileDestination.parse(state.uri.toString());
          final code = destination?.uri.queryParameters['code'];
          return code == null
              ? _unavailable(context)
              : PublicCertificatePage(key: ValueKey(code), code: code);
        },
      ),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});

Widget _unavailable(BuildContext context) => Scaffold(
  appBar: AppBar(title: Text(AppLocalizations.of(context)!.title)),
  body: Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Text(AppLocalizations.of(context)!.cmsUnavailable),
    ),
  ),
);

void main() => runApp(const ProviderScope(child: EdpApp()));

class EdpApp extends ConsumerStatefulWidget {
  const EdpApp({super.key});

  @override
  ConsumerState<EdpApp> createState() => _EdpAppState();
}

class _EdpAppState extends ConsumerState<EdpApp> {
  @override
  void initState() {
    super.initState();
    ref.listenManual(sessionProvider, (previous, next) {
      if (next != null && previous?.id != next.id) {
        ref.read(localeProvider.notifier).useLanguage(next.locale);
      }
    });
    Future.microtask(
      () => ref.read(sessionStateProvider.notifier).restoreAtEntry(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      locale: ref.watch(localeProvider),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      onGenerateTitle: (context) => AppLocalizations.of(context)!.title,
      theme: EdpTheme.light(),
      routerConfig: ref.watch(routerProvider),
      builder: (context, child) =>
          MobilePolicyBanner(child: child ?? const SizedBox.shrink()),
    );
  }
}

class _AccountDestination extends ConsumerStatefulWidget {
  final MobileDestination? next;
  const _AccountDestination({this.next});
  @override
  ConsumerState<_AccountDestination> createState() =>
      _AccountDestinationState();
}

class _AccountDestinationState extends ConsumerState<_AccountDestination> {
  bool queued = false;
  int navigationGeneration = 0;
  void _continue() {
    final next = widget.next;
    if (queued ||
        next == null ||
        next.uri.path == '/account' ||
        ref.read(sessionProvider) == null) {
      return;
    }
    queued = true;
    final generation = navigationGeneration;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || generation != navigationGeneration) return;
      queued = false;
      if (ref.read(sessionProvider) != null &&
          widget.next?.toString() == next.toString()) {
        context.go(next.toString());
      }
    });
  }

  @override
  void initState() {
    super.initState();
    _continue();
  }

  @override
  void didUpdateWidget(_AccountDestination oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.next?.toString() != widget.next?.toString()) {
      navigationGeneration++;
      queued = false;
      _continue();
    }
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(sessionProvider, (previous, profile) {
      if (profile != null) {
        _continue();
      } else {
        navigationGeneration++;
        queued = false;
      }
    });
    return const AccountPage();
  }
}

class PublicHome extends ConsumerWidget {
  const PublicHome({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = AppLocalizations.of(context)!;
    final theme = Theme.of(context);
    final session = ref.watch(sessionStateProvider);
    final profile = session.profile;
    return Scaffold(
      appBar: AppBar(
        actions: [
          TextButton(
            onPressed: ref.read(localeProvider.notifier).toggle,
            child: Text(text.language),
          ),
        ],
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset('assets/images/cse-logo.png', width: 42, height: 42),
            const SizedBox(width: 10),
            const Text('EDP'),
          ],
        ),
      ),
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
                if (session.status == SessionStatus.restoring)
                  const LinearProgressIndicator(),
                if (session.status == SessionStatus.unavailable) ...[
                  Text(text.mobileSessionUnavailable),
                  TextButton(
                    onPressed: ref
                        .read(sessionStateProvider.notifier)
                        .retryRestore,
                    child: Text(text.cmsRetry),
                  ),
                ],
                if (profile != null) ...[
                  Text(profile.name, style: theme.textTheme.titleLarge),
                  for (final grant in profile.grants) ...[
                    _HomeLink(
                      title:
                          '${grant.organizationName} · ${text.mobileApplications}',
                      icon: Icons.description_outlined,
                      onTap: () => context.push(
                        Uri(
                          path: '/applications',
                          queryParameters: {
                            'organization': grant.organizationId,
                          },
                        ).toString(),
                      ),
                    ),
                    if (grant.permissions.contains('participant.self') ||
                        grant.permissions.contains('lms.learn'))
                      for (final link in [
                        (
                          text.mobileLearning,
                          '/learning',
                          'learning',
                          Icons.school_outlined,
                        ),
                        (
                          text.mobileSchedule,
                          '/learning',
                          'schedule',
                          Icons.calendar_month,
                        ),
                        (
                          text.mobileSupport,
                          '/support',
                          'support',
                          Icons.support_agent,
                        ),
                        (
                          text.mobileMentoring,
                          '/support',
                          'mentoring',
                          Icons.people_outline,
                        ),
                        (
                          text.mobilePlans,
                          '/support',
                          'plans',
                          Icons.edit_document,
                        ),
                        (
                          text.mobileResources,
                          '/support',
                          'resources',
                          Icons.library_books_outlined,
                        ),
                        (
                          text.mobileBusiness,
                          '/alumni',
                          'business',
                          Icons.business_outlined,
                        ),
                        (
                          text.mobileImpact,
                          '/alumni',
                          'impact',
                          Icons.insights,
                        ),
                      ])
                        _HomeLink(
                          title: '${grant.organizationName} · ${link.$1}',
                          icon: link.$4,
                          onTap: () => context.push(
                            Uri(
                              path: link.$2,
                              queryParameters: {
                                'organization': grant.organizationId,
                                'section': link.$3,
                              },
                            ).toString(),
                          ),
                        ),
                    if (grant.permissions.contains('participant.self'))
                      _HomeLink(
                        title:
                            '${grant.organizationName} · ${text.mobileUpdates}',
                        icon: Icons.notifications_outlined,
                        onTap: () => context.push(
                          '/updates?organization=${grant.organizationId}',
                        ),
                      ),
                  ],
                  const SizedBox(height: 12),
                ],
                _HomeLink(
                  title: text.authTitle,
                  icon: Icons.person_outline,
                  onTap: () => context.push('/account'),
                ),
                const SizedBox(height: 12),
                _HomeLink(
                  title: text.cmsPages,
                  icon: Icons.menu_book_outlined,
                  onTap: () => context.push('/pages'),
                ),
                for (final link in [
                  (text.mobileNews, '/news', Icons.newspaper),
                  (text.mobileEvents, '/events', Icons.event),
                  (text.mobileFaq, '/faq', Icons.help_outline),
                  (text.mobileStories, '/testimonials', Icons.people_outline),
                ]) ...[
                  const SizedBox(height: 12),
                  _HomeLink(
                    title: link.$1,
                    icon: link.$3,
                    onTap: () => context.push(link.$2),
                  ),
                ],
                const SizedBox(height: 12),
                _HomeLink(
                  title: text.mobileApplications,
                  icon: Icons.description_outlined,
                  onTap: () {
                    const org = String.fromEnvironment(
                      'PUBLIC_ORGANIZATION_ID',
                    );
                    context.push(
                      Uri(
                        path: '/applications',
                        queryParameters: MobileDestination.uuid.hasMatch(org)
                            ? {'organization': org}
                            : null,
                      ).toString(),
                    );
                  },
                ),
                const SizedBox(height: 12),
                _HomeLink(
                  title: text.mobileResources,
                  icon: Icons.library_books_outlined,
                  onTap: () {
                    const org = String.fromEnvironment(
                      'PUBLIC_ORGANIZATION_ID',
                    );
                    context.push(
                      Uri(
                        path: '/resources',
                        queryParameters: MobileDestination.uuid.hasMatch(org)
                            ? {'organization': org}
                            : null,
                      ).toString(),
                    );
                  },
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
