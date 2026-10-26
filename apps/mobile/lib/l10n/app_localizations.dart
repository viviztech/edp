import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ta.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ta'),
  ];

  /// No description provided for @filePolicyCount.
  ///
  /// In en, this message translates to:
  /// **'This policy allows up to {count} documents across requirements.'**
  String filePolicyCount(int count);

  /// No description provided for @title.
  ///
  /// In en, this message translates to:
  /// **'Entrepreneurship Development Program'**
  String get title;

  /// No description provided for @welcome.
  ///
  /// In en, this message translates to:
  /// **'Build your skills. Shape your business.'**
  String get welcome;

  /// No description provided for @availability.
  ///
  /// In en, this message translates to:
  /// **'Program details and applications will be available here soon.'**
  String get availability;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'தமிழில் படிக்க'**
  String get language;

  /// No description provided for @authTitle.
  ///
  /// In en, this message translates to:
  /// **'Your account'**
  String get authTitle;

  /// No description provided for @authEmail.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get authEmail;

  /// No description provided for @authPassword.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get authPassword;

  /// No description provided for @authName.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get authName;

  /// No description provided for @authToken.
  ///
  /// In en, this message translates to:
  /// **'Verification or reset code'**
  String get authToken;

  /// No description provided for @authLogin.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get authLogin;

  /// No description provided for @authRegister.
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get authRegister;

  /// No description provided for @authVerify.
  ///
  /// In en, this message translates to:
  /// **'Verify email'**
  String get authVerify;

  /// No description provided for @authRequestVerification.
  ///
  /// In en, this message translates to:
  /// **'Send verification'**
  String get authRequestVerification;

  /// No description provided for @authRequestReset.
  ///
  /// In en, this message translates to:
  /// **'Forgot password'**
  String get authRequestReset;

  /// No description provided for @authReset.
  ///
  /// In en, this message translates to:
  /// **'Reset password'**
  String get authReset;

  /// No description provided for @authLogout.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get authLogout;

  /// No description provided for @authLogoutAll.
  ///
  /// In en, this message translates to:
  /// **'Sign out all devices'**
  String get authLogoutAll;

  /// No description provided for @authAccepted.
  ///
  /// In en, this message translates to:
  /// **'If the account is eligible, a message has been queued. Follow the instructions in that message.'**
  String get authAccepted;

  /// No description provided for @authCompleted.
  ///
  /// In en, this message translates to:
  /// **'Done. You can now sign in.'**
  String get authCompleted;

  /// No description provided for @authLoading.
  ///
  /// In en, this message translates to:
  /// **'Please wait…'**
  String get authLoading;

  /// No description provided for @authError.
  ///
  /// In en, this message translates to:
  /// **'The request could not be completed. Check your details and try again.'**
  String get authError;

  /// No description provided for @authUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Account messages are not available yet. Please try again later.'**
  String get authUnavailable;

  /// No description provided for @authInvalid.
  ///
  /// In en, this message translates to:
  /// **'Email or password is incorrect, or the account is not verified.'**
  String get authInvalid;

  /// No description provided for @authLimited.
  ///
  /// In en, this message translates to:
  /// **'Too many attempts. Please wait 15 minutes.'**
  String get authLimited;

  /// No description provided for @authSessionExpired.
  ///
  /// In en, this message translates to:
  /// **'Your session expired. Please sign in again.'**
  String get authSessionExpired;

  /// No description provided for @authSessions.
  ///
  /// In en, this message translates to:
  /// **'Active devices'**
  String get authSessions;

  /// No description provided for @authNoSessions.
  ///
  /// In en, this message translates to:
  /// **'No active devices.'**
  String get authNoSessions;

  /// No description provided for @authRevoke.
  ///
  /// In en, this message translates to:
  /// **'Sign out device'**
  String get authRevoke;

  /// No description provided for @authCurrent.
  ///
  /// In en, this message translates to:
  /// **'This device'**
  String get authCurrent;

  /// No description provided for @authStaff.
  ///
  /// In en, this message translates to:
  /// **'Staff workspace'**
  String get authStaff;

  /// No description provided for @authDenied.
  ///
  /// In en, this message translates to:
  /// **'You do not have access to this workspace.'**
  String get authDenied;

  /// No description provided for @authOrganizations.
  ///
  /// In en, this message translates to:
  /// **'Your organizations'**
  String get authOrganizations;

  /// No description provided for @authAudit.
  ///
  /// In en, this message translates to:
  /// **'Audit history'**
  String get authAudit;

  /// No description provided for @authNoAudit.
  ///
  /// In en, this message translates to:
  /// **'No audit events to show.'**
  String get authNoAudit;

  /// No description provided for @authPasswordHelp.
  ///
  /// In en, this message translates to:
  /// **'Use 12–128 characters.'**
  String get authPasswordHelp;

  /// No description provided for @authBack.
  ///
  /// In en, this message translates to:
  /// **'Back to account'**
  String get authBack;

  /// No description provided for @authNoOrganizations.
  ///
  /// In en, this message translates to:
  /// **'No staff access is assigned to your account.'**
  String get authNoOrganizations;

  /// No description provided for @authRefresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh'**
  String get authRefresh;

  /// No description provided for @authNext.
  ///
  /// In en, this message translates to:
  /// **'Next'**
  String get authNext;

  /// No description provided for @cmsPages.
  ///
  /// In en, this message translates to:
  /// **'Pages'**
  String get cmsPages;

  /// No description provided for @cmsEmpty.
  ///
  /// In en, this message translates to:
  /// **'No pages yet.'**
  String get cmsEmpty;

  /// No description provided for @cmsError.
  ///
  /// In en, this message translates to:
  /// **'Unable to complete the request. Retry or sign in again.'**
  String get cmsError;

  /// No description provided for @cmsLoading.
  ///
  /// In en, this message translates to:
  /// **'Loading'**
  String get cmsLoading;

  /// No description provided for @cmsMore.
  ///
  /// In en, this message translates to:
  /// **'Load more'**
  String get cmsMore;

  /// No description provided for @cmsBack.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get cmsBack;

  /// No description provided for @cmsUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This page is unavailable.'**
  String get cmsUnavailable;

  /// No description provided for @cmsRetry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get cmsRetry;

  /// No description provided for @mobileApplications.
  ///
  /// In en, this message translates to:
  /// **'My applications'**
  String get mobileApplications;

  /// No description provided for @mobileNoApplications.
  ///
  /// In en, this message translates to:
  /// **'You have no saved applications yet.'**
  String get mobileNoApplications;

  /// No description provided for @mobileNews.
  ///
  /// In en, this message translates to:
  /// **'News'**
  String get mobileNews;

  /// No description provided for @mobileEvents.
  ///
  /// In en, this message translates to:
  /// **'Events'**
  String get mobileEvents;

  /// No description provided for @mobileFaq.
  ///
  /// In en, this message translates to:
  /// **'Frequently asked questions'**
  String get mobileFaq;

  /// No description provided for @mobileStories.
  ///
  /// In en, this message translates to:
  /// **'Success stories'**
  String get mobileStories;

  /// No description provided for @mobileSessionUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Your account could not be restored. Retry or sign in.'**
  String get mobileSessionUnavailable;

  /// No description provided for @mobileDraft.
  ///
  /// In en, this message translates to:
  /// **'Draft'**
  String get mobileDraft;

  /// No description provided for @mobileSubmitted.
  ///
  /// In en, this message translates to:
  /// **'Submitted'**
  String get mobileSubmitted;

  /// No description provided for @mobileUnderReview.
  ///
  /// In en, this message translates to:
  /// **'Under review'**
  String get mobileUnderReview;

  /// No description provided for @mobileShortlisted.
  ///
  /// In en, this message translates to:
  /// **'Shortlisted'**
  String get mobileShortlisted;

  /// No description provided for @mobileInterview.
  ///
  /// In en, this message translates to:
  /// **'Interview scheduled'**
  String get mobileInterview;

  /// No description provided for @mobileSelected.
  ///
  /// In en, this message translates to:
  /// **'Selected'**
  String get mobileSelected;

  /// No description provided for @mobileWaitlisted.
  ///
  /// In en, this message translates to:
  /// **'Waitlisted'**
  String get mobileWaitlisted;

  /// No description provided for @mobileRejected.
  ///
  /// In en, this message translates to:
  /// **'Not selected'**
  String get mobileRejected;

  /// No description provided for @mobileEnrolled.
  ///
  /// In en, this message translates to:
  /// **'Enrolled'**
  String get mobileEnrolled;

  /// No description provided for @mobileSchedule.
  ///
  /// In en, this message translates to:
  /// **'My schedule'**
  String get mobileSchedule;

  /// No description provided for @mobileLearning.
  ///
  /// In en, this message translates to:
  /// **'My learning'**
  String get mobileLearning;

  /// No description provided for @mobileSupport.
  ///
  /// In en, this message translates to:
  /// **'Support'**
  String get mobileSupport;

  /// No description provided for @mobileMentoring.
  ///
  /// In en, this message translates to:
  /// **'Mentoring'**
  String get mobileMentoring;

  /// No description provided for @mobilePlans.
  ///
  /// In en, this message translates to:
  /// **'Business plan'**
  String get mobilePlans;

  /// No description provided for @mobileResources.
  ///
  /// In en, this message translates to:
  /// **'Resources and funding'**
  String get mobileResources;

  /// No description provided for @mobileUpdates.
  ///
  /// In en, this message translates to:
  /// **'Updates'**
  String get mobileUpdates;

  /// No description provided for @mobileBusiness.
  ///
  /// In en, this message translates to:
  /// **'My business'**
  String get mobileBusiness;

  /// No description provided for @mobileImpact.
  ///
  /// In en, this message translates to:
  /// **'My outcomes'**
  String get mobileImpact;

  /// No description provided for @mobileUnsaved.
  ///
  /// In en, this message translates to:
  /// **'Leave this page? Your unsaved changes will be lost.'**
  String get mobileUnsaved;

  /// No description provided for @mobileUncertainLeave.
  ///
  /// In en, this message translates to:
  /// **'The last request still needs review. Leave this page? Reopen this exact application to check the saved result before trying again.'**
  String get mobileUncertainLeave;

  /// No description provided for @mobileStay.
  ///
  /// In en, this message translates to:
  /// **'Stay'**
  String get mobileStay;

  /// No description provided for @mobileLeave.
  ///
  /// In en, this message translates to:
  /// **'Leave'**
  String get mobileLeave;

  /// No description provided for @mobileSaved.
  ///
  /// In en, this message translates to:
  /// **'Saved'**
  String get mobileSaved;

  /// No description provided for @mobileSave.
  ///
  /// In en, this message translates to:
  /// **'Save draft'**
  String get mobileSave;

  /// No description provided for @mobileSubmit.
  ///
  /// In en, this message translates to:
  /// **'Submit application'**
  String get mobileSubmit;

  /// No description provided for @mobileConfirmSubmit.
  ///
  /// In en, this message translates to:
  /// **'Submit this application? The submitted answers and evidence will be frozen.'**
  String get mobileConfirmSubmit;

  /// No description provided for @mobileCommandUncertain.
  ///
  /// In en, this message translates to:
  /// **'The result is uncertain. Refresh the exact record before deciding whether to try again. Your input is preserved.'**
  String get mobileCommandUncertain;

  /// No description provided for @mobileConflict.
  ///
  /// In en, this message translates to:
  /// **'The record changed elsewhere. Review the current saved version before saving your edits.'**
  String get mobileConflict;

  /// No description provided for @mobileReadOnly.
  ///
  /// In en, this message translates to:
  /// **'This application is read only.'**
  String get mobileReadOnly;

  /// No description provided for @mobileIntakes.
  ///
  /// In en, this message translates to:
  /// **'Open application intakes'**
  String get mobileIntakes;

  /// No description provided for @mobileNoIntakes.
  ///
  /// In en, this message translates to:
  /// **'There are no open intakes for this organization.'**
  String get mobileNoIntakes;

  /// No description provided for @mobileStartApplication.
  ///
  /// In en, this message translates to:
  /// **'Start or resume application'**
  String get mobileStartApplication;

  /// No description provided for @mobileSubmitSuccess.
  ///
  /// In en, this message translates to:
  /// **'Application submitted'**
  String get mobileSubmitSuccess;

  /// No description provided for @mobileRequired.
  ///
  /// In en, this message translates to:
  /// **'Required'**
  String get mobileRequired;

  /// No description provided for @mobileRefreshRecord.
  ///
  /// In en, this message translates to:
  /// **'Refresh saved record'**
  String get mobileRefreshRecord;

  /// No description provided for @mobileUseSaved.
  ///
  /// In en, this message translates to:
  /// **'Use saved answers'**
  String get mobileUseSaved;

  /// No description provided for @mobileKeepEdits.
  ///
  /// In en, this message translates to:
  /// **'Keep my edits'**
  String get mobileKeepEdits;

  /// No description provided for @mobileDocuments.
  ///
  /// In en, this message translates to:
  /// **'Supporting documents'**
  String get mobileDocuments;

  /// No description provided for @mobileProgramIntake.
  ///
  /// In en, this message translates to:
  /// **'Program applications'**
  String get mobileProgramIntake;

  /// No description provided for @fileCollectionDisabled.
  ///
  /// In en, this message translates to:
  /// **'Document collection is unavailable. Existing document status remains visible.'**
  String get fileCollectionDisabled;

  /// No description provided for @fileNativeRequired.
  ///
  /// In en, this message translates to:
  /// **'Document selection and private downloads require the Android or iOS app.'**
  String get fileNativeRequired;

  /// No description provided for @fileChoose.
  ///
  /// In en, this message translates to:
  /// **'Choose document'**
  String get fileChoose;

  /// No description provided for @fileReplace.
  ///
  /// In en, this message translates to:
  /// **'Replace document'**
  String get fileReplace;

  /// No description provided for @fileRemove.
  ///
  /// In en, this message translates to:
  /// **'Remove document'**
  String get fileRemove;

  /// No description provided for @fileConfirmRemove.
  ///
  /// In en, this message translates to:
  /// **'Remove this document from the draft?'**
  String get fileConfirmRemove;

  /// No description provided for @fileUpload.
  ///
  /// In en, this message translates to:
  /// **'Upload selected bytes'**
  String get fileUpload;

  /// No description provided for @fileRecoverIntent.
  ///
  /// In en, this message translates to:
  /// **'Recover this upload registration'**
  String get fileRecoverIntent;

  /// No description provided for @fileRefresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh document status'**
  String get fileRefresh;

  /// No description provided for @fileReadBeforeRetry.
  ///
  /// In en, this message translates to:
  /// **'Check the saved document status before continuing. Bytes will not be resent automatically.'**
  String get fileReadBeforeRetry;

  /// No description provided for @fileReselect.
  ///
  /// In en, this message translates to:
  /// **'Reselect identical document'**
  String get fileReselect;

  /// No description provided for @fileDiscard.
  ///
  /// In en, this message translates to:
  /// **'Discard selected copy'**
  String get fileDiscard;

  /// No description provided for @fileSelected.
  ///
  /// In en, this message translates to:
  /// **'Selected private copy'**
  String get fileSelected;

  /// No description provided for @fileDownload.
  ///
  /// In en, this message translates to:
  /// **'Verify private download'**
  String get fileDownload;

  /// No description provided for @fileDownloadReceipt.
  ///
  /// In en, this message translates to:
  /// **'Private download verified'**
  String get fileDownloadReceipt;

  /// No description provided for @fileCloseReceipt.
  ///
  /// In en, this message translates to:
  /// **'Close and delete private copy'**
  String get fileCloseReceipt;

  /// No description provided for @filePending.
  ///
  /// In en, this message translates to:
  /// **'Awaiting upload'**
  String get filePending;

  /// No description provided for @fileUploading.
  ///
  /// In en, this message translates to:
  /// **'Upload in progress'**
  String get fileUploading;

  /// No description provided for @fileQuarantined.
  ///
  /// In en, this message translates to:
  /// **'Awaiting security scan'**
  String get fileQuarantined;

  /// No description provided for @fileScanning.
  ///
  /// In en, this message translates to:
  /// **'Security scan in progress'**
  String get fileScanning;

  /// No description provided for @fileClean.
  ///
  /// In en, this message translates to:
  /// **'Scan complete'**
  String get fileClean;

  /// No description provided for @fileInfected.
  ///
  /// In en, this message translates to:
  /// **'Unsafe document'**
  String get fileInfected;

  /// No description provided for @fileRejected.
  ///
  /// In en, this message translates to:
  /// **'Document rejected'**
  String get fileRejected;

  /// No description provided for @fileDeleted.
  ///
  /// In en, this message translates to:
  /// **'Document deleted'**
  String get fileDeleted;

  /// No description provided for @fileUnusable.
  ///
  /// In en, this message translates to:
  /// **'This document is not currently usable for submission.'**
  String get fileUnusable;

  /// No description provided for @fileFrozenEvidence.
  ///
  /// In en, this message translates to:
  /// **'Submitted document proof'**
  String get fileFrozenEvidence;

  /// No description provided for @fileInvalid.
  ///
  /// In en, this message translates to:
  /// **'The selected bytes are empty, changed, invalid or do not match a supported type. Choose a valid document.'**
  String get fileInvalid;

  /// No description provided for @fileTooLarge.
  ///
  /// In en, this message translates to:
  /// **'The document exceeds the displayed byte limit.'**
  String get fileTooLarge;

  /// No description provided for @fileUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Private file handling is unavailable. Refresh the document status before trying again.'**
  String get fileUnavailable;

  /// No description provided for @fileLimits.
  ///
  /// In en, this message translates to:
  /// **'{minimum}–{maximum} documents; up to {bytes} bytes each'**
  String fileLimits(int minimum, int maximum, int bytes);

  /// No description provided for @fileRetention.
  ///
  /// In en, this message translates to:
  /// **'Retention: {days} days; rejected documents: {rejectedDays} days'**
  String fileRetention(int days, int rejectedDays);

  /// No description provided for @fileProof.
  ///
  /// In en, this message translates to:
  /// **'{mediaType} · {bytes} bytes · version {version}'**
  String fileProof(String mediaType, int bytes, int version);

  /// No description provided for @mobileHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get mobileHome;

  /// No description provided for @mobileDateFormat.
  ///
  /// In en, this message translates to:
  /// **'Use YYYY-MM-DD'**
  String get mobileDateFormat;

  /// No description provided for @mobileReviewSaved.
  ///
  /// In en, this message translates to:
  /// **'Review the saved answers before choosing how to continue.'**
  String get mobileReviewSaved;

  /// No description provided for @mobileChooseOrganization.
  ///
  /// In en, this message translates to:
  /// **'Choose a program organization or open a saved application below.'**
  String get mobileChooseOrganization;

  /// No description provided for @mobileDocumentsReady.
  ///
  /// In en, this message translates to:
  /// **'Required documents are ready.'**
  String get mobileDocumentsReady;

  /// No description provided for @mobileDocumentsPending.
  ///
  /// In en, this message translates to:
  /// **'Required documents must be uploaded and usable before submission.'**
  String get mobileDocumentsPending;

  /// No description provided for @mobileStatusHistory.
  ///
  /// In en, this message translates to:
  /// **'Status history'**
  String get mobileStatusHistory;

  /// No description provided for @mobileApplicationUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This application is unavailable or you no longer have access.'**
  String get mobileApplicationUnavailable;

  /// No description provided for @mobileConnectionInterrupted.
  ///
  /// In en, this message translates to:
  /// **'The connection was interrupted. Your current input is preserved. Retry when connected.'**
  String get mobileConnectionInterrupted;

  /// No description provided for @mobileCheckAnswers.
  ///
  /// In en, this message translates to:
  /// **'Check the answer types, required fields and acknowledgements, then try again.'**
  String get mobileCheckAnswers;

  /// No description provided for @mobileWaitAndRetry.
  ///
  /// In en, this message translates to:
  /// **'Please wait before trying again.'**
  String get mobileWaitAndRetry;

  /// No description provided for @authLogoutUnconfirmed.
  ///
  /// In en, this message translates to:
  /// **'Signed out on this device. Server revocation could not be confirmed; try signing out all devices when connected.'**
  String get authLogoutUnconfirmed;

  /// No description provided for @mobileSavedVersion.
  ///
  /// In en, this message translates to:
  /// **'Saved version {version}'**
  String mobileSavedVersion(int version);

  /// No description provided for @mobileCompletion.
  ///
  /// In en, this message translates to:
  /// **'{percent}% complete'**
  String mobileCompletion(int percent);

  /// No description provided for @learnTitle.
  ///
  /// In en, this message translates to:
  /// **'My training'**
  String get learnTitle;

  /// No description provided for @learnLearning.
  ///
  /// In en, this message translates to:
  /// **'Learning'**
  String get learnLearning;

  /// No description provided for @learnSchedule.
  ///
  /// In en, this message translates to:
  /// **'Schedule'**
  String get learnSchedule;

  /// No description provided for @learnAttendance.
  ///
  /// In en, this message translates to:
  /// **'Attendance'**
  String get learnAttendance;

  /// No description provided for @learnRefresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh'**
  String get learnRefresh;

  /// No description provided for @learnLoading.
  ///
  /// In en, this message translates to:
  /// **'Loading…'**
  String get learnLoading;

  /// No description provided for @learnEmpty.
  ///
  /// In en, this message translates to:
  /// **'No records are available.'**
  String get learnEmpty;

  /// No description provided for @learnError.
  ///
  /// In en, this message translates to:
  /// **'This information is unavailable. Try again.'**
  String get learnError;

  /// No description provided for @learnStart.
  ///
  /// In en, this message translates to:
  /// **'Start course'**
  String get learnStart;

  /// No description provided for @learnComplete.
  ///
  /// In en, this message translates to:
  /// **'Mark lesson complete'**
  String get learnComplete;

  /// No description provided for @learnCompleted.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get learnCompleted;

  /// No description provided for @learnLocked.
  ///
  /// In en, this message translates to:
  /// **'Complete the prerequisites to open this lesson.'**
  String get learnLocked;

  /// No description provided for @learnProgress.
  ///
  /// In en, this message translates to:
  /// **'Course progress'**
  String get learnProgress;

  /// No description provided for @learnQuiz.
  ///
  /// In en, this message translates to:
  /// **'Quiz'**
  String get learnQuiz;

  /// No description provided for @learnAttempts.
  ///
  /// In en, this message translates to:
  /// **'Attempts remaining'**
  String get learnAttempts;

  /// No description provided for @learnSubmitQuiz.
  ///
  /// In en, this message translates to:
  /// **'Submit answers'**
  String get learnSubmitQuiz;

  /// No description provided for @learnScore.
  ///
  /// In en, this message translates to:
  /// **'Best score'**
  String get learnScore;

  /// No description provided for @learnPassed.
  ///
  /// In en, this message translates to:
  /// **'Passed'**
  String get learnPassed;

  /// No description provided for @learnFailed.
  ///
  /// In en, this message translates to:
  /// **'Not passed'**
  String get learnFailed;

  /// No description provided for @learnAssignment.
  ///
  /// In en, this message translates to:
  /// **'Assignment'**
  String get learnAssignment;

  /// No description provided for @learnResponse.
  ///
  /// In en, this message translates to:
  /// **'Your response'**
  String get learnResponse;

  /// No description provided for @learnSubmitAssignment.
  ///
  /// In en, this message translates to:
  /// **'Submit assignment'**
  String get learnSubmitAssignment;

  /// No description provided for @learnRemaining.
  ///
  /// In en, this message translates to:
  /// **'Submissions remaining'**
  String get learnRemaining;

  /// No description provided for @learnPendingReview.
  ///
  /// In en, this message translates to:
  /// **'Awaiting trainer review'**
  String get learnPendingReview;

  /// No description provided for @learnFeedback.
  ///
  /// In en, this message translates to:
  /// **'Trainer feedback'**
  String get learnFeedback;

  /// No description provided for @learnFiles.
  ///
  /// In en, this message translates to:
  /// **'Assignment files'**
  String get learnFiles;

  /// No description provided for @learnChoose.
  ///
  /// In en, this message translates to:
  /// **'Choose a file'**
  String get learnChoose;

  /// No description provided for @learnUpload.
  ///
  /// In en, this message translates to:
  /// **'Upload selected bytes'**
  String get learnUpload;

  /// No description provided for @learnRecover.
  ///
  /// In en, this message translates to:
  /// **'Recover the same file request'**
  String get learnRecover;

  /// No description provided for @learnReadback.
  ///
  /// In en, this message translates to:
  /// **'Read current saved state'**
  String get learnReadback;

  /// No description provided for @learnContinue.
  ///
  /// In en, this message translates to:
  /// **'I reviewed the saved state'**
  String get learnContinue;

  /// No description provided for @learnUncertain.
  ///
  /// In en, this message translates to:
  /// **'The result is uncertain. Read the saved state before another action.'**
  String get learnUncertain;

  /// No description provided for @learnConflict.
  ///
  /// In en, this message translates to:
  /// **'The saved version changed. Refresh and review it.'**
  String get learnConflict;

  /// No description provided for @learnSaved.
  ///
  /// In en, this message translates to:
  /// **'Saved. Current server state is shown.'**
  String get learnSaved;

  /// No description provided for @learnDiscard.
  ///
  /// In en, this message translates to:
  /// **'Discard local inputs'**
  String get learnDiscard;

  /// No description provided for @learnClose.
  ///
  /// In en, this message translates to:
  /// **'Close and delete private copy'**
  String get learnClose;

  /// No description provided for @learnDownload.
  ///
  /// In en, this message translates to:
  /// **'Read private copy'**
  String get learnDownload;

  /// No description provided for @learnReceipt.
  ///
  /// In en, this message translates to:
  /// **'Private download receipt'**
  String get learnReceipt;

  /// No description provided for @learnPrivateReceipt.
  ///
  /// In en, this message translates to:
  /// **'The private copy is deleted when closed, backgrounded or left.'**
  String get learnPrivateReceipt;

  /// No description provided for @learnRemove.
  ///
  /// In en, this message translates to:
  /// **'Remove file'**
  String get learnRemove;

  /// No description provided for @learnConfirmRemove.
  ///
  /// In en, this message translates to:
  /// **'Remove this staged file?'**
  String get learnConfirmRemove;

  /// No description provided for @learnCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get learnCancel;

  /// No description provided for @learnConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get learnConfirm;

  /// No description provided for @learnReselect.
  ///
  /// In en, this message translates to:
  /// **'Select the exact registered bytes again'**
  String get learnReselect;

  /// No description provided for @learnFrozen.
  ///
  /// In en, this message translates to:
  /// **'Frozen submission evidence'**
  String get learnFrozen;

  /// No description provided for @learnDisabled.
  ///
  /// In en, this message translates to:
  /// **'File collection is disabled.'**
  String get learnDisabled;

  /// No description provided for @learnNativeRequired.
  ///
  /// In en, this message translates to:
  /// **'Private file selection requires the Android or iOS app.'**
  String get learnNativeRequired;

  /// No description provided for @learnLimits.
  ///
  /// In en, this message translates to:
  /// **'File limits'**
  String get learnLimits;

  /// No description provided for @learnBytes.
  ///
  /// In en, this message translates to:
  /// **'bytes'**
  String get learnBytes;

  /// No description provided for @learnCount.
  ///
  /// In en, this message translates to:
  /// **'files'**
  String get learnCount;

  /// No description provided for @learnMinimum.
  ///
  /// In en, this message translates to:
  /// **'minimum'**
  String get learnMinimum;

  /// No description provided for @learnMaximum.
  ///
  /// In en, this message translates to:
  /// **'maximum'**
  String get learnMaximum;

  /// No description provided for @learnPending.
  ///
  /// In en, this message translates to:
  /// **'Not uploaded'**
  String get learnPending;

  /// No description provided for @learnUploading.
  ///
  /// In en, this message translates to:
  /// **'Uploading'**
  String get learnUploading;

  /// No description provided for @learnQuarantined.
  ///
  /// In en, this message translates to:
  /// **'Awaiting security scan'**
  String get learnQuarantined;

  /// No description provided for @learnScanning.
  ///
  /// In en, this message translates to:
  /// **'Security scan in progress'**
  String get learnScanning;

  /// No description provided for @learnClean.
  ///
  /// In en, this message translates to:
  /// **'Scan complete'**
  String get learnClean;

  /// No description provided for @learnInfected.
  ///
  /// In en, this message translates to:
  /// **'Unsafe file'**
  String get learnInfected;

  /// No description provided for @learnRejected.
  ///
  /// In en, this message translates to:
  /// **'File rejected'**
  String get learnRejected;

  /// No description provided for @learnDeleted.
  ///
  /// In en, this message translates to:
  /// **'Deleted'**
  String get learnDeleted;

  /// No description provided for @learnUnusable.
  ///
  /// In en, this message translates to:
  /// **'This file is not usable for submission.'**
  String get learnUnusable;

  /// No description provided for @learnFilePending.
  ///
  /// In en, this message translates to:
  /// **'Finish or discard the selected file before another action.'**
  String get learnFilePending;

  /// No description provided for @learnSelected.
  ///
  /// In en, this message translates to:
  /// **'Selected byte proof'**
  String get learnSelected;

  /// No description provided for @learnDiscardSelection.
  ///
  /// In en, this message translates to:
  /// **'Discard selection'**
  String get learnDiscardSelection;

  /// No description provided for @learnCertificate.
  ///
  /// In en, this message translates to:
  /// **'Certificate'**
  String get learnCertificate;

  /// No description provided for @learnEligible.
  ///
  /// In en, this message translates to:
  /// **'Course requirements met; certificate issuance is handled by the program.'**
  String get learnEligible;

  /// No description provided for @learnIneligible.
  ///
  /// In en, this message translates to:
  /// **'Certificate requirements are incomplete.'**
  String get learnIneligible;

  /// No description provided for @learnVerify.
  ///
  /// In en, this message translates to:
  /// **'Verify certificate and show QR'**
  String get learnVerify;

  /// No description provided for @learnValid.
  ///
  /// In en, this message translates to:
  /// **'Valid'**
  String get learnValid;

  /// No description provided for @learnRevoked.
  ///
  /// In en, this message translates to:
  /// **'Revoked'**
  String get learnRevoked;

  /// No description provided for @learnIssuer.
  ///
  /// In en, this message translates to:
  /// **'Issuer'**
  String get learnIssuer;

  /// No description provided for @learnIssued.
  ///
  /// In en, this message translates to:
  /// **'Issued'**
  String get learnIssued;

  /// No description provided for @learnQr.
  ///
  /// In en, this message translates to:
  /// **'Public certificate verification QR'**
  String get learnQr;

  /// No description provided for @learnMaterial.
  ///
  /// In en, this message translates to:
  /// **'Read lesson material'**
  String get learnMaterial;

  /// No description provided for @learnMaterialLimit.
  ///
  /// In en, this message translates to:
  /// **'Private material downloads are limited to 2 MiB. Supported document/image/text formats only.'**
  String get learnMaterialLimit;

  /// No description provided for @learnToken.
  ///
  /// In en, this message translates to:
  /// **'Attendance code or edp-attendance payload'**
  String get learnToken;

  /// No description provided for @learnCheckIn.
  ///
  /// In en, this message translates to:
  /// **'Check in'**
  String get learnCheckIn;

  /// No description provided for @learnCamera.
  ///
  /// In en, this message translates to:
  /// **'Enter or paste the trainer’s code. Camera scanning is not available in this build.'**
  String get learnCamera;

  /// No description provided for @learnAttended.
  ///
  /// In en, this message translates to:
  /// **'Attended'**
  String get learnAttended;

  /// No description provided for @learnRequired.
  ///
  /// In en, this message translates to:
  /// **'Required'**
  String get learnRequired;

  /// No description provided for @learnThreshold.
  ///
  /// In en, this message translates to:
  /// **'Required percentage'**
  String get learnThreshold;

  /// No description provided for @learnLowAttendance.
  ///
  /// In en, this message translates to:
  /// **'Attendance is below the required percentage.'**
  String get learnLowAttendance;

  /// No description provided for @learnUnmarked.
  ///
  /// In en, this message translates to:
  /// **'Not marked'**
  String get learnUnmarked;

  /// No description provided for @learnPresent.
  ///
  /// In en, this message translates to:
  /// **'Present'**
  String get learnPresent;

  /// No description provided for @learnAbsent.
  ///
  /// In en, this message translates to:
  /// **'Absent'**
  String get learnAbsent;

  /// No description provided for @learnLate.
  ///
  /// In en, this message translates to:
  /// **'Late'**
  String get learnLate;

  /// No description provided for @learnExcused.
  ///
  /// In en, this message translates to:
  /// **'Excused'**
  String get learnExcused;

  /// No description provided for @learnScheduled.
  ///
  /// In en, this message translates to:
  /// **'Scheduled'**
  String get learnScheduled;

  /// No description provided for @learnCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get learnCancelled;

  /// No description provided for @learnInPerson.
  ///
  /// In en, this message translates to:
  /// **'In person'**
  String get learnInPerson;

  /// No description provided for @learnOnline.
  ///
  /// In en, this message translates to:
  /// **'Online'**
  String get learnOnline;

  /// No description provided for @learnHybrid.
  ///
  /// In en, this message translates to:
  /// **'Hybrid'**
  String get learnHybrid;

  /// No description provided for @learnSessionExpired.
  ///
  /// In en, this message translates to:
  /// **'Your session expired. Sign in again.'**
  String get learnSessionExpired;

  /// No description provided for @learnAccessDenied.
  ///
  /// In en, this message translates to:
  /// **'Access is unavailable for this account.'**
  String get learnAccessDenied;

  /// No description provided for @learnInvalid.
  ///
  /// In en, this message translates to:
  /// **'Check the input and selected answers.'**
  String get learnInvalid;

  /// No description provided for @learnWait.
  ///
  /// In en, this message translates to:
  /// **'Wait before trying again.'**
  String get learnWait;

  /// No description provided for @learnTooLarge.
  ///
  /// In en, this message translates to:
  /// **'This file exceeds the supported size.'**
  String get learnTooLarge;

  /// No description provided for @learnLeave.
  ///
  /// In en, this message translates to:
  /// **'Leave and discard unsaved work?'**
  String get learnLeave;

  /// No description provided for @learnStay.
  ///
  /// In en, this message translates to:
  /// **'Stay'**
  String get learnStay;

  /// No description provided for @learnLeaveAction.
  ///
  /// In en, this message translates to:
  /// **'Leave'**
  String get learnLeaveAction;

  /// No description provided for @learnApplication.
  ///
  /// In en, this message translates to:
  /// **'Application'**
  String get learnApplication;

  /// No description provided for @learnSelection.
  ///
  /// In en, this message translates to:
  /// **'Selection'**
  String get learnSelection;

  /// No description provided for @learnEnrollment.
  ///
  /// In en, this message translates to:
  /// **'Enrollment'**
  String get learnEnrollment;

  /// No description provided for @learnSession.
  ///
  /// In en, this message translates to:
  /// **'Session'**
  String get learnSession;

  /// No description provided for @learnCourseCompletionIncomplete.
  ///
  /// In en, this message translates to:
  /// **'Complete the required lessons.'**
  String get learnCourseCompletionIncomplete;

  /// No description provided for @learnQuizRequirementsIncomplete.
  ///
  /// In en, this message translates to:
  /// **'Pass the required quizzes.'**
  String get learnQuizRequirementsIncomplete;

  /// No description provided for @learnAssignmentRequirementsIncomplete.
  ///
  /// In en, this message translates to:
  /// **'Pass the required assignments.'**
  String get learnAssignmentRequirementsIncomplete;

  /// No description provided for @learnRecord.
  ///
  /// In en, this message translates to:
  /// **'Record'**
  String get learnRecord;

  /// No description provided for @domainDiscardThisTicketSUnsentText23075b.
  ///
  /// In en, this message translates to:
  /// **'Discard this ticket’s unsent text and selected private copies?'**
  String get domainDiscardThisTicketSUnsentText23075b;

  /// No description provided for @domainClose7d9eb7.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get domainClose7d9eb7;

  /// No description provided for @domainMySupportTicketsbca759.
  ///
  /// In en, this message translates to:
  /// **'My support tickets'**
  String get domainMySupportTicketsbca759;

  /// No description provided for @domainTicketStatusFiltere21337.
  ///
  /// In en, this message translates to:
  /// **'Ticket status filter'**
  String get domainTicketStatusFiltere21337;

  /// No description provided for @domainAllStatuses8ee573.
  ///
  /// In en, this message translates to:
  /// **'All statuses'**
  String get domainAllStatuses8ee573;

  /// No description provided for @domainRefreshTickets1c30a6.
  ///
  /// In en, this message translates to:
  /// **'Refresh tickets'**
  String get domainRefreshTickets1c30a6;

  /// No description provided for @domainNoSupportTickets72f5d9.
  ///
  /// In en, this message translates to:
  /// **'No support tickets.'**
  String get domainNoSupportTickets72f5d9;

  /// No description provided for @domainMoreTickets0e480f.
  ///
  /// In en, this message translates to:
  /// **'More tickets'**
  String get domainMoreTickets0e480f;

  /// No description provided for @domainCreateASupportTicket9709e0.
  ///
  /// In en, this message translates to:
  /// **'Create a support ticket'**
  String get domainCreateASupportTicket9709e0;

  /// No description provided for @domainCategory292c06.
  ///
  /// In en, this message translates to:
  /// **'Category'**
  String get domainCategory292c06;

  /// No description provided for @domainPriorityd60dbb.
  ///
  /// In en, this message translates to:
  /// **'Priority'**
  String get domainPriorityd60dbb;

  /// No description provided for @domainSubject689712.
  ///
  /// In en, this message translates to:
  /// **'Subject'**
  String get domainSubject689712;

  /// No description provided for @domainQuestionRequestba73e0.
  ///
  /// In en, this message translates to:
  /// **'Question / request'**
  String get domainQuestionRequestba73e0;

  /// No description provided for @domainCreateTickete836fc.
  ///
  /// In en, this message translates to:
  /// **'Create ticket'**
  String get domainCreateTickete836fc;

  /// No description provided for @domainRecoverThisExactTicketRequestdf25ad.
  ///
  /// In en, this message translates to:
  /// **'Recover this exact ticket request'**
  String get domainRecoverThisExactTicketRequestdf25ad;

  /// No description provided for @domainRefreshThisConversation6b5a20.
  ///
  /// In en, this message translates to:
  /// **'Refresh this conversation'**
  String get domainRefreshThisConversation6b5a20;

  /// No description provided for @domainVerifyPrivateDownload3a2d36.
  ///
  /// In en, this message translates to:
  /// **'Verify private download'**
  String get domainVerifyPrivateDownload3a2d36;

  /// No description provided for @domainMoreMessages9b4a40.
  ///
  /// In en, this message translates to:
  /// **'More messages'**
  String get domainMoreMessages9b4a40;

  /// No description provided for @domainSharedReply4d437b.
  ///
  /// In en, this message translates to:
  /// **'Shared reply'**
  String get domainSharedReply4d437b;

  /// No description provided for @domainOptionalPlainTextAttachment030a73.
  ///
  /// In en, this message translates to:
  /// **'Optional plain text attachment'**
  String get domainOptionalPlainTextAttachment030a73;

  /// No description provided for @domainUtf8TextMaximum32768ded21d.
  ///
  /// In en, this message translates to:
  /// **'UTF-8 text, maximum 32,768 bytes'**
  String get domainUtf8TextMaximum32768ded21d;

  /// No description provided for @domainSendSharedReplyf121d3.
  ///
  /// In en, this message translates to:
  /// **'Send shared reply'**
  String get domainSendSharedReplyf121d3;

  /// No description provided for @domainReasonForClosingReopening5e3744.
  ///
  /// In en, this message translates to:
  /// **'Reason for closing / reopening'**
  String get domainReasonForClosingReopening5e3744;

  /// No description provided for @domainCloseThisResolvedTicket3edf38.
  ///
  /// In en, this message translates to:
  /// **'Close this resolved ticket?'**
  String get domainCloseThisResolvedTicket3edf38;

  /// No description provided for @domainCloseResolvedTicketf3687f.
  ///
  /// In en, this message translates to:
  /// **'Close resolved ticket'**
  String get domainCloseResolvedTicketf3687f;

  /// No description provided for @domainReopenTickete6b8d8.
  ///
  /// In en, this message translates to:
  /// **'Reopen ticket'**
  String get domainReopenTickete6b8d8;

  /// No description provided for @domainTicketHistory183fea.
  ///
  /// In en, this message translates to:
  /// **'Ticket history'**
  String get domainTicketHistory183fea;

  /// No description provided for @domainMoreHistory7e2113.
  ///
  /// In en, this message translates to:
  /// **'More history'**
  String get domainMoreHistory7e2113;

  /// No description provided for @domainPrivateDownloadVerified22d5aa.
  ///
  /// In en, this message translates to:
  /// **'Private download verified'**
  String get domainPrivateDownloadVerified22d5aa;

  /// No description provided for @domainCloseAndDeletePrivateCopy3f2b2d.
  ///
  /// In en, this message translates to:
  /// **'Close and delete private copy'**
  String get domainCloseAndDeletePrivateCopy3f2b2d;

  /// No description provided for @domainSupportNotifications3a8090.
  ///
  /// In en, this message translates to:
  /// **'Support notifications'**
  String get domainSupportNotifications3a8090;

  /// No description provided for @domainRefreshNotificationsAndPreferencef9bb90.
  ///
  /// In en, this message translates to:
  /// **'Refresh notifications and preference'**
  String get domainRefreshNotificationsAndPreferencef9bb90;

  /// No description provided for @domainInAppSupportNotificationsd81899.
  ///
  /// In en, this message translates to:
  /// **'In-app support notifications'**
  String get domainInAppSupportNotificationsd81899;

  /// No description provided for @domainMoreNotifications9e58f9.
  ///
  /// In en, this message translates to:
  /// **'More notifications'**
  String get domainMoreNotifications9e58f9;

  /// No description provided for @domainSecureSharedAttachmentsff80f8.
  ///
  /// In en, this message translates to:
  /// **'Secure shared attachments'**
  String get domainSecureSharedAttachmentsff80f8;

  /// No description provided for @domainFileCollectionIsUnavailable1eb8de.
  ///
  /// In en, this message translates to:
  /// **'File collection is unavailable.'**
  String get domainFileCollectionIsUnavailable1eb8de;

  /// No description provided for @domainRetentionDays51de08.
  ///
  /// In en, this message translates to:
  /// **'Retention days'**
  String get domainRetentionDays51de08;

  /// No description provided for @domainRefreshAttachmentStatusd7974f.
  ///
  /// In en, this message translates to:
  /// **'Refresh attachment status'**
  String get domainRefreshAttachmentStatusd7974f;

  /// No description provided for @domainUsableb4d1bf.
  ///
  /// In en, this message translates to:
  /// **'Usable'**
  String get domainUsableb4d1bf;

  /// No description provided for @domainNotUsabled7464d.
  ///
  /// In en, this message translates to:
  /// **'Not usable'**
  String get domainNotUsabled7464d;

  /// No description provided for @domainRemoveStagedFilea50773.
  ///
  /// In en, this message translates to:
  /// **'Remove staged file'**
  String get domainRemoveStagedFilea50773;

  /// No description provided for @domainRemoveThisStagedAttachmentf4b57b.
  ///
  /// In en, this message translates to:
  /// **'Remove this staged attachment?'**
  String get domainRemoveThisStagedAttachmentf4b57b;

  /// No description provided for @domainMoreAttachments1f9e79.
  ///
  /// In en, this message translates to:
  /// **'More attachments'**
  String get domainMoreAttachments1f9e79;

  /// No description provided for @domainChooseSharedAttachment971b66.
  ///
  /// In en, this message translates to:
  /// **'Choose shared attachment'**
  String get domainChooseSharedAttachment971b66;

  /// No description provided for @domainRecoverExactFileRegistrationa8a032.
  ///
  /// In en, this message translates to:
  /// **'Recover exact file registration'**
  String get domainRecoverExactFileRegistrationa8a032;

  /// No description provided for @domainUploadSelectedBytes08b1dc.
  ///
  /// In en, this message translates to:
  /// **'Upload selected bytes'**
  String get domainUploadSelectedBytes08b1dc;

  /// No description provided for @domainDiscardSelectedPrivateCopy449966.
  ///
  /// In en, this message translates to:
  /// **'Discard selected private copy'**
  String get domainDiscardSelectedPrivateCopy449966;

  /// No description provided for @domainAnUploadedFileIsAttachedOnly99c018.
  ///
  /// In en, this message translates to:
  /// **'An uploaded file is attached only after a usable file is selected and the shared reply succeeds.'**
  String get domainAnUploadedFileIsAttachedOnly99c018;

  /// No description provided for @domainOfficialLinkCopiede5a1aa.
  ///
  /// In en, this message translates to:
  /// **'Official link copied.'**
  String get domainOfficialLinkCopiede5a1aa;

  /// No description provided for @domainVerified4f7838.
  ///
  /// In en, this message translates to:
  /// **'Verified'**
  String get domainVerified4f7838;

  /// No description provided for @domainCloses74c21a.
  ///
  /// In en, this message translates to:
  /// **'Closes'**
  String get domainCloses74c21a;

  /// No description provided for @domainResourcesOpportunitiesAndFunding0ba4d7.
  ///
  /// In en, this message translates to:
  /// **'Resources, opportunities and funding'**
  String get domainResourcesOpportunitiesAndFunding0ba4d7;

  /// No description provided for @domainResourceTypec9bf2e.
  ///
  /// In en, this message translates to:
  /// **'Resource type'**
  String get domainResourceTypec9bf2e;

  /// No description provided for @domainAllTypesf10988.
  ///
  /// In en, this message translates to:
  /// **'All types'**
  String get domainAllTypesf10988;

  /// No description provided for @domainAvailability12f67f.
  ///
  /// In en, this message translates to:
  /// **'Availability'**
  String get domainAvailability12f67f;

  /// No description provided for @domainApplyFiltersd80ab1.
  ///
  /// In en, this message translates to:
  /// **'Apply filters'**
  String get domainApplyFiltersd80ab1;

  /// No description provided for @domainNoMatchingResourcesfee1b1.
  ///
  /// In en, this message translates to:
  /// **'No matching resources.'**
  String get domainNoMatchingResourcesfee1b1;

  /// No description provided for @domainDetails45989d.
  ///
  /// In en, this message translates to:
  /// **'Details'**
  String get domainDetails45989d;

  /// No description provided for @domainOpenOfficialSource7bd352.
  ///
  /// In en, this message translates to:
  /// **'Open official source'**
  String get domainOpenOfficialSource7bd352;

  /// No description provided for @domainUnsave51883b.
  ///
  /// In en, this message translates to:
  /// **'Unsave'**
  String get domainUnsave51883b;

  /// No description provided for @domainSave1509f5.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get domainSave1509f5;

  /// No description provided for @domainExpressInterest97c8c3.
  ///
  /// In en, this message translates to:
  /// **'Express interest'**
  String get domainExpressInterest97c8c3;

  /// No description provided for @domainTrackMyFundingApplicationb7f857.
  ///
  /// In en, this message translates to:
  /// **'Track my funding application'**
  String get domainTrackMyFundingApplicationb7f857;

  /// No description provided for @domainMoreResources3f990f.
  ///
  /// In en, this message translates to:
  /// **'More resources'**
  String get domainMoreResources3f990f;

  /// No description provided for @domainRefreshSavedItemsAndFundingStatusea7e93.
  ///
  /// In en, this message translates to:
  /// **'Refresh saved items and funding status'**
  String get domainRefreshSavedItemsAndFundingStatusea7e93;

  /// No description provided for @domainSavedResources5d702b.
  ///
  /// In en, this message translates to:
  /// **'Saved resources'**
  String get domainSavedResources5d702b;

  /// No description provided for @domainResourceNoLongerAvailable008112.
  ///
  /// In en, this message translates to:
  /// **'Resource no longer available'**
  String get domainResourceNoLongerAvailable008112;

  /// No description provided for @domainMoreSavedItems5862e9.
  ///
  /// In en, this message translates to:
  /// **'More saved items'**
  String get domainMoreSavedItems5862e9;

  /// No description provided for @domainOpportunityInterests68b05b.
  ///
  /// In en, this message translates to:
  /// **'Opportunity interests'**
  String get domainOpportunityInterests68b05b;

  /// No description provided for @domainMoreInterests5eaef0.
  ///
  /// In en, this message translates to:
  /// **'More interests'**
  String get domainMoreInterests5eaef0;

  /// No description provided for @domainSelfReportedFundingProgress81e27b.
  ///
  /// In en, this message translates to:
  /// **'Self-reported funding progress'**
  String get domainSelfReportedFundingProgress81e27b;

  /// No description provided for @domainReasonUpdate49c0dc.
  ///
  /// In en, this message translates to:
  /// **'Reason / update'**
  String get domainReasonUpdate49c0dc;

  /// No description provided for @domainRecordThisFundingStatusUpdate888dec.
  ///
  /// In en, this message translates to:
  /// **'Record this funding status update?'**
  String get domainRecordThisFundingStatusUpdate888dec;

  /// No description provided for @domainMoreFundingCases3e9368.
  ///
  /// In en, this message translates to:
  /// **'More funding cases'**
  String get domainMoreFundingCases3e9368;

  /// No description provided for @domainMyMentoringb93152.
  ///
  /// In en, this message translates to:
  /// **'My mentoring'**
  String get domainMyMentoringb93152;

  /// No description provided for @domainRefreshMentoringeee9c0.
  ///
  /// In en, this message translates to:
  /// **'Refresh mentoring'**
  String get domainRefreshMentoringeee9c0;

  /// No description provided for @domainNoMentoringAssignmentsAreAvailable4ebb99.
  ///
  /// In en, this message translates to:
  /// **'No mentoring assignments are available.'**
  String get domainNoMentoringAssignmentsAreAvailable4ebb99;

  /// No description provided for @domainCompletedSessionfca593.
  ///
  /// In en, this message translates to:
  /// **'Completed session'**
  String get domainCompletedSessionfca593;

  /// No description provided for @domainRating15b4690a.
  ///
  /// In en, this message translates to:
  /// **'Rating (1–5)'**
  String get domainRating15b4690a;

  /// No description provided for @domainFeedbackCommentbf4a27.
  ///
  /// In en, this message translates to:
  /// **'Feedback comment'**
  String get domainFeedbackCommentbf4a27;

  /// No description provided for @domainSendSessionFeedbacke07582.
  ///
  /// In en, this message translates to:
  /// **'Send session feedback'**
  String get domainSendSessionFeedbacke07582;

  /// No description provided for @domainDiscardUnsavedTextAndSelectedPrivatea3487b.
  ///
  /// In en, this message translates to:
  /// **'Discard unsaved text and selected private copies before changing sections?'**
  String get domainDiscardUnsavedTextAndSelectedPrivatea3487b;

  /// No description provided for @domainLeaveThisPageAndDiscardUnsavedcb9eed.
  ///
  /// In en, this message translates to:
  /// **'Leave this page and discard unsaved work?'**
  String get domainLeaveThisPageAndDiscardUnsavedcb9eed;

  /// No description provided for @domainParticipantSupporte5a040.
  ///
  /// In en, this message translates to:
  /// **'Participant support'**
  String get domainParticipantSupporte5a040;

  /// No description provided for @domainMyBusinessPlanf1ef69.
  ///
  /// In en, this message translates to:
  /// **'My business plan'**
  String get domainMyBusinessPlanf1ef69;

  /// No description provided for @domainRefreshPlanscbc510.
  ///
  /// In en, this message translates to:
  /// **'Refresh plans'**
  String get domainRefreshPlanscbc510;

  /// No description provided for @domainNoActiveEnrollmentIsAvailableFor2f3a04.
  ///
  /// In en, this message translates to:
  /// **'No active enrollment is available for plan authoring.'**
  String get domainNoActiveEnrollmentIsAvailableFor2f3a04;

  /// No description provided for @domainActiveEnrollmentebb2ab.
  ///
  /// In en, this message translates to:
  /// **'Active enrollment'**
  String get domainActiveEnrollmentebb2ab;

  /// No description provided for @domainDiscardEditsBeforeChangingEnrollment28e2f9.
  ///
  /// In en, this message translates to:
  /// **'Discard edits before changing enrollment?'**
  String get domainDiscardEditsBeforeChangingEnrollment28e2f9;

  /// No description provided for @domainReviewTheCurrentSavedPlanBefore514269.
  ///
  /// In en, this message translates to:
  /// **'Review the current saved plan before continuing. Your edits are retained.'**
  String get domainReviewTheCurrentSavedPlanBefore514269;

  /// No description provided for @domainUseCurrentVersionAndKeepMybb6388.
  ///
  /// In en, this message translates to:
  /// **'Use current version and keep my edits'**
  String get domainUseCurrentVersionAndKeepMybb6388;

  /// No description provided for @domainUseSavedPlanfee405.
  ///
  /// In en, this message translates to:
  /// **'Use saved plan'**
  String get domainUseSavedPlanfee405;

  /// No description provided for @domainCreatePlan4e207a.
  ///
  /// In en, this message translates to:
  /// **'Create plan'**
  String get domainCreatePlan4e207a;

  /// No description provided for @domainSaveThisSection1e6c91.
  ///
  /// In en, this message translates to:
  /// **'Save this section'**
  String get domainSaveThisSection1e6c91;

  /// No description provided for @domainSubmitThisSavedPlanForReview262665.
  ///
  /// In en, this message translates to:
  /// **'Submit this saved plan for review?'**
  String get domainSubmitThisSavedPlanForReview262665;

  /// No description provided for @domainSubmitSavedPlan231cac.
  ///
  /// In en, this message translates to:
  /// **'Submit saved plan'**
  String get domainSubmitSavedPlan231cac;

  /// No description provided for @domainSubmission8d11f7.
  ///
  /// In en, this message translates to:
  /// **'Submission'**
  String get domainSubmission8d11f7;

  /// No description provided for @domainPublicResourcesbacc34.
  ///
  /// In en, this message translates to:
  /// **'Public resources'**
  String get domainPublicResourcesbacc34;

  /// No description provided for @domainTheResultIsUnknownRefreshThis9caf4b.
  ///
  /// In en, this message translates to:
  /// **'The result is unknown. Refresh this record before deciding to retry.'**
  String get domainTheResultIsUnknownRefreshThis9caf4b;

  /// No description provided for @domainThisRecordIsUnavailableForThis7a537f.
  ///
  /// In en, this message translates to:
  /// **'This record is unavailable for this account.'**
  String get domainThisRecordIsUnavailableForThis7a537f;

  /// No description provided for @domainTheRecordChangedRefreshAndReview2840a2.
  ///
  /// In en, this message translates to:
  /// **'The record changed. Refresh and review your retained text.'**
  String get domainTheRecordChangedRefreshAndReview2840a2;

  /// No description provided for @domainSignInAgainToContinue40f531.
  ///
  /// In en, this message translates to:
  /// **'Sign in again to continue.'**
  String get domainSignInAgainToContinue40f531;

  /// No description provided for @domainCheckTheEnteredValuesAndDisplayedee60bd.
  ///
  /// In en, this message translates to:
  /// **'Check the entered values and displayed limits.'**
  String get domainCheckTheEnteredValuesAndDisplayedee60bd;

  /// No description provided for @domainPleaseWaitBeforeTryingAgaind24731.
  ///
  /// In en, this message translates to:
  /// **'Please wait before trying again.'**
  String get domainPleaseWaitBeforeTryingAgaind24731;

  /// No description provided for @domainUnableToLoadThisInformationYour85597a.
  ///
  /// In en, this message translates to:
  /// **'Unable to load this information. Your text is retained.'**
  String get domainUnableToLoadThisInformationYour85597a;

  /// No description provided for @domainCancel19766e.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get domainCancel19766e;

  /// No description provided for @domainConfirmeebdd2.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get domainConfirmeebdd2;

  /// No description provided for @domainLeaveThisUnsavedOrUnconfirmedWork5e200a.
  ///
  /// In en, this message translates to:
  /// **'Leave this unsaved or unconfirmed work?'**
  String get domainLeaveThisUnsavedOrUnconfirmedWork5e200a;

  /// No description provided for @domainStay08fd1d.
  ///
  /// In en, this message translates to:
  /// **'Stay'**
  String get domainStay08fd1d;

  /// No description provided for @domainLeavefc6e4a.
  ///
  /// In en, this message translates to:
  /// **'Leave'**
  String get domainLeavefc6e4a;

  /// No description provided for @domainBusinessAndOutcomes964516.
  ///
  /// In en, this message translates to:
  /// **'Business and outcomes'**
  String get domainBusinessAndOutcomes964516;

  /// No description provided for @domainPrivateBusiness9c181b.
  ///
  /// In en, this message translates to:
  /// **'Private business'**
  String get domainPrivateBusiness9c181b;

  /// No description provided for @domainSelfReportedImpact0006f1.
  ///
  /// In en, this message translates to:
  /// **'Self-reported impact'**
  String get domainSelfReportedImpact0006f1;

  /// No description provided for @domainTheseProfilesArePrivatePublicSharingc4f5b1.
  ///
  /// In en, this message translates to:
  /// **'These profiles are private. Public sharing is off. Follow-up dates come from your saved program policy.'**
  String get domainTheseProfilesArePrivatePublicSharingc4f5b1;

  /// No description provided for @domainRefresh0e9161.
  ///
  /// In en, this message translates to:
  /// **'Refresh'**
  String get domainRefresh0e9161;

  /// No description provided for @domainNoEligibleActiveOrCompletedEnrollment98e845.
  ///
  /// In en, this message translates to:
  /// **'No eligible active or completed enrollment is available.'**
  String get domainNoEligibleActiveOrCompletedEnrollment98e845;

  /// No description provided for @domainEnrollment2d91aa.
  ///
  /// In en, this message translates to:
  /// **'Enrollment'**
  String get domainEnrollment2d91aa;

  /// No description provided for @domainDiscardThisUnsavedInputAnUnconfirmed91fe23.
  ///
  /// In en, this message translates to:
  /// **'Discard this unsaved input? An unconfirmed command must still be checked in saved state.'**
  String get domainDiscardThisUnsavedInputAnUnconfirmed91fe23;

  /// No description provided for @domainDiscardeb1a70.
  ///
  /// In en, this message translates to:
  /// **'Discard'**
  String get domainDiscardeb1a70;

  /// No description provided for @domainDiscardUnsavedInput9136d8.
  ///
  /// In en, this message translates to:
  /// **'Discard unsaved input'**
  String get domainDiscardUnsavedInput9136d8;

  /// No description provided for @domainImmutableProfileRevisionsLatest20cf668b.
  ///
  /// In en, this message translates to:
  /// **'Immutable profile revisions (latest 20)'**
  String get domainImmutableProfileRevisionsLatest20cf668b;

  /// No description provided for @domainVersiondd1679.
  ///
  /// In en, this message translates to:
  /// **'Version'**
  String get domainVersiondd1679;

  /// No description provided for @domainFollowUpReportsfd330c.
  ///
  /// In en, this message translates to:
  /// **'Follow-up reports'**
  String get domainFollowUpReportsfd330c;

  /// No description provided for @domainDue907173.
  ///
  /// In en, this message translates to:
  /// **'Due'**
  String get domainDue907173;

  /// No description provided for @domainDaysSavedPolicy6d4582.
  ///
  /// In en, this message translates to:
  /// **'days (saved policy)'**
  String get domainDaysSavedPolicy6d4582;

  /// No description provided for @domainOverdued66094.
  ///
  /// In en, this message translates to:
  /// **'Overdue'**
  String get domainOverdued66094;

  /// No description provided for @domainCompletedImmutableSelfReport17ca7c.
  ///
  /// In en, this message translates to:
  /// **'Completed immutable self-report'**
  String get domainCompletedImmutableSelfReport17ca7c;

  /// No description provided for @domainOpenFollowUpReport53a6b8.
  ///
  /// In en, this message translates to:
  /// **'Open follow-up report'**
  String get domainOpenFollowUpReport53a6b8;

  /// No description provided for @domainPrivateBusinessProfilef1fb7d.
  ///
  /// In en, this message translates to:
  /// **'Private business profile'**
  String get domainPrivateBusinessProfilef1fb7d;

  /// No description provided for @domainSavePrivateProfile9988a7.
  ///
  /// In en, this message translates to:
  /// **'Save private profile'**
  String get domainSavePrivateProfile9988a7;

  /// No description provided for @domainReadSavedStated9f3b0.
  ///
  /// In en, this message translates to:
  /// **'Read saved state'**
  String get domainReadSavedStated9f3b0;

  /// No description provided for @domainReviewTheSavedProfileBeforeAnother264cad.
  ///
  /// In en, this message translates to:
  /// **'Review the saved profile before another write.'**
  String get domainReviewTheSavedProfileBeforeAnother264cad;

  /// No description provided for @domainNoProfileExistsForThisEnrollment99706d.
  ///
  /// In en, this message translates to:
  /// **'No profile exists for this enrollment.'**
  String get domainNoProfileExistsForThisEnrollment99706d;

  /// No description provided for @domainUseSavedProfile913e70.
  ///
  /// In en, this message translates to:
  /// **'Use saved profile'**
  String get domainUseSavedProfile913e70;

  /// No description provided for @domainKeepMyEditsForExplicitSavea5c95a.
  ///
  /// In en, this message translates to:
  /// **'Keep my edits for explicit save'**
  String get domainKeepMyEditsForExplicitSavea5c95a;

  /// No description provided for @domainReportThisFollowUpOnce8ce6ce.
  ///
  /// In en, this message translates to:
  /// **'Report this follow-up once'**
  String get domainReportThisFollowUpOnce8ce6ce;

  /// No description provided for @domainReadSavedOutcomeBeforeRetry66f67c.
  ///
  /// In en, this message translates to:
  /// **'Read saved outcome before retry'**
  String get domainReadSavedOutcomeBeforeRetry66f67c;

  /// No description provided for @domainSubmitImmutableOutcome109e03.
  ///
  /// In en, this message translates to:
  /// **'Submit immutable outcome'**
  String get domainSubmitImmutableOutcome109e03;

  /// No description provided for @domainSelfReportedObservationsTheseAreSeparate3a51e7.
  ///
  /// In en, this message translates to:
  /// **'Self-reported observations. These are separate from business follow-up reports and do not establish verified impact.'**
  String get domainSelfReportedObservationsTheseAreSeparate3a51e7;

  /// No description provided for @domainRefreshObservations34ae4c.
  ///
  /// In en, this message translates to:
  /// **'Refresh observations'**
  String get domainRefreshObservations34ae4c;

  /// No description provided for @domainNoEligibleEnrollments16c2f5.
  ///
  /// In en, this message translates to:
  /// **'No eligible enrollments.'**
  String get domainNoEligibleEnrollments16c2f5;

  /// No description provided for @domainMoreEnrollments6edb68.
  ///
  /// In en, this message translates to:
  /// **'More enrollments'**
  String get domainMoreEnrollments6edb68;

  /// No description provided for @domainPinnedDefinitionEdition03b94a.
  ///
  /// In en, this message translates to:
  /// **'Pinned definition edition'**
  String get domainPinnedDefinitionEdition03b94a;

  /// No description provided for @domainMoreDefinitions6f842b.
  ///
  /// In en, this message translates to:
  /// **'More definitions'**
  String get domainMoreDefinitions6f842b;

  /// No description provided for @domainReadExactObservationStatee6cbb6.
  ///
  /// In en, this message translates to:
  /// **'Read exact observation state'**
  String get domainReadExactObservationStatee6cbb6;

  /// No description provided for @domainExplicitlyRetryUnchangedRequest0c8f5a.
  ///
  /// In en, this message translates to:
  /// **'Explicitly retry unchanged request'**
  String get domainExplicitlyRetryUnchangedRequest0c8f5a;

  /// No description provided for @domainDiscardPendingRequestChooseACurrent24ad4d.
  ///
  /// In en, this message translates to:
  /// **'Discard pending request; choose a current record'**
  String get domainDiscardPendingRequestChooseACurrent24ad4d;

  /// No description provided for @domainStartAnotherObservatione8e1c1.
  ///
  /// In en, this message translates to:
  /// **'Start another observation'**
  String get domainStartAnotherObservatione8e1c1;

  /// No description provided for @domainObservationHistoryEachRevisionIsRetaineda9da2a.
  ///
  /// In en, this message translates to:
  /// **'Observation history (each revision is retained)'**
  String get domainObservationHistoryEachRevisionIsRetaineda9da2a;

  /// No description provided for @domainRevision2e516d.
  ///
  /// In en, this message translates to:
  /// **'Revision'**
  String get domainRevision2e516d;

  /// No description provided for @domainSupersedeWithAReason4294f3.
  ///
  /// In en, this message translates to:
  /// **'Supersede with a reason'**
  String get domainSupersedeWithAReason4294f3;

  /// No description provided for @domainMoreObservationHistory11b7c2.
  ///
  /// In en, this message translates to:
  /// **'More observation history'**
  String get domainMoreObservationHistory11b7c2;

  /// No description provided for @domainTheActionCouldNotBeConfirmedaed76e.
  ///
  /// In en, this message translates to:
  /// **'The action could not be confirmed. Your input is kept. Refresh saved state before retrying an uncertain action.'**
  String get domainTheActionCouldNotBeConfirmedaed76e;

  /// No description provided for @domainEnrollmentUpdatesc8101a.
  ///
  /// In en, this message translates to:
  /// **'Enrollment updates'**
  String get domainEnrollmentUpdatesc8101a;

  /// No description provided for @domainInAppEnrollmentUpdatesRefreshTof8b773.
  ///
  /// In en, this message translates to:
  /// **'In-app enrollment updates. Refresh to check for new updates.'**
  String get domainInAppEnrollmentUpdatesRefreshTof8b773;

  /// No description provided for @domainReceiveEnrollmentUpdatesc62c16.
  ///
  /// In en, this message translates to:
  /// **'Receive enrollment updates'**
  String get domainReceiveEnrollmentUpdatesc62c16;

  /// No description provided for @domainReadSavedNotificationPreference918105.
  ///
  /// In en, this message translates to:
  /// **'Read saved notification preference'**
  String get domainReadSavedNotificationPreference918105;

  /// No description provided for @domainRefreshInboxa804e4.
  ///
  /// In en, this message translates to:
  /// **'Refresh inbox'**
  String get domainRefreshInboxa804e4;

  /// No description provided for @domainNoAvailableUpdatesba4851.
  ///
  /// In en, this message translates to:
  /// **'No available updates.'**
  String get domainNoAvailableUpdatesba4851;

  /// No description provided for @domainYourProgramEnrollmentIsConfirmed72dce5.
  ///
  /// In en, this message translates to:
  /// **'Your program enrollment is confirmed.'**
  String get domainYourProgramEnrollmentIsConfirmed72dce5;

  /// No description provided for @domainCheckSavedReadStatus1e817a.
  ///
  /// In en, this message translates to:
  /// **'Check saved read status'**
  String get domainCheckSavedReadStatus1e817a;

  /// No description provided for @domainMarkReadb49c9b.
  ///
  /// In en, this message translates to:
  /// **'Mark read'**
  String get domainMarkReadb49c9b;

  /// No description provided for @domainOpenCurrentSchedule031f2c.
  ///
  /// In en, this message translates to:
  /// **'Open current schedule'**
  String get domainOpenCurrentSchedule031f2c;

  /// No description provided for @domainMoreUpdates5fdeda.
  ///
  /// In en, this message translates to:
  /// **'More updates'**
  String get domainMoreUpdates5fdeda;

  /// No description provided for @alumniFieldName.
  ///
  /// In en, this message translates to:
  /// **'Business name'**
  String get alumniFieldName;

  /// No description provided for @alumniFieldSector.
  ///
  /// In en, this message translates to:
  /// **'Sector'**
  String get alumniFieldSector;

  /// No description provided for @alumniFieldProductsServices.
  ///
  /// In en, this message translates to:
  /// **'Products and services'**
  String get alumniFieldProductsServices;

  /// No description provided for @alumniFieldStage.
  ///
  /// In en, this message translates to:
  /// **'Business stage'**
  String get alumniFieldStage;

  /// No description provided for @alumniFieldRegistrationInfo.
  ///
  /// In en, this message translates to:
  /// **'Registration details (optional)'**
  String get alumniFieldRegistrationInfo;

  /// No description provided for @alumniFieldStartedOn.
  ///
  /// In en, this message translates to:
  /// **'Started on (YYYY-MM-DD)'**
  String get alumniFieldStartedOn;

  /// No description provided for @alumniFieldTeamSize.
  ///
  /// In en, this message translates to:
  /// **'Team size'**
  String get alumniFieldTeamSize;

  /// No description provided for @alumniFieldInvestmentBand.
  ///
  /// In en, this message translates to:
  /// **'Investment band (INR)'**
  String get alumniFieldInvestmentBand;

  /// No description provided for @alumniFieldFundingStatus.
  ///
  /// In en, this message translates to:
  /// **'Funding status'**
  String get alumniFieldFundingStatus;

  /// No description provided for @alumniFieldRevenueBand.
  ///
  /// In en, this message translates to:
  /// **'Revenue band (INR)'**
  String get alumniFieldRevenueBand;

  /// No description provided for @alumniFieldSupportNeeds.
  ///
  /// In en, this message translates to:
  /// **'Support needs (optional)'**
  String get alumniFieldSupportNeeds;

  /// No description provided for @alumniFieldReportedOn.
  ///
  /// In en, this message translates to:
  /// **'Reported on (YYYY-MM-DD)'**
  String get alumniFieldReportedOn;

  /// No description provided for @alumniFieldBusinessStarted.
  ///
  /// In en, this message translates to:
  /// **'Business has started'**
  String get alumniFieldBusinessStarted;

  /// No description provided for @alumniFieldBusinessActive.
  ///
  /// In en, this message translates to:
  /// **'Business is active'**
  String get alumniFieldBusinessActive;

  /// No description provided for @alumniFieldJobsCreated.
  ///
  /// In en, this message translates to:
  /// **'Jobs created'**
  String get alumniFieldJobsCreated;

  /// No description provided for @alumniFieldFundingBand.
  ///
  /// In en, this message translates to:
  /// **'Funding band (INR)'**
  String get alumniFieldFundingBand;

  /// No description provided for @alumniFieldChallenges.
  ///
  /// In en, this message translates to:
  /// **'Challenges (optional)'**
  String get alumniFieldChallenges;

  /// No description provided for @alumniFieldSupportRequested.
  ///
  /// In en, this message translates to:
  /// **'Support requested (optional)'**
  String get alumniFieldSupportRequested;

  /// No description provided for @alumniFieldMentorInterventions.
  ///
  /// In en, this message translates to:
  /// **'Mentor support (optional)'**
  String get alumniFieldMentorInterventions;

  /// No description provided for @alumniFieldOutcomes.
  ///
  /// In en, this message translates to:
  /// **'Outcomes (optional)'**
  String get alumniFieldOutcomes;

  /// No description provided for @alumniFieldObservedOn.
  ///
  /// In en, this message translates to:
  /// **'Observed on (YYYY-MM-DD)'**
  String get alumniFieldObservedOn;

  /// No description provided for @alumniFieldReason.
  ///
  /// In en, this message translates to:
  /// **'Reason for this observation or revision'**
  String get alumniFieldReason;

  /// No description provided for @alumniFieldIdea.
  ///
  /// In en, this message translates to:
  /// **'Idea'**
  String get alumniFieldIdea;

  /// No description provided for @alumniFieldStarting.
  ///
  /// In en, this message translates to:
  /// **'Starting'**
  String get alumniFieldStarting;

  /// No description provided for @alumniFieldOperating.
  ///
  /// In en, this message translates to:
  /// **'Operating'**
  String get alumniFieldOperating;

  /// No description provided for @alumniFieldPaused.
  ///
  /// In en, this message translates to:
  /// **'Paused'**
  String get alumniFieldPaused;

  /// No description provided for @alumniFieldClosed.
  ///
  /// In en, this message translates to:
  /// **'Closed'**
  String get alumniFieldClosed;

  /// No description provided for @alumniFieldNone.
  ///
  /// In en, this message translates to:
  /// **'None'**
  String get alumniFieldNone;

  /// No description provided for @alumniFieldUnder1l.
  ///
  /// In en, this message translates to:
  /// **'Under ₹1 lakh'**
  String get alumniFieldUnder1l;

  /// No description provided for @alumniField1lTo5l.
  ///
  /// In en, this message translates to:
  /// **'₹1–5 lakh'**
  String get alumniField1lTo5l;

  /// No description provided for @alumniField5lTo25l.
  ///
  /// In en, this message translates to:
  /// **'₹5–25 lakh'**
  String get alumniField5lTo25l;

  /// No description provided for @alumniFieldOver25l.
  ///
  /// In en, this message translates to:
  /// **'Over ₹25 lakh'**
  String get alumniFieldOver25l;

  /// No description provided for @alumniFieldUnder10k.
  ///
  /// In en, this message translates to:
  /// **'Under ₹10,000'**
  String get alumniFieldUnder10k;

  /// No description provided for @alumniField10kTo50k.
  ///
  /// In en, this message translates to:
  /// **'₹10,000–50,000'**
  String get alumniField10kTo50k;

  /// No description provided for @alumniField50kTo2l.
  ///
  /// In en, this message translates to:
  /// **'₹50,000–2 lakh'**
  String get alumniField50kTo2l;

  /// No description provided for @alumniFieldOver2l.
  ///
  /// In en, this message translates to:
  /// **'Over ₹2 lakh'**
  String get alumniFieldOver2l;

  /// No description provided for @alumniFieldUndisclosed.
  ///
  /// In en, this message translates to:
  /// **'Prefer not to disclose'**
  String get alumniFieldUndisclosed;

  /// No description provided for @alumniFieldSeeking.
  ///
  /// In en, this message translates to:
  /// **'Seeking funding'**
  String get alumniFieldSeeking;

  /// No description provided for @alumniFieldApplied.
  ///
  /// In en, this message translates to:
  /// **'Applied'**
  String get alumniFieldApplied;

  /// No description provided for @alumniFieldApproved.
  ///
  /// In en, this message translates to:
  /// **'Approved'**
  String get alumniFieldApproved;

  /// No description provided for @alumniFieldDisbursed.
  ///
  /// In en, this message translates to:
  /// **'Disbursed'**
  String get alumniFieldDisbursed;

  /// No description provided for @alumniFieldBaseline.
  ///
  /// In en, this message translates to:
  /// **'Baseline observation'**
  String get alumniFieldBaseline;

  /// No description provided for @alumniFieldOutcome.
  ///
  /// In en, this message translates to:
  /// **'Outcome observation'**
  String get alumniFieldOutcome;

  /// No description provided for @alumniFieldActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get alumniFieldActive;

  /// No description provided for @alumniFieldCompleted.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get alumniFieldCompleted;

  /// No description provided for @alumniFieldPublished.
  ///
  /// In en, this message translates to:
  /// **'Published'**
  String get alumniFieldPublished;

  /// No description provided for @alumniFieldArchived.
  ///
  /// In en, this message translates to:
  /// **'Archived'**
  String get alumniFieldArchived;

  /// No description provided for @supportLabelSupport.
  ///
  /// In en, this message translates to:
  /// **'Helpdesk'**
  String get supportLabelSupport;

  /// No description provided for @supportLabelMentoring.
  ///
  /// In en, this message translates to:
  /// **'Mentoring'**
  String get supportLabelMentoring;

  /// No description provided for @supportLabelPlans.
  ///
  /// In en, this message translates to:
  /// **'Business plan'**
  String get supportLabelPlans;

  /// No description provided for @supportLabelResources.
  ///
  /// In en, this message translates to:
  /// **'Resources and funding'**
  String get supportLabelResources;

  /// No description provided for @supportLabelOpen.
  ///
  /// In en, this message translates to:
  /// **'Open'**
  String get supportLabelOpen;

  /// No description provided for @supportLabelAssigned.
  ///
  /// In en, this message translates to:
  /// **'Assigned'**
  String get supportLabelAssigned;

  /// No description provided for @supportLabelInProgress.
  ///
  /// In en, this message translates to:
  /// **'In progress'**
  String get supportLabelInProgress;

  /// No description provided for @supportLabelWaitingForUser.
  ///
  /// In en, this message translates to:
  /// **'Waiting for your reply'**
  String get supportLabelWaitingForUser;

  /// No description provided for @supportLabelResolved.
  ///
  /// In en, this message translates to:
  /// **'Resolved'**
  String get supportLabelResolved;

  /// No description provided for @supportLabelClosed.
  ///
  /// In en, this message translates to:
  /// **'Closed'**
  String get supportLabelClosed;

  /// No description provided for @supportLabelLow.
  ///
  /// In en, this message translates to:
  /// **'Low'**
  String get supportLabelLow;

  /// No description provided for @supportLabelNormal.
  ///
  /// In en, this message translates to:
  /// **'Normal'**
  String get supportLabelNormal;

  /// No description provided for @supportLabelHigh.
  ///
  /// In en, this message translates to:
  /// **'High'**
  String get supportLabelHigh;

  /// No description provided for @supportLabelUrgent.
  ///
  /// In en, this message translates to:
  /// **'Urgent'**
  String get supportLabelUrgent;

  /// No description provided for @supportLabelFunding.
  ///
  /// In en, this message translates to:
  /// **'Funding'**
  String get supportLabelFunding;

  /// No description provided for @supportLabelRegistration.
  ///
  /// In en, this message translates to:
  /// **'Registration'**
  String get supportLabelRegistration;

  /// No description provided for @supportLabelTaxCompliance.
  ///
  /// In en, this message translates to:
  /// **'Tax and compliance guidance'**
  String get supportLabelTaxCompliance;

  /// No description provided for @supportLabelMarketing.
  ///
  /// In en, this message translates to:
  /// **'Marketing'**
  String get supportLabelMarketing;

  /// No description provided for @supportLabelTechnology.
  ///
  /// In en, this message translates to:
  /// **'Technology'**
  String get supportLabelTechnology;

  /// No description provided for @supportLabelBusinessPlanning.
  ///
  /// In en, this message translates to:
  /// **'Business planning'**
  String get supportLabelBusinessPlanning;

  /// No description provided for @supportLabelBanking.
  ///
  /// In en, this message translates to:
  /// **'Banking'**
  String get supportLabelBanking;

  /// No description provided for @supportLabelGeneral.
  ///
  /// In en, this message translates to:
  /// **'General'**
  String get supportLabelGeneral;

  /// No description provided for @supportLabelActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get supportLabelActive;

  /// No description provided for @supportLabelCompleted.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get supportLabelCompleted;

  /// No description provided for @supportLabelCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get supportLabelCancelled;

  /// No description provided for @supportLabelScheduled.
  ///
  /// In en, this message translates to:
  /// **'Scheduled'**
  String get supportLabelScheduled;

  /// No description provided for @supportLabelPhone.
  ///
  /// In en, this message translates to:
  /// **'Phone'**
  String get supportLabelPhone;

  /// No description provided for @supportLabelOnline.
  ///
  /// In en, this message translates to:
  /// **'Online'**
  String get supportLabelOnline;

  /// No description provided for @supportLabelInPerson.
  ///
  /// In en, this message translates to:
  /// **'In person'**
  String get supportLabelInPerson;

  /// No description provided for @supportLabelHybrid.
  ///
  /// In en, this message translates to:
  /// **'Hybrid'**
  String get supportLabelHybrid;

  /// No description provided for @supportLabelEnded.
  ///
  /// In en, this message translates to:
  /// **'Ended'**
  String get supportLabelEnded;

  /// No description provided for @supportLabelDraft.
  ///
  /// In en, this message translates to:
  /// **'Draft'**
  String get supportLabelDraft;

  /// No description provided for @supportLabelSubmitted.
  ///
  /// In en, this message translates to:
  /// **'Submitted'**
  String get supportLabelSubmitted;

  /// No description provided for @supportLabelChangesRequested.
  ///
  /// In en, this message translates to:
  /// **'Changes requested'**
  String get supportLabelChangesRequested;

  /// No description provided for @supportLabelApproved.
  ///
  /// In en, this message translates to:
  /// **'Approved'**
  String get supportLabelApproved;

  /// No description provided for @supportLabelInterested.
  ///
  /// In en, this message translates to:
  /// **'Interested'**
  String get supportLabelInterested;

  /// No description provided for @supportLabelEligibilityCheck.
  ///
  /// In en, this message translates to:
  /// **'Eligibility check'**
  String get supportLabelEligibilityCheck;

  /// No description provided for @supportLabelDocumentPreparation.
  ///
  /// In en, this message translates to:
  /// **'Document preparation'**
  String get supportLabelDocumentPreparation;

  /// No description provided for @supportLabelApplied.
  ///
  /// In en, this message translates to:
  /// **'Applied'**
  String get supportLabelApplied;

  /// No description provided for @supportLabelUnderReview.
  ///
  /// In en, this message translates to:
  /// **'Under review'**
  String get supportLabelUnderReview;

  /// No description provided for @supportLabelRejected.
  ///
  /// In en, this message translates to:
  /// **'Rejected'**
  String get supportLabelRejected;

  /// No description provided for @supportLabelDisbursed.
  ///
  /// In en, this message translates to:
  /// **'Disbursed'**
  String get supportLabelDisbursed;

  /// No description provided for @supportLabelScheme.
  ///
  /// In en, this message translates to:
  /// **'Scheme'**
  String get supportLabelScheme;

  /// No description provided for @supportLabelOpportunity.
  ///
  /// In en, this message translates to:
  /// **'Opportunity'**
  String get supportLabelOpportunity;

  /// No description provided for @supportLabelAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get supportLabelAll;

  /// No description provided for @supportLabelUpcoming.
  ///
  /// In en, this message translates to:
  /// **'Upcoming'**
  String get supportLabelUpcoming;

  /// No description provided for @supportLabelCreated.
  ///
  /// In en, this message translates to:
  /// **'Created'**
  String get supportLabelCreated;

  /// No description provided for @supportLabelMessage.
  ///
  /// In en, this message translates to:
  /// **'Message'**
  String get supportLabelMessage;

  /// No description provided for @supportLabelReply.
  ///
  /// In en, this message translates to:
  /// **'Reply'**
  String get supportLabelReply;

  /// No description provided for @supportLabelStatus.
  ///
  /// In en, this message translates to:
  /// **'Status'**
  String get supportLabelStatus;

  /// No description provided for @supportLabelReopened.
  ///
  /// In en, this message translates to:
  /// **'Reopened'**
  String get supportLabelReopened;

  /// No description provided for @supportLabelPriority.
  ///
  /// In en, this message translates to:
  /// **'Priority'**
  String get supportLabelPriority;

  /// No description provided for @supportLabelAssignment.
  ///
  /// In en, this message translates to:
  /// **'Assignment'**
  String get supportLabelAssignment;

  /// No description provided for @supportLabelStaged.
  ///
  /// In en, this message translates to:
  /// **'Staged'**
  String get supportLabelStaged;

  /// No description provided for @supportLabelRemoved.
  ///
  /// In en, this message translates to:
  /// **'Removed'**
  String get supportLabelRemoved;

  /// No description provided for @supportLabelPosted.
  ///
  /// In en, this message translates to:
  /// **'Posted'**
  String get supportLabelPosted;

  /// No description provided for @supportLabelPending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get supportLabelPending;

  /// No description provided for @supportLabelPendingUpload.
  ///
  /// In en, this message translates to:
  /// **'Awaiting upload'**
  String get supportLabelPendingUpload;

  /// No description provided for @supportLabelQuarantined.
  ///
  /// In en, this message translates to:
  /// **'Awaiting security check'**
  String get supportLabelQuarantined;

  /// No description provided for @supportLabelClean.
  ///
  /// In en, this message translates to:
  /// **'Security check passed'**
  String get supportLabelClean;

  /// No description provided for @supportLabelInfected.
  ///
  /// In en, this message translates to:
  /// **'Security check failed'**
  String get supportLabelInfected;

  /// No description provided for @supportLabelDeleted.
  ///
  /// In en, this message translates to:
  /// **'Deleted'**
  String get supportLabelDeleted;

  /// No description provided for @supportLabelExpired.
  ///
  /// In en, this message translates to:
  /// **'Expired'**
  String get supportLabelExpired;

  /// No description provided for @supportLabelQ.
  ///
  /// In en, this message translates to:
  /// **'Search'**
  String get supportLabelQ;

  /// No description provided for @supportLabelSector.
  ///
  /// In en, this message translates to:
  /// **'Sector'**
  String get supportLabelSector;

  /// No description provided for @supportLabelGeography.
  ///
  /// In en, this message translates to:
  /// **'Geography'**
  String get supportLabelGeography;

  /// No description provided for @supportLabelTag.
  ///
  /// In en, this message translates to:
  /// **'Tag'**
  String get supportLabelTag;

  /// No description provided for @supportLabelExecutiveSummary.
  ///
  /// In en, this message translates to:
  /// **'Executive summary'**
  String get supportLabelExecutiveSummary;

  /// No description provided for @supportLabelProblem.
  ///
  /// In en, this message translates to:
  /// **'Problem'**
  String get supportLabelProblem;

  /// No description provided for @supportLabelSolution.
  ///
  /// In en, this message translates to:
  /// **'Solution'**
  String get supportLabelSolution;

  /// No description provided for @supportLabelProductService.
  ///
  /// In en, this message translates to:
  /// **'Product service'**
  String get supportLabelProductService;

  /// No description provided for @supportLabelCustomerSegments.
  ///
  /// In en, this message translates to:
  /// **'Customer segments'**
  String get supportLabelCustomerSegments;

  /// No description provided for @supportLabelMarket.
  ///
  /// In en, this message translates to:
  /// **'Market'**
  String get supportLabelMarket;

  /// No description provided for @supportLabelCompetition.
  ///
  /// In en, this message translates to:
  /// **'Competition'**
  String get supportLabelCompetition;

  /// No description provided for @supportLabelValueProposition.
  ///
  /// In en, this message translates to:
  /// **'Value proposition'**
  String get supportLabelValueProposition;

  /// No description provided for @supportLabelBusinessModel.
  ///
  /// In en, this message translates to:
  /// **'Business model'**
  String get supportLabelBusinessModel;

  /// No description provided for @supportLabelPricing.
  ///
  /// In en, this message translates to:
  /// **'Pricing'**
  String get supportLabelPricing;

  /// No description provided for @supportLabelSalesMarketing.
  ///
  /// In en, this message translates to:
  /// **'Sales marketing'**
  String get supportLabelSalesMarketing;

  /// No description provided for @supportLabelOperations.
  ///
  /// In en, this message translates to:
  /// **'Operations'**
  String get supportLabelOperations;

  /// No description provided for @supportLabelTeam.
  ///
  /// In en, this message translates to:
  /// **'Team'**
  String get supportLabelTeam;

  /// No description provided for @supportLabelInvestment.
  ///
  /// In en, this message translates to:
  /// **'Investment'**
  String get supportLabelInvestment;

  /// No description provided for @supportLabelRevenueAssumptions.
  ///
  /// In en, this message translates to:
  /// **'Revenue assumptions'**
  String get supportLabelRevenueAssumptions;

  /// No description provided for @supportLabelExpenseAssumptions.
  ///
  /// In en, this message translates to:
  /// **'Expense assumptions'**
  String get supportLabelExpenseAssumptions;

  /// No description provided for @supportLabelBreakEvenInputs.
  ///
  /// In en, this message translates to:
  /// **'Break even inputs'**
  String get supportLabelBreakEvenInputs;

  /// No description provided for @supportLabelFundingRequirement.
  ///
  /// In en, this message translates to:
  /// **'Funding requirement'**
  String get supportLabelFundingRequirement;

  /// No description provided for @supportLabelRisks.
  ///
  /// In en, this message translates to:
  /// **'Risks'**
  String get supportLabelRisks;

  /// No description provided for @supportLabelMilestones.
  ///
  /// In en, this message translates to:
  /// **'Milestones'**
  String get supportLabelMilestones;

  /// No description provided for @attendanceScan.
  ///
  /// In en, this message translates to:
  /// **'Scan attendance QR'**
  String get attendanceScan;

  /// No description provided for @attendanceScanExplanation.
  ///
  /// In en, this message translates to:
  /// **'Scan the trainer\'s attendance QR code or enter the code below. Review it, then press Check in.'**
  String get attendanceScanExplanation;

  /// No description provided for @attendanceScanInvalid.
  ///
  /// In en, this message translates to:
  /// **'This QR code is not an EDP attendance code. Enter the trainer\'s code instead.'**
  String get attendanceScanInvalid;

  /// No description provided for @attendanceScanUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Camera scanning is unavailable. You can enter or paste the trainer\'s code.'**
  String get attendanceScanUnavailable;

  /// No description provided for @mobileUpdateAvailable.
  ///
  /// In en, this message translates to:
  /// **'A newer app version is available.'**
  String get mobileUpdateAvailable;

  /// No description provided for @mobileUpdateRequired.
  ///
  /// In en, this message translates to:
  /// **'Please update this app to continue using the supported version.'**
  String get mobileUpdateRequired;

  /// No description provided for @mobileUpdateOpen.
  ///
  /// In en, this message translates to:
  /// **'Open approved download'**
  String get mobileUpdateOpen;

  /// No description provided for @mobileUpdateDismiss.
  ///
  /// In en, this message translates to:
  /// **'Later'**
  String get mobileUpdateDismiss;

  /// No description provided for @mobileLinkedUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This linked record is unavailable for the current account. Refresh or return to the list.'**
  String get mobileLinkedUnavailable;

  /// No description provided for @mobileYes.
  ///
  /// In en, this message translates to:
  /// **'Yes'**
  String get mobileYes;

  /// No description provided for @mobileNo.
  ///
  /// In en, this message translates to:
  /// **'No'**
  String get mobileNo;

  /// No description provided for @mobileRead.
  ///
  /// In en, this message translates to:
  /// **'Read'**
  String get mobileRead;

  /// No description provided for @mobileUnread.
  ///
  /// In en, this message translates to:
  /// **'Unread'**
  String get mobileUnread;

  /// No description provided for @mobileSubmitSelfReport.
  ///
  /// In en, this message translates to:
  /// **'Submit self-report'**
  String get mobileSubmitSelfReport;

  /// No description provided for @mobileSaveRevision.
  ///
  /// In en, this message translates to:
  /// **'Save superseding revision'**
  String get mobileSaveRevision;

  /// No description provided for @fileProtectionRequired.
  ///
  /// In en, this message translates to:
  /// **'Private files require encrypted device storage and a secure screen lock. Unlock your device and check its security settings, then try again.'**
  String get fileProtectionRequired;

  /// No description provided for @fileRetryProtection.
  ///
  /// In en, this message translates to:
  /// **'Retry protected storage'**
  String get fileRetryProtection;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ta'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ta':
      return AppLocalizationsTa();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
