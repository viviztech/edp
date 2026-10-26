import '../../l10n/app_localizations.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_failure.dart';
import 'alumni_models.dart';
import 'alumni_repository.dart';
import 'alumni_strings.dart';

class AlumniPage extends StatefulWidget {
  final String organizationId, initialSection;
  final String? initialEnrollmentId, initialFollowUpId;
  final DateTime Function() now;
  const AlumniPage({
    super.key,
    required this.organizationId,
    this.initialSection = 'business',
    this.initialEnrollmentId,
    this.initialFollowUpId,
    this.now = DateTime.now,
  });
  @override
  State<AlumniPage> createState() => _AlumniPageState();
}

class _AlumniPageState extends State<AlumniPage> {
  late String section = widget.initialSection;
  bool dirty = false, leaving = false;
  Future<bool> _leave() async =>
      !dirty ||
      (await showDialog<bool>(
            context: context,
            builder: (context) => AlertDialog(
              content: Text(
                AppLocalizations.of(
                  context,
                )!.domainLeaveThisUnsavedOrUnconfirmedWork5e200a,
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: Text(AppLocalizations.of(context)!.domainStay08fd1d),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: Text(AppLocalizations.of(context)!.domainLeavefc6e4a),
                ),
              ],
            ),
          )) ==
          true;
  @override
  Widget build(BuildContext context) => PopScope(
    canPop: leaving || !dirty,
    onPopInvokedWithResult: (didPop, _) async {
      if (!didPop && await _leave() && mounted) {
        setState(() => leaving = true);
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) Navigator.pop(context);
        });
      }
    },
    child: Scaffold(
      appBar: AppBar(
        title: Text(
          AppLocalizations.of(context)!.domainBusinessAndOutcomes964516,
        ),
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: Column(
              children: [
                Wrap(
                  spacing: 8,
                  children: [
                    for (final item in ['business', 'impact'])
                      TextButton(
                        onPressed: () async {
                          if (section == item || !await _leave() || !mounted) {
                            return;
                          }
                          setState(() {
                            section = item;
                            dirty = false;
                          });
                        },
                        child: Text(
                          item == 'business'
                              ? AppLocalizations.of(
                                  context,
                                )!.domainPrivateBusiness9c181b
                              : AppLocalizations.of(
                                  context,
                                )!.domainSelfReportedImpact0006f1,
                        ),
                      ),
                  ],
                ),
                Expanded(
                  child: section == 'impact'
                      ? _ImpactWorkspace(
                          key: ValueKey('impact:${widget.organizationId}'),
                          organization: widget.organizationId,
                          now: widget.now,
                          onDirty: (value) {
                            if (mounted && dirty != value) {
                              setState(() => dirty = value);
                            }
                          },
                        )
                      : _BusinessWorkspace(
                          key: ValueKey('business:${widget.organizationId}'),
                          organization: widget.organizationId,
                          now: widget.now,
                          initialEnrollmentId: widget.initialEnrollmentId,
                          initialFollowUpId: widget.initialFollowUpId,
                          onDirty: (value) {
                            if (mounted && dirty != value) {
                              setState(() => dirty = value);
                            }
                          },
                        ),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

class _BusinessWorkspace extends ConsumerStatefulWidget {
  final String organization;
  final DateTime Function() now;
  final ValueChanged<bool> onDirty;
  final String? initialEnrollmentId, initialFollowUpId;
  const _BusinessWorkspace({
    super.key,
    required this.organization,
    required this.now,
    required this.onDirty,
    this.initialEnrollmentId,
    this.initialFollowUpId,
  });
  @override
  ConsumerState<_BusinessWorkspace> createState() => _BusinessWorkspaceState();
}

class _BusinessWorkspaceState extends ConsumerState<_BusinessWorkspace>
    with WidgetsBindingObserver {
  List<BusinessEntry> entries = [];
  String? selected;
  String? editingFollow;
  int formEpoch = 0;
  bool busy = false, dirty = false;
  Object? failure;
  AlumniRepository get repository => ref.read(alumniRepositoryProvider);
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(load());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && !dirty) unawaited(load());
  }

  Future<void> load() async {
    if (busy) return;
    setState(() {
      busy = true;
      failure = null;
    });
    try {
      final value = await repository.businesses(widget.organization);
      if (mounted) {
        setState(() {
          entries = value;
          selected = entries.any((e) => e.enrollmentId == selected)
              ? selected
              : widget.initialEnrollmentId == null
              ? entries.firstOrNull?.enrollmentId
              : entries
                    .where((e) => e.enrollmentId == widget.initialEnrollmentId)
                    .firstOrNull
                    ?.enrollmentId;
          final linked = entries
              .where((e) => e.enrollmentId == selected)
              .firstOrNull;
          if (widget.initialFollowUpId != null &&
              linked?.profile?.followUps.any(
                    (f) => f.id == widget.initialFollowUpId,
                  ) ==
                  true) {
            editingFollow = widget.initialFollowUpId;
          }
        });
      }
    } catch (error) {
      if (mounted) setState(() => failure = error);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final entry = entries.where((e) => e.enrollmentId == selected).firstOrNull;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          AppLocalizations.of(
            context,
          )!.domainTheseProfilesArePrivatePublicSharingc4f5b1,
        ),
        if (busy) const LinearProgressIndicator(),
        if (failure != null) _error(context, failure),
        if (!busy &&
            widget.initialEnrollmentId != null &&
            (entry == null ||
                (widget.initialFollowUpId != null &&
                    entry.profile?.followUps.any(
                          (f) => f.id == widget.initialFollowUpId,
                        ) !=
                        true)))
          Text(AppLocalizations.of(context)!.mobileLinkedUnavailable),
        TextButton(
          onPressed: busy || dirty ? null : load,
          child: Text(AppLocalizations.of(context)!.domainRefresh0e9161),
        ),
        if (!busy && entries.isEmpty)
          Text(
            AppLocalizations.of(
              context,
            )!.domainNoEligibleActiveOrCompletedEnrollment98e845,
          ),
        for (final value in entries)
          ListTile(
            title: Text(
              '${AppLocalizations.of(context)!.domainEnrollment2d91aa} ${value.enrollmentId}',
            ),
            selected: selected == value.enrollmentId,
            leading: Icon(
              selected == value.enrollmentId
                  ? Icons.radio_button_checked
                  : Icons.radio_button_off,
            ),
            onTap: dirty
                ? null
                : () => setState(() {
                    selected = value.enrollmentId;
                    editingFollow = null;
                  }),
          ),
        if (entry != null) ...[
          if (dirty)
            TextButton(
              onPressed: () async {
                final discard = await showDialog<bool>(
                  context: context,
                  builder: (context) => AlertDialog(
                    content: Text(
                      AppLocalizations.of(
                        context,
                      )!.domainDiscardThisUnsavedInputAnUnconfirmed91fe23,
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: Text(
                          AppLocalizations.of(context)!.domainStay08fd1d,
                        ),
                      ),
                      TextButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: Text(
                          AppLocalizations.of(context)!.domainDiscardeb1a70,
                        ),
                      ),
                    ],
                  ),
                );
                if (discard == true && mounted) {
                  setState(() {
                    dirty = false;
                    editingFollow = null;
                    formEpoch++;
                  });
                  widget.onDirty(false);
                  unawaited(load());
                }
              },
              child: Text(
                AppLocalizations.of(context)!.domainDiscardUnsavedInput9136d8,
              ),
            ),
          if (editingFollow == null)
            _ProfileEditor(
              key: ValueKey(
                '${entry.enrollmentId}:${entry.profile?.version}:$formEpoch',
              ),
              organization: widget.organization,
              entry: entry,
              repository: repository,
              onDirty: (value) {
                dirty = value;
                widget.onDirty(value);
              },
              onSaved: () {
                dirty = false;
                widget.onDirty(false);
                unawaited(load());
              },
            ),
          if (entry.profile case final profile?) ...[
            ExpansionTile(
              title: Text(
                AppLocalizations.of(
                  context,
                )!.domainImmutableProfileRevisionsLatest20cf668b,
              ),
              children: [
                for (final revision in profile.revisions)
                  ListTile(
                    title: Text(
                      '${AppLocalizations.of(context)!.domainVersiondd1679} ${revision.version} · ${revision.createdAt.toLocal()}',
                    ),
                    subtitle: Text(
                      profileFieldKeys
                          .where((key) => key != 'public_opt_in')
                          .map(
                            (key) =>
                                '${alumniLabel(context, key)}: ${revision.snapshot[key] ?? '—'}',
                          )
                          .join('\n'),
                    ),
                  ),
              ],
            ),
            Text(
              AppLocalizations.of(context)!.domainFollowUpReportsfd330c,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            for (final follow in profile.followUps)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        '${AppLocalizations.of(context)!.domainDue907173} ${follow.dueOn} · ${follow.offsetDays} ${AppLocalizations.of(context)!.domainDaysSavedPolicy6d4582}',
                      ),
                      if (follow.status == 'pending' &&
                          follow.dueOn.compareTo(_today(widget.now)) < 0)
                        Text(AppLocalizations.of(context)!.domainOverdued66094),
                      if (follow.outcome case final outcome?) ...[
                        Text(
                          AppLocalizations.of(
                            context,
                          )!.domainCompletedImmutableSelfReport17ca7c,
                        ),
                        for (final field in outcome.fields.entries)
                          Text(
                            '${alumniLabel(context, field.key)}: ${_display(context, field.value)}',
                          ),
                      ] else if (editingFollow == follow.id)
                        _OutcomeEditor(
                          key: ValueKey('${follow.id}:$formEpoch'),
                          organization: widget.organization,
                          entry: entry,
                          follow: follow,
                          repository: repository,
                          now: widget.now,
                          onDirty: (value) {
                            dirty = value;
                            widget.onDirty(value);
                          },
                          onSaved: () {
                            dirty = false;
                            widget.onDirty(false);
                            unawaited(load());
                          },
                        ),
                      if (follow.outcome == null && editingFollow != follow.id)
                        TextButton(
                          onPressed: dirty
                              ? null
                              : () => setState(() => editingFollow = follow.id),
                          child: Text(
                            AppLocalizations.of(
                              context,
                            )!.domainOpenFollowUpReport53a6b8,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
          ],
        ],
      ],
    );
  }
}

class _ProfileEditor extends StatefulWidget {
  final String organization;
  final BusinessEntry entry;
  final AlumniRepository repository;
  final ValueChanged<bool> onDirty;
  final VoidCallback onSaved;
  const _ProfileEditor({
    super.key,
    required this.organization,
    required this.entry,
    required this.repository,
    required this.onDirty,
    required this.onSaved,
  });
  @override
  State<_ProfileEditor> createState() => _ProfileEditorState();
}

class _ProfileEditorState extends State<_ProfileEditor> {
  late BusinessProfile? saved = widget.entry.profile;
  late Map<String, dynamic> values = saved == null
      ? {
          'name': '',
          'sector': '',
          'products_services': '',
          'stage': 'idea',
          'registration_info': null,
          'started_on': null,
          'team_size': 0,
          'investment_band': 'undisclosed',
          'funding_status': 'none',
          'revenue_band': 'undisclosed',
          'support_needs': null,
          'public_opt_in': false,
        }
      : Map.of(saved!.fields);
  bool busy = false, blocked = false, readback = false;
  BusinessProfile? candidate;
  Object? failure;
  void changed(String key, dynamic value) {
    setState(() => values[key] = value);
    widget.onDirty(true);
  }

  Future<void> save() async {
    if (busy || blocked) return;
    setState(() {
      busy = true;
      failure = null;
    });
    widget.onDirty(true);
    try {
      await widget.repository.saveProfile(
        widget.organization,
        widget.entry.enrollmentId,
        Map.of(values),
        previous: saved,
      );
      if (mounted) widget.onSaved();
    } catch (error) {
      if (mounted) {
        setState(() {
          failure = error;
          blocked =
              error is! ApiFailure ||
              error.uncertain ||
              error.kind == ApiFailureKind.conflict;
          readback = false;
        });
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> reconcile() async {
    if (busy) return;
    setState(() {
      busy = true;
      failure = null;
    });
    try {
      final entries = await widget.repository.businesses(widget.organization);
      final current = entries
          .where((e) => e.enrollmentId == widget.entry.enrollmentId)
          .firstOrNull;
      if (current == null) {
        throw const ApiFailure(
          'enrollment_unavailable',
          kind: ApiFailureKind.notFound,
        );
      }
      if (mounted) {
        setState(() {
          candidate = current.profile;
          readback = true;
        });
      }
    } catch (error) {
      if (mounted) setState(() => failure = error);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text(
        AppLocalizations.of(context)!.domainPrivateBusinessProfilef1fb7d,
        style: Theme.of(context).textTheme.titleLarge,
      ),
      if (busy) const LinearProgressIndicator(),
      if (failure != null) _error(context, failure),
      for (final field in [
        'name',
        'sector',
        'products_services',
        'registration_info',
        'started_on',
        'team_size',
        'support_needs',
      ])
        _field(
          context,
          field,
          values[field]?.toString() ?? '',
          enabled: !busy && !blocked,
          max: field == 'name'
              ? 160
              : field == 'sector'
              ? 120
              : field == 'registration_info'
              ? 240
              : field == 'team_size'
              ? 6
              : field == 'started_on'
              ? 10
              : 4000,
          onChanged: (value) => changed(
            field,
            field == 'team_size'
                ? int.tryParse(value) ?? -1
                : value.isEmpty &&
                      {
                        'registration_info',
                        'started_on',
                        'support_needs',
                      }.contains(field)
                ? null
                : value,
          ),
        ),
      for (final item in [
        ('stage', businessStages),
        ('investment_band', moneyBands),
        ('funding_status', fundingStates),
        ('revenue_band', revenueBands),
      ])
        _choice(
          context,
          item.$1,
          values[item.$1] as String,
          item.$2,
          !busy && !blocked,
          (value) => changed(item.$1, value),
        ),
      if (!blocked)
        FilledButton(
          onPressed: busy ? null : save,
          child: Text(
            AppLocalizations.of(context)!.domainSavePrivateProfile9988a7,
          ),
        ),
      if (blocked) ...[
        TextButton(
          onPressed: busy ? null : reconcile,
          child: Text(AppLocalizations.of(context)!.domainReadSavedStated9f3b0),
        ),
        if (readback) ...[
          Text(
            AppLocalizations.of(
              context,
            )!.domainReviewTheSavedProfileBeforeAnother264cad,
          ),
          Text(
            candidate == null
                ? AppLocalizations.of(
                    context,
                  )!.domainNoProfileExistsForThisEnrollment99706d
                : '${candidate!.fields['name']} · ${AppLocalizations.of(context)!.domainVersiondd1679} ${candidate!.version}',
          ),
          TextButton(
            onPressed: () {
              setState(() {
                saved = candidate;
                if (candidate != null) values = Map.of(candidate!.fields);
                blocked = false;
                readback = false;
                failure = null;
              });
              widget.onDirty(candidate == null);
            },
            child: Text(
              AppLocalizations.of(context)!.domainUseSavedProfile913e70,
            ),
          ),
          TextButton(
            onPressed: () => setState(() {
              saved = candidate;
              blocked = false;
              readback = false;
              failure = null;
            }),
            child: Text(
              AppLocalizations.of(
                context,
              )!.domainKeepMyEditsForExplicitSavea5c95a,
            ),
          ),
        ],
      ],
    ],
  );
}

class _OutcomeEditor extends StatefulWidget {
  final String organization;
  final DateTime Function() now;
  final BusinessEntry entry;
  final BusinessFollowUp follow;
  final AlumniRepository repository;
  final ValueChanged<bool> onDirty;
  final VoidCallback onSaved;
  const _OutcomeEditor({
    super.key,
    required this.organization,
    required this.now,
    required this.entry,
    required this.follow,
    required this.repository,
    required this.onDirty,
    required this.onSaved,
  });
  @override
  State<_OutcomeEditor> createState() => _OutcomeEditorState();
}

class _OutcomeEditorState extends State<_OutcomeEditor> {
  late Map<String, dynamic> values = {
    'reported_on': _today(widget.now),
    'business_started': false,
    'business_active': false,
    'jobs_created': 0,
    'funding_band': 'undisclosed',
    'revenue_band': 'undisclosed',
    'challenges': null,
    'support_requested': null,
    'mentor_interventions': null,
    'outcomes': null,
  };
  bool busy = false, blocked = false;
  Object? failure;
  void changed(String key, dynamic value) {
    setState(() => values[key] = value);
    widget.onDirty(true);
  }

  Future<void> submit() async {
    if (busy || blocked) return;
    setState(() {
      busy = true;
      failure = null;
    });
    widget.onDirty(true);
    try {
      await widget.repository.submitOutcome(
        widget.organization,
        widget.follow.id,
        Map.of(values),
      );
      if (mounted) widget.onSaved();
    } catch (error) {
      if (mounted) {
        setState(() {
          failure = error;
          blocked =
              error is! ApiFailure ||
              error.uncertain ||
              error.kind == ApiFailureKind.conflict;
        });
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> reconcile() async {
    if (busy) return;
    setState(() {
      busy = true;
      failure = null;
    });
    try {
      final entries = await widget.repository.businesses(widget.organization);
      final follow = entries
          .where((e) => e.enrollmentId == widget.entry.enrollmentId)
          .firstOrNull
          ?.profile
          ?.followUps
          .where((f) => f.id == widget.follow.id)
          .firstOrNull;
      if (follow == null) {
        throw const ApiFailure(
          'follow_up_unavailable',
          kind: ApiFailureKind.notFound,
        );
      }
      if (mounted) {
        if (follow.outcome != null) {
          widget.onSaved();
        } else {
          setState(() => blocked = false);
        }
      }
    } catch (error) {
      if (mounted) setState(() => failure = error);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ExpansionTile(
    title: Text(
      AppLocalizations.of(context)!.domainReportThisFollowUpOnce8ce6ce,
    ),
    children: [
      if (busy) const LinearProgressIndicator(),
      if (failure != null) _error(context, failure),
      for (final key in [
        'reported_on',
        'jobs_created',
        'challenges',
        'support_requested',
        'mentor_interventions',
        'outcomes',
      ])
        _field(
          context,
          key,
          values[key]?.toString() ?? '',
          enabled: !busy && !blocked,
          max: key == 'reported_on'
              ? 10
              : key == 'jobs_created'
              ? 6
              : 4000,
          onChanged: (value) => changed(
            key,
            key == 'jobs_created'
                ? int.tryParse(value) ?? -1
                : value.isEmpty && key != 'reported_on'
                ? null
                : value,
          ),
        ),
      for (final key in ['business_started', 'business_active'])
        CheckboxListTile(
          title: Text(alumniLabel(context, key)),
          value: values[key] as bool,
          onChanged: busy || blocked ? null : (value) => changed(key, value!),
        ),
      _choice(
        context,
        'funding_band',
        values['funding_band'] as String,
        moneyBands,
        !busy && !blocked,
        (value) => changed('funding_band', value),
      ),
      _choice(
        context,
        'revenue_band',
        values['revenue_band'] as String,
        revenueBands,
        !busy && !blocked,
        (value) => changed('revenue_band', value),
      ),
      if (blocked)
        TextButton(
          onPressed: busy ? null : reconcile,
          child: Text(
            AppLocalizations.of(
              context,
            )!.domainReadSavedOutcomeBeforeRetry66f67c,
          ),
        )
      else
        FilledButton(
          onPressed: busy ? null : submit,
          child: Text(
            AppLocalizations.of(context)!.domainSubmitImmutableOutcome109e03,
          ),
        ),
    ],
  );
}

class _ImpactWorkspace extends ConsumerStatefulWidget {
  final String organization;
  final DateTime Function() now;
  final ValueChanged<bool> onDirty;
  const _ImpactWorkspace({
    super.key,
    required this.organization,
    required this.now,
    required this.onDirty,
  });
  @override
  ConsumerState<_ImpactWorkspace> createState() => _ImpactWorkspaceState();
}

class _ImpactWorkspaceState extends ConsumerState<_ImpactWorkspace>
    with WidgetsBindingObserver {
  final Map<String, ImpactEnrollment> enrollments = {};
  final Map<String, ImpactDefinition> definitions = {};
  final Map<String, ImpactObservation> records = {};
  String? enrollmentCursor,
      definitionCursor,
      recordCursor,
      enrollmentId,
      definitionId;
  String stage = 'baseline', reason = '', jobs = '0';
  late String observedOn = _today(widget.now);
  bool started = false,
      active = false,
      busy = false,
      blocked = false,
      readbackDone = false,
      dirty = false;
  int expectedRevision = 0;
  Map<String, dynamic>? pending;
  Object? failure;
  AlumniRepository get repository => ref.read(alumniRepositoryProvider);
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(load());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    pending = null;
    records.clear();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && !dirty && !blocked) {
      unawaited(load());
    }
  }

  void changed(VoidCallback change) {
    setState(change);
    dirty = true;
    widget.onDirty(true);
  }

  Future<void> load({String? part}) async {
    if (busy) return;
    setState(() {
      busy = true;
      failure = null;
    });
    try {
      final page = await repository.impact(
        widget.organization,
        enrollmentCursor: part == 'enrollments' ? enrollmentCursor : null,
        definitionCursor: part == 'definitions' ? definitionCursor : null,
        recordCursor: part == 'records' ? recordCursor : null,
      );
      if (!mounted) return;
      setState(() {
        if (part == null) {
          enrollments.clear();
          definitions.clear();
          records.clear();
        }
        if (part == null || part == 'enrollments') {
          for (final item in page.enrollments) {
            enrollments[item.id] = item;
          }
          enrollmentCursor = page.enrollmentCursor;
        }
        for (final item in page.definitions) {
          definitions[item.id] = item;
        }
        if (part == null || part == 'definitions') {
          definitionCursor = page.definitionCursor;
        }
        if (part == null || part == 'records') {
          for (final item in page.records) {
            records[item.id] = item;
          }
          recordCursor = page.recordCursor;
        }
        enrollmentId ??= enrollments.keys.firstOrNull;
        definitionId ??= definitions.values
            .where((d) => d.state == 'published')
            .firstOrNull
            ?.id;
      });
    } catch (error) {
      if (mounted) setState(() => failure = error);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> save({bool replay = false}) async {
    if (busy || (blocked && !(replay && readbackDone))) return;
    final selectedEnrollment = enrollmentId, selectedDefinition = definitionId;
    if (selectedEnrollment == null || selectedDefinition == null) return;
    pending ??= Map.unmodifiable({
      'enrollment_id': selectedEnrollment,
      'definition_id': selectedDefinition,
      'stage': stage,
      'observed_on': observedOn,
      'business_started': started,
      'business_active': active,
      'jobs_created': int.tryParse(jobs) ?? -1,
      'expected_revision': expectedRevision,
      'reason': reason.trim(),
      'request_id': newAlumniRequestId(),
    });
    setState(() {
      busy = true;
      failure = null;
    });
    dirty = true;
    widget.onDirty(true);
    try {
      final result = await repository.recordImpact(
        widget.organization,
        pending!,
      );
      if (!mounted) return;
      setState(() {
        records[result.id] = result;
        expectedRevision = result.revision;
        pending = null;
        blocked = false;
        readbackDone = false;
      });
      dirty = false;
      widget.onDirty(false);
    } catch (error) {
      if (mounted) {
        setState(() {
          failure = error;
          blocked =
              error is! ApiFailure ||
              error.uncertain ||
              error.kind == ApiFailureKind.conflict;
          readbackDone = false;
          if (!blocked) pending = null;
        });
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> readback() async {
    final body = pending;
    if (busy || body == null) return;
    setState(() {
      busy = true;
      failure = null;
    });
    try {
      final page = await repository.impact(
        widget.organization,
        enrollmentId: body['enrollment_id'] as String,
        stage: body['stage'] as String,
        observedOn: body['observed_on'] as String,
      );
      if (!mounted) return;
      final accepted = page.records
          .where((r) => r.requestId == body['request_id'])
          .firstOrNull;
      setState(() {
        for (final value in page.records) {
          records[value.id] = value;
        }
        for (final definition in page.definitions) {
          definitions[definition.id] = definition;
        }
        readbackDone = true;
        if (accepted != null) {
          expectedRevision = accepted.revision;
          pending = null;
          blocked = false;
        }
      });
      if (accepted != null) {
        dirty = false;
        widget.onDirty(false);
      }
    } catch (error) {
      if (mounted) setState(() => failure = error);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void revise(ImpactObservation record) {
    if (busy || dirty || blocked) return;
    changed(() {
      enrollmentId = record.enrollmentId;
      definitionId = record.definitionId;
      stage = record.stage;
      observedOn = record.observedOn;
      expectedRevision = record.revision;
      started = record.businessStarted;
      active = record.businessActive;
      jobs = '${record.jobsCreated}';
      reason = '';
    });
  }

  @override
  Widget build(BuildContext context) {
    final tamil = Localizations.localeOf(context).languageCode == 'ta';
    final definition = definitions[definitionId];
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          AppLocalizations.of(
            context,
          )!.domainSelfReportedObservationsTheseAreSeparate3a51e7,
        ),
        if (busy) const LinearProgressIndicator(),
        if (failure != null) _error(context, failure),
        TextButton(
          onPressed: busy || dirty || blocked ? null : () => load(),
          child: Text(
            AppLocalizations.of(context)!.domainRefreshObservations34ae4c,
          ),
        ),
        if (enrollments.isEmpty)
          Text(AppLocalizations.of(context)!.domainNoEligibleEnrollments16c2f5),
        if (enrollments.isNotEmpty)
          DropdownButtonFormField<String>(
            isExpanded: true,
            initialValue: enrollments.containsKey(enrollmentId)
                ? enrollmentId
                : null,
            decoration: InputDecoration(
              labelText: AppLocalizations.of(context)!.domainEnrollment2d91aa,
            ),
            items: [
              for (final entry in enrollments.values)
                DropdownMenuItem(
                  value: entry.id,
                  child: Text(
                    '${tamil ? entry.nameTa : entry.nameEn} · ${alumniLabel(context, entry.status)}',
                  ),
                ),
            ],
            onChanged: busy || blocked || expectedRevision > 0
                ? null
                : (value) => changed(() => enrollmentId = value),
          ),
        if (enrollmentCursor != null)
          TextButton(
            onPressed: busy ? null : () => load(part: 'enrollments'),
            child: Text(
              AppLocalizations.of(context)!.domainMoreEnrollments6edb68,
            ),
          ),
        if (definitions.isNotEmpty)
          DropdownButtonFormField<String>(
            key: ValueKey('definition:$definitionId'),
            isExpanded: true,
            initialValue: definitions.containsKey(definitionId)
                ? definitionId
                : null,
            decoration: InputDecoration(
              labelText: AppLocalizations.of(
                context,
              )!.domainPinnedDefinitionEdition03b94a,
            ),
            items: [
              for (final value in definitions.values.where(
                (d) => d.state == 'published' || d.id == definitionId,
              ))
                DropdownMenuItem(
                  value: value.id,
                  child: Text(
                    '${tamil ? value.titleTa : value.titleEn} · ${value.edition}',
                  ),
                ),
            ],
            onChanged: busy || blocked || expectedRevision > 0
                ? null
                : (value) => changed(() => definitionId = value),
          ),
        if (definitionCursor != null)
          TextButton(
            onPressed: busy ? null : () => load(part: 'definitions'),
            child: Text(
              AppLocalizations.of(context)!.domainMoreDefinitions6f842b,
            ),
          ),
        if (definition != null)
          Text(tamil ? definition.definitionTa : definition.definitionEn),
        _choice(
          context,
          'stage',
          stage,
          ['baseline', 'outcome'],
          !busy && !blocked && expectedRevision == 0,
          (value) => changed(() => stage = value),
        ),
        _field(
          context,
          'observed_on',
          observedOn,
          enabled: !busy && !blocked && expectedRevision == 0,
          max: 10,
          onChanged: (value) => changed(() => observedOn = value),
        ),
        for (final key in ['business_started', 'business_active'])
          CheckboxListTile(
            title: Text(alumniLabel(context, key)),
            value: key == 'business_started' ? started : active,
            onChanged: busy || blocked
                ? null
                : (value) => changed(() {
                    if (key == 'business_started') {
                      started = value!;
                    } else {
                      active = value!;
                    }
                  }),
          ),
        _field(
          context,
          'jobs_created',
          jobs,
          enabled: !busy && !blocked,
          max: 6,
          onChanged: (value) => changed(() => jobs = value),
        ),
        _field(
          context,
          'reason',
          reason,
          enabled: !busy && !blocked,
          max: 500,
          onChanged: (value) => changed(() => reason = value),
        ),
        if (!blocked)
          FilledButton(
            onPressed: busy || enrollmentId == null || definitionId == null
                ? null
                : () => save(),
            child: Text(
              expectedRevision == 0
                  ? AppLocalizations.of(context)!.mobileSubmitSelfReport
                  : AppLocalizations.of(context)!.mobileSaveRevision,
            ),
          ),
        if (blocked) ...[
          TextButton(
            onPressed: busy ? null : readback,
            child: Text(
              AppLocalizations.of(
                context,
              )!.domainReadExactObservationStatee6cbb6,
            ),
          ),
          if (readbackDone) ...[
            TextButton(
              onPressed: busy ? null : () => save(replay: true),
              child: Text(
                AppLocalizations.of(
                  context,
                )!.domainExplicitlyRetryUnchangedRequest0c8f5a,
              ),
            ),
            TextButton(
              onPressed: busy
                  ? null
                  : () {
                      setState(() {
                        pending = null;
                        blocked = false;
                        readbackDone = false;
                        expectedRevision = 0;
                        dirty = false;
                      });
                      widget.onDirty(false);
                    },
              child: Text(
                AppLocalizations.of(
                  context,
                )!.domainDiscardPendingRequestChooseACurrent24ad4d,
              ),
            ),
          ],
        ],
        TextButton(
          onPressed: busy || blocked
              ? null
              : () {
                  setState(() {
                    expectedRevision = 0;
                    reason = '';
                    observedOn = _today(widget.now);
                  });
                  dirty = false;
                  widget.onDirty(false);
                },
          child: Text(
            AppLocalizations.of(context)!.domainStartAnotherObservatione8e1c1,
          ),
        ),
        Text(
          AppLocalizations.of(
            context,
          )!.domainObservationHistoryEachRevisionIsRetaineda9da2a,
          style: Theme.of(context).textTheme.titleLarge,
        ),
        for (final record in records.values)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    '${alumniLabel(context, record.stage)} · ${record.observedOn} · ${AppLocalizations.of(context)!.domainRevision2e516d} ${record.revision}',
                  ),
                  Text(
                    '${tamil ? definitions[record.definitionId]?.titleTa ?? record.definitionId : definitions[record.definitionId]?.titleEn ?? record.definitionId} · ${definitions[record.definitionId]?.edition ?? '—'}',
                  ),
                  Text(
                    '${alumniLabel(context, 'business_started')}: ${_display(context, record.businessStarted)}\n${alumniLabel(context, 'business_active')}: ${_display(context, record.businessActive)}\n${alumniLabel(context, 'jobs_created')}: ${record.jobsCreated}\n${record.reason}',
                  ),
                  TextButton(
                    onPressed: busy || dirty || blocked
                        ? null
                        : () => revise(record),
                    child: Text(
                      AppLocalizations.of(
                        context,
                      )!.domainSupersedeWithAReason4294f3,
                    ),
                  ),
                ],
              ),
            ),
          ),
        if (recordCursor != null)
          TextButton(
            onPressed: busy ? null : () => load(part: 'records'),
            child: Text(
              AppLocalizations.of(context)!.domainMoreObservationHistory11b7c2,
            ),
          ),
      ],
    );
  }
}

String _today(DateTime Function() now) =>
    now().toUtc().toIso8601String().substring(0, 10);
Widget _error(BuildContext context, Object? error) => Semantics(
  liveRegion: true,
  child: Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Text(alumniFailure(context, error)),
  ),
);
String _display(BuildContext context, Object? value) => value == null
    ? '—'
    : value is bool
    ? value
          ? AppLocalizations.of(context)!.mobileYes
          : AppLocalizations.of(context)!.mobileNo
    : value is String
    ? alumniLabel(context, value)
    : '$value';
Widget _field(
  BuildContext context,
  String key,
  String value, {
  required bool enabled,
  required int max,
  required ValueChanged<String> onChanged,
}) => _AlumniField(
  key: ValueKey(key),
  field: key,
  value: value,
  enabled: enabled,
  max: max,
  onChanged: onChanged,
);

class _AlumniField extends StatefulWidget {
  final String field, value;
  final bool enabled;
  final int max;
  final ValueChanged<String> onChanged;
  const _AlumniField({
    super.key,
    required this.field,
    required this.value,
    required this.enabled,
    required this.max,
    required this.onChanged,
  });
  @override
  State<_AlumniField> createState() => _AlumniFieldState();
}

class _AlumniFieldState extends State<_AlumniField> {
  late final controller = TextEditingController(text: widget.value);
  @override
  void didUpdateWidget(covariant _AlumniField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (controller.text != widget.value) {
      controller.value = TextEditingValue(
        text: widget.value,
        selection: TextSelection.collapsed(offset: widget.value.length),
      );
    }
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: TextField(
      controller: controller,
      enabled: widget.enabled,
      maxLength: widget.max,
      maxLines: widget.max >= 500 ? 3 : 1,
      decoration: InputDecoration(
        labelText: alumniLabel(context, widget.field),
        border: const OutlineInputBorder(),
      ),
      onChanged: widget.onChanged,
    ),
  );
}

Widget _choice(
  BuildContext context,
  String key,
  String value,
  List<String> options,
  bool enabled,
  ValueChanged<String> onChanged,
) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 6),
  child: DropdownButtonFormField<String>(
    key: ValueKey('$key:$value'),
    initialValue: value,
    isExpanded: true,
    decoration: InputDecoration(
      labelText: alumniLabel(context, key),
      border: const OutlineInputBorder(),
    ),
    items: [
      for (final option in options)
        DropdownMenuItem(
          value: option,
          child: Text(alumniLabel(context, option)),
        ),
    ],
    onChanged: enabled ? (value) => onChanged(value!) : null,
  ),
);
