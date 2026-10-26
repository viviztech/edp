import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_failure.dart';
import '../../core/attendance/attendance_scanner.dart';
import '../../l10n/app_localizations.dart';
import '../../core/files/private_files.dart';
import '../../core/files/providers.dart';
import 'assignment_files.dart';
import 'learning_models.dart';
import 'learning_repository.dart';
import 'learning_words.dart';
import 'student_controller.dart';

class StudentPage extends ConsumerStatefulWidget {
  final String organizationId, initialSection;
  final String? initialCourseId, initialLessonId;
  const StudentPage({
    super.key,
    required this.organizationId,
    this.initialSection = 'learning',
    this.initialCourseId,
    this.initialLessonId,
  });
  @override
  ConsumerState<StudentPage> createState() => _StudentPageState();
}

class _StudentPageState extends ConsumerState<StudentPage>
    with WidgetsBindingObserver {
  late StudentController model;
  late String section;
  final token = TextEditingController();
  PrivateFileScope? _scope;
  PrivateSnapshot? receipt;
  CancelToken? _transfer;
  bool _privateBusy = false, _leaving = false, _foreground = true;
  ApiFailure? _privateFailure;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    section =
        {'learning', 'schedule', 'attendance'}.contains(widget.initialSection)
        ? widget.initialSection
        : 'learning';
    _initialize();
  }

  void _initialize() {
    model = StudentController(
      ref.read(learningRepositoryProvider),
      organizationId: widget.organizationId,
    )..addListener(_changed);
    unawaited(
      Future.wait([
        model.loadLearning(),
        model.loadSchedule(),
        model.loadAttendance(),
      ]),
    );
  }

  @override
  void didUpdateWidget(StudentPage old) {
    super.didUpdateWidget(old);
    if (old.organizationId != widget.organizationId) {
      model.removeListener(_changed);
      model.dispose();
      _transfer?.cancel();
      unawaited(_releaseReceipt());
      unawaited(_scope?.close() ?? Future.value());
      _scope = null;
      _privateBusy = false;
      _privateFailure = null;
      token.clear();
      _initialize();
    }
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if ({
      AppLifecycleState.paused,
      AppLifecycleState.hidden,
      AppLifecycleState.detached,
    }.contains(state)) {
      _foreground = false;
      _transfer?.cancel();
      unawaited(_releaseReceipt());
      token.clear();
    }
    if (state == AppLifecycleState.resumed) {
      _foreground = true;
      unawaited(model.loadSchedule());
      if (model.needsReview) {
        unawaited(model.reconcile());
      } else {
        unawaited(model.loadLearning());
        unawaited(model.loadAttendance());
      }
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    model.removeListener(_changed);
    model.dispose();
    token.dispose();
    _transfer?.cancel();
    unawaited(_cleanup());
    super.dispose();
  }

  Future<void> _cleanup() async {
    try {
      await _releaseReceipt(notify: false);
    } finally {
      try {
        await _scope?.close();
      } catch (_) {}
    }
  }

  Future<void> _releaseReceipt({bool notify = true}) async {
    final copy = receipt;
    receipt = null;
    if (copy != null) {
      try {
        await copy.dispose();
      } catch (_) {}
    }
    if (notify && mounted) setState(() {});
  }

  String _date(DateTime at) => DateFormat.yMMMd(
    Localizations.localeOf(context).languageCode,
  ).add_jm().format(at.toLocal());
  Future<void> _leave() async {
    if (model.busy || _privateBusy) return;
    final text = LearningWords(context);
    final leave = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(text['leave']),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(text['stay']),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(text['leaveAction']),
          ),
        ],
      ),
    );
    if (leave == true && mounted) {
      setState(() => _leaving = true);
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = LearningWords(context);
    return PopScope(
      canPop: _leaving || (!model.blocksNavigation && !_privateBusy),
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) unawaited(_leave());
      },
      child: Scaffold(
        appBar: AppBar(title: Text(text['title'])),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final value in ['learning', 'schedule', 'attendance'])
                  ChoiceChip(
                    label: Text(text[value]),
                    selected: section == value,
                    onSelected: (_) => setState(() => section = value),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            if (model.busy || _privateBusy) const LinearProgressIndicator(),
            if (model.commandFailure case final error?)
              Semantics(liveRegion: true, child: Text(text.failure(error))),
            if (model.notice == 'saved')
              Semantics(liveRegion: true, child: Text(text['saved'])),
            if (model.needsReview) ...[
              Text(text['uncertain']),
              TextButton(
                onPressed: model.busy || model.retryDelayed
                    ? null
                    : model.reconcile,
                child: Text(text['readback']),
              ),
              if (model.readbackReady)
                FilledButton(
                  onPressed: model.busy ? null : model.acknowledgeReadback,
                  child: Text(text['continue']),
                ),
            ],
            if (_privateFailure case final error?) Text(text.failure(error)),
            if (receipt case final copy?)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(text['receipt']),
                      Text(
                        '${copy.mediaType} · ${copy.byteSize} ${text['bytes']}',
                      ),
                      SelectableText(copy.sha256),
                      Text(text['privateReceipt']),
                      TextButton(
                        onPressed: _releaseReceipt,
                        child: Text(text['close']),
                      ),
                    ],
                  ),
                ),
              ),
            if (section == 'learning') ..._learning(text),
            if (section == 'schedule') ..._schedule(text),
            if (section == 'attendance') ..._attendance(text),
            if (model.dirty)
              TextButton(
                onPressed: model.busy || model.fileLocks.isNotEmpty
                    ? null
                    : () => setState(model.discardInputs),
                child: Text(text['discard']),
              ),
          ],
        ),
      ),
    );
  }

  List<Widget> _learning(LearningWords text) => [
    TextButton(
      onPressed: model.busy ? null : model.loadLearning,
      child: Text(text['refresh']),
    ),
    if (model.loadingLearning) Text(text['loading']),
    if (model.learningFailure case final error?) Text(text.failure(error)),
    if (!model.loadingLearning &&
        model.learningFailure == null &&
        model.courses.isEmpty)
      Text(text['empty']),
    if (!model.loadingLearning &&
        model.learningFailure == null &&
        widget.initialCourseId != null &&
        _linkedCourses.isEmpty)
      Text(AppLocalizations.of(context)!.mobileLinkedUnavailable),
    for (final course in _linkedCourses)
      Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                course.title.text(text.tamil),
                style: Theme.of(context).textTheme.titleLarge,
              ),
              Text(course.description.text(text.tamil)),
              Text(
                '${text['progress']}: ${course.percent}% (${course.completedLessons}/${course.requiredLessons})',
              ),
              LinearProgressIndicator(value: course.percent / 100),
              if (course.enrollmentVersion == null)
                FilledButton(
                  onPressed: model.canCommand
                      ? () => model.start(course)
                      : null,
                  child: Text(text['start']),
                ),
              for (final module in course.modules)
                ExpansionTile(
                  initiallyExpanded:
                      widget.initialLessonId != null &&
                      module.lessons.any(
                        (lesson) => lesson.id == widget.initialLessonId,
                      ),
                  title: Text(module.title.text(text.tamil)),
                  children: [
                    for (final lesson in module.lessons)
                      _lesson(text, course, lesson),
                  ],
                ),
              const SizedBox(height: 12),
              Text(
                text['certificate'],
                style: Theme.of(context).textTheme.titleMedium,
              ),
              Text(text[course.eligible ? 'eligible' : 'ineligible']),
              for (final reason in course.blockingReasons) Text(text[reason]),
              if (course.certificate case final certificate?) ...[
                Text(certificate.title.text(text.tamil)),
                Text(certificate.statement.text(text.tamil)),
                Text(
                  '${text[certificate.status]} · ${_date(certificate.issuedAt)}',
                ),
                Text(certificate.issuer),
                SelectableText(certificate.code),
                OutlinedButton(
                  onPressed: _privateBusy
                      ? null
                      : () => _verify(certificate.code),
                  child: Text(text['verify']),
                ),
              ],
            ],
          ),
        ),
      ),
  ];
  Iterable<LearningCourse> get _linkedCourses => model.courses.where(
    (course) =>
        (widget.initialCourseId == null ||
            course.id == widget.initialCourseId) &&
        (widget.initialLessonId == null ||
            course.lessons.any(
              (lesson) => lesson.id == widget.initialLessonId,
            )),
  );
  Widget _lesson(
    LearningWords text,
    LearningCourse course,
    LearningLesson lesson,
  ) => Padding(
    padding: const EdgeInsets.all(12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          lesson.title.text(text.tamil),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        if (lesson.locked)
          Text(text['locked'])
        else ...[
          Text(lesson.body.text(text.tamil)),
          if (lesson.completed)
            Text(text['completed'])
          else
            OutlinedButton(
              onPressed: model.canCommand
                  ? () => model.complete(course, lesson)
                  : null,
              child: Text(text['complete']),
            ),
          if (lesson.materials.isNotEmpty) Text(text['materialLimit']),
          for (final material in lesson.materials)
            TextButton(
              onPressed: model.canCommand && !_privateBusy && material.available
                  ? () => _material(course, material)
                  : null,
              child: Text(
                '${text['material']}: ${material.label.text(text.tamil)}',
              ),
            ),
          for (final quiz in lesson.quizzes) _quiz(text, course, quiz),
          for (final assignment in lesson.assignments)
            StudentAssignmentCard(
              key: ValueKey(
                '${widget.organizationId}:${course.id}:${assignment.id}',
              ),
              model: model,
              course: course,
              assignment: assignment,
            ),
        ],
      ],
    ),
  );
  Widget _quiz(
    LearningWords text,
    LearningCourse course,
    LearningQuiz quiz,
  ) => Card(
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            quiz.title.text(text.tamil),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text(quiz.instructions.text(text.tamil)),
          Text('${text['attempts']}: ${quiz.remainingAttempts}'),
          if (quiz.bestPercent != null)
            Text(
              '${text['score']}: ${quiz.bestPercent}% · ${text[quiz.passed ? 'passed' : 'failed']}',
            ),
          for (final question in quiz.questions) ...[
            Text(question.prompt.text(text.tamil)),
            RadioGroup<String>(
              groupValue: model.quizAnswers[quiz.id]?[question.id],
              onChanged: (value) {
                if (value != null) model.setQuiz(quiz.id, question.id, value);
              },
              child: Column(
                children: [
                  for (final choice in question.choices)
                    RadioListTile<String>(
                      title: Text(choice.label.text(text.tamil)),
                      value: choice.id,
                      enabled:
                          model.canCommand &&
                          quiz.available &&
                          quiz.remainingAttempts > 0 &&
                          !quiz.passed,
                    ),
                ],
              ),
            ),
          ],
          FilledButton(
            onPressed:
                model.canCommand &&
                    quiz.available &&
                    quiz.remainingAttempts > 0 &&
                    !quiz.passed
                ? () => model.submitQuiz(course, quiz)
                : null,
            child: Text(text['submitQuiz']),
          ),
        ],
      ),
    ),
  );
  List<Widget> _schedule(LearningWords text) => [
    TextButton(
      onPressed: model.loadingSchedule ? null : model.loadSchedule,
      child: Text(text['refresh']),
    ),
    if (model.loadingSchedule) Text(text['loading']),
    if (model.scheduleFailure case final error?) Text(text.failure(error)),
    if (model.schedule case final schedule?) ...[
      if (schedule.sessions.isEmpty && schedule.events.isEmpty)
        Text(text['empty']),
      for (final session in schedule.sessions)
        Card(
          child: ListTile(
            title: Text(session.title.text(text.tamil)),
            subtitle: Text(
              '${_date(session.startsAt)} – ${_date(session.endsAt)}\n${text[session.status]} · ${text[session.mode]}${session.location == null ? '' : '\n${session.location}'}',
            ),
          ),
        ),
      for (final event in schedule.events)
        ListTile(
          title: Text(event.title.text(text.tamil)),
          subtitle: Text('${text[event.kind]} · ${_date(event.at)}'),
        ),
    ],
  ];
  List<Widget> _attendance(LearningWords text) => [
    TextButton(
      onPressed: model.busy ? null : model.loadAttendance,
      child: Text(text['refresh']),
    ),
    Text(AppLocalizations.of(context)!.attendanceScanExplanation),
    OutlinedButton.icon(
      onPressed: model.canCommand && !_privateBusy ? _scanAttendance : null,
      icon: const Icon(Icons.qr_code_scanner),
      label: Text(AppLocalizations.of(context)!.attendanceScan),
    ),
    TextField(
      controller: token,
      maxLength: 143,
      autocorrect: false,
      enableSuggestions: false,
      decoration: InputDecoration(labelText: text['token']),
      enabled: model.canCommand && !_privateBusy,
    ),
    FilledButton(
      onPressed: model.canCommand && !_privateBusy
          ? () async {
              final value = token.text;
              token.clear();
              await model.checkIn(value);
            }
          : null,
      child: Text(text['checkIn']),
    ),
    if (model.loadingAttendance) Text(text['loading']),
    if (model.attendanceFailure case final error?) Text(text.failure(error)),
    if (!model.loadingAttendance &&
        model.attendanceFailure == null &&
        model.attendance.isEmpty)
      Text(text['empty']),
    for (final enrollment in model.attendance)
      Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                enrollment.cohort.text(text.tamil),
                style: Theme.of(context).textTheme.titleMedium,
              ),
              Text(
                '${text['attended']}: ${enrollment.attended}/${enrollment.required} · ${enrollment.percent}%',
              ),
              Text('${text['threshold']}: ${enrollment.threshold}%'),
              if (enrollment.lowAttendance) Text(text['lowAttendance']),
              for (final session in enrollment.sessions)
                ListTile(
                  title: Text(session.title.text(text.tamil)),
                  subtitle: Text(
                    '${_date(session.startsAt)} – ${_date(session.endsAt)}\n${text[session.status]} · ${text[session.attendanceStatus ?? 'unmarked']}',
                  ),
                ),
            ],
          ),
        ),
      ),
  ];
  Future<void> _scanAttendance() async {
    final current = model;
    final text = AppLocalizations.of(context)!;
    setState(() {
      _privateBusy = true;
      _privateFailure = null;
    });
    try {
      final value = await ref
          .read(attendanceScannerProvider)
          .scan(
            instruction: text.attendanceScanExplanation,
            cancel: text.learnCancel,
          );
      if (mounted && current == model && _foreground && value != null) {
        token.text = value;
      }
    } on ApiFailure catch (error) {
      if (mounted && current == model) {
        setState(() => _privateFailure = error);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error.code == 'invalid_attendance_token'
                  ? text.attendanceScanInvalid
                  : text.attendanceScanUnavailable,
            ),
          ),
        );
      }
    } finally {
      if (mounted && current == model) setState(() => _privateBusy = false);
    }
  }

  Future<void> _material(
    LearningCourse course,
    LearningMaterial material,
  ) async {
    setState(() {
      _privateBusy = true;
      _privateFailure = null;
    });
    final current = model;
    _transfer = CancelToken();
    try {
      final store = ref.read(privateFilesProvider);
      if (!store.supported) {
        throw const ApiFailure(
          'private_files_unsupported',
          kind: ApiFailureKind.unavailable,
        );
      }
      final scope = _scope ?? await store.createScope();
      if (!mounted || model != current || !_foreground) {
        await scope.close();
        return;
      }
      _scope = scope;
      final copy = await current.repository.material(
        widget.organizationId,
        course.id,
        material.id,
        _scope!,
        cancelToken: _transfer,
      );
      if (!mounted || model != current || !_foreground) {
        await copy.dispose();
        return;
      }
      await _releaseReceipt();
      if (!mounted || model != current || !_foreground) {
        await copy.dispose();
        return;
      }
      setState(() => receipt = copy);
    } catch (error) {
      if (mounted && model == current) {
        setState(
          () => _privateFailure = error is ApiFailure
              ? error
              : const ApiFailure(
                  'material_unavailable',
                  kind: ApiFailureKind.unavailable,
                ),
        );
      }
    } finally {
      if (mounted && model == current) setState(() => _privateBusy = false);
    }
  }

  Future<void> _verify(String code) async {
    final current = model;
    setState(() {
      _privateBusy = true;
      _privateFailure = null;
    });
    try {
      final result = await current.repository.verify(code);
      if (!mounted || current != model || !_foreground) return;
      final text = LearningWords(context);
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(result.title.text(text.tamil)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(result.course.text(text.tamil)),
                Text(text[result.status]),
                Text(result.issuer),
                Text(_date(result.issuedAt)),
                Semantics(
                  label: text['qr'],
                  image: true,
                  child: SizedBox(
                    width: 240,
                    height: 240,
                    child: CustomPaint(
                      painter: CertificateQrPainter(result.qr),
                    ),
                  ),
                ),
                SelectableText(code),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(text['cancel']),
            ),
          ],
        ),
      );
    } catch (error) {
      if (mounted && current == model) {
        setState(
          () => _privateFailure = error is ApiFailure
              ? error
              : const ApiFailure(
                  'verification_unavailable',
                  kind: ApiFailureKind.unavailable,
                ),
        );
      }
    } finally {
      if (mounted && current == model) setState(() => _privateBusy = false);
    }
  }
}

