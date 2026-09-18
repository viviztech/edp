# CODEX MASTER INPUT --- Entrepreneurship Development Program (EDP) Digital Platform

**Project owner / client:** Center for Social Justice and Equity\
**Development approach:** Agile SDLC, modular monolith first, API-first\
**Primary backend:** FastAPI / Python --- STRICT: do not introduce
Laravel, PHP, Filament, or WordPress\
**Primary database:** PostgreSQL\
**Web:** Next.js + TypeScript\
**Mobile:** Flutter + Dart, one app serving public users, applicants,
enrolled students, alumni, and mentors where permitted\
**Target:** Production-ready web + mobile ecosystem within the approved
project scope and budget.

------------------------------------------------------------------------

## 0. HOW CODEX MUST USE THIS FILE

You are the senior solution architect, technical lead, backend engineer,
frontend engineer, Flutter engineer, DevOps engineer, QA engineer,
security reviewer, and documentation owner for this project.

Treat this file as the master implementation specification. Work
incrementally and keep the repository runnable after every milestone.

### Mandatory operating rules

1.  Do not replace the FastAPI/Python architecture with Laravel, PHP,
    Django, Firebase-as-backend, Supabase-as-backend, or another primary
    backend.
2.  Do not attempt to generate the whole project in one uncontrolled
    pass.
3.  Start by auditing the repository. If it is empty, initialize the
    structure defined below.
4.  Before coding a milestone, write/update the milestone plan and
    acceptance criteria in `/docs/sdlc/`.
5.  Implement database migrations, API, tests, permissions, audit
    logging, documentation, and UI together for each completed vertical
    slice.
6.  Never hard-code secrets, tokens, passwords, API keys, Meta
    credentials, Firebase credentials, database passwords, encryption
    keys, or production URLs.
7.  Use environment variables and provide safe `.env.example` files.
8.  Never commit `.env`, private keys, service-account JSON, production
    dumps, uploaded identity documents, or user data.
9.  Use UUID primary identifiers for externally exposed business
    entities unless a justified internal integer key is more
    appropriate.
10. Use UTC in storage. Convert to the user's configured/local timezone
    at presentation boundaries.
11. Use database transactions for multi-record business operations.
12. Use idempotency for webhooks, payment-like operations if later
    added, bulk imports, notification jobs, and other retryable
    integrations.
13. Validate all API input with Pydantic.
14. Enforce authorization on the server; hiding a button in the UI is
    not authorization.
15. Use Alembic for every schema change. Never modify production schema
    manually.
16. Add automated tests for every critical workflow.
17. Avoid premature microservices. Build a well-separated modular
    monolith first. Extract a service only when operational evidence
    justifies it.
18. Do not invent third-party API capabilities. Create provider
    interfaces/adapters where credentials or final vendors are not yet
    confirmed.
19. All external integrations must support graceful failure, retries
    where safe, structured logging, and administrative visibility.
20. Keep English/Tamil localization capability in the architecture from
    the start.
21. Meet WCAG-oriented accessibility practices for public web and key
    authenticated interfaces.
22. Treat applicant/student information as sensitive. Apply least
    privilege, data minimization, secure file access, and auditability.
23. Generate OpenAPI documentation from FastAPI and keep business
    documentation in `/docs`.
24. At the end of each milestone, run linting, type checks, tests,
    migration checks, and builds. Fix failures before marking it
    complete.
25. Do not mark a feature complete merely because endpoints exist.
    Completion requires UI/API integration, authorization, validation,
    tests, documentation, and acceptance criteria.

------------------------------------------------------------------------

# 1. PRODUCT VISION

Build an end-to-end Entrepreneurship Development Program digital
ecosystem covering:

**Awareness → Marketing Lead → Registration → Application → Screening →
Selection → Enrollment → Training → Attendance → Assessment → Mentoring
→ Business Planning → Schemes/Funding/Opportunity Discovery → Business
Launch → Post-Training Support → Business Growth → Impact Measurement**

The platform is not only an LMS. It is a combined public information
platform, CRM, applicant management system, program management system,
LMS, entrepreneurship resource hub, mentoring platform, post-training
business-support platform, and impact-monitoring system.

------------------------------------------------------------------------

# 2. USER CHANNELS

## 2.1 Public Website

Public users must be able to: - Discover the program. - View
eligibility, benefits, curriculum, schedules, centers, FAQs, events,
news, success stories, resources, schemes and opportunities intended for
public visibility. - Submit enquiries. - Register/login. - Start and
submit a program application. - Track application status after
authentication. - Receive appropriate communications. - Install/open the
mobile app where applicable.

## 2.2 Administration Web Application

Authorized staff use a secure web application for: - CMS - CRM - Meta
lead management - Application processing - Selection - Program/batch
management - Student management - Trainers/mentors - LMS - Attendance -
Assessments - Certificates - Schemes/funding/opportunities - Helpdesk -
Business support - Impact tracking - Reports - Integrations -
Roles/permissions - Audit logs - System settings

## 2.3 Flutter Mobile App

Build one Flutter app with role/state-aware experiences.

### Public / Guest

-   Program discovery
-   News/events
-   Public resources
-   Public schemes/opportunities
-   FAQ/contact
-   Registration/login

### Applicant

-   Profile
-   Application form
-   Document upload
-   Application progress
-   Interview/selection notifications
-   Status timeline

### Enrolled Student

-   Dashboard
-   Program/batch
-   Course/LMS
-   Lesson materials
-   Video links/streams
-   Quiz/assessment
-   Assignments
-   Attendance
-   Certificates
-   Mentor information
-   Business-plan builder
-   Schemes
-   Funding
-   Opportunities
-   Notifications
-   Helpdesk

### Alumni / Entrepreneur

-   Business profile
-   Post-training follow-ups
-   Mentoring
-   Funding/scheme tracking
-   Opportunities
-   Business-development tools
-   Support tickets
-   Outcome/impact updates

------------------------------------------------------------------------

# 3. APPROVED TECHNOLOGY STACK

## Backend

