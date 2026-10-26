import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/links/external_links.dart';
import '../../l10n/app_localizations.dart';
import 'knowledge.dart';
import 'support_common.dart';

class PublicResourceDetail extends ConsumerStatefulWidget {
  final String organizationId, itemId;
  const PublicResourceDetail({
    super.key,
    required this.organizationId,
    required this.itemId,
  });
  @override
  ConsumerState<PublicResourceDetail> createState() =>
      _PublicResourceDetailState();
}

class _PublicResourceDetailState extends ConsumerState<PublicResourceDetail> {
  late Future<KnowledgeItem> result;
  bool opening = false;
  Future<KnowledgeItem> load() => ref
      .read(knowledgeRepositoryProvider)
      .detail(widget.organizationId, widget.itemId, public: true);
  @override
  void initState() {
    super.initState();
    result = load();
  }

  @override
  Widget build(BuildContext context) {
    final text = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(text.domainPublicResourcesbacc34)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: FutureBuilder<KnowledgeItem>(
          future: result,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return Column(
                children: [
                  Text(text.mobileLinkedUnavailable),
                  TextButton(
                    onPressed: () => setState(() => result = load()),
                    child: Text(text.cmsRetry),
                  ),
                ],
              );
            }
            final item = snapshot.data;
            if (item == null) {
              return const Center(child: CircularProgressIndicator());
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextButton(
                  onPressed: () => setState(() => result = load()),
                  child: Text(text.learnRefresh),
                ),
                Text(
                  item.title,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                Text(item.provider),
                Text(item.description),
                Text(item.eligibility),
                Text(item.benefits),
                Text(item.process),
                for (final document in item.documents) Text(document),
                Text(
                  '${text.domainVerified4f7838}: ${dateText(context, item.verifiedAt, dateOnly: true)}',
                ),
                if (item.closesOn != null)
                  Text(
                    '${text.domainCloses74c21a}: ${dateText(context, item.closesOn!, dateOnly: true)}',
                  ),
                SelectableText(item.officialUrl),
                TextButton(
                  onPressed: opening
                      ? null
                      : () async {
                          final messenger = ScaffoldMessenger.of(context);
                          setState(() => opening = true);
                          try {
                            final current = await load();
                            if (mounted) {
                              await ref
                                  .read(externalLinksProvider)
                                  .open(current.officialUrl);
                            }
                          } catch (_) {
                            if (mounted) {
                              messenger.showSnackBar(
                                SnackBar(
                                  content: Text(text.mobileLinkedUnavailable),
                                ),
                              );
                            }
                          } finally {
                            if (mounted) setState(() => opening = false);
                          }
                        },
                  child: Text(text.domainOpenOfficialSource7bd352),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
