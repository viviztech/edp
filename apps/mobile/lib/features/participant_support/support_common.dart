import '../../l10n/app_localizations.dart';
import 'dart:math';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_failure.dart';
import '../../core/navigation/destinations.dart';

mixin SupportRetry on ChangeNotifier {
  DateTime? _retryUntil;
  Timer? _retryTimer;
  bool get retryDelayed => _retryUntil?.isAfter(DateTime.now().toUtc()) == true;
  void recordFailure(ApiFailure failure) {
    final delay = failure.retryAfter;
    if (delay == null || delay <= Duration.zero) return;
    _retryUntil = DateTime.now().toUtc().add(delay);
    _retryTimer?.cancel();
    _retryTimer = Timer(delay, () {
      _retryUntil = null;
      notifyListeners();
    });
  }

  @override
  void dispose() {
    _retryTimer?.cancel();
    super.dispose();
  }
}

Map<String, dynamic> object(Object? value) =>
    (value as Map).cast<String, dynamic>();
String identifier(Object? value) {
  if (value is! String || !MobileDestination.uuid.hasMatch(value)) {
    throw const FormatException('Invalid identifier');
  }
  return value;
}

int versionOf(Object? value) {
  if (value is! int || value < 1) {
    throw const FormatException('Invalid version');
  }
  return value;
}

List<T> rows<T>(
  Object? value,
  T Function(Map<String, dynamic>) decode, {
  int max = 1000,
}) {
  final values = value as List;
  if (values.length > max) throw const FormatException('Unbounded response');
  return List.unmodifiable(values.map((v) => decode(object(v))));
}

T decode<T>(T Function() body, {bool command = false}) {
  try {
    return body();
  } catch (_) {
    throw ApiFailure(
      'invalid_response',
      kind: ApiFailureKind.invalidResponse,
      outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
    );
  }
}

String uuid() {
  final random = Random.secure();
  final bytes = List.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  final hex = bytes.map((v) => v.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}

String tr(BuildContext context, String en, String ta) =>
    Localizations.localeOf(context).languageCode == 'ta' ? ta : en;
String dateText(BuildContext context, DateTime value, {bool dateOnly = false}) {
  final format = DateFormat.yMMMd(Localizations.localeOf(context).languageCode);
  return dateOnly
      ? format.format(value)
      : format.add_jm().format(value.toLocal());
}

ApiFailure failureOf(Object error, {bool command = false}) =>
    error is ApiFailure
    ? error
    : ApiFailure(
        'service_unavailable',
        kind: ApiFailureKind.unavailable,
        outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
      );
String failureText(BuildContext context, ApiFailure failure) {
  if (failure.code == 'private_storage_unavailable') {
    return AppLocalizations.of(context)!.fileProtectionRequired;
  }
  if (failure.uncertain) {
    return AppLocalizations.of(
      context,
    )!.domainTheResultIsUnknownRefreshThis9caf4b;
  }
  return switch (failure.kind) {
    ApiFailureKind.forbidden || ApiFailureKind.notFound => AppLocalizations.of(
      context,
    )!.domainThisRecordIsUnavailableForThis7a537f,
    ApiFailureKind.conflict => AppLocalizations.of(
      context,
    )!.domainTheRecordChangedRefreshAndReview2840a2,
    ApiFailureKind.invalidSession => AppLocalizations.of(
      context,
    )!.domainSignInAgainToContinue40f531,
    ApiFailureKind.validation => AppLocalizations.of(
      context,
    )!.domainCheckTheEnteredValuesAndDisplayedee60bd,
    ApiFailureKind.rateLimited => AppLocalizations.of(
      context,
    )!.domainPleaseWaitBeforeTryingAgaind24731,
    _ => AppLocalizations.of(
      context,
    )!.domainUnableToLoadThisInformationYour85597a,
  };
}

class SupportError extends StatelessWidget {
  final ApiFailure? failure;
  const SupportError(this.failure, {super.key});
  @override
  Widget build(BuildContext context) => failure == null
      ? const SizedBox.shrink()
      : Semantics(
          liveRegion: true,
          child: Text(failureText(context, failure!)),
        );
}

class PageBatch<T> {
  final List<T> items;
  final String? cursor;
  PageBatch.fromJson(
    Map<String, dynamic> data,
    T Function(Map<String, dynamic>) parse,
  ) : items = rows(data['items'], parse, max: 100),
      cursor = data['next_cursor'] == null
          ? null
          : identifier(data['next_cursor']);
}

Future<bool> confirmAction(BuildContext context, String message) async =>
    await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(AppLocalizations.of(context)!.domainCancel19766e),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(AppLocalizations.of(context)!.domainConfirmeebdd2),
          ),
        ],
      ),
    ) ==
    true;
