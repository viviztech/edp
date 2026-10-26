import '../../core/api/api_failure.dart';

final learningUuid = RegExp(
  r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
);
Map<String, dynamic> learningObject(Object? value) =>
    Map<String, dynamic>.from(value as Map);
List<Map<String, dynamic>> learningObjects(Object? value) =>
    (value as List).map(learningObject).toList();
String learningId(Object? value) {
  if (value is! String || !learningUuid.hasMatch(value)) {
    throw const FormatException();
  }
  return value;
}

int learningInt(Object? value, {int min = 0, int max = 2147483647}) {
  if (value is! int || value < min || value > max) {
    throw const FormatException();
  }
  return value;
}

String learningText(Object? value, {int max = 20000}) {
  if (value is! String || value.length > max) throw const FormatException();
  return value;
}

DateTime learningDate(Object? value) => DateTime.parse(value as String);
T learningDecode<T>(T Function() read, {bool command = false}) {
  try {
    return read();
  } catch (_) {
    throw ApiFailure(
      'invalid_response',
      kind: ApiFailureKind.invalidResponse,
      outcome: command ? CommandOutcome.uncertain : CommandOutcome.rejected,
    );
  }
}

class LearningLabel {
  final String en, ta;
  LearningLabel(Map<String, dynamic> data, [String prefix = 'title'])
    : en = learningText(data['${prefix}_en']),
      ta = learningText(data['${prefix}_ta']);
  String text(bool tamil) => tamil ? ta : en;
}

class LearningChoice {
  final String id;
  final LearningLabel label;
  LearningChoice(Map<String, dynamic> data)
    : id = learningId(data['id']),
      label = LearningLabel(data, 'label');
}

class LearningQuestion {
  final String id;
  final LearningLabel prompt;
  final List<LearningChoice> choices;
  LearningQuestion(Map<String, dynamic> data)
    : id = learningId(data['id']),
      prompt = LearningLabel(data, 'prompt'),
      choices = learningObjects(
        data['choices'],
      ).map(LearningChoice.new).toList();
}

class LearningQuiz {
  final String id;
  final LearningLabel title, instructions;
  final int remainingAttempts, attempts, passingPercent;
  final int? bestPercent;
  final bool available, passed;
  final List<LearningQuestion> questions;
  LearningQuiz(Map<String, dynamic> data)
    : id = learningId(data['id']),
      title = LearningLabel(data),
      instructions = LearningLabel(data, 'instructions'),
      remainingAttempts = learningInt(data['remaining_attempts'], max: 10),
      attempts = learningInt(data['attempt_count'], max: 10),
      passingPercent = learningInt(data['passing_percent'], max: 100),
      bestPercent = data['best_percent'] == null
          ? null
          : learningInt(data['best_percent'], max: 100),
      available = data['available'] as bool,
      passed = data['passed'] as bool,
      questions = learningObjects(
        data['questions'],
      ).map(LearningQuestion.new).toList();
}

class LearningSubmission {
  final String id, response;
  final int revision;
  final DateTime submittedAt;
  final int? score;
  final bool? passed;
  final String? feedback;
  LearningSubmission(Map<String, dynamic> data)
    : id = learningId(data['id']),
      response = learningText(data['response_text'], max: 10000),
      revision = learningInt(data['revision'], min: 1, max: 10),
      submittedAt = learningDate(data['submitted_at']),
      score = data['grade'] == null
          ? null
          : learningInt(learningObject(data['grade'])['score_points']),
      passed = data['grade'] == null
          ? null
          : learningObject(data['grade'])['passed'] as bool,
      feedback = data['grade'] == null
          ? null
          : learningText(learningObject(data['grade'])['feedback'], max: 5000);
}

class LearningAssignment {
  final String id;
  final LearningLabel title, instructions;
  final int remainingSubmissions, maximumPoints, passingPoints;
  final bool available;
  final List<LearningSubmission> submissions;
  LearningAssignment(Map<String, dynamic> data)
    : id = learningId(data['id']),
      title = LearningLabel(data),
      instructions = LearningLabel(data, 'instructions'),
      remainingSubmissions = learningInt(
        data['remaining_submissions'],
        max: 10,
      ),
      maximumPoints = learningInt(data['maximum_points'], min: 1, max: 1000),
      passingPoints = learningInt(data['passing_points'], max: 1000),
      available = data['available'] as bool,
      submissions = learningObjects(
        data['submissions'],
      ).map(LearningSubmission.new).toList();
  bool get awaitingReview =>
      submissions.isNotEmpty && submissions.last.score == null;
}

class LearningMaterial {
  final String id, kind;
  final LearningLabel label;
  final bool available;
  LearningMaterial(Map<String, dynamic> data)
    : id = learningId(data['id']),
      kind = data['kind'] as String,
      label = LearningLabel(data, 'label'),
      available = data['available'] as bool;
}

class LearningLesson {
  final String id;
  final LearningLabel title, body;
  final bool locked, completed;
  final List<LearningMaterial> materials;
  final List<LearningQuiz> quizzes;
  final List<LearningAssignment> assignments;
  LearningLesson(Map<String, dynamic> data)
    : id = learningId(data['id']),
      title = LearningLabel(data),
      body = LearningLabel(data, 'body'),
      locked = data['locked'] as bool,
      completed = data['completed'] as bool,
      materials = learningObjects(
        data['materials'],
      ).map(LearningMaterial.new).toList(),
      quizzes = learningObjects(data['quizzes']).map(LearningQuiz.new).toList(),
      assignments = learningObjects(
        data['assignments'],
      ).map(LearningAssignment.new).toList();
}