-   Python 3.13-compatible codebase
-   FastAPI
-   Pydantic v2
-   SQLAlchemy 2.x async patterns where appropriate
-   Alembic
-   PostgreSQL
-   Redis
-   Celery for durable background jobs and scheduled workloads
-   HTTPX for outbound HTTP
-   Structured logging
-   Pytest
-   Ruff
-   MyPy or Pyright-compatible typing discipline

## Web

-   Next.js
-   React
-   TypeScript strict mode
-   Tailwind CSS
-   Accessible component primitives
-   TanStack Query for server-state where useful
-   React Hook Form + schema-based validation
-   Internationalization supporting English and Tamil

## Mobile

-   Flutter
-   Dart
-   Riverpod or equivalent maintainable state-management pattern; use
    one consistently
-   Dio or equivalent API client
-   GoRouter or equivalent declarative navigation
-   Secure storage for tokens
-   Firebase Cloud Messaging for push notifications
-   Localization for English/Tamil
-   Offline-aware caching for appropriate read-only learning/resource
    content

## Data / Infrastructure

-   PostgreSQL
-   Redis
-   S3-compatible object storage
-   Docker
-   Docker Compose for local development
-   Nginx or equivalent reverse proxy in deployment
-   GitHub Actions CI/CD
-   Sentry-compatible error monitoring
-   Prometheus/Grafana-compatible observability when deployed at
    required scale

## Integrations

-   Meta Lead Ads / Graph API via official APIs and webhooks
-   WhatsApp Cloud API via official Meta APIs when approved
-   Transactional email provider through an adapter
-   SMS provider through an adapter
-   Firebase Cloud Messaging
-   S3-compatible storage
-   Optional analytics/BI adapter
-   AI provider adapter for future approved AI modules

------------------------------------------------------------------------

# 4. REPOSITORY ARCHITECTURE

Use a monorepo unless an existing repository imposes another justified
structure.

``` text
edp-platform/
├── apps/
│   ├── api/                  # FastAPI
│   ├── web/                  # Next.js public + authenticated web
│   └── mobile/               # Flutter
├── packages/
│   ├── api-contracts/        # generated/shared API schemas where practical
│   └── design-tokens/        # optional shared design definitions
├── infra/
│   ├── docker/
│   ├── nginx/
│   ├── monitoring/
│   └── deployment/
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── database/
│   ├── security/
│   ├── testing/
│   ├── deployment/
│   ├── user-guides/
│   └── sdlc/
├── scripts/
├── .github/workflows/
├── docker-compose.yml
├── .env.example
├── README.md
└── CODEX_MASTER_INPUT.md
```

FastAPI internal organization:

``` text
apps/api/app/
├── main.py
├── core/
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── logging.py
│   ├── exceptions.py
│   └── middleware.py
├── common/
│   ├── enums.py
│   ├── pagination.py
│   ├── responses.py
│   ├── storage.py
│   └── audit.py
├── modules/
│   ├── identity/
│   ├── users/
│   ├── organizations/
│   ├── cms/
│   ├── crm/
│   ├── applications/
│   ├── selection/
│   ├── programs/
│   ├── participants/
│   ├── lms/
│   ├── attendance/
│   ├── assessments/
│   ├── certificates/
│   ├── mentors/
│   ├── business_plans/
│   ├── schemes/
│   ├── funding/
│   ├── opportunities/
│   ├── businesses/
│   ├── support/
│   ├── communications/
│   ├── integrations/
│   ├── impact/
│   ├── reports/
│   └── system/
├── workers/
├── tests/
└── migrations/
```

Each business module should preferably contain its own models, schemas,
repository/data-access layer, service/business layer, routes,
permissions and tests rather than placing all models/routes in giant
global files.

------------------------------------------------------------------------

# 5. IDENTITY, AUTHENTICATION AND AUTHORIZATION

Implement: - Email and/or mobile-number based account model. - Password
hashing using a modern recommended password-hashing algorithm/library. -
Access token + refresh-token flow suitable for web/mobile. -
Refresh-token rotation/revocation. - Logout from current device and
optionally all devices. - Password reset. - Email/mobile verification
interfaces; actual provider can be adapter-driven. - Account status:
pending, active, suspended, archived. - Device/session visibility where
practical. - Rate limiting on authentication endpoints. - Brute-force
protections. - Optional MFA architecture for privileged administrators.

Roles should be configurable, with initial roles: - Super Admin -
Program Director - Program Manager - CRM Executive - Marketing
Executive - Selection Committee - Trainer - Mentor - Training Center
Coordinator - Funding Coordinator - Content Manager - Support
Executive - Participant

Use permissions rather than hard-coding role checks throughout business
logic.

Examples: - cms.page.view/create/update/publish -
crm.lead.view/create/update/assign/export -
application.view/review/shortlist/reject -
selection.score/manage/finalize - participant.view/update -
lms.course.manage - attendance.manage - assessment.manage -
certificate.issue - scheme.manage - funding.manage -
opportunity.manage - mentor.manage - business.support -
report.view/export - system.manage - audit.view

Create permission middleware/dependencies and automated authorization
tests.

------------------------------------------------------------------------

# 6. CMS MODULE

Entities: - Page - Menu - MenuItem - Banner - FAQ - NewsArticle -
Event - Testimonial - MediaAsset - Download/Resource -
ContactSubmission - SEO metadata - Translation/localized content

Requirements: - Draft/published/archived lifecycle. - Slugs. - Scheduled
publishing if feasible. - SEO title, description, canonical metadata. -
English/Tamil localized fields. - Media library using object storage. -
Public APIs with caching. - Admin preview. - Audit history for content
changes.

Public pages: - Home - About - Eligibility - Benefits - Training
Structure - Mentors - Success Stories - Resources - Schemes - Funding
Opportunities - Events - News - FAQ - Contact - Apply

------------------------------------------------------------------------

# 7. CRM + META LEAD MANAGEMENT

CRM entities: - Lead - LeadSource - Campaign - LeadActivity - LeadNote -
LeadAssignment - LeadTag - FollowUp - CommunicationLog - Conversion

Lead lifecycle: NEW → CONTACTED → INTERESTED → REGISTRATION_STARTED →
APPLICATION_SUBMITTED → QUALIFIED / NOT_QUALIFIED → CONVERTED

