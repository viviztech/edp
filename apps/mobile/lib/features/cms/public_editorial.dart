import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../l10n/app_localizations.dart';
import '../identity/providers.dart';

class EditorialItem {
  final String id, kind, slug, title, body;
  final DateTime? startsAt, endsAt;

  EditorialItem.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      kind = json['kind'] as String,
      slug = json['slug'] as String,
      title = json['title'] as String,
      body = json['body'] as String,
      startsAt = json['starts_at'] == null
          ? null
          : DateTime.parse(json['starts_at'] as String),
      endsAt = json['ends_at'] == null
          ? null
          : DateTime.parse(json['ends_at'] as String);
}

class EditorialBatch {
  final List<EditorialItem> items;
  final String? nextCursor;

  EditorialBatch.fromJson(Map<String, dynamic> json)
    : items = (json['items'] as List)
          .map(
            (item) =>
                EditorialItem.fromJson(Map<String, dynamic>.from(item as Map)),
          )
          .toList(),
      nextCursor = json['next_cursor'] as String?;
}

class EditorialRepository {
  final Dio dio;
  final String organization;

  EditorialRepository(this.dio, this.organization);

  String _path(String kind) {
    if (!RegExp(
          r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
        ).hasMatch(organization) ||
        !const {'news', 'event', 'faq', 'testimonial'}.contains(kind)) {
      throw StateError('Public content unavailable');
    }
    return '/public/organizations/$organization/editorial';
  }

  Future<EditorialBatch> list(
    String kind,
    String locale, {
    String? cursor,
  }) async {
    final response = await dio.get<Map<String, dynamic>>(
      _path(kind),
      queryParameters: {
        'kind': kind,
        'locale': locale,
        'limit': 25,
        'cursor': ?cursor,
      },
    );
    return EditorialBatch.fromJson(response.data!);
  }

  Future<EditorialItem> get(String kind, String slug, String locale) async {
    final path = _path(kind);
    if (slug.length > 120 ||
        !RegExp(r'^[a-z0-9]+(-[a-z0-9]+)*$').hasMatch(slug)) {
      throw StateError('Public content unavailable');
    }
    final response = await dio.get<Map<String, dynamic>>(
      '$path/$kind/${Uri.encodeComponent(slug)}',
      queryParameters: {'locale': locale},
    );
    return EditorialItem.fromJson(response.data!);
  }
}

final editorialRepositoryProvider = Provider<EditorialRepository>(
  (ref) => EditorialRepository(
    ref.watch(authRepositoryProvider).dio,
    const String.fromEnvironment('PUBLIC_ORGANIZATION_ID'),
  ),
);

String editorialKindTitle(String kind, String locale) => switch (kind) {
  'news' => locale == 'ta' ? 'செய்திகள்' : 'News',
  'event' => locale == 'ta' ? 'நிகழ்வுகள்' : 'Events',
  'faq' => locale == 'ta' ? 'அடிக்கடி கேட்கப்படும் கேள்விகள்' : 'FAQs',
  'testimonial' => locale == 'ta' ? 'பங்கேற்பாளர் கருத்துகள்' : 'Testimonials',
  _ => locale == 'ta' ? 'புதுப்பிப்புகள்' : 'Updates',
};

class PublicEditorial extends ConsumerStatefulWidget {
  final String kind;
  final String? slug;

  const PublicEditorial({super.key, required this.kind, this.slug});

  @override
  ConsumerState<PublicEditorial> createState() => _PublicEditorialState();
}

