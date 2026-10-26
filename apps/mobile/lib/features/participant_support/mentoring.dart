import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../identity/providers.dart';
import 'support_common.dart';

final mentoringRepositoryProvider = Provider(
  (ref) => MentoringRepository(ref.watch(domainApiProvider)),
);

class MentorAssignment {
  final String id, mentorName, state;
  final DateTime startsOn;
  final DateTime? endsOn;
  MentorAssignment.fromJson(Map<String, dynamic> data)
    : id = identifier(data['id']),
      mentorName = data['mentor_name'] as String,
      state = data['state'] as String,
      startsOn = DateTime.parse(data['starts_on'] as String),
      endsOn = data['ends_on'] == null
          ? null
          : DateTime.parse(data['ends_on'] as String);
}

class MentorSession {
  final String id, assignmentId, topic, status, mode;
  final String? location;
  final DateTime startsAt, endsAt;
  MentorSession.fromJson(Map<String, dynamic> data)
    : id = identifier(data['id']),
      assignmentId = identifier(data['assignment_id']),
      topic = data['topic'] as String,
      status = data['status'] as String,
      mode = data['mode'] as String,
      location = data['location_or_link'] as String?,
      startsAt = DateTime.parse(data['starts_at'] as String),
      endsAt = DateTime.parse(data['ends_at'] as String);
}

class SharedMentorNote {
  final String assignmentId, body;
  SharedMentorNote.fromJson(Map<String, dynamic> data)
    : assignmentId = identifier(data['assignment_id']),
      body = data['body'] as String {
    if (data['visibility'] != 'shared_with_participant') {
      throw const FormatException('Private note');
    }
  }
}

class MentorWork {
  final String assignmentId, title, state;
  final String? description;
  final int? progress;
  final DateTime? due;
  MentorWork.fromJson(Map<String, dynamic> data)
    : assignmentId = identifier(data['assignment_id']),
      title = (data['title'] ?? data['purpose']) as String,
      state = data['state'] as String,
      description = data['description'] as String?,
      progress = data['progress_percent'] as int?,
      due = (data['target_date'] ?? data['due_at']) == null
          ? null
          : DateTime.parse((data['target_date'] ?? data['due_at']) as String);
}

class MentorFeedback {
  final String sessionId;
  final int rating;
  final String? comment;
  MentorFeedback.fromJson(Map<String, dynamic> data)
    : sessionId = identifier(data['session_id']),
      rating = data['rating'] as int,
      comment = data['comment'] as String? {
    if (rating < 1 || rating > 5) throw const FormatException();
  }
}

class MyMentoring {
  final List<MentorAssignment> assignments;
  final List<MentorSession> sessions;
  final List<SharedMentorNote> notes;
  final List<MentorWork> goals, actions, followUps;
  final List<MentorFeedback> feedback;
  MyMentoring.fromJson(Map<String, dynamic> data)
    : assignments = rows(data['assignments'], MentorAssignment.fromJson),
      sessions = rows(data['sessions'], MentorSession.fromJson),
      notes = rows(data['notes'], SharedMentorNote.fromJson),
      goals = rows(data['goals'], MentorWork.fromJson),
      actions = rows(data['action_items'], MentorWork.fromJson),
      followUps = rows(data['follow_ups'], MentorWork.fromJson),
      feedback = rows(data['feedback'], MentorFeedback.fromJson) {
    final ids = assignments.map((a) => a.id).toSet();
    if (sessions.any((s) => !ids.contains(s.assignmentId)) ||
        notes.any((n) => !ids.contains(n.assignmentId)) ||
        [
          ...goals,
          ...actions,
          ...followUps,
        ].any((w) => !ids.contains(w.assignmentId))) {
      throw const FormatException();
    }
  }
}

class MentoringRepository {
  final DomainApi api;
  MentoringRepository(this.api);
  String root(String org) => '/mentoring/organizations/${identifier(org)}';
  Future<MyMentoring> read(String org) async {
    final data = await api.get('${root(org)}/my-mentoring');
    return decode(() => MyMentoring.fromJson(object(data)));
  }

  Future<MentorFeedback> feedback(
    String org,
    String session,
    int rating,
    String comment,
  ) async {
    if (rating < 1 || rating > 5 || comment.length > 2000) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await api.post(
      '${root(org)}/feedback',
      data: {
        'session_id': identifier(session),
        'rating': rating,
        'comment': comment.isEmpty ? null : comment,
      },
    );
    return decode(() {
      final result = MentorFeedback.fromJson(object(data));
      if (result.sessionId != session) throw const FormatException();
      return result;
    }, command: true);
  }
}

class MentoringController extends ChangeNotifier with SupportRetry {
  final MentoringRepository repository;
  final String organizationId;
  MyMentoring? data;
  ApiFailure? failure;
  bool busy = false, requiresReadback = false, _disposed = false;
  String? pendingSession;
  int rating = 5;
  String comment = '';
  MentoringController(this.repository, this.organizationId);
  Future<void> refresh() async {
    if (busy || retryDelayed || _disposed) return;
    busy = true;
    failure = null;
    notifyListeners();
    try {
      final result = await repository.read(organizationId);
      if (_disposed) return;
      data = result;
      requiresReadback = false;
      if (result.feedback.any((f) => f.sessionId == pendingSession)) {
        pendingSession = null;
        comment = '';
      }
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e);
        recordFailure(failure!);
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> send(String session) async {
    if (busy || retryDelayed || requiresReadback || _disposed || data == null) {
      return;
    }
    if (!data!.sessions.any(
          (s) => s.id == session && s.status == 'completed',
        ) ||
        data!.feedback.any((f) => f.sessionId == session)) {
      return;
    }
    pendingSession = session;
    busy = true;
    failure = null;
    notifyListeners();
    try {
      await repository.feedback(organizationId, session, rating, comment);
      if (_disposed) return;
      comment = '';
      pendingSession = null;
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
        requiresReadback =
            failure!.uncertain || failure!.kind == ApiFailureKind.conflict;
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
    if (failure == null) await refresh();
  }

  @override
  void dispose() {
    _disposed = true;
    data = null;
    comment = '';
    super.dispose();
  }
}
