import 'package:flutter/widgets.dart';
import '../../l10n/app_localizations.dart';
import '../../core/api/api_failure.dart';

class LearningWords {
  final bool tamil;
  final AppLocalizations text;
  LearningWords(BuildContext context)
    : tamil = Localizations.localeOf(context).languageCode == 'ta',
      text = AppLocalizations.of(context)!;
  String operator [](String key) => switch (key) {
    'title' => text.learnTitle,
    'learning' => text.learnLearning,
    'schedule' => text.learnSchedule,
    'attendance' => text.learnAttendance,
    'refresh' => text.learnRefresh,
    'loading' => text.learnLoading,
    'empty' => text.learnEmpty,
    'error' => text.learnError,
    'start' => text.learnStart,
    'complete' => text.learnComplete,
    'completed' => text.learnCompleted,
    'locked' => text.learnLocked,
    'progress' => text.learnProgress,
    'quiz' => text.learnQuiz,
    'attempts' => text.learnAttempts,
    'submitQuiz' => text.learnSubmitQuiz,
    'score' => text.learnScore,
    'passed' => text.learnPassed,
    'failed' => text.learnFailed,
    'assignment' => text.learnAssignment,
    'response' => text.learnResponse,
    'submitAssignment' => text.learnSubmitAssignment,
    'remaining' => text.learnRemaining,
    'pendingReview' => text.learnPendingReview,
    'feedback' => text.learnFeedback,
    'files' => text.learnFiles,
    'choose' => text.learnChoose,
    'upload' => text.learnUpload,
    'recover' => text.learnRecover,
    'readback' => text.learnReadback,
    'continue' => text.learnContinue,
    'uncertain' => text.learnUncertain,
    'conflict' => text.learnConflict,
    'saved' => text.learnSaved,
    'discard' => text.learnDiscard,
    'close' => text.learnClose,
    'download' => text.learnDownload,
    'receipt' => text.learnReceipt,
    'privateReceipt' => text.learnPrivateReceipt,
    'remove' => text.learnRemove,
    'confirmRemove' => text.learnConfirmRemove,
    'cancel' => text.learnCancel,
    'confirm' => text.learnConfirm,
    'reselect' => text.learnReselect,
    'frozen' => text.learnFrozen,
    'disabled' => text.learnDisabled,
    'nativeRequired' => text.learnNativeRequired,
    'limits' => text.learnLimits,
    'bytes' => text.learnBytes,
    'count' => text.learnCount,
    'minimum' => text.learnMinimum,
    'maximum' => text.learnMaximum,
    'pending' => text.learnPending,
    'uploading' => text.learnUploading,
    'quarantined' => text.learnQuarantined,
    'scanning' => text.learnScanning,
    'clean' => text.learnClean,
    'infected' => text.learnInfected,
    'rejected' => text.learnRejected,
    'deleted' => text.learnDeleted,
    'unusable' => text.learnUnusable,
    'filePending' => text.learnFilePending,
    'selected' => text.learnSelected,
    'discardSelection' => text.learnDiscardSelection,
    'certificate' => text.learnCertificate,
    'eligible' => text.learnEligible,
    'ineligible' => text.learnIneligible,
    'verify' => text.learnVerify,
    'valid' => text.learnValid,
    'revoked' => text.learnRevoked,
    'issuer' => text.learnIssuer,
    'issued' => text.learnIssued,
    'qr' => text.learnQr,
    'material' => text.learnMaterial,
    'materialLimit' => text.learnMaterialLimit,
    'token' => text.learnToken,
    'checkIn' => text.learnCheckIn,
    'camera' => text.learnCamera,
    'attended' => text.learnAttended,
    'required' => text.learnRequired,
    'threshold' => text.learnThreshold,
    'lowAttendance' => text.learnLowAttendance,
    'unmarked' => text.learnUnmarked,
    'present' => text.learnPresent,
    'absent' => text.learnAbsent,
    'late' => text.learnLate,
    'excused' => text.learnExcused,
    'scheduled' => text.learnScheduled,
    'cancelled' => text.learnCancelled,
    'in_person' => text.learnInPerson,
    'online' => text.learnOnline,
    'hybrid' => text.learnHybrid,
    'sessionExpired' => text.learnSessionExpired,
    'accessDenied' => text.learnAccessDenied,
    'invalid' => text.learnInvalid,
    'wait' => text.learnWait,
    'tooLarge' => text.learnTooLarge,
    'leave' => text.learnLeave,
    'stay' => text.learnStay,
    'leaveAction' => text.learnLeaveAction,
    'application' => text.learnApplication,
    'selection' => text.learnSelection,
    'enrollment' => text.learnEnrollment,
    'session' => text.learnSession,
    'course_completion_incomplete' => text.learnCourseCompletionIncomplete,
    'quiz_requirements_incomplete' => text.learnQuizRequirementsIncomplete,
    'assignment_requirements_incomplete' =>
      text.learnAssignmentRequirementsIncomplete,
    _ => text.learnRecord,
  };
  String failure(ApiFailure error) {
    if (error.code == 'private_storage_unavailable') {
      return text.fileProtectionRequired;
    }
    if (error.uncertain) return this['uncertain'];
    if (error.kind == ApiFailureKind.invalidSession) {
      return this['sessionExpired'];
    }
    if (error.kind == ApiFailureKind.forbidden ||
        error.kind == ApiFailureKind.notFound) {
      return this['accessDenied'];
    }
    if (error.kind == ApiFailureKind.conflict) return this['conflict'];
    if (error.kind == ApiFailureKind.validation) return this['invalid'];
    if (error.kind == ApiFailureKind.rateLimited) return this['wait'];
    if (error.kind == ApiFailureKind.oversized) return this['tooLarge'];
    return this['error'];
  }
}
