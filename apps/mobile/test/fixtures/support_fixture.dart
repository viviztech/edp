import 'package:dio/dio.dart';
import 'package:edp_mobile/core/api/api_failure.dart';
import 'package:edp_mobile/core/api/domain_api.dart';
import 'package:edp_mobile/features/identity/auth_repository.dart';
import 'package:edp_mobile/features/participant_support/plans.dart';

import '../core_api_test.dart' show ApiMemoryStore;

const supportOrg = '11111111-1111-4111-8111-111111111111';
const supportEnrollment = '22222222-2222-4222-8222-222222222222';
const supportPlan = '33333333-3333-4333-8333-333333333333';
const supportAssignment = '44444444-4444-4444-8444-444444444444';
const supportSession = '55555555-5555-4555-8555-555555555555';
const supportTicket = '66666666-6666-4666-8666-666666666666';
const supportItem = '77777777-7777-4777-8777-777777777777';
const supportCase = '88888888-8888-4888-8888-888888888888';

Map<String, dynamic> supportPlanJson({int version = 1}) => {
  'id': supportPlan,
  'enrollment_id': supportEnrollment,
  'status': 'draft',
  'version': version,
  'completed_sections': 1,
  'total_sections': 20,
  'sections': {planSections.first: 'Synthetic retained plan'},
  'submissions': <Object>[],
};
Map<String, dynamic> supportTicketJson({int version = 1}) => {
  'id': supportTicket,
  'number': 'EDP-SYNTHETIC',
  'category': 'funding',
  'subject': 'Synthetic support request',
  'status': 'open',
  'priority': 'normal',
  'version': version,
  'access': 'owner',
};
Map<String, dynamic> supportResourceJson() => {
  'id': supportItem,
  'kind': 'funding',
  'locale': 'ta',
  'state': 'published',
  'title': 'சோதனை நிதி',
  'provider': 'Synthetic provider',
  'description': 'Synthetic resource',
  'eligibility': 'Official criteria',
  'benefits': 'Official support',
  'sector': 'Food',
  'geography': 'Tamil Nadu',
  'application_process': 'Official process',
  'official_url': 'https://example.org/funding',
  'availability': 'open',
  'contact': '',
  'tags': ['enterprise'],
  'documents': ['Business registration'],
  'last_verified_at': '2026-10-20',
  'opens_on': null,
  'closes_on': null,
  'funding_amount_min': '100.01',
  'funding_amount_max': '200.02',
};
Map<String, dynamic> supportFundingJson() => {
  'id': supportCase,
  'item_id': supportItem,
  'item_title': 'சோதனை நிதி',
  'status': 'interested',
  'version': 1,
  'source': supportResourceJson(),
  'history': [
    {
      'status': 'interested',
      'reason': 'Synthetic interest',
      'created_at': '2026-10-20T10:00:00Z',
    },
  ],
};
Map<String, dynamic> supportMentoringJson() => {
  'assignments': [
    {
      'id': supportAssignment,
      'mentor_name': 'Synthetic mentor',
      'state': 'active',
      'starts_on': '2026-10-20',
      'ends_on': null,
    },
  ],
  'sessions': [
    {
      'id': supportSession,
      'assignment_id': supportAssignment,
      'topic': 'Customer discovery',
      'status': 'completed',
      'mode': 'phone',
      'location_or_link': null,
      'starts_at': '2026-10-20T10:00:00Z',
      'ends_at': '2026-10-20T11:00:00Z',
    },
  ],
  'notes': [
    {
      'assignment_id': supportAssignment,
      'body': 'Synthetic shared guidance',
      'visibility': 'shared_with_participant',
    },
  ],
  'goals': <Object>[],
  'action_items': <Object>[],
  'follow_ups': <Object>[],
  'feedback': <Object>[],
};

class SupportFixtureApi extends DomainApi {
  final AuthRepository identity;
  SupportFixtureApi._(this.identity) : super(identity);
  factory SupportFixtureApi() =>
      SupportFixtureApi._(AuthRepository(Dio(), ApiMemoryStore()));
  ApiFailure? readFailure, writeFailure;
  bool lostPlan = false, lostCreate = false;
  int writes = 0, planVersion = 1;
  final List<Object?> bodies = [];
  final List<Map<String, dynamic>?> queries = [];

  @override
  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    queries.add(queryParameters);
    if (readFailure != null) throw readFailure!;
    if (path.contains('/business-plans/')) {
      return {
        'entries': [
          {
            'enrollment_id': supportEnrollment,
            'program_id': supportOrg,
            'plan': supportPlanJson(version: planVersion),
          },
        ],
      };
    }
    if (path.endsWith('/my-mentoring')) return supportMentoringJson();
    if (path.endsWith('/catalog')) {
      return {
        'items': [supportResourceJson()],
        'next_cursor': null,
      };
    }
    if (path.contains('/knowledge/') && path.endsWith('/mine')) {
      return {
        'saved_items': <Object>[],
        'interests': <Object>[],
        'funding_cases': [supportFundingJson()],
        'next_saved_cursor': supportItem,
        'next_interest_cursor': supportAssignment,
        'next_case_cursor': supportCase,
      };
    }
    if (path.endsWith('/files')) {
      return {
        'collection_enabled': false,
        'max_upload_bytes': 0,
        'policy': null,
        'items': <Object>[],
        'next_cursor': null,
      };
    }
    if (path.endsWith('/preference')) return {'enabled': true, 'version': 1};
    if (path.endsWith('/notices')) {
      return {'items': <Object>[], 'next_cursor': null};
    }
    if (path.endsWith('/messages')) {
      return {
        'items': [
          {
            'id': supportSession,
            'body': 'Synthetic shared message',
            'internal': false,
            'created_at': '2026-10-20T10:00:00Z',
            'attachments': <Object>[],
            'files': <Object>[],
          },
        ],
        'next_cursor': null,
      };
    }
    if (path.endsWith('/history')) {
      return {
        'items': [
          {
            'event': 'created',
            'status': 'open',
            'version': 1,
            'reason': null,
            'created_at': '2026-10-20T10:00:00Z',
          },
        ],
        'next_cursor': null,
      };
    }
    if (path.endsWith('/tickets')) {
      return {
        'items': [supportTicketJson()],
        'next_cursor': null,
      };
    }
    if (path.endsWith('/$supportTicket')) return supportTicketJson();
    throw StateError('Unexpected synthetic read');
  }

  @override
  Future<dynamic> post(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    writes++;
    bodies.add(data);
    if (writeFailure != null) throw writeFailure!;
    if (path.contains('/business-plans/')) {
      planVersion++;
      if (lostPlan) {
        lostPlan = false;
        throw const ApiFailure(
          'timeout',
          kind: ApiFailureKind.timeout,
          outcome: CommandOutcome.uncertain,
        );
      }
      return supportPlanJson(version: planVersion);
    }
    if (path.endsWith('/feedback')) {
      return {
        'session_id': supportSession,
        'rating': 5,
        'comment': 'Synthetic feedback',
      };
    }
    if (path.endsWith('/tickets')) {
      if (lostCreate) {
        lostCreate = false;
        throw const ApiFailure(
          'timeout',
          kind: ApiFailureKind.timeout,
          outcome: CommandOutcome.uncertain,
        );
      }
      return supportTicketJson();
    }
    throw StateError('Unexpected synthetic write');
  }
}
