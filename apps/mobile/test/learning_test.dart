import 'dart:async';

import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/core/files/file_transport.dart';
import 'package:edp_mobile/core/files/private_files.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/features/learning/assignment_files.dart';
import 'package:edp_mobile/features/learning/learning_models.dart';
import 'package:edp_mobile/features/learning/learning_repository.dart';
import 'package:edp_mobile/features/learning/student_controller.dart';
import 'package:flutter_test/flutter_test.dart';

import 'file_transport_test.dart'
    show FileTestTokens, FileTestSnapshot, FileTestScope;

const learningOrg = '11111111-1111-4111-8111-111111111111';
const learningCourse = '22222222-2222-4222-8222-222222222222';
const learningLesson = '33333333-3333-4333-8333-333333333333';
const learningQuiz = '44444444-4444-4444-8444-444444444444';
const learningQuestion = '55555555-5555-4555-8555-555555555555';
const learningChoice = '66666666-6666-4666-8666-666666666666';
const learningAssignment = '77777777-7777-4777-8777-777777777777';
const learningBinding = '88888888-8888-4888-8888-888888888888';

Map<String, dynamic> learningCourseJson() => {
  'id': learningCourse,
  'enrollment_id': learningOrg,
  'title_en': 'Business foundations',
  'title_ta': 'தொழில் அடிப்படைகள்',
  'description_en': 'Learn enterprise skills',
  'description_ta': 'தொழில் திறன்களைக் கற்கவும்',
  'course_enrollment': {'version': 1},
  'progress': {'percent': 0, 'completed_lessons': 0, 'required_lessons': 2},
  'certificate_eligibility': {
    'eligible': false,
    'blocking_reasons': ['course_completion_incomplete'],
  },
  'certificate': null,
  'modules': [
    {
      'id': learningOrg,
      'title_en': 'First module',
      'title_ta': 'முதல் தொகுதி',
      'lessons': [
        {
          'id': learningLesson,
          'title_en': 'Customer needs',
          'title_ta': 'வாடிக்கையாளர் தேவைகள்',
          'body_en': 'Describe the customer.',
          'body_ta': 'வாடிக்கையாளரை விவரிக்கவும்.',
          'locked': false,
          'completed': false,
          'materials': <Object>[],
          'quizzes': [
            {
              'id': learningQuiz,
              'title_en': 'Customer quiz',
              'title_ta': 'வாடிக்கையாளர் வினா',
              'instructions_en': 'Choose one answer',
              'instructions_ta': 'ஒரு பதிலைத் தேர்ந்தெடுக்கவும்',
              'remaining_attempts': 2,
              'attempt_count': 0,
              'passing_percent': 70,
              'best_percent': null,
              'available': true,
              'passed': false,
              'questions': [
                {
                  'id': learningQuestion,
                  'prompt_en': 'Who is the customer?',
                  'prompt_ta': 'வாடிக்கையாளர் யார்?',
                  'choices': [
                    {
                      'id': learningChoice,
                      'label_en': 'Buyer',
                      'label_ta': 'வாங்குபவர்',
                    },
                  ],
                },
              ],
            },
          ],
          'assignments': [
            {
              'id': learningAssignment,
              'title_en': 'Business proposal',
              'title_ta': 'தொழில் திட்டம்',
              'instructions_en': 'Write a proposal',
              'instructions_ta': 'திட்டத்தை எழுதவும்',
              'remaining_submissions': 2,
              'maximum_points': 100,
              'passing_points': 60,
              'available': true,
              'submissions': <Object>[],
            },
          ],
        },
      ],
    },
  ],
};

class LearningTestRepository extends LearningRepository {
  LearningTestRepository()
    : super(
        DomainApi(AuthRepository(Dio(), FileTestTokens())),
        AuthRepository(Dio(), FileTestTokens()),
      );
  List<LearningCourse> current = [LearningCourse(learningCourseJson())];
  int writes = 0, reads = 0;
  Object? writeFailure, readFailure;
  Completer<List<LearningCourse>>? gate;
  @override
  Future<List<LearningCourse>> readLearning(String org) async {
    reads++;
    if (readFailure != null) throw readFailure!;
    if (gate != null) return gate!.future;
    return current;
  }

  @override
  Future<StudentTimeline> timeline(String org) async =>
      StudentTimeline({'sessions': <Object>[], 'events': <Object>[]});
  @override
  Future<List<StudentAttendance>> attendance(String org) async => [];
  @override
  Future<void> quiz(
    String org,
    String course,
    LearningQuiz quiz,
    Map<String, String> choices,
  ) async {
    writes++;
    if (writeFailure != null) throw writeFailure!;
  }

  @override
  Future<void> start(String org, String course) async {
    writes++;
    if (writeFailure != null) throw writeFailure!;
  }
}

