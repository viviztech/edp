import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../l10n/app_localizations.dart';
import '../identity/providers.dart';

class EditorialItem {
  final String id, kind, slug, title, body;
  final DateTime? startsAt;
  EditorialItem.fromJson(Map<String, dynamic> j)
    : id = j['id'] as String,
      kind = j['kind'] as String,
      slug = j['slug'] as String,
      title = j['title'] as String,
      body = j['body'] as String,
      startsAt = j['starts_at'] == null
          ? null
          : DateTime.parse(j['starts_at'] as String);
}

class EditorialRepository {
  final Dio dio;
  final String organization;
  EditorialRepository(this.dio, this.organization);
  Future<List<EditorialItem>> list(String kind, String locale) async {
    if (!RegExp(r'^[0-9a-fA-F-]{36}$').hasMatch(organization))
      throw StateError('Public organization unavailable');
    final r = await dio.get<Map<String, dynamic>>(
      '/public/organizations/$organization/editorial',
      queryParameters: {'kind': kind, 'locale': locale, 'limit': 25},
    );
    return (r.data!['items'] as List)
        .map((x) => EditorialItem.fromJson(Map<String, dynamic>.from(x as Map)))
        .toList();
  }
}

final editorialRepositoryProvider = Provider(
  (ref) => EditorialRepository(
    ref.watch(authRepositoryProvider).dio,
    const String.fromEnvironment('PUBLIC_ORGANIZATION_ID'),
  ),
);

class PublicEditorial extends ConsumerStatefulWidget {
  final String kind;
  const PublicEditorial({super.key, required this.kind});
  @override
  ConsumerState<PublicEditorial> createState() => _PublicEditorialState();
}

class _PublicEditorialState extends ConsumerState<PublicEditorial> {
  List<EditorialItem> items = [];
  bool loading = true, failed = false;
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    load();
  }

  Future<void> load() async {
    try {
      final r = await ref
          .read(editorialRepositoryProvider)
          .list(widget.kind, Localizations.localeOf(context).languageCode);
      if (mounted) setState(() => items = r);
    } catch (_) {
      if (mounted) setState(() => failed = true);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(widget.kind)),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : failed
          ? Center(child: Text(t.cmsUnavailable))
          : ListView(
              padding: const EdgeInsets.all(24),
              children: items
                  .map(
                    (i) => ListTile(
                      title: Text(i.title),
                      subtitle: Text(
                        i.body,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
            ),
    );
  }
}
