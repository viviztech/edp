import 'package:edp_mobile/features/learning/learning_repository.dart';
import 'package:flutter_test/flutter_test.dart';
import 'helpers.dart';
import '../file_transport_test.dart' show FileTestSnapshot, FileTestScope;
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:edp_mobile/core/files/file_transport.dart';
import 'package:edp_mobile/features/learning/assignment_files.dart';

void main() {
  group('M03 real synthetic Flutter API acceptance', () {
    late LiveApiFixture fixture;
    setUpAll(() => fixture = LiveApiFixture.load());

    test(
      'student completes ordered lessons, quiz and assignment, sees grade and verifies certificate',
      () async {
        final director = await fixture.signIn('director');
        final owner = await fixture.signIn('owner');
        final peer = await fixture.signIn('peer');
        addTearDown(director.close);
        addTearDown(owner.close);
        addTearDown(peer.close);
        final org = fixture.organizationId;
        final root = '/courses/organizations/$org';
        Future<Map<String, dynamic>> create(
          String path,
          Map<String, Object?> body,
        ) async =>
            jsonObject(await director.api.post('$root$path', data: body));
        final course = await create('', {
          'code': 'mobile-learning',
          'title_en': 'Mobile learning',
          'title_ta': 'கைபேசிக் கற்றல்',
          'description_en': 'Synthetic course',
          'description_ta': 'சோதனைப் பாடம்',
        });
        final id = course['id'] as String;
        final module = await create('/modules', {
          'course_id': id,
          'position': 1,
          'title_en': 'Customers',
          'title_ta': 'வாடிக்கையாளர்கள்',
        });
        Future<Map<String, dynamic>> lesson(int position) =>
            create('/lessons', {
              'course_id': id,
              'module_id': module['id'],
              'position': position,
              'title_en': 'Lesson $position',
              'title_ta': 'பாடம் $position',
              'body_en': 'Observe a customer need.',
              'body_ta': 'வாடிக்கையாளர் தேவையைக் கவனியுங்கள்.',
              'duration_minutes': 10,
            });
        final first = await lesson(1), second = await lesson(2);
        await create('/prerequisites', {
          'course_id': id,
          'lesson_id': second['id'],
          'prerequisite_lesson_id': first['id'],
          'reason': 'Synthetic ordered learning',
        });
        final quiz = await create('/quizzes', {
          'course_id': id,
          'lesson_id': first['id'],
          'position': 1,
          'title_en': 'Customer quiz',
          'title_ta': 'வாடிக்கையாளர் வினா',
          'instructions_en': 'Choose evidence.',
          'instructions_ta': 'ஆதாரத்தைத் தேர்ந்தெடுக்கவும்.',
          'passing_percent': 60,
          'max_attempts': 2,
        });
        final question = await create('/quiz-questions', {
          'course_id': id,
          'quiz_id': quiz['id'],
          'position': 1,
          'prompt_en': 'Which is evidence?',
          'prompt_ta': 'எது ஆதாரம்?',
          'points': 10,
        });
        Future<Map<String, dynamic>> choice(bool correct, int position) =>
            create('/quiz-choices', {
              'course_id': id,
              'quiz_id': quiz['id'],
              'question_id': question['id'],
              'position': position,
              'label_en': correct ? 'An interview' : 'An assumption',
              'label_ta': correct ? 'நேர்காணல்' : 'ஊகம்',
              'is_correct': correct,
            });
        final wrong = await choice(false, 1), right = await choice(true, 2);
        final assignment = await create('/assignments', {
          'course_id': id,
          'lesson_id': first['id'],
          'position': 1,
          'title_en': 'Customer evidence',
          'title_ta': 'வாடிக்கையாளர் ஆதாரம்',
          'instructions_en': 'Describe one interview.',
          'instructions_ta': 'ஒரு நேர்காணலை விவரிக்கவும்.',
          'maximum_points': 20,
          'passing_points': 12,
          'max_submissions': 2,
        });
        await director.api.put(
          '$root/courses/$id/assignments/${assignment['id']}/file-rule',
          data: {
            'policy_id': fixture.domainIntake['policy_id'],
            'minimum_files': 1,
            'maximum_files': 3,
          },
        );
        await create('/$id/publish', {
          'expected_version': 1,
          'reason': 'Synthetic content acceptance',
        });
        await create('/cohort-assignments', {
          'course_id': id,
          'cohort_id': fixture.enrollment('owner')['cohort_id'],
          'position': 1,
          'reason': 'Synthetic course delivery',
        });
        final repository = LearningRepository(owner.api, owner.identity);
        var mine = (await repository.readLearning(org)).single;
        expect(mine.enrollmentVersion, isNull);
        expect(mine.lessons.last.locked, isTrue);
        expect(
          (await LearningRepository(peer.api, peer.identity).readLearning(org)),
          isEmpty,
        );
        await expectLater(
          repository.readLearning(fixture.otherOrganizationId),
          throwsA(apiFailureWithStatus(403)),
        );
        await repository.start(org, id);
        mine = (await repository.readLearning(org)).single;
        await expectLater(
          repository.complete(org, mine, second['id'] as String),
          throwsA(apiFailureWithStatus(409)),
        );
        await repository.quiz(org, id, mine.lessons.first.quizzes.single, {
          question['id'] as String: wrong['id'] as String,
        });
        mine = (await repository.readLearning(org)).single;
        expect(mine.lessons.first.quizzes.single.attempts, 1);
        expect(mine.lessons.first.quizzes.single.passed, isFalse);
        await repository.quiz(org, id, mine.lessons.first.quizzes.single, {
          question['id'] as String: right['id'] as String,
        });
        final files = AssignmentFilesRepository(
          owner.api,
          FileTransport(owner.identity),
        );
        final assignmentId = assignment['id'] as String;
        final snapshot = FileTestSnapshot(
          base64Decode(
            jsonObject(fixture.domainIntake['payloads'])['text/plain']
                as String,
          ),
        );
        addTearDown(snapshot.dispose);
        final rule = await files.list(org, id, assignmentId);
        expect(rule.collectionEnabled, isTrue);
        var file = await files.register(org, id, assignmentId, {
          'client_request_id': learningRequestId(),
          'expected_revision': rule.nextRevision,
          'media_type': snapshot.mediaType,
          'byte_size': snapshot.byteSize,
          'sha256': snapshot.sha256,
        }, snapshot);
        file = await files.upload(
          org,
          id,
          assignmentId,
          file,
          snapshot,
          CancelToken(),
        );
        expect(file.usable, isFalse);
        await fixture.requestSyntheticScan(file.fileId);
        final deadline = DateTime.now().add(const Duration(seconds: 10));
        while (!file.usable && DateTime.now().isBefore(deadline)) {
          await Future<void>.delayed(const Duration(milliseconds: 100));
          file = await files.detail(org, id, assignmentId, file.id);
        }
        expect(file.usable, isTrue);
        await expectLater(
          AssignmentFilesRepository(
            peer.api,
            FileTransport(peer.identity),
          ).detail(org, id, assignmentId, file.id),
          throwsA(apiFailureWithStatus(403)),
        );
        final scope = FileTestScope();
        final copy = await files.download(
          org,
          id,
          assignmentId,
          file,
          scope,
          CancelToken(),
        );
        expect(copy.sha256, snapshot.sha256);
        await copy.dispose();
        await scope.close();
        await repository.submit(
          org,
          id,
          assignment['id'] as String,
          'Five customers described the same problem.',
          [file.id],
        );
        mine = (await repository.readLearning(org)).single;
        final submission =
            mine.lessons.first.assignments.single.submissions.single;
        expect(submission.revision, 1);
        expect(submission.score, isNull);
        final frozen = await files.detail(org, id, assignmentId, file.id);
        expect(frozen.state, 'submitted');
        expect(frozen.frozenVersion, isNotNull);
        await create(
          '/trainer-delivery/$id/assignment-submissions/${submission.id}/grade',
          {'score_points': 18, 'feedback': 'Synthetic reviewed evidence'},
        );
        await repository.complete(org, mine, first['id'] as String);
        mine = (await repository.readLearning(org)).single;
        await repository.complete(org, mine, second['id'] as String);
        mine = (await repository.readLearning(org)).single;
        expect(mine.percent, 100);
        expect(mine.eligible, isTrue);
        expect(
          mine.lessons.first.assignments.single.submissions.single.feedback,
          'Synthetic reviewed evidence',
        );
        final template = await create('/certificate-templates', {
          'course_id': id,
          'code': 'mobile-certificate',
          'title_en': 'Completion',
          'title_ta': 'நிறைவு',
          'statement_en': 'Completed synthetic course',
          'statement_ta': 'சோதனைப் பாடம் நிறைவு',
          'issuer_name': 'Synthetic organization',
        });
        await create('/certificate-templates/${template['id']}/publish', {
          'expected_version': 1,
          'reason': 'Synthetic template acceptance',
        });
        final learning = jsonObject(await owner.api.get('$root/my-learning'));
        final enrollment = jsonObject(
          (learning['courses'] as List).single,
        )['course_enrollment'];
        await create('/certificates/issue', {
          'course_enrollment_id': jsonObject(enrollment)['id'],
          'template_id': template['id'],
          'reason': 'Synthetic completion evidence',
        });
        mine = (await repository.readLearning(org)).single;
        expect(mine.certificate!.status, 'valid');
        final public = await repository.verify(mine.certificate!.code);
        expect(public.status, 'valid');
        expect(public.qr.squares, isNotEmpty);
      },
    );

    test(
      'student schedule and explicit attendance check-in reject replay and peer token access',
      () async {
        final director = await fixture.signIn('director');
        final owner = await fixture.signIn('owner');
        final peer = await fixture.signIn('peer');
        addTearDown(director.close);
        addTearDown(owner.close);
        addTearDown(peer.close);
        final org = fixture.organizationId;
        final time = DateTime.now().toUtc();
        await director.api.put(
          '/attendance/organizations/$org/policy',
          data: {
            'cohort_id': fixture.enrollment('owner')['cohort_id'],
            'threshold_percent': 75,
            'late_after_minutes': 10,
            'opens_before_minutes': 15,
            'closes_after_minutes': 30,
            'reason': 'Synthetic attendance policy',
          },
        );
        final session = jsonObject(
          await director.api.post(
            '/programs/organizations/$org/sessions',
            data: {
              'cohort_id': fixture.enrollment('owner')['cohort_id'],
              'title_en': 'Synthetic check-in',
              'title_ta': 'சோதனை வருகை',
              'starts_at': time
                  .subtract(const Duration(minutes: 1))
                  .toIso8601String(),
              'ends_at': time
                  .add(const Duration(minutes: 45))
                  .toIso8601String(),
              'mode': 'in_person',
              'location': 'Synthetic center',
            },
          ),
        );
        final window = jsonObject(
          await director.api.post(
            '/attendance/organizations/$org/windows',
            data: {
              'session_id': session['id'],
              'reason': 'Synthetic mobile attendance',
            },
          ),
        );
        final repository = LearningRepository(owner.api, owner.identity);
        expect(
          (await repository.timeline(org)).sessions.map((s) => s.id),
          contains(session['id']),
        );
        final token = window['check_in_token'] as String;
        await expectLater(
          LearningRepository(peer.api, peer.identity).checkIn(org, token),
          throwsA(apiFailureWithStatus(403)),
        );
        await repository.checkIn(org, 'edp-attendance:$token');
        final attendance = await repository.attendance(org);
        expect(attendance, isNotEmpty);
        await expectLater(
          repository.checkIn(org, token),
          throwsA(apiFailureWithStatus(409)),
        );
      },
    );
  }, skip: liveAcceptanceSkipReason);
}