Capture attribution fields when supplied: - platform - source -
campaign_id/name - adset_id/name - ad_id/name - form_id/name -
meta_lead_id - UTM source/medium/campaign/content/term - landing page -
referral - received_at

Meta integration: - Webhook verification endpoint. - Secure webhook
processing. - Store raw event metadata safely for troubleshooting, with
retention policy. - Idempotency using provider event/lead identifiers. -
Fetch permitted lead details from Meta using server-side credentials. -
Map form fields through configurable mappings. - Create/update CRM
lead. - Trigger follow-up automation. - Record integration failures and
retry safely. - Admin integration-health page. - Do not expose Meta
tokens to browser/mobile.

CRM features: - Search/filter/sort. - Assignment. - Notes. -
Tasks/follow-ups. - Status changes. - Activity timeline. - Bulk actions
with authorization. - CSV export only for authorized users and
audited. - Duplicate detection based on normalized phone/email. -
Conversion from lead to applicant without losing attribution.

------------------------------------------------------------------------

# 8. REGISTRATION AND APPLICATION

Application should support: - Save as draft. - Multi-step form. -
Completion percentage. - Eligibility questions. - Personal/contact
details. - Address/location. - Education. - Employment/current
occupation. - Entrepreneurship interest. - Existing business details if
applicable. - Proposed business idea. - Sector/category. - Experience. -
Investment/funding requirement. - Training-center preference if
applicable. - Required declarations/consents. - Configurable supporting
documents. - Final declaration and submission. - Immutable submitted
snapshot or versioned history for reviewed data. - Application number
generation.

Statuses: DRAFT → SUBMITTED → UNDER_REVIEW → SHORTLISTED →
INTERVIEW_SCHEDULED → SELECTED / WAITLISTED / REJECTED → ENROLLED

Rules: - Prevent accidental duplicate submissions. - Allow controlled
reopening only by authorized staff. - Keep status history. - Store
reviewer notes separately from applicant-visible comments. - Log every
consequential decision.

------------------------------------------------------------------------

# 9. SELECTION MANAGEMENT

Create configurable selection cycles.

Features: - Eligibility rules. - Review queues. - Reviewer assignment. -
Scoring rubrics. - Weighted criteria. - Interview scheduling. - Panel
members. - Interview scoring. - Comments. - Shortlist/waitlist. -
Conflict/override handling by authorized users. - Finalization with
audit trail. - Bulk selection communication. - Automatic participant
creation after enrollment approval.

Default example rubric, configurable: - Business idea: 20 -
Entrepreneurial interest: 20 - Feasibility: 20 - Market potential: 15 -
Social/economic impact: 15 - Interview: 10

Do not hard-code the rubric; store criteria and weights in database
tables.

------------------------------------------------------------------------

# 10. PROGRAM, COHORT AND PARTICIPANT MANAGEMENT

Entities: - Program - Cohort/Batch - TrainingCenter - Session -
Trainer - Participant - Enrollment - ParticipantStatus - ProgramCalendar

Support multiple programs and batches.

Participant timeline should aggregate: - original lead - application -
selection - enrollment - attendance - learning progress - assessments -
mentoring - business plan - funding activity - business outcomes -
support interactions

Do not duplicate person data unnecessarily across
CRM/applicant/participant tables. Design a normalized identity/person
strategy and preserve lifecycle links.

------------------------------------------------------------------------

# 11. LMS

Entities: - Course - CourseModule - Lesson - LessonMaterial -
Enrollment - LessonProgress - CourseProgress - Assignment - Submission -
Quiz - Question - Choice - QuizAttempt - Assessment - Grade -
CertificateTemplate - Certificate

Features: - Course ordering. - Prerequisites where configured. -
Text/video/document lessons. - Signed/private media URLs. - Completion
tracking. - Quiz attempts. - Assignment upload. - Trainer review. -
Scores/feedback. - Course completion rules. - Certificate eligibility. -
Certificate generation with unique verification identifier/QR. - Public
certificate verification endpoint exposing only safe fields. - Progress
reports. - English/Tamil content support.

Do not build a video streaming platform from scratch. Integrate
object/video hosting through an abstraction.

------------------------------------------------------------------------

# 12. ATTENDANCE

Implement: - Program session attendance. - Manual trainer/admin
marking. - Time-limited QR check-in. - Unique session token. - Check-in
window. - Duplicate prevention. - Optional location policy as a
future/configurable feature; do not collect precise location by
default. - Present/Absent/Late/Excused statuses. - Correction workflow
with reason and audit trail. - Attendance percentage. - Low-attendance
alerts based on configurable thresholds. - Reports by
participant/session/batch/program.

------------------------------------------------------------------------

# 13. MENTORING

Entities: - MentorProfile - Expertise - MentorAvailability -
MentorAssignment - MentoringSession - MentoringNote - ActionItem -
Goal - FollowUp

Features: - Match/assign mentor. - Schedule sessions. - Notes with
visibility controls. - Goals/actions. - Progress. - Follow-up
reminders. - Participant feedback. - Admin monitoring.

------------------------------------------------------------------------

# 14. BUSINESS PLAN BUILDER

Create a structured, versioned business-plan workflow: - Executive
summary - Problem - Solution - Product/service - Customer segments -
Market - Competition - Value proposition - Business model - Pricing -
Sales/marketing - Operations - Team - Investment - Revenue assumptions -
Expense assumptions - Break-even inputs - Funding requirement - Risks -
Milestones

Features: - Autosave/draft. - Section completion. - Mentor comments. -
Version history. - Approval/review state. - PDF export later through a
server-side document-generation service. - Do not provide financial
claims as guarantees.

------------------------------------------------------------------------

# 15. SCHEMES, FUNDING AND OPPORTUNITIES

## Schemes

Fields: - title - provider/department - type - description -
eligibility - benefits - geography - target sector - application
process - documents - official source URL - opening/closing dates -
status - tags - language - last_verified_at

## Funding Agencies / Programs

-   organization
-   funding type
-   amount/range if officially supplied
-   eligibility
-   sectors
-   geography
-   documents
-   process
-   official source
-   contact/reference information
-   dates/status

