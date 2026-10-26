import '../../l10n/app_localizations.dart';
import 'package:flutter/material.dart';

String alumniText(BuildContext context, String english, String tamil) =>
    Localizations.localeOf(context).languageCode == 'ta' ? tamil : english;
String alumniLabel(BuildContext context, String key) {
  final text = AppLocalizations.of(context)!;
  return switch (key) {
    'name' => text.alumniFieldName,
    'sector' => text.alumniFieldSector,
    'products_services' => text.alumniFieldProductsServices,
    'stage' => text.alumniFieldStage,
    'registration_info' => text.alumniFieldRegistrationInfo,
    'started_on' => text.alumniFieldStartedOn,
    'team_size' => text.alumniFieldTeamSize,
    'investment_band' => text.alumniFieldInvestmentBand,
    'funding_status' => text.alumniFieldFundingStatus,
    'revenue_band' => text.alumniFieldRevenueBand,
    'support_needs' => text.alumniFieldSupportNeeds,
    'reported_on' => text.alumniFieldReportedOn,
    'business_started' => text.alumniFieldBusinessStarted,
    'business_active' => text.alumniFieldBusinessActive,
    'jobs_created' => text.alumniFieldJobsCreated,
    'funding_band' => text.alumniFieldFundingBand,
    'challenges' => text.alumniFieldChallenges,
    'support_requested' => text.alumniFieldSupportRequested,
    'mentor_interventions' => text.alumniFieldMentorInterventions,
    'outcomes' => text.alumniFieldOutcomes,
    'observed_on' => text.alumniFieldObservedOn,
    'reason' => text.alumniFieldReason,
    'idea' => text.alumniFieldIdea,
    'starting' => text.alumniFieldStarting,
    'operating' => text.alumniFieldOperating,
    'paused' => text.alumniFieldPaused,
    'closed' => text.alumniFieldClosed,
    'none' => text.alumniFieldNone,
    'under_1l' => text.alumniFieldUnder1l,
    '1l_to_5l' => text.alumniField1lTo5l,
    '5l_to_25l' => text.alumniField5lTo25l,
    'over_25l' => text.alumniFieldOver25l,
    'under_10k' => text.alumniFieldUnder10k,
    '10k_to_50k' => text.alumniField10kTo50k,
    '50k_to_2l' => text.alumniField50kTo2l,
    'over_2l' => text.alumniFieldOver2l,
    'undisclosed' => text.alumniFieldUndisclosed,
    'seeking' => text.alumniFieldSeeking,
    'applied' => text.alumniFieldApplied,
    'approved' => text.alumniFieldApproved,
    'disbursed' => text.alumniFieldDisbursed,
    'baseline' => text.alumniFieldBaseline,
    'outcome' => text.alumniFieldOutcome,
    'active' => text.alumniFieldActive,
    'completed' => text.alumniFieldCompleted,
    'published' => text.alumniFieldPublished,
    'archived' => text.alumniFieldArchived,
    _ => key,
  };
}

String alumniFailure(BuildContext context, Object? error) =>
    AppLocalizations.of(context)!.domainTheActionCouldNotBeConfirmedaed76e;
