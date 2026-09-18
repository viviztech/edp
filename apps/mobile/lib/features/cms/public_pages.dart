import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../l10n/app_localizations.dart';
import '../identity/providers.dart';

class PublishedPage {
  final String id, slug, title, body;
  PublishedPage.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      slug = json['slug'] as String,
      title = json['title'] as String,
      body = json['body'] as String;
}

class PageBatch {
  final List<PublishedPage> items;
  final String? nextCursor;
  PageBatch.fromJson(Map<String, dynamic> json)
    : items = (json['items'] as List)
          .map(
            (x) => PublishedPage.fromJson(Map<String, dynamic>.from(x as Map)),
          )
          .toList(),
      nextCursor = json['next_cursor'] as String?;
}

class PublicPageRepository {
  final Dio dio;
  final String organization;
  PublicPageRepository(this.dio, this.organization);
  String get path {
    if (!RegExp(r'^[0-9a-fA-F-]{36}$').hasMatch(organization)) {
      throw StateError('Public organization unavailable');
    }
    return '/public/organizations/$organization/pages';
  }

  Future<PageBatch> list(String locale, {String? cursor}) async {
    final r = await dio.get<Map<String, dynamic>>(
      path,
      queryParameters: {'locale': locale, 'limit': 25, 'cursor': ?cursor},
    );
    return PageBatch.fromJson(r.data!);
  }

  Future<PublishedPage> get(String slug, String locale) async {
    final r = await dio.get<Map<String, dynamic>>(
      '$path/${Uri.encodeComponent(slug)}',
      queryParameters: {'locale': locale},
    );
    return PublishedPage.fromJson(r.data!);
  }
}

final publicPageRepositoryProvider = Provider<PublicPageRepository>(
  (ref) => PublicPageRepository(
    ref.watch(authRepositoryProvider).dio,
    const String.fromEnvironment('PUBLIC_ORGANIZATION_ID'),
  ),
);

class PublicPages extends ConsumerStatefulWidget {
  final String? slug;
  const PublicPages({super.key, this.slug});
  @override
  ConsumerState<PublicPages> createState() => _PublicPagesState();
}

class _PublicPagesState extends ConsumerState<PublicPages> {
  List<PublishedPage> items = [];
  PublishedPage? page;
  String? cursor, language;
  bool loading = true, failed = false;
  int generation = 0;
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final lang = Localizations.localeOf(context).languageCode;
    if (lang != language) {
      language = lang;
      load();
    }
  }

  @override
  void didUpdateWidget(covariant PublicPages old) {
    super.didUpdateWidget(old);
    if (old.slug != widget.slug) load();
  }

  Future<void> load({bool more = false}) async {
    final request = ++generation;
    setState(() {
      loading = true;
      failed = false;
    });
    try {
      final repo = ref.read(publicPageRepositoryProvider);
      if (widget.slug != null) {
        final result = await repo.get(widget.slug!, language!);
        if (!mounted || request != generation) return;
        setState(() => page = result);
      } else {
        final result = await repo.list(language!, cursor: more ? cursor : null);
        if (!mounted || request != generation) return;
        setState(() {
          items = more ? [...items, ...result.items] : result.items;
          cursor = result.nextCursor;
        });
      }
    } catch (_) {
      if (mounted && request == generation) setState(() => failed = true);
    } finally {
      if (mounted && request == generation) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(t.cmsPages)),
      body: SafeArea(
        child: loading
            ? Center(
                child: Semantics(
                  label: t.cmsLoading,
                  child: const CircularProgressIndicator(),
                ),
              )
            : failed
            ? Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(t.cmsUnavailable),
                    TextButton(onPressed: load, child: Text(t.cmsRetry)),
                  ],
                ),
              )
            : ListView(
                padding: const EdgeInsets.all(24),
                children: widget.slug != null
                    ? [
                        Text(
                          page!.title,
                          style: Theme.of(context).textTheme.headlineLarge,
                        ),
                        const SizedBox(height: 24),
                        SelectableText(page!.body),
                      ]
                    : [
                        if (items.isEmpty) Text(t.cmsEmpty),
                        ...items.map(
                          (p) => ListTile(
                            title: Text(p.title),
                            onTap: () => context.push('/pages/${p.slug}'),
                          ),
                        ),
                        if (cursor != null)
                          TextButton(
                            onPressed: () => load(more: true),
                            child: Text(t.cmsMore),
                          ),
                      ],
              ),
      ),
    );
  }
}