## Participant Funding Tracker

INTERESTED → ELIGIBILITY_CHECK → DOCUMENT_PREPARATION → APPLIED →
UNDER_REVIEW → APPROVED / REJECTED → DISBURSED

## Opportunities

Support: - tenders - procurement - exhibitions - trade fairs -
buyer-seller meetings - incubation - accelerators - competitions -
dealership/franchise information - networking events

Include bookmarks/saved items and expressions of interest.

Future recommendation engine should be isolated behind a service
interface. Initial release can use deterministic filters/rules.

------------------------------------------------------------------------

# 16. POST-TRAINING BUSINESS SUPPORT

Business profile: - business name - owner/participant - sector -
products/services - business stage - registration information - start
date - team size - investment - funding status - sales/revenue bands
rather than unnecessarily precise data where possible - support needs -
public visibility opt-in

Follow-up cycles should be configurable; default examples: - 30 days -
90 days - 6 months - 12 months - 24 months

Track: - business started - business active - jobs created - funding
facilitated - market linkages - sales/revenue bands - challenges -
support requested - mentor interventions - outcomes

Preserve historical snapshots so impact reports can compare periods.

------------------------------------------------------------------------

# 17. DIGITAL BUSINESS TOOLS

Build as staged modules, not all in MVP.

Priority tools: 1. Business profile builder. 2. Digital visiting card.
3. Product/service catalogue. 4. Quotation generator. 5. Basic invoice
generator. 6. Customer/lead mini-CRM. 7. Expense/revenue tracker. 8.
Marketing campaign planner. 9. Social content planner. 10. Marketing
creative/template library.

Keep accounting/invoicing features appropriately scoped; do not claim
statutory/accounting compliance without explicit requirements and
validation.

------------------------------------------------------------------------

# 18. HELPDESK

Entities: - Ticket - TicketCategory - TicketMessage - TicketAttachment -
TicketAssignment - SLA/Priority - StatusHistory

Categories: - Funding - Registration - Tax/compliance guidance -
Marketing - Technology - Business planning - Banking - Mentoring -
General

Workflow: OPEN → ASSIGNED → IN_PROGRESS → WAITING_FOR_USER → RESOLVED →
CLOSED

Add notifications and complete audit history.

------------------------------------------------------------------------

# 19. COMMUNICATION AND AUTOMATION

Channels: - In-app - Push - Email - SMS - WhatsApp

Build a provider-neutral notification layer.

Entities: - NotificationTemplate - Notification - DeliveryAttempt -
CommunicationPreference - AutomationRule - AutomationExecution

Example events: - lead.created - registration.started -
application.submitted - application.shortlisted - interview.scheduled -
applicant.selected - enrollment.created - training.session.upcoming -
attendance.low - assignment.due - course.completed -
certificate.issued - mentor.session.upcoming - followup.due -
funding.status_changed - ticket.updated

Background workers must handle external delivery.

Record: - provider - provider message id - queued/sent/delivered/failed
status where provider supports it - error - retry count - timestamps

Honor communication consent/preferences and required transactional
exceptions.

------------------------------------------------------------------------

# 20. REPORTS AND IMPACT ANALYTICS

Dashboards:

## Marketing

-   Leads by source/campaign.
-   Registrations.
-   Applications.
-   Lead-to-application conversion.
-   Application-to-selection conversion.
-   Selection-to-enrollment conversion.
-   Campaign attribution where data exists.

## Program

-   Enrollments.
-   Active participants.
-   Attendance.
-   Dropouts.
-   Completion.
-   Certificates.

## Learning

-   Course progress.
-   Assessment results.
-   Assignment completion.

## Entrepreneurship

-   Business ideas.
-   Business plans.
-   Businesses started.
-   Businesses active.
-   Business growth snapshots.
-   Jobs created.

## Funding

-   Applications.
-   Approvals.
-   Disbursements where recorded.
-   Funding facilitated.

## Support

-   Tickets.
-   Resolution time.
-   Mentor sessions.
-   Follow-ups.

## Impact

Participant lifecycle: APPLICANT → TRAINEE → CERTIFIED →
ASPIRING_ENTREPRENEUR → BUSINESS_STARTED → BUSINESS_OPERATIONAL →
BUSINESS_GROWING → EMPLOYMENT_GENERATOR

Reports must clearly define numerator/denominator, period, cohort and
filters. Avoid ambiguous KPIs.

Exports: - CSV - XLSX/PDF only where required and generated server-side
with access controls - Every sensitive export must be
permission-protected and auditable.

------------------------------------------------------------------------

# 21. MOBILE APP UX

Use one app with progressive access.

Navigation should change based on authentication and lifecycle state.

### Guest tabs

Home \| Programs \| Opportunities \| Resources \| Account

### Applicant tabs

Home \| Application \| Updates \| Resources \| Profile

### Student tabs

Home \| Learn \| Opportunities \| Support \| Profile

Student home cards: - Today's sessions - Attendance - Continue
learning - Pending assignments - Mentor - Business plan progress -
Recommended schemes/opportunities - Notifications

Requirements: - Deep links. - Push notification routing. - Secure token
storage. - Refresh-token handling. - Offline-safe retry for
non-destructive actions. - Cached read-only resources. - No sensitive
documents in unencrypted app cache. - App version/update policy
endpoint. - Error/empty/loading states. - Accessibility and scalable
text. - English/Tamil localization.

------------------------------------------------------------------------

# 22. WEB UX

Public web: - SEO-first server rendering. - Fast Core Web
Vitals-oriented implementation. - Mobile-first. - Accessible
navigation. - Clear Apply CTA. - Landing-page support for Meta
campaigns. - Structured metadata. - Sitemap/robots. - Consent-aware
analytics.

Admin: - Responsive desktop-first operations UI. - Dashboard. - Data
tables with server-side pagination/filter/sort. - Saved filters if
useful. - Bulk actions guarded by permissions. - Record detail
timelines. - Form autosave only where safe. - Confirmation for
destructive/consequential actions. - Audit history links for privileged
users.

------------------------------------------------------------------------

# 23. DATABASE DESIGN PRINCIPLES

