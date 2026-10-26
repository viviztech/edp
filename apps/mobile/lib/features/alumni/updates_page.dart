import '../../l10n/app_localizations.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_failure.dart';
import 'alumni_models.dart';
import 'alumni_repository.dart';
import 'alumni_strings.dart';

class UpdatesPage extends ConsumerStatefulWidget {
  final String organizationId;
  final void Function(String enrollmentId)? onOpenSchedule;
  const UpdatesPage({
    super.key,
    required this.organizationId,
    this.onOpenSchedule,
  });
  @override
  ConsumerState<UpdatesPage> createState() => _UpdatesPageState();
}

class _UpdatesPageState extends ConsumerState<UpdatesPage>
    with WidgetsBindingObserver {
  final Map<String, EnrollmentNotice> notices = {};
  final Set<String> uncertainRead = {}, cursors = {};
  EnrollmentNoticePreference? preference;
  String? cursor;
  Object? inboxError, preferenceError;
  bool inboxBusy = false,
      preferenceBusy = false,
      commandBusy = false,
      uncertainPreference = false;
  AlumniRepository get repository => ref.read(alumniRepositoryProvider);
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(loadInbox());
    unawaited(loadPreference());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    notices.clear();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && !commandBusy) {
      unawaited(loadInbox());
      unawaited(loadPreference());
    }
  }

  Future<void> loadInbox({bool more = false}) async {
    if (inboxBusy || commandBusy || (more && cursor == null)) return;
    setState(() {
      inboxBusy = true;
      inboxError = null;
    });
    try {
      final page = await repository.notices(
        widget.organizationId,
        cursor: more ? cursor : null,
      );
      if (!mounted) return;
      if (more && page.cursor != null && cursors.contains(page.cursor)) {
        throw const ApiFailure(
          'invalid_response',
          kind: ApiFailureKind.invalidResponse,
        );
      }
      setState(() {
        if (!more) {
          notices.clear();
          cursors.clear();
        }
        for (final notice in page.items) {
          notices[notice.id] = notice;
          uncertainRead.remove(notice.id);
        }
        cursor = page.cursor;
        if (cursor != null) cursors.add(cursor!);
      });
    } catch (error) {
      if (mounted) setState(() => inboxError = error);
    } finally {
      if (mounted) setState(() => inboxBusy = false);
    }
  }

  Future<void> loadPreference() async {
    if (preferenceBusy || commandBusy) return;
    setState(() {
      preferenceBusy = true;
      preferenceError = null;
    });
    try {
      final value = await repository.preference(widget.organizationId);
      if (mounted) {
        setState(() {
          preference = value;
          uncertainPreference = false;
        });
      }
    } catch (error) {
      if (mounted) setState(() => preferenceError = error);
    } finally {
      if (mounted) setState(() => preferenceBusy = false);
    }
  }

  Future<void> setPreference(bool enabled) async {
    if (preference == null ||
        preferenceBusy ||
        commandBusy ||
        uncertainPreference) {
      return;
    }
    setState(() {
      preferenceBusy = true;
      preferenceError = null;
    });
    try {
      final value = await repository.setPreference(
        widget.organizationId,
        preference!,
        enabled,
      );
      if (mounted) setState(() => preference = value);
    } catch (error) {
      if (mounted) {
        setState(() {
          preferenceError = error;
          uncertainPreference =
              error is! ApiFailure ||
              error.uncertain ||
              error.kind == ApiFailureKind.conflict;
        });
      }
    } finally {
      if (mounted) setState(() => preferenceBusy = false);
    }
  }

  Future<void> markRead(EnrollmentNotice notice) async {
    if (commandBusy || uncertainRead.contains(notice.id)) return;
    setState(() {
      commandBusy = true;
      inboxError = null;
    });
    try {
      final value = await repository.markRead(widget.organizationId, notice);
      if (mounted) setState(() => notices[value.id] = value);
    } catch (error) {
      if (mounted) {
        setState(() {
          inboxError = error;
          if (error is! ApiFailure ||
              error.uncertain ||
              error.kind == ApiFailureKind.conflict) {
            uncertainRead.add(notice.id);
          }
        });
      }
    } finally {
      if (mounted) setState(() => commandBusy = false);
    }
  }

  Future<void> readback(EnrollmentNotice notice) async {
    if (commandBusy) return;
    setState(() {
      commandBusy = true;
      inboxError = null;
    });
    try {
      final value = await repository.noticeById(
        widget.organizationId,
        notice.id,
      );
      if (mounted) {
        setState(() {
          notices[value.id] = value;
          uncertainRead.remove(value.id);
        });
      }
    } catch (error) {
      if (mounted) setState(() => inboxError = error);
    } finally {
      if (mounted) setState(() => commandBusy = false);
    }
  }

  Future<void> openSchedule(EnrollmentNotice notice) async {
    if (commandBusy || inboxBusy) return;
    setState(() {
      commandBusy = true;
      inboxError = null;
    });
    try {
      final enrollment = await repository.scheduleTarget(
        widget.organizationId,
        notice.id,
      );
      if (!mounted) return;
      if (widget.onOpenSchedule case final open?) {
        open(enrollment);
      } else {
        context.push(
          Uri(
            path: '/learning',
            queryParameters: {
              'organization': widget.organizationId,
              'section': 'schedule',
            },
          ).toString(),
        );
      }
    } catch (error) {
      if (mounted) setState(() => inboxError = error);
    } finally {
      if (mounted) setState(() => commandBusy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(AppLocalizations.of(context)!.domainEnrollmentUpdatesc8101a),
    ),
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                AppLocalizations.of(
                  context,
                )!.domainInAppEnrollmentUpdatesRefreshTof8b773,
              ),
              if (preferenceBusy || inboxBusy || commandBusy)
                const LinearProgressIndicator(),
              if (preferenceError != null)
                Semantics(
                  liveRegion: true,
                  child: Text(alumniFailure(context, preferenceError)),
                ),
              if (preference case final current?)
                SwitchListTile(
                  title: Text(
                    AppLocalizations.of(
                      context,
                    )!.domainReceiveEnrollmentUpdatesc62c16,
                  ),
                  value: current.enabled,
                  onChanged:
                      preferenceBusy || commandBusy || uncertainPreference
                      ? null
                      : setPreference,
                ),
              TextButton(
                onPressed: preferenceBusy || commandBusy
                    ? null
                    : loadPreference,
                child: Text(
                  AppLocalizations.of(
                    context,
                  )!.domainReadSavedNotificationPreference918105,
                ),
              ),
              if (inboxError != null)
                Semantics(
                  liveRegion: true,
                  child: Text(alumniFailure(context, inboxError)),
                ),
              TextButton(
                onPressed: inboxBusy || commandBusy ? null : loadInbox,
                child: Text(
                  AppLocalizations.of(context)!.domainRefreshInboxa804e4,
                ),
              ),
              if (!inboxBusy && notices.isEmpty)
                Text(
                  AppLocalizations.of(context)!.domainNoAvailableUpdatesba4851,
                ),
              for (final notice in notices.values)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          AppLocalizations.of(
                            context,
                          )!.domainYourProgramEnrollmentIsConfirmed72dce5,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        Text(
                          DateFormat.yMMMd(
                            Localizations.localeOf(context).languageCode,
                          ).add_jm().format(notice.createdAt.toLocal()),
                        ),
                        Text(
                          notice.readAt == null
                              ? AppLocalizations.of(context)!.mobileUnread
                              : AppLocalizations.of(context)!.mobileRead,
                        ),
                        if (uncertainRead.contains(notice.id))
                          TextButton(
                            onPressed: commandBusy
                                ? null
                                : () => readback(notice),
                            child: Text(
                              AppLocalizations.of(
                                context,
                              )!.domainCheckSavedReadStatus1e817a,
                            ),
                          )
                        else if (notice.readAt == null)
                          TextButton(
                            onPressed: commandBusy || inboxBusy
                                ? null
                                : () => markRead(notice),
                            child: Text(
                              AppLocalizations.of(
                                context,
                              )!.domainMarkReadb49c9b,
                            ),
                          ),
                        FilledButton(
                          onPressed: commandBusy || inboxBusy
                              ? null
                              : () => openSchedule(notice),
                          child: Text(
                            AppLocalizations.of(
                              context,
                            )!.domainOpenCurrentSchedule031f2c,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              if (cursor != null)
                TextButton(
                  onPressed: inboxBusy || commandBusy
                      ? null
                      : () => loadInbox(more: true),
                  child: Text(
                    AppLocalizations.of(context)!.domainMoreUpdates5fdeda,
                  ),
                ),
            ],
          ),
        ),
      ),
    ),
  );
}
