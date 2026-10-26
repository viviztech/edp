import '../../l10n/app_localizations.dart';
import 'package:flutter/material.dart';

import 'knowledge_view.dart';

class PublicResourcesPage extends StatelessWidget {
  final String organizationId;
  const PublicResourcesPage({super.key, required this.organizationId});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(AppLocalizations.of(context)!.domainPublicResourcesbacc34),
    ),
    body: SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: KnowledgeView(organizationId: organizationId, public: true),
    ),
  );
}