Before implementing modules: 1. Produce `/docs/database/erd.md`. 2.
Produce Mermaid ER diagrams by domain. 3. Define unique constraints and
indexes. 4. Define soft-delete/archive policy per entity. 5. Define
retention requirements. 6. Define ownership and foreign-key delete
behavior. 7. Avoid JSON blobs for relational data merely to save time.
8. Use JSONB only for genuinely dynamic provider payloads/configuration.
9. Index common filters, foreign keys and unique external identifiers.
10. Use optimistic concurrency/version fields for workflows where
concurrent editing is likely. 11. Use created_at/updated_at consistently
and created_by/updated_by where audit requirements justify them.

------------------------------------------------------------------------

# 24. API STANDARDS

Prefix: `/api/v1`

Example route groups: - /auth - /public - /cms - /crm - /applications -
/selection - /programs - /participants - /courses - /attendance -
/assessments - /certificates - /mentors - /business-plans - /schemes -
/funding - /opportunities - /businesses - /support - /notifications -
/reports - /integrations - /system

Standards: - Consistent response/error envelope where useful. - Correct
HTTP status codes. - Pagination. - Filtering/sorting. - Request
correlation ID. - OpenAPI tags. - Examples for complex schemas. -
Idempotency key support where required. - API versioning. - Rate limits
by endpoint sensitivity. - Never leak stack traces or secrets. -
Explicit CORS configuration. - Secure upload validation. - Signed URLs
for private files.

Generate an API client for web/mobile when practical rather than
manually duplicating every contract.

------------------------------------------------------------------------

# 25. SECURITY BASELINE

Implement: - OWASP-oriented secure defaults. - TLS-only production. -
Secure headers. - Strict CORS. - CSRF protection for cookie-based
browser flows if used. - XSS-safe rendering. - SQL injection protection
through ORM/parameterized queries. - SSRF protections for server-side
URL fetches. - File type/size validation. - Malware-scanning
hook/interface for uploads if required. - Private bucket by default. -
Signed expiring file URLs. - Rate limiting. - Login throttling. -
Password reset token expiration. - Refresh-token revocation. - Secrets
management. - Least privilege DB/cloud credentials. - Audit logs. -
Admin security events. - Data export auditing. - Backup and restore
procedure. - Dependency scanning. - Container image scanning in CI where
available. - No sensitive values in logs. - PII masking in diagnostic
logs. - Consent and privacy fields. - Data deletion/anonymization
workflow based on approved policy. - Security review before production.

Never implement custom cryptographic algorithms.

------------------------------------------------------------------------

# 26. TESTING STRATEGY

Backend: - Unit tests for business services. - API integration tests. -
Database tests. - Permission tests. - Workflow/state-transition tests. -
Webhook idempotency tests. - Background-job tests. - Upload/security
tests.

Web: - Component tests for critical UI. - Integration tests. -
End-to-end tests for critical journeys.

Flutter: - Unit tests. - Widget tests. - Integration tests for critical
journeys.

Required E2E journeys: 1. Public user → registration → application
submission. 2. Meta webhook → CRM lead → applicant conversion. 3.
Reviewer → shortlist → interview → selection. 4. Selected applicant →
enrollment → participant login. 5. Student → lesson → quiz/assignment →
progress. 6. Trainer → attendance session → student QR check-in. 7.
Mentor assignment → session → action item. 8. Student → business plan →
mentor review. 9. Student → funding tracker. 10. Alumni → business
follow-up. 11. Support ticket lifecycle. 12. Admin → CMS publish →
public page. 13. Unauthorized user attempts protected action and is
denied. 14. Sensitive export is permission checked and audited.

CI quality gate: - Backend lint. - Backend type check. - Backend
tests. - Migration validation. - Web lint/type check/test/build. -
Flutter analyze/test/build check where CI environment permits. - Secret
scan. - Dependency/security scan where configured.

------------------------------------------------------------------------

# 27. OBSERVABILITY

Implement: - Structured JSON production logs. - Correlation/request
IDs. - Error tracking. - Health endpoint. - Readiness endpoint. -
Database health. - Redis health. - Worker health. - Integration
health. - Job failure visibility. - Metrics hooks. - Audit trail
separate from debug logs.

Do not expose internal health details publicly without protection.

------------------------------------------------------------------------

# 28. BACKUP / DISASTER RECOVERY

Document: - PostgreSQL automated backups. - Retention. - Point-in-time
recovery if infrastructure supports it. - Object-storage
versioning/backup policy. - Restore test procedure. - RPO/RTO targets to
be confirmed with client. - Incident-response contacts/process
placeholders. - Recovery runbook.

A backup is not considered complete until restore has been tested in
staging.

------------------------------------------------------------------------

# 29. ENVIRONMENTS

Maintain: - Local - Test/CI - Staging - Production

Each must have separate credentials and data.

Never copy production personal data into local development without
approved anonymization.

Provide seed data for development/testing: - roles - permissions -
sample program - sample batch - sample courses - sample CMS content -
synthetic leads/applicants/participants

No real participant data in repository fixtures.

------------------------------------------------------------------------

# 30. AGILE SDLC EXECUTION PLAN

Use two-week sprints where practical.

## Phase 0 --- Discovery & Requirements

Deliver: - Product requirements. - Personas. - User journeys. -
Functional requirements. - Non-functional requirements. - Data/privacy
inventory. - Integration inventory. - Acceptance criteria. -
Risks/assumptions/dependencies. - MVP vs Phase 2 classification.

## Phase 1 --- Architecture & UX Foundation

Deliver: - Architecture decision records. - ERD. - API conventions. -
Repository. - Docker dev environment. - CI. - design system. - auth
skeleton. - RBAC. - audit framework. - localization framework.

## Phase 2 --- Public Website + CMS

Deliver: - CMS. - Public pages. - SEO. - media. - news/events/FAQ. -
contact. - admin publishing workflow.

## Phase 3 --- CRM + Meta

Deliver: - CRM. - lead attribution. - Meta webhook. - configurable form
mapping. - lead assignments/follow-ups. - communications foundation.

## Phase 4 --- Registration + Selection