class CertificateQrPainter extends CustomPainter {
  final CertificateQr qr;
  CertificateQrPainter(this.qr);
  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = Colors.white);
    final scale = size.shortestSide / qr.dimension;
    final paint = Paint()
      ..color = Colors.black
      ..isAntiAlias = false;
    for (final square in qr.squares) {
      canvas.drawRect(
        Rect.fromLTWH(
          square.$1 * scale,
          square.$2 * scale,
          square.$3 * scale,
          square.$3 * scale,
        ),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(CertificateQrPainter oldDelegate) => oldDelegate.qr != qr;
}

class StudentAssignmentCard extends ConsumerStatefulWidget {
  final StudentController model;
  final LearningCourse course;
  final LearningAssignment assignment;
  const StudentAssignmentCard({
    super.key,
    required this.model,
    required this.course,
    required this.assignment,
  });
  @override
  ConsumerState<StudentAssignmentCard> createState() =>
      _StudentAssignmentCardState();
}

class _StudentAssignmentCardState extends ConsumerState<StudentAssignmentCard>
    with WidgetsBindingObserver {
  AssignmentFilesController? files;
  late TextEditingController response;
  PrivateSnapshot? receipt;
  bool opening = true;
  bool _foreground = true;
  CancelToken? _downloadToken;
  ApiFailure? scopeFailure;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    response = TextEditingController(
      text: widget.model.assignmentText[widget.assignment.id] ?? '',
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) unawaited(_initialize());
    });
  }

  Future<void> _initialize() async {
    PrivateFileScope? scope;
    try {
      final store = ref.read(privateFilesProvider);
      if (store.supported) scope = await store.createScope();
    } catch (error) {
      scopeFailure = error is ApiFailure
          ? error
          : const ApiFailure(
              'private_files_unavailable',
              kind: ApiFailureKind.unavailable,
            );
      /* Metadata and text remain available. */
    }
    if (!mounted) {
      await scope?.close();
      return;
    }
    files = AssignmentFilesController(
      ref.read(assignmentFilesRepositoryProvider),
      scope,
      org: widget.model.organizationId,
      course: widget.course.id,
      assignment: widget.assignment.id,
    )..addListener(_changed);
    setState(() => opening = false);
    await files!.load();
  }

  void _retryProtectedStorage() {
    if (opening || files?.busy == true || files?.hasPending == true) return;
    files?.removeListener(_changed);
    files?.dispose();
    files = null;
    setState(() {
      opening = true;
      scopeFailure = null;
    });
    unawaited(_initialize());
  }

  void _changed() {
    if (!mounted) return;
    widget.model.setFileLock(
      widget.assignment.id,
      files!.busy || files!.hasPending,
    );
    setState(() {});
  }

  @override
  void didUpdateWidget(StudentAssignmentCard old) {
    super.didUpdateWidget(old);
    if (old.assignment.submissions.length !=
        widget.assignment.submissions.length) {
      unawaited(files?.load());
    }
    final current = widget.model.assignmentText[widget.assignment.id] ?? '';
    if (current != response.text) response.text = current;
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if ({
      AppLifecycleState.paused,
      AppLifecycleState.hidden,
      AppLifecycleState.detached,
    }.contains(state)) {
      _foreground = false;
      _downloadToken?.cancel();
      files?.pause();
      unawaited(_release());
    }
    if (state == AppLifecycleState.resumed) {
      _foreground = true;
      unawaited(files?.resume());
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    final controller = files;
    controller?.removeListener(_changed);
    controller?.dispose();
    _downloadToken?.cancel();
    response.dispose();
    unawaited(_release(notify: false));
    super.dispose();
  }

  Future<void> _release({bool notify = true}) async {
    final copy = receipt;
    receipt = null;
    if (copy != null) {
      try {
        await copy.dispose();
      } catch (_) {}
    }
    if (notify && mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final text = LearningWords(context),
        assignment = widget.assignment,
        model = widget.model,
        controller = files;
    final enabled = model.canEditFile(assignment.id);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              assignment.title.text(text.tamil),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(assignment.instructions.text(text.tamil)),
            Text('${text['remaining']}: ${assignment.remainingSubmissions}'),
            for (final submission in assignment.submissions) ...[
              Text(
                '${submission.revision} · ${DateFormat.yMMMd(text.tamil ? 'ta' : 'en').add_jm().format(submission.submittedAt.toLocal())}',
              ),
              Text(submission.response),
              if (submission.score == null)
                Text(text['pendingReview'])
              else ...[
                Text(
                  '${submission.score}/${assignment.maximumPoints} · ${text[submission.passed == true ? 'passed' : 'failed']}',
                ),
                Text('${text['feedback']}: ${submission.feedback}'),
              ],
            ],
            TextField(
              controller: response,
              maxLength: 10000,
              minLines: 3,
              maxLines: 8,
              decoration: InputDecoration(labelText: text['response']),
              enabled:
                  model.canCommand &&
                  assignment.available &&
                  assignment.remainingSubmissions > 0 &&
                  !assignment.awaitingReview,
              onChanged: (value) => model.setAssignment(assignment.id, value),
            ),
            if (opening) Text(text['loading']),
            if (scopeFailure case final failure?) Text(text.failure(failure)),
            if (!opening &&
                controller?.scope == null &&
                ref.read(privateFilesProvider).supported)
              TextButton(
                onPressed: controller?.busy == true
                    ? null
                    : _retryProtectedStorage,
                child: Text(AppLocalizations.of(context)!.fileRetryProtection),
              ),
            if (controller != null) ...[
              Text(
                text['files'],
                style: Theme.of(context).textTheme.titleSmall,
              ),
              if (controller.busy) const LinearProgressIndicator(),
              if (controller.failure case final error?)
                Text(text.failure(error)),
              if (controller.batch case final batch?) ...[
                if (!batch.collectionEnabled) Text(text['disabled']),
                if (controller.scope == null && scopeFailure == null)
                  Text(text['nativeRequired']),
                if (batch.rule case final rule?) ...[
                  Text(rule.notice.text(text.tamil)),
                  Text(
                    '${text['limits']}: ${rule.minimum}–${rule.maximum} ${text['count']}, ${batch.effectiveBytes} ${text['bytes']}',
                  ),
                  Text(rule.types.join(', ')),
                ],
                for (final file in batch.items) ...[
                  Text(
                    '${text[file.fileState]} · ${file.mediaType} · ${file.byteSize} ${text['bytes']}',
                  ),
                  SelectableText(file.sha256),
                  if (!file.usable) Text(text['unusable']),
                  if (file.frozenAt != null)
                    Text(
                      '${text['frozen']}: ${file.frozenVersion} · ${file.frozenAt!.toLocal()}',
                    ),
                  Wrap(
                    spacing: 8,
                    children: [
                      if (file.state == 'active' && file.fileState == 'pending')
                        TextButton(
                          onPressed:
                              enabled &&
                                  !controller.busy &&
                                  !controller.hasPending
                              ? () => controller.pick(existing: file)
                              : null,
                          child: Text(text['reselect']),
                        ),
                      if (file.state == 'active')
                        TextButton(
                          onPressed:
                              enabled &&
                                  !controller.busy &&
                                  !controller.hasPending
                              ? () => _remove(file)
                              : null,
                          child: Text(text['remove']),
                        ),
                      if (file.usable &&
                          controller.scope != null &&
                          batch.collectionEnabled)
                        TextButton(
                          onPressed: enabled && !controller.busy
                              ? () => _download(file)
                              : null,
                          child: Text(text['download']),
                        ),
                    ],
                  ),
                ],
                if (batch.collectionEnabled &&
                    batch.rule != null &&
                    controller.scope != null)
                  OutlinedButton(
                    onPressed:
                        enabled &&
                            controller.canPick &&
                            batch.staged.length < batch.rule!.maximum &&
                            assignment.available &&
                            !assignment.awaitingReview
                        ? controller.pick
                        : null,
                    child: Text(text['choose']),
                  ),
              ],
              if (controller.selected case final selected?) ...[
                Text(text['selected']),
                Text('${selected.byteSize} ${text['bytes']}'),
                SelectableText(selected.sha256),
                if (controller.pending == null)
                  TextButton(
                    onPressed:
                        enabled && !controller.busy && !controller.retryDelayed
                        ? controller.recoverIntent
                        : null,
                    child: Text(text['recover']),
                  ),
                if (controller.pending?.fileState == 'pending' &&
                    !controller.needsReadback)
                  FilledButton(
                    onPressed:
                        enabled && !controller.busy && !controller.retryDelayed
                        ? controller.upload
                        : null,
                    child: Text(text['upload']),
                  ),
              ],
              if (controller.needsReadback)
                TextButton(
                  onPressed:
                      enabled && !controller.busy && !controller.retryDelayed
                      ? controller.reconcile
                      : null,
                  child: Text(text['readback']),
                ),
              if (controller.hasPending)
                TextButton(
                  onPressed: !controller.busy ? controller.discard : null,
                  child: Text(text['discardSelection']),
                ),
              TextButton(
                onPressed: enabled && !controller.busy ? controller.load : null,
                child: Text(text['refresh']),
              ),
              FilledButton(
                onPressed:
                    model.canCommand &&
                        assignment.available &&
                        assignment.remainingSubmissions > 0 &&
                        !assignment.awaitingReview &&
                        controller.ready
                    ? () async {
                        await model.submitAssignment(
                          widget.course,
                          assignment,
                          controller.batch!.usableIds,
                        );
                        await controller.load();
                      }
                    : null,
                child: Text(text['submitAssignment']),
              ),
            ],
            if (receipt case final copy?) ...[
              Text(text['receipt']),
              Text('${copy.mediaType} · ${copy.byteSize} ${text['bytes']}'),
              SelectableText(copy.sha256),
              TextButton(onPressed: _release, child: Text(text['close'])),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _remove(AssignmentAttachment file) async {
    final text = LearningWords(context);
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(text['confirmRemove']),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(text['cancel']),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(text['confirm']),
          ),
        ],
      ),
    );
    if (yes == true && mounted) await files!.remove(file);
  }

  Future<void> _download(AssignmentAttachment file) async {
    final controller = files!;
    if (controller.busy || !_foreground) return;
    controller.busy = true;
    _downloadToken = CancelToken();
    _changed();
    try {
      final copy = await controller.repository.download(
        controller.org,
        controller.course,
        controller.assignment,
        file,
        controller.scope!,
        _downloadToken!,
      );
      if (!mounted || !_foreground || controller.scope?.closed != false) {
        await copy.dispose();
        return;
      }
      await _release();
      if (!mounted || !_foreground || controller.scope?.closed != false) {
        await copy.dispose();
        return;
      }
      setState(() => receipt = copy);
    } on ApiFailure catch (error) {
      if (mounted) {
        controller.failure = error;
        setState(() {});
      }
    } finally {
      if (mounted) {
        controller.busy = false;
        _downloadToken = null;
        _changed();
      }
    }
  }
}
