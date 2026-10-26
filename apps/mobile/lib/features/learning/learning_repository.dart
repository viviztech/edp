import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart' as crypto;
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../../core/files/private_files.dart';
import '../identity/auth_repository.dart';
import '../identity/providers.dart';
import 'learning_models.dart';

final learningRepositoryProvider = Provider(
  (ref) => LearningRepository(
    ref.watch(domainApiProvider),
    ref.watch(authRepositoryProvider),
  ),
);
const materialReadLimit = 2 * 1024 * 1024;

String learningRoot(String organization) {
  learningId(organization);
  return '/courses/organizations/$organization';
}

String attendanceToken(String entered) {
  final value = entered.trim();
  final token = value.startsWith('edp-attendance:')
      ? value.substring(15)
      : value;
  if (!RegExp(r'^[A-Za-z0-9_-]{32,128}$').hasMatch(token)) {
    throw const ApiFailure(
      'invalid_attendance_token',
      kind: ApiFailureKind.validation,
      outcome: CommandOutcome.notSent,
    );
  }
  return token;
}

String materialApiPath(String organization, String supplied) {
  learningId(organization);
  final pattern = RegExp(
    '^/api/courses/organizations/$organization/material-delivery/([A-Za-z0-9_-]+[.][A-Za-z0-9_-]+)\$',
  );
  final match = pattern.firstMatch(supplied);
  if (match == null || match.group(1)!.length > 1024) {
    throw const ApiFailure(
      'unsafe_material_path',
      kind: ApiFailureKind.unsafeRequest,
      outcome: CommandOutcome.notSent,
    );
  }
  return '/courses/organizations/$organization/material-delivery/${match.group(1)}';
}

/// Render only the rectangle-only SVG produced by the server QR generator.
/// No external references, SVG execution or general document parser is used.
class CertificateQr {
  final double dimension;
  final List<(double, double, double)> squares;
  CertificateQr._(this.dimension, this.squares);
  factory CertificateQr.parse(String svg) {
    if (svg.length > 256 * 1024 ||
        svg.contains(
          RegExp(
            r'<(?:script|image|foreignObject|use)\b',
            caseSensitive: false,
          ),
        )) {
      throw const FormatException();
    }
    final box = RegExp(r'viewBox="0 0 ([0-9.]+) ([0-9.]+)"').firstMatch(svg);
    final path = RegExp(r'<path d="([^"]+)"').firstMatch(svg);
    if (box == null || path == null || box.group(1) != box.group(2)) {
      throw const FormatException();
    }
    final dimension = double.parse(box.group(1)!);
    if (!dimension.isFinite || dimension < 10 || dimension > 250) {
      throw const FormatException();
    }
    final squares = <(double, double, double)>[];
    final expression = RegExp(
      r'M([0-9.]+),([0-9.]+)H([0-9.]+)V([0-9.]+)H([0-9.]+)z',
    );
    var offset = 0;
    for (final match in expression.allMatches(path.group(1)!)) {
      if (match.start != offset || squares.length >= 20000) {
        throw const FormatException();
      }
      offset = match.end;
      final x = double.parse(match.group(1)!),
          y = double.parse(match.group(2)!);
      final right = double.parse(match.group(3)!),
          bottom = double.parse(match.group(4)!);
      if (match.group(1) != match.group(5) ||
          ![
            x,
            y,
            right,
            bottom,
          ].every((n) => n.isFinite && n >= 0 && n <= dimension) ||
          right <= x ||
          bottom - y != right - x) {
        throw const FormatException();
      }
      squares.add((x, y, right - x));
    }
    if (offset != path.group(1)!.length || squares.isEmpty) {
      throw const FormatException();
    }
    return CertificateQr._(dimension, squares);
  }
}

class CertificateVerification {
  final String status, issuer;
  final LearningLabel title, course;
  final DateTime issuedAt;
  final CertificateQr qr;
  CertificateVerification(Map<String, dynamic> data, this.qr)
    : status = data['status'] as String,
      issuer = learningText(data['issuer_name']),
      title = LearningLabel(data, 'certificate_title'),
      course = LearningLabel(data, 'course_title'),
      issuedAt = learningDate(data['issued_at']);
}

class LearningRepository {
  final DomainApi api;
  final AuthRepository identity;
  LearningRepository(this.api, this.identity);
  Future<List<LearningCourse>> readLearning(String org) async {
    final data = await api.get('${learningRoot(org)}/my-learning');
    return learningDecode(() {
      final courses = learningObjects(
        learningObject(data)['courses'],
      ).map(LearningCourse.new).toList();
      if (courses.length > 500 ||
          courses.map((item) => item.id).toSet().length != courses.length) {
        throw const FormatException();
      }
      return courses;
    });
  }