Deliver: - applicant account. - multi-step application. - documents. -
review. - scoring. - interviews. - shortlist/select/waitlist/reject. -
enrollment conversion.

## Phase 5 --- Program + Participant Portal

Deliver: - programs/batches/centers. - participant profiles. -
calendars. - participant web dashboard. - mobile applicant/student
authentication and dashboard.

## Phase 6 --- LMS + Attendance

Deliver: - courses/modules/lessons. - progress. - quiz/assignment. -
attendance. - QR. - certificates. - Flutter learning experience.

## Phase 7 --- Mentoring + Business Plan

Deliver: - mentors. - assignments. - sessions. - goals/actions. -
business-plan builder. - mentor review.

## Phase 8 --- Schemes + Funding + Opportunities

Deliver: - repositories. - search/filter. - saved items. - funding
tracker. - mobile experiences.

## Phase 9 --- Post-Training + Helpdesk

Deliver: - business profiles. - periodic follow-ups. - support
tickets. - business outcome tracking.

## Phase 10 --- Reporting + Impact

Deliver: - operational dashboards. - impact dashboards. - exports. -
cohort/period filters. - data definitions.

## Phase 11 --- Business Tools

Deliver prioritized tools within remaining approved scope: -
profile/card/catalogue. - quotation. - mini CRM. - expense/revenue
tracker. - marketing planner.

## Phase 12 --- Hardening & Launch

Deliver: - security review. - performance testing. - accessibility
review. - backup/restore test. - production deployment. - monitoring. -
admin training. - user documentation. - handover. - stabilization.

------------------------------------------------------------------------

# 31. MVP PRIORITY WITH ₹10 LAKH PROJECT CEILING

Engineering decisions must respect the approved overall project ceiling.
Avoid expensive unnecessary infrastructure or over-engineering.

### P0 --- must launch

-   Architecture/security foundation.
-   Public website.
-   CMS.
-   CRM.
-   Meta lead capture.
-   Registration/application.
-   Selection.
-   Program/batch/participant management.
-   Flutter public/applicant/student app.
-   LMS essentials.
-   Attendance.
-   Assessments.
-   Certificates.
-   Mentoring essentials.
-   Schemes/funding/opportunities repository.
-   Notifications foundation.
-   Helpdesk.
-   Core reports.
-   Impact baseline.
-   Deployment, testing, training, documentation.

### P1 --- deliver if included in final contracted scope/time

-   Business plan builder.
-   Post-training business profiles/follow-ups.
-   Advanced dashboards.
-   Digital visiting card.
-   Catalogue.
-   Quotation tool.
-   Mini CRM.

### P2 --- future enhancement

-   Advanced AI.
-   Intelligent recommendation engine.
-   Advanced marketing automation.
-   Advanced financial tools.
-   Marketplace.
-   Complex BI/data warehouse.
-   Microservices decomposition.
-   Advanced offline LMS.
-   Additional third-party integrations.

Never sacrifice security, tests, backup, authorization, auditability or
core workflow correctness to fit P1/P2 features.

------------------------------------------------------------------------

# 32. BUDGET-AWARE ENGINEERING RULES

To stay within the ₹10 lakh development ceiling: - Prefer open-source
components with mature ecosystems. - Use modular monolith. - One Flutter
app. - One Next.js application capable of serving
public/authenticated/admin areas with clear authorization boundaries,
unless separation is justified. - One PostgreSQL cluster initially. -
One Redis deployment initially. - S3-compatible storage. - Avoid
Kubernetes for initial launch. - Avoid Kafka unless actual throughput
proves it necessary. - Avoid Elasticsearch/OpenSearch initially unless
PostgreSQL search is insufficient; Meilisearch may be introduced only
when justified. - Avoid building video infrastructure. - Avoid custom
chat infrastructure. - Avoid unnecessary microservices. - Use provider
adapters so paid services can be chosen later. - Keep cloud architecture
horizontally upgradeable.

Track external recurring costs separately: - hosting/cloud -
object/video storage - domain/DNS - email/SMS/WhatsApp - Meta
advertising spend - Apple/Google developer accounts - monitoring
services - AI API usage These are operational costs, not to be silently
treated as development budget.

------------------------------------------------------------------------

# 33. PERFORMANCE TARGETS

Initial targets, validate during architecture: - Public pages optimized
for fast mobile loading. - Standard authenticated API reads target
low-latency under normal load. - Server-side pagination for large
datasets. - No unbounded list endpoints. - No N+1 database queries in
high-use endpoints. - Cache public/reference data where safe. - Move
slow external calls to jobs. - Database indexes verified with query
plans for high-volume reports. - Load-test critical endpoints before
launch.

Do not invent an unsupported concurrency number. Establish capacity
through load testing.

------------------------------------------------------------------------

# 34. DOCUMENTATION REQUIRED

Maintain: - `/README.md` - `/docs/product-requirements.md` -
`/docs/architecture/system-architecture.md` -
`/docs/architecture/adr/` - `/docs/database/erd.md` -
`/docs/api/api-guidelines.md` - `/docs/security/security-model.md` -
`/docs/security/privacy-data-inventory.md` -
`/docs/testing/test-strategy.md` - `/docs/deployment/local.md` -
`/docs/deployment/staging.md` - `/docs/deployment/production.md` -
`/docs/deployment/backup-restore.md` - `/docs/integrations/meta.md` -
`/docs/integrations/notifications.md` -
`/docs/mobile/mobile-architecture.md` - `/docs/sdlc/backlog.md` -
`/docs/sdlc/definition-of-done.md` - `/docs/sdlc/release-checklist.md` -
`/docs/user-guides/admin.md` - `/docs/user-guides/participant.md`

------------------------------------------------------------------------

# 35. DEFINITION OF DONE

A feature is done only when: - Requirements and acceptance criteria
exist. - Database migration exists where required. - Backend
implementation is complete. - Validation is complete. - Permissions are
complete. - Audit behavior is complete where required. - Web/mobile UI
is complete for the scoped channel. - Loading/error/empty states
exist. - Tests pass. - Localization keys are used. - API docs are
correct. - Security implications reviewed. - No secrets committed. -
Logging/monitoring added where needed. - Documentation updated. - CI
passes. - Product workflow has been manually smoke-tested.

