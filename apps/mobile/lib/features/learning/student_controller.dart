import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../core/api/api_failure.dart';
import 'learning_models.dart';
import 'learning_repository.dart';

class StudentController extends ChangeNotifier {
  final LearningRepository repository;
  final String organizationId;
  List<LearningCourse> courses = [];
  StudentTimeline? schedule;
  List<StudentAttendance> attendance = [];
  ApiFailure? learningFailure,
      scheduleFailure,
      attendanceFailure,
      commandFailure;
  bool loadingLearning = false,
      loadingSchedule = false,
      loadingAttendance = false,
      busy = false;
  bool needsReview = false, readbackReady = false, commandAcknowledged = false;
  final Map<String, Map<String, String>> quizAnswers = {};
  final Map<String, String> assignmentText = {};
  final Set<String> fileLocks = {};
  String? notice;
  bool _closed = false;
  int _learningGeneration = 0,
      _scheduleGeneration = 0,
      _attendanceGeneration = 0;
  DateTime? _retryUntil;
  Timer? _retry;
  StudentController(this.repository, {required this.organizationId});
  bool get retryDelayed => _retryUntil?.isAfter(DateTime.now().toUtc()) == true;
  bool get canCommand =>
      !_closed && !busy && !needsReview && !retryDelayed && fileLocks.isEmpty;
  bool canEditFile(String id) =>
      !_closed &&
      !busy &&
      !needsReview &&
      !retryDelayed &&
      fileLocks.every((value) => value == id);
  bool get dirty =>
      assignmentText.values.any((value) => value.isNotEmpty) ||
      quizAnswers.values.any((value) => value.isNotEmpty);
  bool get blocksNavigation =>
      busy || needsReview || fileLocks.isNotEmpty || dirty;
  void _emit() {
    if (!_closed) notifyListeners();
  }

  ApiFailure _safe(Object error) => error is ApiFailure
      ? error
      : const ApiFailure(
          'learning_unavailable',
          kind: ApiFailureKind.unavailable,
        );
  Future<void> loadLearning({bool propagate = false}) async {
    if (_closed) return;
    final generation = ++_learningGeneration;
    loadingLearning = true;
    learningFailure = null;
    _emit();
    try {
      final current = await repository.readLearning(organizationId);
      if (_closed || generation != _learningGeneration) return;
      courses = current;
    } catch (error) {
      if (!_closed && generation == _learningGeneration) {
        courses = [];
        learningFailure = _safe(error);
      }
      if (propagate) rethrow;
    } finally {
      if (!_closed && generation == _learningGeneration) {
        loadingLearning = false;
        _emit();
      }
    }
  }

  Future<void> loadSchedule() async {
    if (_closed) return;
    final generation = ++_scheduleGeneration;
    loadingSchedule = true;
    scheduleFailure = null;
    _emit();
    try {
      final current = await repository.timeline(organizationId);
      if (!_closed && generation == _scheduleGeneration) schedule = current;
    } catch (error) {
      if (!_closed && generation == _scheduleGeneration) {
        schedule = null;
        scheduleFailure = _safe(error);
      }
    } finally {
      if (!_closed && generation == _scheduleGeneration) {
        loadingSchedule = false;
        _emit();
      }
    }
  }

  Future<void> loadAttendance({bool propagate = false}) async {
    if (_closed) return;
    final generation = ++_attendanceGeneration;
    loadingAttendance = true;
    attendanceFailure = null;
    _emit();
    try {
      final current = await repository.attendance(organizationId);
      if (!_closed && generation == _attendanceGeneration) attendance = current;
    } catch (error) {
      if (!_closed && generation == _attendanceGeneration) {
        attendance = [];
        attendanceFailure = _safe(error);
      }
      if (propagate) rethrow;
    } finally {
      if (!_closed && generation == _attendanceGeneration) {
        loadingAttendance = false;
        _emit();
      }
    }
  }

