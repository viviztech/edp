import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../l10n/app_localizations.dart';
import 'learning_repository.dart';
import 'student_page.dart' show CertificateQrPainter;

class PublicCertificatePage extends ConsumerStatefulWidget {
  final String code;
  const PublicCertificatePage({super.key, required this.code});
  @override
  ConsumerState<PublicCertificatePage> createState() =>
      _PublicCertificatePageState();
}

class _PublicCertificatePageState extends ConsumerState<PublicCertificatePage> {
  late Future<CertificateVerification> result;
  @override
  void initState() {
    super.initState();
    result = ref.read(learningRepositoryProvider).verify(widget.code);
  }

  @override
  Widget build(BuildContext context) {
    final text = AppLocalizations.of(context)!,
        tamil = Localizations.localeOf(context).languageCode == 'ta';
    return Scaffold(
      appBar: AppBar(title: Text(text.learnCertificate)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: FutureBuilder<CertificateVerification>(
          future: result,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return Column(
                children: [
                  Text(text.mobileLinkedUnavailable),
                  TextButton(
                    onPressed: () => setState(
                      () => result = ref
                          .read(learningRepositoryProvider)
                          .verify(widget.code),
                    ),
                    child: Text(text.cmsRetry),
                  ),
                ],
              );
            }
            final value = snapshot.data;
            if (value == null) {
              return const Center(child: CircularProgressIndicator());
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  value.title.text(tamil),
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                Text(value.course.text(tamil)),
                TextButton(
                  onPressed: () => setState(
                    () => result = ref
                        .read(learningRepositoryProvider)
                        .verify(widget.code),
                  ),
                  child: Text(text.learnRefresh),
                ),
                Text(
                  value.status == 'valid' ? text.learnValid : text.learnRevoked,
                ),
                Text(value.issuer),
                Text(
                  DateFormat.yMMMd(
                    tamil ? 'ta' : 'en',
                  ).format(value.issuedAt.toLocal()),
                ),
                Center(
                  child: Semantics(
                    label: text.learnQr,
                    image: true,
                    child: SizedBox(
                      width: 240,
                      height: 240,
                      child: CustomPaint(
                        painter: CertificateQrPainter(value.qr),
                      ),
                    ),
                  ),
                ),
                SelectableText(widget.code),
              ],
            );
          },
        ),
      ),
    );
  }
}
