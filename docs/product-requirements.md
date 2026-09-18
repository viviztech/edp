# EDP product requirements

Status: proposed baseline for implementation. Authority: `EDP_CODEX_MASTER_INPUT.md`, Sections 0–46. Changes require traceable requirement updates or an approved ADR. Development ceiling: ₹10 lakh; no monetary estimates inferred. Recurring infrastructure/provider costs are separate.

## People and journeys

Public visitors discover eligibility, programs and opportunities on responsive English/Tamil web/mobile. Applicants register, save drafts, consent, upload private documents and follow reviewed status. Participants see schedules, learning, attendance, assessments, mentoring, certificates and support. Alumni record outcomes and access ongoing resources. Mentors and trainers see assigned people only. Staff operate scoped queues, publishing and reporting; directors see program-wide aggregates.

Primary journey: discover → attributed lead → register → apply → review → interview → select → enroll → learn → attendance/assessment → certify → mentor → opportunities/support → record business outcome → report impact. One person can participate in multiple programs; account status, application status and participant lifecycle are distinct.

## Requirements and acceptance

Every row inherits the [Definition of Done](sdlc/definition-of-done.md). Backlog IDs provide stories, dependencies and technical tasks.

| ID / master section | Requirement | Observable acceptance | Priority / backlog |
|---|---|---|---|
| R01 / 3–5,25 | Platform, identity and scoped permissions | Rotated refresh replay revokes family; suspended users and unassigned staff denied; consequential writes audited | P0 / F01–F04 |
| R02 / 6,22 | Public content and CMS | Only published localized content appears publicly; preview restricted; enquiry captured; SEO and accessible navigation verified | P0 / C01 |
| R03 / 7 | CRM and Meta | Signed duplicate webhook produces one attributed lead; assigned staff manage follow-ups; conversion preserves attribution | P0 / C02–C03 |
| R04 / 8 | Application | Draft persists; required fields/consent/documents enforced; retry gives same submission; reviewed version immutable | P0 / A01 |
| R05 / 9 | Selection | Configurable weighted rubric; assigned reviewer scores; authorized reasoned override; only selected application enrolls once | P0 / A02 |
| R06 / 10 | Program/participant | Multiple programs/cohorts/centers; enrollment preserves person/application links; scoped timeline and schedule visible | P0 / P01 |
| R07 / 11 | LMS, assessment and certificates | Enrolled learner accesses private lesson; attempts/grades persist; completion rules gate certificate; public verification minimal | P0 / L01–L02 |
| R08 / 12 | Attendance | Expired/wrong-session QR denied; concurrent duplicate check-in creates one record; corrections require reason | P0 / L03 |
| R09 / 13 | Mentoring essentials | Assigned mentor records session/goals; private note invisible to participant and other mentors | P0 / M01 |
| R10 / 15 | Schemes/funding/opportunities | Filter public/eligible items; show official source and verification date; bookmark and controlled funding progression | P0 / K01 |
| R11 / 18 | Helpdesk | Participant opens ticket; assigned staff respond; internal notes hidden; controlled reopen and history | P0 / S01 |
| R12 / 19 | Communications | Consent/preferences enforced; retries bounded; duplicate event does not duplicate delivery intention; failures visible | P0 / N01 |
| R13 / 20,45 | Core reporting and impact | Cohort/period denominator documented; audited exports; minimal baseline and post-training business outcome recorded | P0 / I01 |
| R14 / 21 | One Flutter app | Guest/applicant/student navigation; secure session storage; deep-link authorization; English/Tamil; cache never stores private documents | P0 / F04 plus domain slices |
| R15 / 26–29,41 | Operations | Green CI, tested restore, monitored staging, approved UAT and production runbooks | P0 / O01 |
| R16 / 14,16 | Business plan and expanded follow-ups | Versioned plan, mentor review; opt-in business profile and dated outcome snapshots | P1 / B01–B02 |
| R17 / 17,20 | Business tools and advanced dashboards | Owner-isolated card/catalogue/quotation/mini CRM; defined metrics | P1 / B03–B04 |
| R18 / 31,43 | Future capabilities | Separate scope approval, data controls and measurable need before implementation | P2 / X01–X03 |

## Nonfunctional acceptance

- UUID business IDs; UTC timestamptz; transactions; explicit FKs and indexes; migrations for every schema change; no generic status mutation.
- Server-authoritative permissions and object scopes; TLS in deployed environments; private object storage; secure token lifecycle; sensitive access/export audit; no PII in logs.
- English and Tamil keys from first shell; approved translations/content needed for launch. Keyboard/focus, labels, semantic markup, contrast and scalable mobile text tested.
- Bounded list APIs; external calls off request path; query-plan checks and load tests before declaring capacity. Latency/concurrency budgets await measured baseline and client volumes.
- Idempotent integrations, durable database outbox, bounded retries and operator-visible failures. No claim of exactly-once external delivery.
- Each critical journey must pass negative authorization tests and channel-specific E2E tests. CI and manual smoke evidence required for completion.

## Boundaries and acceptance authority

P0 is the launch scope, not Milestone 1. P1 is conditional on contract/time. P2 is deferred. Do not trade security, backup, tests or workflow integrity for optional modules. No payments, biometric/location tracking, custom video/chat, accounting compliance, marketplace, Kubernetes/Kafka or automated funding decisions at launch.

Product owner confirms policies/content and UAT; technical owner owns architecture/security evidence; operations owner owns restore/monitoring readiness. Named owners remain open. Section 45's complete 21-step journey is the final product acceptance, never a bootstrap acceptance claim.

## Milestone 2 acceptance detail

See [Milestone 2 plan](sdlc/milestone-02-plan.md) for C01.1-C01.6 public/CMS stories, channels and measurable acceptance. Initial publishing uses independent English/Tamil drafts and immutable live revisions; media, enquiry, navigation and structured content follow as separate slices.
