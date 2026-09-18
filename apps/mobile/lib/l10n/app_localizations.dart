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