Map<String, dynamic> assignmentFileJson(
  PrivateSnapshot snapshot, {
  String state = 'pending',
  String bindingState = 'active',
  String? request,
}) => {
  'id': learningBinding,
  'target_revision': 1,
  'state': bindingState,
  'version': 1,
  'submission_id': null,
  'evidence': null,
  'usable': state == 'clean',
  'file': {
    'id': learningCourse,
    'organization_id': learningOrg,
    'resource_id': learningBinding,
    'purpose': 'assignment_submission',
    'client_request_id': request ?? learningQuestion,
    'state': state,
    'media_type': snapshot.mediaType,
    'sha256': snapshot.sha256,
    'byte_size': snapshot.byteSize,
    'version': 1,
  },
};

class LearningFileTestRepository extends AssignmentFilesRepository {
  LearningFileTestRepository()
    : super(
        DomainApi(AuthRepository(Dio(), FileTestTokens())),
        FileTransport(AuthRepository(Dio(), FileTestTokens())),
      );
  final sample = FileTestSnapshot([65, 66]);
  int registers = 0, uploads = 0, details = 0;
  bool lostIntent = false, lostUpload = false;
  List<AssignmentAttachment> current = [];
  final bodies = <Map<String, Object>>[];
  @override
  Future<AssignmentFileBatch> list(
    String org,
    String course,
    String assignment,
  ) async => AssignmentFileBatch({
    'collection_enabled': true,
    'max_upload_bytes': 1024,
    'next_revision': 1,
    'rule': {
      'minimum_files': 1,
      'maximum_files': 1,
      'max_file_bytes': 1024,
      'allowed_mime_types': ['text/plain'],
      'notice_en': 'Synthetic only',
      'notice_ta': 'செயற்கை மட்டும்',
    },
    'items': current
        .map(
          (item) => assignmentFileJson(
            sample,
            state: item.fileState,
            request: item.requestId,
          ),
        )
        .toList(),
  }, learningOrg);
  @override
  Future<AssignmentAttachment> register(
    String org,
    String course,
    String assignment,
    Map<String, Object> intent,
    PrivateSnapshot snapshot,
  ) async {
    registers++;
    bodies.add(intent);
    current = [
      AssignmentAttachment(
        assignmentFileJson(
          snapshot,
          request: intent['client_request_id'] as String,
        ),
        learningOrg,
      ),
    ];
    if (lostIntent) {
      lostIntent = false;
      throw const ApiFailure(
        'timeout',
        kind: ApiFailureKind.timeout,
        outcome: CommandOutcome.uncertain,
      );
    }
    return current.single;
  }

  @override
  Future<AssignmentAttachment> upload(
    String org,
    String course,
    String assignment,
    AssignmentAttachment file,
    PrivateSnapshot snapshot,
    CancelToken token,
  ) async {
    uploads++;
    current = [
      AssignmentAttachment(
        assignmentFileJson(
          snapshot,
          state: 'quarantined',
          request: file.requestId,
        ),
        learningOrg,
      ),
    ];
    if (lostUpload) {
      throw const ApiFailure(
        'timeout',
        kind: ApiFailureKind.timeout,
        outcome: CommandOutcome.uncertain,
      );
    }
    return current.single;
  }

  @override
  Future<AssignmentAttachment> detail(
    String org,
    String course,
    String assignment,
    String id,
  ) async {
    details++;
    return current.single;
  }
}