class _PublicEditorialState extends ConsumerState<PublicEditorial> {
  List<EditorialItem> items = [];
  EditorialItem? item;
  String? cursor, language;
  bool loading = true, failed = false, loadingMore = false, moreFailed = false;
  int generation = 0;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final currentLanguage = Localizations.localeOf(context).languageCode;
    if (currentLanguage != language) {
      language = currentLanguage;
      load();
    }
  }

  @override
  void didUpdateWidget(covariant PublicEditorial oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.kind != widget.kind || oldWidget.slug != widget.slug) load();
  }

  Future<void> load({bool more = false}) async {
    if (more && (loading || loadingMore || cursor == null)) return;
    final request = ++generation;
    final requestCursor = more ? cursor : null;
    setState(() {
      failed = false;
      moreFailed = false;
      loading = !more;
      loadingMore = more;
      if (!more) {
        items = [];
        item = null;
        cursor = null;
      }
    });
    try {
      final repository = ref.read(editorialRepositoryProvider);
      if (widget.slug != null) {
        final result = await repository.get(
          widget.kind,
          widget.slug!,
          language!,
        );
        if (!mounted || request != generation) return;
        setState(() => item = result);
      } else {
        final result = await repository.list(
          widget.kind,
          language!,
          cursor: requestCursor,
        );
        if (!mounted || request != generation) return;
        setState(() {
          items = more ? [...items, ...result.items] : result.items;
          cursor = result.nextCursor;
        });
      }
    } catch (_) {
      if (!mounted || request != generation) return;
      setState(() {
        if (more) {
          moreFailed = true;
        } else {
          failed = true;
        }
      });
    } finally {
      if (mounted && request == generation) {
        setState(() {
          loading = false;
          loadingMore = false;
        });
      }
    }
  }

  Widget loadingIndicator(AppLocalizations text) => Center(
    child: Semantics(
      label: text.cmsLoading,
      child: const CircularProgressIndicator(),
    ),
  );

  List<Widget> eventDates(EditorialItem entry) {
    final tamil = language == 'ta';
    final formatter = DateFormat.yMMMd(language).add_jm();
    return [
      if (entry.startsAt != null) ...[
        const SizedBox(height: 12),
        Text(
          '${tamil ? 'தொடக்கம்' : 'Starts'}: '
          '${formatter.format(entry.startsAt!.toLocal())}',
        ),
      ],
      if (entry.endsAt != null) ...[
        const SizedBox(height: 8),
        Text(
          '${tamil ? 'முடிவு' : 'Ends'}: '
          '${formatter.format(entry.endsAt!.toLocal())}',
        ),
      ],
    ];
  }

  @override
  Widget build(BuildContext context) {
    final text = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(
        title: Text(
          editorialKindTitle(widget.kind, language ?? 'en'),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
      body: SafeArea(
        child: loading
            ? loadingIndicator(text)
            : failed
            ? Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(text.cmsUnavailable),
                      TextButton(onPressed: load, child: Text(text.cmsRetry)),
                    ],
                  ),
                ),
              )
            : ListView(
                padding: const EdgeInsets.all(24),
                children: widget.slug != null
                    ? [
                        Semantics(
                          header: true,
                          child: Text(
                            item!.title,
                            style: Theme.of(context).textTheme.headlineLarge,
                          ),
                        ),
                        ...eventDates(item!),
                        const SizedBox(height: 24),
                        SelectableText(item!.body),
                      ]
                    : [
                        if (items.isEmpty)
                          Text(
                            language == 'ta'
                                ? 'வெளியிடப்பட்ட தகவல்கள் இன்னும் இல்லை.'
                                : 'No published items yet.',
                          ),
                        ...items.map(
                          (entry) => ListTile(
                            title: Text(entry.title),
                            subtitle: Text(
                              entry.body,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () => Navigator.of(context).push<void>(
                              MaterialPageRoute(
                                builder: (_) => PublicEditorial(
                                  kind: widget.kind,
                                  slug: entry.slug,
                                ),
                              ),
                            ),
                          ),
                        ),
                        if (moreFailed) Text(text.cmsUnavailable),
                        if (loadingMore)
                          Padding(
                            padding: const EdgeInsets.all(16),
                            child: loadingIndicator(text),
                          )
                        else if (cursor != null)
                          TextButton(
                            onPressed: () => load(more: true),
                            child: Text(
                              moreFailed ? text.cmsRetry : text.cmsMore,
                            ),
                          ),
                      ],
              ),
      ),
    );
  }
}
