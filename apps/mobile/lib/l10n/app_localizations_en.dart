// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String filePolicyCount(int count) {
    return 'This policy allows up to $count documents across requirements.';
  }

  @override
  String get title => 'Entrepreneurship Development Program';

  @override
  String get welcome => 'Build your skills. Shape your business.';

  @override
  String get availability =>
      'Program details and applications will be available here soon.';

  @override
  String get language => 'தமிழில் படிக்க';

  @override
  String get authTitle => 'Your account';

  @override
  String get authEmail => 'Email';

  @override
  String get authPassword => 'Password';

  @override
  String get authName => 'Name';

  @override
  String get authToken => 'Verification or reset code';

  @override
  String get authLogin => 'Sign in';

  @override
  String get authRegister => 'Create account';

  @override
  String get authVerify => 'Verify email';

  @override
  String get authRequestVerification => 'Send verification';

  @override
  String get authRequestReset => 'Forgot password';

  @override
  String get authReset => 'Reset password';

  @override
  String get authLogout => 'Sign out';

  @override
  String get authLogoutAll => 'Sign out all devices';

  @override
  String get authAccepted =>
      'If the account is eligible, a message has been queued. Follow the instructions in that message.';

  @override
  String get authCompleted => 'Done. You can now sign in.';

  @override
  String get authLoading => 'Please wait…';

  @override
  String get authError =>
      'The request could not be completed. Check your details and try again.';

  @override
  String get authUnavailable =>
      'Account messages are not available yet. Please try again later.';

  @override
  String get authInvalid =>
      'Email or password is incorrect, or the account is not verified.';

  @override
  String get authLimited => 'Too many attempts. Please wait 15 minutes.';

  @override
  String get authSessionExpired =>
      'Your session expired. Please sign in again.';

  @override
  String get authSessions => 'Active devices';

  @override
  String get authNoSessions => 'No active devices.';

  @override
  String get authRevoke => 'Sign out device';

  @override
  String get authCurrent => 'This device';

  @override
  String get authStaff => 'Staff workspace';

  @override
  String get authDenied => 'You do not have access to this workspace.';

  @override
  String get authOrganizations => 'Your organizations';

  @override
  String get authAudit => 'Audit history';

  @override
  String get authNoAudit => 'No audit events to show.';

  @override
  String get authPasswordHelp => 'Use 12–128 characters.';

  @override
  String get authBack => 'Back to account';

  @override
  String get authNoOrganizations =>
      'No staff access is assigned to your account.';

  @override
  String get authRefresh => 'Refresh';

  @override
  String get authNext => 'Next';

  @override
  String get cmsPages => 'Pages';

  @override
  String get cmsEmpty => 'No pages yet.';

  @override
  String get cmsError =>
      'Unable to complete the request. Retry or sign in again.';

  @override
  String get cmsLoading => 'Loading';

  @override
  String get cmsMore => 'Load more';

  @override
  String get cmsBack => 'Back';

  @override
  String get cmsUnavailable => 'This page is unavailable.';

  @override
  String get cmsRetry => 'Retry';

  @override
  String get mobileApplications => 'My applications';

  @override
  String get mobileNoApplications => 'You have no saved applications yet.';

  @override
  String get mobileNews => 'News';

  @override
  String get mobileEvents => 'Events';

  @override
  String get mobileFaq => 'Frequently asked questions';

  @override
  String get mobileStories => 'Success stories';

  @override
  String get mobileSessionUnavailable =>
      'Your account could not be restored. Retry or sign in.';

  @override
  String get mobileDraft => 'Draft';

  @override
  String get mobileSubmitted => 'Submitted';

  @override
  String get mobileUnderReview => 'Under review';

  @override
  String get mobileShortlisted => 'Shortlisted';

  @override
  String get mobileInterview => 'Interview scheduled';

  @override
  String get mobileSelected => 'Selected';

  @override
  String get mobileWaitlisted => 'Waitlisted';

  @override
  String get mobileRejected => 'Not selected';

  @override
  String get mobileEnrolled => 'Enrolled';

  @override
  String get mobileSchedule => 'My schedule';

  @override
  String get mobileLearning => 'My learning';

  @override
  String get mobileSupport => 'Support';

  @override
  String get mobileMentoring => 'Mentoring';

  @override
  String get mobilePlans => 'Business plan';

  @override
  String get mobileResources => 'Resources and funding';

  @override
  String get mobileUpdates => 'Updates';

  @override
  String get mobileBusiness => 'My business';

  @override
  String get mobileImpact => 'My outcomes';

  @override
  String get mobileUnsaved =>
      'Leave this page? Your unsaved changes will be lost.';

  @override
  String get mobileUncertainLeave =>
      'The last request still needs review. Leave this page? Reopen this exact application to check the saved result before trying again.';

  @override
  String get mobileStay => 'Stay';

  @override
  String get mobileLeave => 'Leave';

  @override
  String get mobileSaved => 'Saved';

  @override
  String get mobileSave => 'Save draft';

  @override
  String get mobileSubmit => 'Submit application';

  @override
  String get mobileConfirmSubmit =>
      'Submit this application? The submitted answers and evidence will be frozen.';

  @override
  String get mobileCommandUncertain =>
      'The result is uncertain. Refresh the exact record before deciding whether to try again. Your input is preserved.';

  @override
  String get mobileConflict =>
      'The record changed elsewhere. Review the current saved version before saving your edits.';

  @override
  String get mobileReadOnly => 'This application is read only.';

  @override
  String get mobileIntakes => 'Open application intakes';

  @override
  String get mobileNoIntakes =>
      'There are no open intakes for this organization.';

  @override
  String get mobileStartApplication => 'Start or resume application';

  @override
  String get mobileSubmitSuccess => 'Application submitted';

  @override
  String get mobileRequired => 'Required';

  @override
  String get mobileRefreshRecord => 'Refresh saved record';

  @override
  String get mobileUseSaved => 'Use saved answers';

  @override
  String get mobileKeepEdits => 'Keep my edits';

  @override
  String get mobileDocuments => 'Supporting documents';

  @override
  String get mobileProgramIntake => 'Program applications';

  @override
  String get fileCollectionDisabled =>
      'Document collection is unavailable. Existing document status remains visible.';

  @override
  String get fileNativeRequired =>
      'Document selection and private downloads require the Android or iOS app.';

  @override
  String get fileChoose => 'Choose document';

  @override
  String get fileReplace => 'Replace document';

  @override
  String get fileRemove => 'Remove document';

  @override
  String get fileConfirmRemove => 'Remove this document from the draft?';

  @override
  String get fileUpload => 'Upload selected bytes';

  @override
  String get fileRecoverIntent => 'Recover this upload registration';

  @override
  String get fileRefresh => 'Refresh document status';

  @override
  String get fileReadBeforeRetry =>
      'Check the saved document status before continuing. Bytes will not be resent automatically.';

  @override
  String get fileReselect => 'Reselect identical document';

  @override
  String get fileDiscard => 'Discard selected copy';

  @override
  String get fileSelected => 'Selected private copy';

  @override
  String get fileDownload => 'Verify private download';

  @override
  String get fileDownloadReceipt => 'Private download verified';

  @override
  String get fileCloseReceipt => 'Close and delete private copy';

  @override
  String get filePending => 'Awaiting upload';

  @override
  String get fileUploading => 'Upload in progress';

  @override
  String get fileQuarantined => 'Awaiting security scan';

  @override
  String get fileScanning => 'Security scan in progress';

  @override
  String get fileClean => 'Scan complete';

  @override
  String get fileInfected => 'Unsafe document';

  @override
  String get fileRejected => 'Document rejected';

  @override
  String get fileDeleted => 'Document deleted';

  @override
  String get fileUnusable =>
      'This document is not currently usable for submission.';

  @override
  String get fileFrozenEvidence => 'Submitted document proof';

  @override
  String get fileInvalid =>
      'The selected bytes are empty, changed, invalid or do not match a supported type. Choose a valid document.';

  @override
  String get fileTooLarge => 'The document exceeds the displayed byte limit.';

  @override
  String get fileUnavailable =>
      'Private file handling is unavailable. Refresh the document status before trying again.';

  @override
  String fileLimits(int minimum, int maximum, int bytes) {
    return '$minimum–$maximum documents; up to $bytes bytes each';
  }

  @override
  String fileRetention(int days, int rejectedDays) {
    return 'Retention: $days days; rejected documents: $rejectedDays days';
  }

  @override
  String fileProof(String mediaType, int bytes, int version) {
    return '$mediaType · $bytes bytes · version $version';
  }

  @override
  String get mobileHome => 'Home';

  @override
  String get mobileDateFormat => 'Use YYYY-MM-DD';

  @override
  String get mobileReviewSaved =>
      'Review the saved answers before choosing how to continue.';

  @override
  String get mobileChooseOrganization =>
      'Choose a program organization or open a saved application below.';

  @override
  String get mobileDocumentsReady => 'Required documents are ready.';

  @override
  String get mobileDocumentsPending =>
      'Required documents must be uploaded and usable before submission.';

  @override
  String get mobileStatusHistory => 'Status history';

  @override
  String get mobileApplicationUnavailable =>
      'This application is unavailable or you no longer have access.';

  @override
  String get mobileConnectionInterrupted =>
      'The connection was interrupted. Your current input is preserved. Retry when connected.';

  @override
  String get mobileCheckAnswers =>
      'Check the answer types, required fields and acknowledgements, then try again.';

  @override
  String get mobileWaitAndRetry => 'Please wait before trying again.';

  @override
  String get authLogoutUnconfirmed =>
      'Signed out on this device. Server revocation could not be confirmed; try signing out all devices when connected.';

  @override
  String mobileSavedVersion(int version) {
    return 'Saved version $version';
  }

  @override
  String mobileCompletion(int percent) {
    return '$percent% complete';
  }

  @override
  String get learnTitle => 'My training';

  @override
  String get learnLearning => 'Learning';

  @override
  String get learnSchedule => 'Schedule';

  @override
  String get learnAttendance => 'Attendance';

  @override
  String get learnRefresh => 'Refresh';

  @override
  String get learnLoading => 'Loading…';

  @override
  String get learnEmpty => 'No records are available.';

  @override
  String get learnError => 'This information is unavailable. Try again.';

  @override
  String get learnStart => 'Start course';

  @override
  String get learnComplete => 'Mark lesson complete';

  @override
  String get learnCompleted => 'Completed';

  @override
  String get learnLocked => 'Complete the prerequisites to open this lesson.';

  @override
  String get learnProgress => 'Course progress';

  @override
  String get learnQuiz => 'Quiz';

  @override
  String get learnAttempts => 'Attempts remaining';

  @override
  String get learnSubmitQuiz => 'Submit answers';

  @override
  String get learnScore => 'Best score';

  @override
  String get learnPassed => 'Passed';

  @override
  String get learnFailed => 'Not passed';

  @override
  String get learnAssignment => 'Assignment';

  @override
  String get learnResponse => 'Your response';

  @override
  String get learnSubmitAssignment => 'Submit assignment';

  @override
  String get learnRemaining => 'Submissions remaining';

  @override
  String get learnPendingReview => 'Awaiting trainer review';

  @override
  String get learnFeedback => 'Trainer feedback';

  @override
  String get learnFiles => 'Assignment files';

  @override
  String get learnChoose => 'Choose a file';

  @override
  String get learnUpload => 'Upload selected bytes';

  @override
  String get learnRecover => 'Recover the same file request';

  @override
  String get learnReadback => 'Read current saved state';

  @override
  String get learnContinue => 'I reviewed the saved state';

  @override
  String get learnUncertain =>
      'The result is uncertain. Read the saved state before another action.';

  @override
  String get learnConflict =>
      'The saved version changed. Refresh and review it.';

  @override
  String get learnSaved => 'Saved. Current server state is shown.';

  @override
  String get learnDiscard => 'Discard local inputs';

  @override
  String get learnClose => 'Close and delete private copy';

  @override
  String get learnDownload => 'Read private copy';

  @override
  String get learnReceipt => 'Private download receipt';

  @override
  String get learnPrivateReceipt =>
      'The private copy is deleted when closed, backgrounded or left.';

  @override
  String get learnRemove => 'Remove file';

  @override
  String get learnConfirmRemove => 'Remove this staged file?';

  @override
  String get learnCancel => 'Cancel';

  @override
  String get learnConfirm => 'Confirm';

  @override
  String get learnReselect => 'Select the exact registered bytes again';

  @override
  String get learnFrozen => 'Frozen submission evidence';

  @override
  String get learnDisabled => 'File collection is disabled.';

  @override
  String get learnNativeRequired =>
      'Private file selection requires the Android or iOS app.';

  @override
  String get learnLimits => 'File limits';

  @override
  String get learnBytes => 'bytes';

  @override
  String get learnCount => 'files';

  @override
  String get learnMinimum => 'minimum';

  @override
  String get learnMaximum => 'maximum';

  @override
  String get learnPending => 'Not uploaded';

  @override
  String get learnUploading => 'Uploading';

  @override
  String get learnQuarantined => 'Awaiting security scan';

  @override
  String get learnScanning => 'Security scan in progress';

  @override
  String get learnClean => 'Scan complete';

  @override
  String get learnInfected => 'Unsafe file';

  @override
  String get learnRejected => 'File rejected';

  @override
  String get learnDeleted => 'Deleted';

  @override
  String get learnUnusable => 'This file is not usable for submission.';

  @override
  String get learnFilePending =>
      'Finish or discard the selected file before another action.';

  @override
  String get learnSelected => 'Selected byte proof';

  @override
  String get learnDiscardSelection => 'Discard selection';

  @override
  String get learnCertificate => 'Certificate';

  @override
  String get learnEligible =>
      'Course requirements met; certificate issuance is handled by the program.';

  @override
  String get learnIneligible => 'Certificate requirements are incomplete.';

  @override
  String get learnVerify => 'Verify certificate and show QR';

  @override
  String get learnValid => 'Valid';

  @override
  String get learnRevoked => 'Revoked';

  @override
  String get learnIssuer => 'Issuer';

  @override
  String get learnIssued => 'Issued';

  @override
  String get learnQr => 'Public certificate verification QR';

  @override
  String get learnMaterial => 'Read lesson material';

  @override
  String get learnMaterialLimit =>
      'Private material downloads are limited to 2 MiB. Supported document/image/text formats only.';

  @override
  String get learnToken => 'Attendance code or edp-attendance payload';

  @override
  String get learnCheckIn => 'Check in';

  @override
  String get learnCamera =>
      'Enter or paste the trainer’s code. Camera scanning is not available in this build.';

  @override
  String get learnAttended => 'Attended';

  @override
  String get learnRequired => 'Required';

  @override
  String get learnThreshold => 'Required percentage';

  @override
  String get learnLowAttendance =>
      'Attendance is below the required percentage.';

  @override
  String get learnUnmarked => 'Not marked';

  @override
  String get learnPresent => 'Present';

  @override
  String get learnAbsent => 'Absent';

  @override
  String get learnLate => 'Late';

  @override
  String get learnExcused => 'Excused';

  @override
  String get learnScheduled => 'Scheduled';

  @override
  String get learnCancelled => 'Cancelled';

  @override
  String get learnInPerson => 'In person';

  @override
  String get learnOnline => 'Online';

  @override
  String get learnHybrid => 'Hybrid';

  @override
  String get learnSessionExpired => 'Your session expired. Sign in again.';

  @override
  String get learnAccessDenied => 'Access is unavailable for this account.';

  @override
  String get learnInvalid => 'Check the input and selected answers.';

  @override
  String get learnWait => 'Wait before trying again.';

  @override
  String get learnTooLarge => 'This file exceeds the supported size.';

  @override
  String get learnLeave => 'Leave and discard unsaved work?';

  @override
  String get learnStay => 'Stay';

  @override
  String get learnLeaveAction => 'Leave';

  @override
  String get learnApplication => 'Application';

  @override
  String get learnSelection => 'Selection';

  @override
  String get learnEnrollment => 'Enrollment';

  @override
  String get learnSession => 'Session';

  @override
  String get learnCourseCompletionIncomplete =>
      'Complete the required lessons.';

  @override
  String get learnQuizRequirementsIncomplete => 'Pass the required quizzes.';

  @override
  String get learnAssignmentRequirementsIncomplete =>
      'Pass the required assignments.';

  @override
  String get learnRecord => 'Record';

  @override
  String get domainDiscardThisTicketSUnsentText23075b =>
      'Discard this ticket’s unsent text and selected private copies?';

  @override
  String get domainClose7d9eb7 => 'Close';

  @override
  String get domainMySupportTicketsbca759 => 'My support tickets';

  @override
  String get domainTicketStatusFiltere21337 => 'Ticket status filter';

  @override
  String get domainAllStatuses8ee573 => 'All statuses';

  @override
  String get domainRefreshTickets1c30a6 => 'Refresh tickets';

  @override
  String get domainNoSupportTickets72f5d9 => 'No support tickets.';

  @override
  String get domainMoreTickets0e480f => 'More tickets';

  @override
  String get domainCreateASupportTicket9709e0 => 'Create a support ticket';

  @override
  String get domainCategory292c06 => 'Category';

  @override
  String get domainPriorityd60dbb => 'Priority';

  @override
  String get domainSubject689712 => 'Subject';

  @override
  String get domainQuestionRequestba73e0 => 'Question / request';

  @override
  String get domainCreateTickete836fc => 'Create ticket';

  @override
  String get domainRecoverThisExactTicketRequestdf25ad =>
      'Recover this exact ticket request';

  @override
  String get domainRefreshThisConversation6b5a20 => 'Refresh this conversation';

  @override
  String get domainVerifyPrivateDownload3a2d36 => 'Verify private download';

  @override
  String get domainMoreMessages9b4a40 => 'More messages';

  @override
  String get domainSharedReply4d437b => 'Shared reply';

  @override
  String get domainOptionalPlainTextAttachment030a73 =>
      'Optional plain text attachment';

  @override
  String get domainUtf8TextMaximum32768ded21d =>
      'UTF-8 text, maximum 32,768 bytes';

  @override
  String get domainSendSharedReplyf121d3 => 'Send shared reply';

  @override
  String get domainReasonForClosingReopening5e3744 =>
      'Reason for closing / reopening';

  @override
  String get domainCloseThisResolvedTicket3edf38 =>
      'Close this resolved ticket?';

  @override
  String get domainCloseResolvedTicketf3687f => 'Close resolved ticket';

  @override
  String get domainReopenTickete6b8d8 => 'Reopen ticket';

  @override
  String get domainTicketHistory183fea => 'Ticket history';

  @override
  String get domainMoreHistory7e2113 => 'More history';

  @override
  String get domainPrivateDownloadVerified22d5aa => 'Private download verified';

  @override
  String get domainCloseAndDeletePrivateCopy3f2b2d =>
      'Close and delete private copy';

  @override
  String get domainSupportNotifications3a8090 => 'Support notifications';

  @override
  String get domainRefreshNotificationsAndPreferencef9bb90 =>
      'Refresh notifications and preference';

  @override
  String get domainInAppSupportNotificationsd81899 =>
      'In-app support notifications';

  @override
  String get domainMoreNotifications9e58f9 => 'More notifications';

  @override
  String get domainSecureSharedAttachmentsff80f8 => 'Secure shared attachments';

  @override
  String get domainFileCollectionIsUnavailable1eb8de =>
      'File collection is unavailable.';

  @override
  String get domainRetentionDays51de08 => 'Retention days';

  @override
  String get domainRefreshAttachmentStatusd7974f => 'Refresh attachment status';

  @override
  String get domainUsableb4d1bf => 'Usable';

  @override
  String get domainNotUsabled7464d => 'Not usable';

  @override
  String get domainRemoveStagedFilea50773 => 'Remove staged file';

  @override
  String get domainRemoveThisStagedAttachmentf4b57b =>
      'Remove this staged attachment?';

  @override
  String get domainMoreAttachments1f9e79 => 'More attachments';

  @override
  String get domainChooseSharedAttachment971b66 => 'Choose shared attachment';

  @override
  String get domainRecoverExactFileRegistrationa8a032 =>
      'Recover exact file registration';

  @override
  String get domainUploadSelectedBytes08b1dc => 'Upload selected bytes';

  @override
  String get domainDiscardSelectedPrivateCopy449966 =>
      'Discard selected private copy';

  @override
  String get domainAnUploadedFileIsAttachedOnly99c018 =>
      'An uploaded file is attached only after a usable file is selected and the shared reply succeeds.';

  @override
  String get domainOfficialLinkCopiede5a1aa => 'Official link copied.';

  @override
  String get domainVerified4f7838 => 'Verified';

  @override
  String get domainCloses74c21a => 'Closes';

  @override
  String get domainResourcesOpportunitiesAndFunding0ba4d7 =>
      'Resources, opportunities and funding';

  @override
  String get domainResourceTypec9bf2e => 'Resource type';

  @override
  String get domainAllTypesf10988 => 'All types';

  @override
  String get domainAvailability12f67f => 'Availability';

  @override
  String get domainApplyFiltersd80ab1 => 'Apply filters';

  @override
  String get domainNoMatchingResourcesfee1b1 => 'No matching resources.';

  @override
  String get domainDetails45989d => 'Details';

  @override
  String get domainOpenOfficialSource7bd352 => 'Open official source';

  @override
  String get domainUnsave51883b => 'Unsave';

  @override
  String get domainSave1509f5 => 'Save';

  @override
  String get domainExpressInterest97c8c3 => 'Express interest';

  @override
  String get domainTrackMyFundingApplicationb7f857 =>
      'Track my funding application';

  @override
  String get domainMoreResources3f990f => 'More resources';

  @override
  String get domainRefreshSavedItemsAndFundingStatusea7e93 =>
      'Refresh saved items and funding status';

  @override
  String get domainSavedResources5d702b => 'Saved resources';

  @override
  String get domainResourceNoLongerAvailable008112 =>
      'Resource no longer available';

  @override
  String get domainMoreSavedItems5862e9 => 'More saved items';

  @override
  String get domainOpportunityInterests68b05b => 'Opportunity interests';

  @override
  String get domainMoreInterests5eaef0 => 'More interests';

  @override
  String get domainSelfReportedFundingProgress81e27b =>
      'Self-reported funding progress';

  @override
  String get domainReasonUpdate49c0dc => 'Reason / update';

  @override
  String get domainRecordThisFundingStatusUpdate888dec =>
      'Record this funding status update?';

  @override
  String get domainMoreFundingCases3e9368 => 'More funding cases';

  @override
  String get domainMyMentoringb93152 => 'My mentoring';

  @override
  String get domainRefreshMentoringeee9c0 => 'Refresh mentoring';

  @override
  String get domainNoMentoringAssignmentsAreAvailable4ebb99 =>
      'No mentoring assignments are available.';

  @override
  String get domainCompletedSessionfca593 => 'Completed session';

  @override
  String get domainRating15b4690a => 'Rating (1–5)';

  @override
  String get domainFeedbackCommentbf4a27 => 'Feedback comment';

  @override
  String get domainSendSessionFeedbacke07582 => 'Send session feedback';

  @override
  String get domainDiscardUnsavedTextAndSelectedPrivatea3487b =>
      'Discard unsaved text and selected private copies before changing sections?';

  @override
  String get domainLeaveThisPageAndDiscardUnsavedcb9eed =>
      'Leave this page and discard unsaved work?';

  @override
  String get domainParticipantSupporte5a040 => 'Participant support';

  @override
  String get domainMyBusinessPlanf1ef69 => 'My business plan';

  @override
  String get domainRefreshPlanscbc510 => 'Refresh plans';

  @override
  String get domainNoActiveEnrollmentIsAvailableFor2f3a04 =>
      'No active enrollment is available for plan authoring.';

  @override
  String get domainActiveEnrollmentebb2ab => 'Active enrollment';

  @override
  String get domainDiscardEditsBeforeChangingEnrollment28e2f9 =>
      'Discard edits before changing enrollment?';

  @override
  String get domainReviewTheCurrentSavedPlanBefore514269 =>
      'Review the current saved plan before continuing. Your edits are retained.';

  @override
  String get domainUseCurrentVersionAndKeepMybb6388 =>
      'Use current version and keep my edits';

  @override
  String get domainUseSavedPlanfee405 => 'Use saved plan';

  @override
  String get domainCreatePlan4e207a => 'Create plan';

  @override
  String get domainSaveThisSection1e6c91 => 'Save this section';

  @override
  String get domainSubmitThisSavedPlanForReview262665 =>
      'Submit this saved plan for review?';

  @override
  String get domainSubmitSavedPlan231cac => 'Submit saved plan';

  @override
  String get domainSubmission8d11f7 => 'Submission';

  @override
  String get domainPublicResourcesbacc34 => 'Public resources';

  @override
  String get domainTheResultIsUnknownRefreshThis9caf4b =>
      'The result is unknown. Refresh this record before deciding to retry.';

  @override
  String get domainThisRecordIsUnavailableForThis7a537f =>
      'This record is unavailable for this account.';

  @override
  String get domainTheRecordChangedRefreshAndReview2840a2 =>
      'The record changed. Refresh and review your retained text.';

  @override
  String get domainSignInAgainToContinue40f531 => 'Sign in again to continue.';

  @override
  String get domainCheckTheEnteredValuesAndDisplayedee60bd =>
      'Check the entered values and displayed limits.';

  @override
  String get domainPleaseWaitBeforeTryingAgaind24731 =>
      'Please wait before trying again.';

  @override
  String get domainUnableToLoadThisInformationYour85597a =>
      'Unable to load this information. Your text is retained.';

  @override
  String get domainCancel19766e => 'Cancel';

  @override
  String get domainConfirmeebdd2 => 'Confirm';

  @override
  String get domainLeaveThisUnsavedOrUnconfirmedWork5e200a =>
      'Leave this unsaved or unconfirmed work?';

  @override
  String get domainStay08fd1d => 'Stay';

  @override
  String get domainLeavefc6e4a => 'Leave';

  @override
  String get domainBusinessAndOutcomes964516 => 'Business and outcomes';

  @override
  String get domainPrivateBusiness9c181b => 'Private business';

  @override
  String get domainSelfReportedImpact0006f1 => 'Self-reported impact';

  @override
  String get domainTheseProfilesArePrivatePublicSharingc4f5b1 =>
      'These profiles are private. Public sharing is off. Follow-up dates come from your saved program policy.';

  @override
  String get domainRefresh0e9161 => 'Refresh';

  @override
  String get domainNoEligibleActiveOrCompletedEnrollment98e845 =>
      'No eligible active or completed enrollment is available.';

  @override
  String get domainEnrollment2d91aa => 'Enrollment';

  @override
  String get domainDiscardThisUnsavedInputAnUnconfirmed91fe23 =>
      'Discard this unsaved input? An unconfirmed command must still be checked in saved state.';

  @override
  String get domainDiscardeb1a70 => 'Discard';

  @override
  String get domainDiscardUnsavedInput9136d8 => 'Discard unsaved input';

  @override
  String get domainImmutableProfileRevisionsLatest20cf668b =>
      'Immutable profile revisions (latest 20)';

  @override
  String get domainVersiondd1679 => 'Version';

  @override
  String get domainFollowUpReportsfd330c => 'Follow-up reports';

  @override
  String get domainDue907173 => 'Due';

  @override
  String get domainDaysSavedPolicy6d4582 => 'days (saved policy)';

  @override
  String get domainOverdued66094 => 'Overdue';

  @override
  String get domainCompletedImmutableSelfReport17ca7c =>
      'Completed immutable self-report';

  @override
  String get domainOpenFollowUpReport53a6b8 => 'Open follow-up report';

  @override
  String get domainPrivateBusinessProfilef1fb7d => 'Private business profile';

  @override
  String get domainSavePrivateProfile9988a7 => 'Save private profile';

  @override
  String get domainReadSavedStated9f3b0 => 'Read saved state';

  @override
  String get domainReviewTheSavedProfileBeforeAnother264cad =>
      'Review the saved profile before another write.';

  @override
  String get domainNoProfileExistsForThisEnrollment99706d =>
      'No profile exists for this enrollment.';

  @override
  String get domainUseSavedProfile913e70 => 'Use saved profile';

  @override
  String get domainKeepMyEditsForExplicitSavea5c95a =>
      'Keep my edits for explicit save';

  @override
  String get domainReportThisFollowUpOnce8ce6ce => 'Report this follow-up once';

  @override
  String get domainReadSavedOutcomeBeforeRetry66f67c =>
      'Read saved outcome before retry';

  @override
  String get domainSubmitImmutableOutcome109e03 => 'Submit immutable outcome';

  @override
  String get domainSelfReportedObservationsTheseAreSeparate3a51e7 =>
      'Self-reported observations. These are separate from business follow-up reports and do not establish verified impact.';

  @override
  String get domainRefreshObservations34ae4c => 'Refresh observations';

  @override
  String get domainNoEligibleEnrollments16c2f5 => 'No eligible enrollments.';

  @override
  String get domainMoreEnrollments6edb68 => 'More enrollments';

  @override
  String get domainPinnedDefinitionEdition03b94a => 'Pinned definition edition';

  @override
  String get domainMoreDefinitions6f842b => 'More definitions';

  @override
  String get domainReadExactObservationStatee6cbb6 =>
      'Read exact observation state';

  @override
  String get domainExplicitlyRetryUnchangedRequest0c8f5a =>
      'Explicitly retry unchanged request';

  @override
  String get domainDiscardPendingRequestChooseACurrent24ad4d =>
      'Discard pending request; choose a current record';

  @override
  String get domainStartAnotherObservatione8e1c1 => 'Start another observation';

  @override
  String get domainObservationHistoryEachRevisionIsRetaineda9da2a =>
      'Observation history (each revision is retained)';

  @override
  String get domainRevision2e516d => 'Revision';

  @override
  String get domainSupersedeWithAReason4294f3 => 'Supersede with a reason';

  @override
  String get domainMoreObservationHistory11b7c2 => 'More observation history';

  @override
  String get domainTheActionCouldNotBeConfirmedaed76e =>
      'The action could not be confirmed. Your input is kept. Refresh saved state before retrying an uncertain action.';

  @override
  String get domainEnrollmentUpdatesc8101a => 'Enrollment updates';

  @override
  String get domainInAppEnrollmentUpdatesRefreshTof8b773 =>
      'In-app enrollment updates. Refresh to check for new updates.';

  @override
  String get domainReceiveEnrollmentUpdatesc62c16 =>
      'Receive enrollment updates';

  @override
  String get domainReadSavedNotificationPreference918105 =>
      'Read saved notification preference';

  @override
  String get domainRefreshInboxa804e4 => 'Refresh inbox';

  @override
  String get domainNoAvailableUpdatesba4851 => 'No available updates.';

  @override
  String get domainYourProgramEnrollmentIsConfirmed72dce5 =>
      'Your program enrollment is confirmed.';

  @override
  String get domainCheckSavedReadStatus1e817a => 'Check saved read status';

  @override
  String get domainMarkReadb49c9b => 'Mark read';

  @override
  String get domainOpenCurrentSchedule031f2c => 'Open current schedule';

  @override
  String get domainMoreUpdates5fdeda => 'More updates';

  @override
  String get alumniFieldName => 'Business name';

  @override
  String get alumniFieldSector => 'Sector';

  @override
  String get alumniFieldProductsServices => 'Products and services';

  @override
  String get alumniFieldStage => 'Business stage';

  @override
  String get alumniFieldRegistrationInfo => 'Registration details (optional)';

  @override
  String get alumniFieldStartedOn => 'Started on (YYYY-MM-DD)';

  @override
  String get alumniFieldTeamSize => 'Team size';

  @override
  String get alumniFieldInvestmentBand => 'Investment band (INR)';

  @override
  String get alumniFieldFundingStatus => 'Funding status';

  @override
  String get alumniFieldRevenueBand => 'Revenue band (INR)';

  @override
  String get alumniFieldSupportNeeds => 'Support needs (optional)';

  @override
  String get alumniFieldReportedOn => 'Reported on (YYYY-MM-DD)';

  @override
  String get alumniFieldBusinessStarted => 'Business has started';

  @override
  String get alumniFieldBusinessActive => 'Business is active';

  @override
  String get alumniFieldJobsCreated => 'Jobs created';

  @override
  String get alumniFieldFundingBand => 'Funding band (INR)';

  @override
  String get alumniFieldChallenges => 'Challenges (optional)';

  @override
  String get alumniFieldSupportRequested => 'Support requested (optional)';

  @override
  String get alumniFieldMentorInterventions => 'Mentor support (optional)';

  @override
  String get alumniFieldOutcomes => 'Outcomes (optional)';

  @override
  String get alumniFieldObservedOn => 'Observed on (YYYY-MM-DD)';

  @override
  String get alumniFieldReason => 'Reason for this observation or revision';

  @override
  String get alumniFieldIdea => 'Idea';

  @override
  String get alumniFieldStarting => 'Starting';

  @override
  String get alumniFieldOperating => 'Operating';

  @override
  String get alumniFieldPaused => 'Paused';

  @override
  String get alumniFieldClosed => 'Closed';

  @override
  String get alumniFieldNone => 'None';

  @override
  String get alumniFieldUnder1l => 'Under ₹1 lakh';

  @override
  String get alumniField1lTo5l => '₹1–5 lakh';

  @override
  String get alumniField5lTo25l => '₹5–25 lakh';

  @override
  String get alumniFieldOver25l => 'Over ₹25 lakh';

  @override
  String get alumniFieldUnder10k => 'Under ₹10,000';

  @override
  String get alumniField10kTo50k => '₹10,000–50,000';

  @override
  String get alumniField50kTo2l => '₹50,000–2 lakh';

  @override
  String get alumniFieldOver2l => 'Over ₹2 lakh';

  @override
  String get alumniFieldUndisclosed => 'Prefer not to disclose';

  @override
  String get alumniFieldSeeking => 'Seeking funding';

  @override
  String get alumniFieldApplied => 'Applied';

  @override
  String get alumniFieldApproved => 'Approved';

  @override
  String get alumniFieldDisbursed => 'Disbursed';

  @override
  String get alumniFieldBaseline => 'Baseline observation';

  @override
  String get alumniFieldOutcome => 'Outcome observation';

  @override
  String get alumniFieldActive => 'Active';

  @override
  String get alumniFieldCompleted => 'Completed';

  @override
  String get alumniFieldPublished => 'Published';

  @override
  String get alumniFieldArchived => 'Archived';

  @override
  String get supportLabelSupport => 'Helpdesk';

  @override
  String get supportLabelMentoring => 'Mentoring';

  @override
  String get supportLabelPlans => 'Business plan';

  @override
  String get supportLabelResources => 'Resources and funding';

  @override
  String get supportLabelOpen => 'Open';

  @override
  String get supportLabelAssigned => 'Assigned';

  @override
  String get supportLabelInProgress => 'In progress';

  @override
  String get supportLabelWaitingForUser => 'Waiting for your reply';

  @override
  String get supportLabelResolved => 'Resolved';

  @override
  String get supportLabelClosed => 'Closed';

  @override
  String get supportLabelLow => 'Low';

  @override
  String get supportLabelNormal => 'Normal';

  @override
  String get supportLabelHigh => 'High';

  @override
  String get supportLabelUrgent => 'Urgent';

  @override
  String get supportLabelFunding => 'Funding';

  @override
  String get supportLabelRegistration => 'Registration';

  @override
  String get supportLabelTaxCompliance => 'Tax and compliance guidance';

  @override
  String get supportLabelMarketing => 'Marketing';

  @override
  String get supportLabelTechnology => 'Technology';

  @override
  String get supportLabelBusinessPlanning => 'Business planning';

  @override
  String get supportLabelBanking => 'Banking';

  @override
  String get supportLabelGeneral => 'General';

  @override
  String get supportLabelActive => 'Active';

  @override
  String get supportLabelCompleted => 'Completed';

  @override
  String get supportLabelCancelled => 'Cancelled';

  @override
  String get supportLabelScheduled => 'Scheduled';

  @override
  String get supportLabelPhone => 'Phone';

  @override
  String get supportLabelOnline => 'Online';

  @override
  String get supportLabelInPerson => 'In person';

  @override
  String get supportLabelHybrid => 'Hybrid';

  @override
  String get supportLabelEnded => 'Ended';

  @override
  String get supportLabelDraft => 'Draft';

  @override
  String get supportLabelSubmitted => 'Submitted';

  @override
  String get supportLabelChangesRequested => 'Changes requested';

  @override
  String get supportLabelApproved => 'Approved';

  @override
  String get supportLabelInterested => 'Interested';

  @override
  String get supportLabelEligibilityCheck => 'Eligibility check';

  @override
  String get supportLabelDocumentPreparation => 'Document preparation';

  @override
  String get supportLabelApplied => 'Applied';

  @override
  String get supportLabelUnderReview => 'Under review';

  @override
  String get supportLabelRejected => 'Rejected';

  @override
  String get supportLabelDisbursed => 'Disbursed';

  @override
  String get supportLabelScheme => 'Scheme';

  @override
  String get supportLabelOpportunity => 'Opportunity';

  @override
  String get supportLabelAll => 'All';

  @override
  String get supportLabelUpcoming => 'Upcoming';

  @override
  String get supportLabelCreated => 'Created';

  @override
  String get supportLabelMessage => 'Message';

  @override
  String get supportLabelReply => 'Reply';

  @override
  String get supportLabelStatus => 'Status';

  @override
  String get supportLabelReopened => 'Reopened';

  @override
  String get supportLabelPriority => 'Priority';

  @override
  String get supportLabelAssignment => 'Assignment';

  @override
  String get supportLabelStaged => 'Staged';

  @override
  String get supportLabelRemoved => 'Removed';

  @override
  String get supportLabelPosted => 'Posted';

  @override
  String get supportLabelPending => 'Pending';

  @override
  String get supportLabelPendingUpload => 'Awaiting upload';

  @override
  String get supportLabelQuarantined => 'Awaiting security check';

  @override
  String get supportLabelClean => 'Security check passed';

  @override
  String get supportLabelInfected => 'Security check failed';

  @override
  String get supportLabelDeleted => 'Deleted';

  @override
  String get supportLabelExpired => 'Expired';

  @override
  String get supportLabelQ => 'Search';

  @override
  String get supportLabelSector => 'Sector';

  @override
  String get supportLabelGeography => 'Geography';

  @override
  String get supportLabelTag => 'Tag';

  @override
  String get supportLabelExecutiveSummary => 'Executive summary';

  @override
  String get supportLabelProblem => 'Problem';

  @override
  String get supportLabelSolution => 'Solution';

  @override
  String get supportLabelProductService => 'Product service';

  @override
  String get supportLabelCustomerSegments => 'Customer segments';

  @override
  String get supportLabelMarket => 'Market';

  @override
  String get supportLabelCompetition => 'Competition';

  @override
  String get supportLabelValueProposition => 'Value proposition';

  @override
  String get supportLabelBusinessModel => 'Business model';

  @override
  String get supportLabelPricing => 'Pricing';

  @override
  String get supportLabelSalesMarketing => 'Sales marketing';

  @override
  String get supportLabelOperations => 'Operations';

  @override
  String get supportLabelTeam => 'Team';

  @override
  String get supportLabelInvestment => 'Investment';

  @override
  String get supportLabelRevenueAssumptions => 'Revenue assumptions';

  @override
  String get supportLabelExpenseAssumptions => 'Expense assumptions';

  @override
  String get supportLabelBreakEvenInputs => 'Break even inputs';

  @override
  String get supportLabelFundingRequirement => 'Funding requirement';

  @override
  String get supportLabelRisks => 'Risks';

  @override
  String get supportLabelMilestones => 'Milestones';

  @override
  String get attendanceScan => 'Scan attendance QR';

  @override
  String get attendanceScanExplanation =>
      'Scan the trainer\'s attendance QR code or enter the code below. Review it, then press Check in.';

  @override
  String get attendanceScanInvalid =>
      'This QR code is not an EDP attendance code. Enter the trainer\'s code instead.';

  @override
  String get attendanceScanUnavailable =>
      'Camera scanning is unavailable. You can enter or paste the trainer\'s code.';

  @override
  String get mobileUpdateAvailable => 'A newer app version is available.';

  @override
  String get mobileUpdateRequired =>
      'Please update this app to continue using the supported version.';

  @override
  String get mobileUpdateOpen => 'Open approved download';

  @override
  String get mobileUpdateDismiss => 'Later';

  @override
  String get mobileLinkedUnavailable =>
      'This linked record is unavailable for the current account. Refresh or return to the list.';

  @override
  String get mobileYes => 'Yes';

  @override
  String get mobileNo => 'No';

  @override
  String get mobileRead => 'Read';

  @override
  String get mobileUnread => 'Unread';

  @override
  String get mobileSubmitSelfReport => 'Submit self-report';

  @override
  String get mobileSaveRevision => 'Save superseding revision';

  @override
  String get fileProtectionRequired =>
      'Private files require encrypted device storage and a secure screen lock. Unlock your device and check its security settings, then try again.';

  @override
  String get fileRetryProtection => 'Retry protected storage';
}