------------------------------------------------------------------------

# 36. INITIAL DATABASE DOMAIN MODEL

Do not blindly create all tables immediately. Validate the ERD first.
Expected domain entities include:

Identity: User, UserProfile, Role, Permission, UserRole, RolePermission,
RefreshSession, VerificationToken

Organization/System: Organization, TrainingCenter, SystemSetting,
AuditLog, IntegrationConfig

CMS: Page, PageTranslation, Menu, MenuItem, Banner, FAQ, NewsArticle,
Event, Testimonial, MediaAsset, ContactSubmission

CRM: Lead, LeadSource, Campaign, LeadActivity, LeadNote, LeadAssignment,
FollowUp, LeadTag, CommunicationLog

Application: Application, ApplicationSection, ApplicationDocument,
ApplicationStatusHistory, EligibilityResponse, Consent

Selection: SelectionCycle, SelectionCriterion, ReviewAssignment,
ApplicationScore, Interview, InterviewPanelMember, SelectionDecision

Program: Program, Cohort, ProgramSession, TrainerProfile, Enrollment

Participant: ParticipantProfile, ParticipantStatusHistory

LMS: Course, CourseModule, Lesson, LessonMaterial, CourseEnrollment,
LessonProgress, Quiz, Question, Choice, QuizAttempt, Assignment,
Submission, Assessment, Grade, Certificate

Attendance: AttendanceSession, AttendanceRecord, AttendanceCorrection

Mentoring: MentorProfile, MentorExpertise, MentorAssignment,
MentoringSession, MentoringNote, Goal, ActionItem

Business Plan: BusinessPlan, BusinessPlanVersion, BusinessPlanSection,
MentorReview

Knowledge: Scheme, FundingAgency, FundingProgram, Opportunity, SavedItem

Funding: ParticipantFundingCase, FundingStatusHistory

Business: BusinessProfile, BusinessProductService,
BusinessProgressSnapshot, BusinessSupportNeed

Support: Ticket, TicketCategory, TicketMessage, TicketAttachment,
TicketAssignment, TicketStatusHistory

Notifications: NotificationTemplate, Notification, DeliveryAttempt,
CommunicationPreference, AutomationRule, AutomationExecution

Impact: ImpactIndicator, ParticipantImpactRecord, CohortImpactSnapshot

------------------------------------------------------------------------

# 37. CRITICAL STATE MACHINES

Implement state transitions in service layer and test them.

Application: DRAFT → SUBMITTED → UNDER_REVIEW → SHORTLISTED →
INTERVIEW_SCHEDULED → SELECTED \| WAITLISTED \| REJECTED → ENROLLED
(only from selected)

Lead: NEW → CONTACTED → INTERESTED → REGISTRATION_STARTED →
APPLICATION_SUBMITTED → QUALIFIED \| NOT_QUALIFIED → CONVERTED

Ticket: OPEN → ASSIGNED → IN_PROGRESS → WAITING_FOR_USER → RESOLVED →
CLOSED Allow controlled reopen.

Funding: INTERESTED → ELIGIBILITY_CHECK → DOCUMENT_PREPARATION → APPLIED
→ UNDER_REVIEW → APPROVED \| REJECTED → DISBURSED (from approved)

Do not permit arbitrary status mutation via generic CRUD.

------------------------------------------------------------------------

# 38. FIRST CODEX EXECUTION --- DO THIS NOW

When this file is first given to Codex, do **not** start by generating
hundreds of application files.

Perform the following in order:

### Step 1 --- Repository Audit

Report: - current repository structure - existing technologies -
existing code that can be retained - conflicts with this specification -
missing prerequisites - security concerns - assumptions requiring
confirmation

### Step 2 --- Create SDLC Documents

Create: - `docs/product-requirements.md` - `docs/sdlc/backlog.md` -
`docs/sdlc/definition-of-done.md` - `docs/sdlc/release-checklist.md` -
`docs/architecture/system-architecture.md` -
`docs/architecture/adr/0001-modular-monolith.md` -
`docs/database/erd.md` - `docs/security/security-model.md` -
`docs/testing/test-strategy.md`

### Step 3 --- Produce Backlog

Break the project into: - Epics - Features - User stories - Acceptance
criteria - Technical tasks - Dependencies - P0/P1/P2 priority -
Estimated complexity (S/M/L/XL, not invented monetary cost)

### Step 4 --- Architecture Review

Before implementation, show: - proposed monorepo tree - module
boundaries - identity model - RBAC model - data model - lifecycle
model - integration architecture - notification architecture -
deployment architecture - major risks

Record architecture decisions as ADRs.

### Step 5 --- Bootstrap

Only after the architecture documents are internally consistent: -
initialize FastAPI - initialize PostgreSQL/SQLAlchemy/Alembic -
initialize Redis/Celery - initialize Next.js - initialize Flutter -
create Docker Compose - create `.env.example` - create CI workflow - add
health/readiness endpoints - add code-quality configuration - add
initial tests

### Step 6 --- Implement Foundation Vertical Slice

Implement: - user model - authentication - refresh sessions - RBAC -
audit log - localization foundation - admin shell - public shell -
Flutter shell - OpenAPI/client strategy

### Step 7 --- Verify

Run: - backend lint/type/test - Alembic migration upgrade/downgrade
validation in test DB - web lint/type/test/build - Flutter
analyze/test - Docker Compose smoke test - secret scan if configured

Create `docs/sdlc/milestone-01-report.md` containing: - completed work -
tests - commands run - unresolved issues - security notes - next
milestone

Then stop and present the milestone report before moving to the next
major milestone.

------------------------------------------------------------------------

# 39. CODING STANDARDS

Python: - Type annotate public functions. - Async only where it provides
actual I/O benefit. - Keep route handlers thin. - Business rules in
services/domain layer. - Data access isolated. - Avoid circular
imports. - Central exception mapping. - Use timezone-aware datetimes. -
No `except Exception: pass`. - No silent failure. - No production
`print()` debugging. - Structured logs.