  void setQuiz(String quiz, String question, String choice) {
    if (!canCommand) return;
    quizAnswers[quiz] = {...?quizAnswers[quiz], question: choice};
    _emit();
  }

  void setAssignment(String assignment, String value) {
    if (!canCommand) return;
    assignmentText[assignment] = value;
  }

  void setFileLock(String assignment, bool locked) {
    if (_closed) return;
    if (fileLocks.contains(assignment) == locked) return;
    if (locked) {
      fileLocks.add(assignment);
    } else {
      fileLocks.remove(assignment);
    }
    _emit();
  }

  Future<void> _command(
    Future<void> Function() write, {
    bool attendanceOnly = false,
  }) async {
    if (!canCommand) return;
    busy = true;
    commandFailure = null;
    notice = null;
    commandAcknowledged = false;
    readbackReady = false;
    _emit();
    try {
      await write();
      if (_closed) return;
      commandAcknowledged = true;
      notice = 'saved';
      if (attendanceOnly) {
        await loadAttendance(propagate: true);
      } else {
        await loadLearning(propagate: true);
      }
    } catch (error) {
      if (!_closed) {
        commandFailure = _safe(error);
        needsReview =
            commandAcknowledged ||
            commandFailure!.uncertain ||
            {
              ApiFailureKind.conflict,
              ApiFailureKind.invalidSession,
              ApiFailureKind.invalidResponse,
            }.contains(commandFailure!.kind);
        final delay = commandFailure!.retryAfter;
        if (delay != null && delay > Duration.zero) {
          _retryUntil = DateTime.now().toUtc().add(delay);
          _retry?.cancel();
          _retry = Timer(delay, () {
            _retryUntil = null;
            _emit();
          });
        }
      }
    } finally {
      if (!_closed) {
        busy = false;
        _emit();
      }
    }
  }

  Future<void> start(LearningCourse course) =>
      _command(() => repository.start(organizationId, course.id));
  Future<void> complete(LearningCourse course, LearningLesson lesson) =>
      _command(() => repository.complete(organizationId, course, lesson.id));
  Future<void> submitQuiz(LearningCourse course, LearningQuiz quiz) => _command(
    () => repository.quiz(
      organizationId,
      course.id,
      quiz,
      Map.of(quizAnswers[quiz.id] ?? {}),
    ),
  );
  Future<void> submitAssignment(
    LearningCourse course,
    LearningAssignment assignment,
    List<String> files,
  ) => _command(
    () => repository.submit(
      organizationId,
      course.id,
      assignment.id,
      assignmentText[assignment.id] ?? '',
      List.of(files),
    ),
  );
  Future<void> checkIn(String entered) => _command(
    () => repository.checkIn(organizationId, entered),
    attendanceOnly: true,
  );
  Future<void> reconcile() async {
    if (_closed || busy || retryDelayed) return;
    busy = true;
    readbackReady = false;
    _emit();
    try {
      await Future.wait([
        loadLearning(propagate: true),
        loadAttendance(propagate: true),
      ]);
      if (!_closed) readbackReady = true;
    } catch (error) {
      if (!_closed) commandFailure = _safe(error);
    } finally {
      if (!_closed) {
        busy = false;
        _emit();
      }
    }
  }

  void acknowledgeReadback() {
    if (_closed || busy || !readbackReady) return;
    needsReview = false;
    readbackReady = false;
    commandFailure = null;
    notice = null;
    _emit();
  }

  void discardInputs() {
    if (_closed || busy || fileLocks.isNotEmpty) return;
    quizAnswers.clear();
    assignmentText.clear();
    _emit();
  }

  @override
  void dispose() {
    _closed = true;
    _learningGeneration++;
    _scheduleGeneration++;
    _attendanceGeneration++;
    _retry?.cancel();
    courses = [];
    attendance = [];
    schedule = null;
    quizAnswers.clear();
    assignmentText.clear();
    fileLocks.clear();
    super.dispose();
  }
}