  Future<StudentTimeline> timeline(String org) async {
    learningId(org);
    return learningDecodeAfter(
      await api.get('/programs/organizations/$org/my-timeline'),
      StudentTimeline.new,
    );
  }

  T learningDecodeAfter<T>(
    Object? data,
    T Function(Map<String, dynamic>) read,
  ) => learningDecode(() => read(learningObject(data)));
  Future<List<StudentAttendance>> attendance(String org) async {
    learningId(org);
    final data = await api.get('/attendance/organizations/$org/my-attendance');
    return learningDecode(
      () => learningObjects(
        learningObject(data)['enrollments'],
      ).map(StudentAttendance.new).toList(),
    );
  }

  Future<void> start(String org, String course) async {
    learningId(course);
    final data = await api.post(
      '${learningRoot(org)}/my-learning/$course/start',
      data: <String, dynamic>{},
    );
    learningDecode(() {
      final result = learningObject(data);
      if (result['organization_id'] != org || result['course_id'] != course) {
        throw const FormatException();
      }
      learningInt(result['version'], min: 1);
    }, command: true);
  }

  Future<void> complete(
    String org,
    LearningCourse course,
    String lesson,
  ) async {
    learningId(lesson);
    if (course.enrollmentVersion == null) {
      throw const ApiFailure(
        'course_not_started',
        kind: ApiFailureKind.conflict,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await api.post(
      '${learningRoot(org)}/my-learning/${course.id}/lessons/$lesson/complete',
      data: {'expected_course_enrollment_version': course.enrollmentVersion},
    );
    learningDecode(() {
      final result = learningObject(data);
      if (result['course_id'] != course.id || result['lesson_id'] != lesson) {
        throw const FormatException();
      }
    }, command: true);
  }

  Future<void> quiz(
    String org,
    String course,
    LearningQuiz quiz,
    Map<String, String> choices,
  ) async {
    learningId(course);
    if (!quiz.available ||
        quiz.remainingAttempts < 1 ||
        quiz.questions.any(
          (question) => !question.choices.any(
            (choice) => choice.id == choices[question.id],
          ),
        )) {
      throw const ApiFailure(
        'invalid_quiz_answers',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await api.post(
      '${learningRoot(org)}/my-learning/$course/quizzes/${quiz.id}/attempts',
      data: {
        'answers': [
          for (final question in quiz.questions)
            {'question_id': question.id, 'choice_id': choices[question.id]},
        ],
      },
    );
    learningDecode(() {
      if (learningObject(data)['quiz_id'] != quiz.id) {
        throw const FormatException();
      }
    }, command: true);
  }

  Future<void> submit(
    String org,
    String course,
    String assignment,
    String response,
    List<String> files,
  ) async {
    learningId(course);
    learningId(assignment);
    if (response.trim().isEmpty ||
        response.length > 10000 ||
        files.length > 100 ||
        files.toSet().length != files.length) {
      throw const ApiFailure(
        'invalid_assignment',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    for (final file in files) {
      learningId(file);
    }
    final data = await api.post(
      '${learningRoot(org)}/my-learning/$course/assignments/$assignment/submissions',
      data: {'response_text': response.trim(), 'file_ids': files},
    );
    learningDecode(() {
      if (learningObject(data)['assignment_id'] != assignment) {
        throw const FormatException();
      }
    }, command: true);
  }

  Future<void> checkIn(String org, String entered) async {
    learningId(org);
    final data = await api.post(
      '/attendance/organizations/$org/check-in',
      data: {'token': attendanceToken(entered)},
    );
    learningDecode(() {
      learningId(learningObject(data)['id']);
      learningId(learningObject(data)['session_id']);
    }, command: true);
  }

  Future<PrivateSnapshot> material(
    String org,
    String course,
    String material,
    PrivateFileScope scope, {
    CancelToken? cancelToken,
  }) async {
    learningId(course);
    learningId(material);
    final generation = identity.sessionGeneration;
    final token = CancelToken();
    final remove = identity.onInvalidated(() => token.cancel());
    if (cancelToken != null) {
      if (cancelToken.isCancelled) {
        token.cancel();
      } else {
        unawaited(cancelToken.whenCancel.then((_) => token.cancel()));
      }
    }
    PrivateSink? sink;
    PrivateSnapshot? result;
    var accepted = false;
    final bytes = BytesBuilder(copy: false);
    try {
      final access = learningObject(
        await api.post(
          '${learningRoot(org)}/my-learning/$course/materials/$material/access',
          data: <String, dynamic>{},
        ),
      );
      final path = materialApiPath(org, access['url'] as String);
      if (!learningDate(access['expires_at']).isAfter(DateTime.now().toUtc())) {
        throw const ApiFailure(
          'material_expired',
          kind: ApiFailureKind.forbidden,
        );
      }
      final response = await identity.authenticatedRequest(
        path,
        responseType: ResponseType.stream,
        cancelToken: token,
        transferTimeout: const Duration(seconds: 30),
      );
      final mime = (response.headers.value('content-type') ?? '')
          .split(';')
          .first
          .trim()
          .toLowerCase();
      final body = response.data;
      if (body is! ResponseBody) throw const FormatException();
      final length = int.tryParse(
        response.headers.value('content-length') ?? '',
      );
      if (!privateMediaTypes.contains(mime) ||
          (length != null && (length < 1 || length > materialReadLimit))) {
        await body.stream.listen((_) {}).cancel();
        throw const ApiFailure(
          'material_format_unavailable',
          kind: ApiFailureKind.unavailable,
        );
      }
      await for (final chunk in body.stream.timeout(
        const Duration(seconds: 30),
      )) {
        if (token.isCancelled ||
            generation != identity.sessionGeneration ||
            scope.closed) {
          throw const ApiFailure(
            'invalid_session',
            kind: ApiFailureKind.invalidSession,
          );
        }
        if (bytes.length + chunk.length > materialReadLimit) {
          throw const ApiFailure(
            'response_too_large',
            kind: ApiFailureKind.oversized,
          );
        }
        bytes.add(chunk);
      }
      if (bytes.length < 1 || (length != null && length != bytes.length)) {
        throw const FormatException();
      }
      final measured = bytes.takeBytes();
      final hash = crypto.sha256.convert(measured).toString();
      sink = await scope.beginDownload(
        mediaType: mime,
        maxBytes: materialReadLimit,
        expectedByteSize: measured.length,
        expectedSha256: hash,
      );
      for (
        var offset = 0;
        offset < measured.length;
        offset += channelChunkBytes
      ) {
        if (token.isCancelled ||
            scope.closed ||
            generation != identity.sessionGeneration) {
          throw const ApiFailure(
            'invalid_session',
            kind: ApiFailureKind.invalidSession,
          );
        }
        await sink.append(
          measured.sublist(
            offset,
            (offset + channelChunkBytes).clamp(0, measured.length),
          ),
        );
      }
      result = await sink.finish();
      await result.verify();
      if (token.isCancelled ||
          scope.closed ||
          generation != identity.sessionGeneration) {
        throw const ApiFailure(
          'invalid_session',
          kind: ApiFailureKind.invalidSession,
        );
      }
      accepted = true;
      return result;
    } on ApiFailure {
      rethrow;
    } catch (_) {
      throw const ApiFailure(
        'material_unavailable',
        kind: ApiFailureKind.unavailable,
      );
    } finally {
      remove();
      token.cancel();
      bytes.clear();
      if (!accepted) {
        await sink?.abort();
        await result?.dispose();
      }
    }
  }

  Future<CertificateVerification> verify(String code) async {
    if (!RegExp(r'^[A-Za-z0-9_-]{20,48}$').hasMatch(code)) {
      throw const ApiFailure(
        'invalid_certificate',
        kind: ApiFailureKind.validation,
      );
    }
    try {
      final response = await identity.dio.get<dynamic>(
        '/certificates/verify/$code',
        options: Options(followRedirects: false, maxRedirects: 0),
      );
      final qrResponse = await identity.dio.get<ResponseBody>(
        '/certificates/verify/$code/qr',
        options: Options(
          responseType: ResponseType.stream,
          followRedirects: false,
          maxRedirects: 0,
        ),
      );
      final bytes = BytesBuilder(copy: false);
      await for (final chunk in qrResponse.data!.stream.timeout(
        const Duration(seconds: 10),
      )) {
        if (bytes.length + chunk.length > 256 * 1024) {
          throw const FormatException();
        }
        bytes.add(chunk);
      }
      return learningDecode<CertificateVerification>(
        () => CertificateVerification(
          learningObject(response.data),
          CertificateQr.parse(utf8.decode(bytes.takeBytes())),
        ),
      );
    } on DioException catch (error) {
      throw ApiFailure.fromDio(error);
    } on ApiFailure {
      rethrow;
    } catch (_) {
      throw const ApiFailure(
        'invalid_response',
        kind: ApiFailureKind.invalidResponse,
      );
    }
  }
}