TypeScript: - Strict mode. - Avoid `any` unless documented. - Typed API
layer. - Server/client component boundaries intentional. - Reusable
forms/tables. - Authorization-aware UI, but backend remains
authoritative.

Flutter: - Feature-first organization. - Immutable state where
practical. - Repository/service layer for API. - Central auth/session
manager. - Central error mapping. - No secrets in application bundle. -
Environment/flavor configuration. - Consistent state-management library.

SQL: - Explicit constraints. - Meaningful indexes. - No destructive
migration without migration/rollback plan. - Avoid uncontrolled
cascades. - Explain complex queries.

------------------------------------------------------------------------

# 40. SOURCE CONTROL

Use: - `main` --- production-ready - `develop` --- integration if team
workflow needs it - feature branches: `feature/<name>` - fix branches:
`fix/<name>`

Commit messages should be descriptive.

Pull request checklist: - requirement linked - tests - migration
impact - security impact - screenshots for UI - API contract changes -
documentation - rollback consideration

Do not commit generated build directories or secrets.

------------------------------------------------------------------------

# 41. RELEASE GATES

Staging release requires: - CI green. - Migrations tested. -
Seed/synthetic data works. - Critical E2E flows pass. - No high-severity
known security issue. - Environment config validated.

Production release additionally requires: - Client-approved UAT. -
Backup enabled. - Restore procedure tested. - Monitoring enabled. -
Error tracking enabled. - DNS/TLS configured. - Meta webhook production
configuration validated. - Push notification production configuration
validated. - Admin accounts provisioned securely. - Privacy/consent copy
approved. - Operational runbook available. - Rollback plan available.

------------------------------------------------------------------------

# 42. NON-GOALS FOR INITIAL RELEASE

Unless explicitly added to scope, do not spend initial budget
building: - Custom video conferencing. - Custom email/SMS
infrastructure. - Full accounting/ERP. - Banking core integration. -
Payment gateway. - Blockchain. - Kubernetes. - Kafka. - Data
warehouse. - Native separate Android and iOS codebases. - Separate
public and student mobile apps. - Complex AI agents. - Automated
credit/funding decisions. - Biometric attendance. - Precise-location
attendance tracking. - Public social network/chat. - Full e-commerce
marketplace.

------------------------------------------------------------------------

# 43. FUTURE AI ARCHITECTURE

Prepare interfaces but do not make AI a blocking dependency.

Potential future modules: - Business idea assistant. - Business plan
drafting assistant. - SWOT assistant. - Marketing-plan assistant. -
Social content assistant. - Product-description assistant. - Pitch
assistant. - Scheme discovery assistant. - Funding matching. - Knowledge
assistant.

Rules: - AI output must be clearly treated as assistance, not guaranteed
business/legal/financial advice. - Keep provider behind an adapter. -
Never send unnecessary sensitive participant data to AI providers. - Add
consent/data controls before production AI use. - Human review for
consequential outputs.

------------------------------------------------------------------------

# 44. QUESTIONS / ASSUMPTIONS REGISTER

Do not block repository foundation on non-critical unknowns. Record them
in `docs/sdlc/open-questions.md`.

Key items to confirm: - Final organization spelling/branding and
official logo. - Exact program name. - Number of
programs/batches/centers expected. - Expected annual applicants and
participants. - Tamil required at launch or shortly after. - Final
application fields. - Selection rubric. - Required applicant
documents. - Communication providers. - WhatsApp approval/business
account. - Meta Business/App ownership and credentials. - Email
provider. - SMS provider. - Hosting/cloud provider. - Domain. - LMS
video hosting choice. - Certificate format/signatory workflow. -
Attendance policy. - Data retention/privacy policy. - Exact impact
indicators. - Funding/scheme data ownership and update responsibility. -
Whether mentor accounts require mobile access. - Whether business tools
are MVP or Phase 2. - Final UAT stakeholders.

For each unknown, create a safe configurable default or interface when
possible; do not fabricate organizational policy.

------------------------------------------------------------------------

# 45. FINAL PRODUCT ACCEPTANCE

The project is considered technically complete only when the agreed P0
scope can demonstrate this connected journey in staging/production-like
conditions:

1.  Staff publishes program content.
2.  Public user sees it on responsive website/mobile.
3.  Meta lead webhook creates an attributed CRM lead.
4.  Prospect registers and submits an application.
5.  Staff reviews and scores application.
6.  Interview/selection workflow completes.
7.  Selected applicant is enrolled.
8.  Participant signs into Flutter app.
9.  Participant sees batch/course schedule.
10. Participant completes learning activity.
11. Attendance is recorded.
12. Assessment/progress is stored.
13. Certificate can be issued when rules are met.
14. Mentor can be assigned and follow-up recorded.
15. Participant can discover schemes/funding/opportunities.
16. Support ticket can be raised/resolved.
17. Post-training business outcome can be recorded.
18. Management dashboard reflects the lifecycle.
19. RBAC prevents unauthorized access.
20. Audit logs show consequential actions.
21. Backups, monitoring, deployment documentation and tests are
    operational.

------------------------------------------------------------------------

# 46. RESPONSE FORMAT FOR CODEX DURING DEVELOPMENT

For each major task, respond with:

**Plan** - What will be changed.

**Files** - Files created/modified.

**Implementation** - Concise explanation of architecture/business
decisions.

**Database** - Migration/schema/index impact.

**Security** - Auth/privacy/security impact.

**Tests** - Tests added and commands executed.

**Validation** - Lint/type/build/migration results.

**Open Issues** - Anything unresolved.

**Next** - Recommended next task.

Never claim tests passed unless they were actually executed
successfully.

------------------------------------------------------------------------

# START COMMAND

Begin SDLC now.

First audit the current repository and create the Phase 0/Phase 1
documentation described in Section 38. Do not implement feature modules
until the requirements, ERD, architecture, security model, backlog and
Definition of Done are coherent.

After creating those documents, bootstrap only the minimum platform
foundation necessary for Milestone 1, run the available verification
commands, and produce `docs/sdlc/milestone-01-report.md`.

Follow this master input for all subsequent implementation unless an
explicitly approved change is recorded in an ADR or updated requirement.