class LearningModule {
  final String id;
  final LearningLabel title;
  final List<LearningLesson> lessons;
  LearningModule(Map<String, dynamic> data)
    : id = learningId(data['id']),
      title = LearningLabel(data),
      lessons = learningObjects(
        data['lessons'],
      ).map(LearningLesson.new).toList();
}

class LearnerCertificate {
  final String code, status, issuer;
  final LearningLabel title, statement;
  final DateTime issuedAt;
  LearnerCertificate(Map<String, dynamic> data)
    : code = learningText(data['verification_code'], max: 48),
      status = data['status'] as String,
      issuer = learningText(data['issuer_name'], max: 200),
      title = LearningLabel(data, 'certificate_title'),
      statement = LearningLabel(data, 'statement'),
      issuedAt = learningDate(data['issued_at']) {
    if (!RegExp(r'^[A-Za-z0-9_-]{20,48}$').hasMatch(code) ||
        !{'valid', 'revoked'}.contains(status)) {
      throw const FormatException();
    }
  }
}

class LearningCourse {
  final String id, enrollmentId;
  final LearningLabel title, description;
  final int? enrollmentVersion;
  final int percent, completedLessons, requiredLessons;
  final bool eligible;
  final List<String> blockingReasons;
  final LearnerCertificate? certificate;
  final List<LearningModule> modules;
  LearningCourse(Map<String, dynamic> data)
    : id = learningId(data['id']),
      enrollmentId = learningId(data['enrollment_id']),
      title = LearningLabel(data),
      description = LearningLabel(data, 'description'),
      enrollmentVersion = data['course_enrollment'] == null
          ? null
          : learningInt(
              learningObject(data['course_enrollment'])['version'],
              min: 1,
            ),
      percent = learningInt(
        learningObject(data['progress'])['percent'],
        max: 100,
      ),
      completedLessons = learningInt(
        learningObject(data['progress'])['completed_lessons'],
      ),
      requiredLessons = learningInt(
        learningObject(data['progress'])['required_lessons'],
      ),
      eligible =
          learningObject(data['certificate_eligibility'])['eligible'] as bool,
      blockingReasons =
          (learningObject(data['certificate_eligibility'])['blocking_reasons']
                  as List)
              .cast<String>(),
      certificate = data['certificate'] == null
          ? null
          : LearnerCertificate(learningObject(data['certificate'])),
      modules = learningObjects(
        data['modules'],
      ).map(LearningModule.new).toList();
  Iterable<LearningLesson> get lessons =>
      modules.expand((module) => module.lessons);
}

class StudentSession {
  final String id, status, mode;
  final String? location;
  final LearningLabel title;
  final DateTime startsAt, endsAt;
  StudentSession(Map<String, dynamic> data)
    : id = learningId(data['id']),
      status = data['status'] as String,
      mode = data['mode'] as String,
      location = data['location'] as String?,
      title = LearningLabel(data),
      startsAt = learningDate(data['starts_at']),
      endsAt = learningDate(data['ends_at']);
}

class StudentTimeline {
  final List<StudentSession> sessions;
  final List<TimelineItem> events;
  StudentTimeline(Map<String, dynamic> data)
    : sessions = learningObjects(
        data['sessions'],
      ).map(StudentSession.new).toList(),
      events = learningObjects(data['events']).map(TimelineItem.new).toList();
}

class TimelineItem {
  final LearningLabel title;
  final String state, kind;
  final DateTime at;
  TimelineItem(Map<String, dynamic> data)
    : title = LearningLabel(data),
      state = data['state'] as String,
      kind = data['kind'] as String,
      at = learningDate(data['occurred_at']);
}

class StudentAttendanceSession {
  final String id, status;
  final String? attendanceStatus;
  final LearningLabel title;
  final DateTime startsAt, endsAt;
  StudentAttendanceSession(Map<String, dynamic> data)
    : id = learningId(data['session_id']),
      status = data['session_status'] as String,
      attendanceStatus = data['record'] == null
          ? null
          : learningObject(data['record'])['status'] as String,
      title = LearningLabel(data),
      startsAt = learningDate(data['starts_at']),
      endsAt = learningDate(data['ends_at']);
}

class StudentAttendance {
  final String enrollmentId;
  final LearningLabel cohort;
  final int percent, threshold, attended, required;
  final bool lowAttendance;
  final List<StudentAttendanceSession> sessions;
  StudentAttendance(Map<String, dynamic> data)
    : enrollmentId = learningId(data['enrollment_id']),
      cohort = LearningLabel(data, 'cohort_name'),
      percent = learningInt(
        learningObject(data['summary'])['percent'],
        max: 100,
      ),
      threshold = learningInt(
        learningObject(data['summary'])['threshold_percent'],
        max: 100,
      ),
      attended = learningInt(learningObject(data['summary'])['attended']),
      required = learningInt(learningObject(data['summary'])['required']),
      lowAttendance = learningObject(data['summary'])['low_attendance'] as bool,
      sessions = learningObjects(
        data['sessions'],
      ).map(StudentAttendanceSession.new).toList();
}