void main() {
  test(
    'attendance parser accepts only bounded raw or exact attendance payload',
    () {
      final token = 'a' * 43;
      expect(attendanceToken(token), token);
      expect(attendanceToken('edp-attendance:$token'), token);
      for (final value in [
        'https://example.com/$token',
        'edp-attendance:$token?x=1',
        'x' * 129,
        'x' * 31,
        'edp-attendance://$token',
      ]) {
        expect(() => attendanceToken(value), throwsA(isA<ApiFailure>()));
      }
    },
  );
  test(
    'material mapping rejects foreign origin, organization, traversal and query before authentication',
    () {
      final valid =
          '/api/courses/organizations/$learningOrg/material-delivery/encoded.signature';
      expect(
        materialApiPath(learningOrg, valid),
        '/courses/organizations/$learningOrg/material-delivery/encoded.signature',
      );
      for (final path in [
        'https://example.com$valid',
        '$valid?next=1',
        '$valid#token',
        valid.replaceFirst(learningOrg, learningCourse),
        valid.replaceFirst('encoded.signature', '../secret'),
        valid.replaceFirst('encoded.signature', '%2e%2e.secret'),
      ]) {
        expect(
          () => materialApiPath(learningOrg, path),
          throwsA(isA<ApiFailure>()),
        );
      }
    },
  );
  test(
    'certificate QR accepts only bounded rectangle paths and rejects executable or malformed SVG',
    () {
      final qr = CertificateQr.parse(
        '<svg viewBox="0 0 21 21"><path d="M4,4H5V5H4zM5,4H6V5H5z"/></svg>',
      );
      expect(qr.squares, hasLength(2));
      for (final value in [
        '<svg viewBox="0 0 21 21"><script/></svg>',
        '<svg viewBox="0 0 21 21"><path d="M4,4H5V6H4z"/></svg>',
        '<svg viewBox="0 0 21 21"><path d="M4,4H5V5H4zX"/></svg>',
      ]) {
        expect(() => CertificateQr.parse(value), throwsFormatException);
      }
    },
  );
  test(
    'lost quiz command preserves selections and requires readback plus explicit acknowledgement',
    () async {
      final repository = LearningTestRepository()
        ..writeFailure = const ApiFailure(
          'timeout',
          kind: ApiFailureKind.timeout,
          outcome: CommandOutcome.uncertain,
        );
      final controller = StudentController(
        repository,
        organizationId: learningOrg,
      );
      addTearDown(controller.dispose);
      await controller.loadLearning();
      final course = controller.courses.single,
          quiz = controller.courses.single.lessons.single.quizzes.single;
      controller.setQuiz(quiz.id, learningQuestion, learningChoice);
      await controller.submitQuiz(course, quiz);
      await controller.submitQuiz(course, quiz);
      expect(repository.writes, 1);
      expect(controller.needsReview, isTrue);
      expect(
        controller.quizAnswers[quiz.id]![learningQuestion],
        learningChoice,
      );
      await controller.reconcile();
      expect(controller.needsReview, isTrue);
      expect(controller.readbackReady, isTrue);
      controller.acknowledgeReadback();
      expect(controller.canCommand, isTrue);
    },
  );
  test(
    'acknowledged command remains acknowledged when projection refresh fails and is never replayed',
    () async {
      final repository = LearningTestRepository();
      final controller = StudentController(
        repository,
        organizationId: learningOrg,
      );
      addTearDown(controller.dispose);
      await controller.loadLearning();
      final course = controller.courses.single;
      repository.readFailure = const ApiFailure(
        'offline',
        kind: ApiFailureKind.offline,
      );
      await controller.start(course);
      expect(controller.commandAcknowledged, isTrue);
      expect(controller.needsReview, isTrue);
      await controller.start(course);
      expect(repository.writes, 1);
    },
  );
  test(
    'late projection after disposal never restores private course data',
    () async {
      final repository = LearningTestRepository()
        ..gate = Completer<List<LearningCourse>>();
      final controller = StudentController(
        repository,
        organizationId: learningOrg,
      );
      final load = controller.loadLearning();
      controller.dispose();
      repository.gate!.complete(repository.current);
      await load;
      expect(controller.courses, isEmpty);
    },
  );
  test(
    'file intent recovery reuses exact UUID and lost PUT reads before allowing another write',
    () async {
      final repository = LearningFileTestRepository()
        ..lostIntent = true
        ..lostUpload = true;
      final scope = FileTestScope()..selected = FileTestSnapshot([65, 66]);
      final controller = AssignmentFilesController(
        repository,
        scope,
        org: learningOrg,
        course: learningCourse,
        assignment: learningAssignment,
      );
      addTearDown(controller.dispose);
      await controller.load();
      await controller.pick();
      expect(controller.pending, isNull);
      expect(controller.intent, isNotNull);
      await controller.recoverIntent();
      expect(repository.bodies[0], repository.bodies[1]);
      await controller.upload();
      await controller.upload();
      expect(repository.uploads, 1);
      expect(controller.needsReadback, isTrue);
      await controller.reconcile();
      expect(repository.details, 1);
      expect(controller.selected, isNull);
      expect(controller.batch!.staged.single.fileState, 'quarantined');
      expect(controller.ready, isFalse);
    },
  );
  test(
    'pending file after process interruption can reselect at its full quota without a new intent',
    () async {
      final repository = LearningFileTestRepository();
      repository.current = [
        AssignmentAttachment(
          assignmentFileJson(repository.sample),
          learningOrg,
        ),
      ];
      final scope = FileTestScope()..selected = FileTestSnapshot([65, 66]);
      final controller = AssignmentFilesController(
        repository,
        scope,
        org: learningOrg,
        course: learningCourse,
        assignment: learningAssignment,
      );
      addTearDown(controller.dispose);
      await controller.load();
      await controller.pick(existing: controller.batch!.staged.single);
      expect(repository.registers, 0);
      expect(controller.pending, isNotNull);
      expect(controller.selected, isNotNull);
    },
  );
  test(
    'late native selection while backgrounded creates no file intent',
    () async {
      final repository = LearningFileTestRepository(),
          gate = Completer<PrivateSnapshot?>();
      final scope = FileTestScope()..picker = () => gate.future;
      final controller = AssignmentFilesController(
        repository,
        scope,
        org: learningOrg,
        course: learningCourse,
        assignment: learningAssignment,
      );
      addTearDown(controller.dispose);
      await controller.load();
      final pick = controller.pick();
      controller.pause();
      final snapshot = FileTestSnapshot([65, 66]);
      gate.complete(snapshot);
      await pick;
      expect(repository.registers, 0);
      expect(snapshot.disposed, isTrue);
    },
  );
}
