# Pending Work Register

**Recorded:** 2026-09-25  
**Purpose:** Preserve the outstanding work associated with completed implementation slices before the project proceeds to the next scheduled module.

## Current position

The completed vertical slices are functionally accepted in the local development environment. They are not yet formally released, and the milestone Definition of Done remains open where remote CI, native-device validation, external providers, staging, production operations, or client approval are required.

P01.3 center/cohort staff bindings has passed the available local API, migration, static-analysis, web, build, and authenticated browser checks. No known functional defect remains in that slice at the time of this record.

## Immediate closure work

These tasks should be completed before or alongside the next feature implementation:

| Priority | Task | Recorded status |
| --- | --- | --- |
| P0 | Commit and push the latest P01.3 implementation, documentation, generated contracts, and completed-flow PDF artifacts to `main` | Changes were still local when this register was created |
| P0 | Run GitHub Actions against the pushed commit | Remote CI had not tested the latest changes |
| P0 | Resolve repository-wide Ruff and strict MyPy checks | Verified 2026-09-26: the focused P01.3 modules pass, while the repository-wide Ruff gate reports 166 pre-existing findings concentrated in legacy CMS code and early migrations; MyPy remains gated behind Ruff in the CI-equivalent command |
| P1 | Reconcile superseded milestone-report wording | Completed 2026-09-26: the P01.2 checkpoint now explicitly points to the superseding P01.3 implementation |

## Deferred implementation and acceptance work

| Area | Pending work | Classification |
| --- | --- | --- |
| Applications | A01.3 supporting-document upload, private storage, malware scanning, retention, and access control | Planned implementation |
| Flutter | Secure storage, deep links, remote revocation, and real-device acceptance | Deferred to the macOS development stage under ADR 0004 |
| Background processing | Full Redis, Celery worker, and Celery Beat container/runtime acceptance | Environment acceptance |
| Notifications | Production email, SMS, FCM, and WhatsApp adapters, credentials, and delivery-status validation | Provider integration |
| Meta | Live credentials, page/app ownership, production webhook validation, and retention approval | Provider and operational acceptance |
| Privacy | Approved consent text, deletion rules, document retention, notification retention, and Meta-event retention | Product/legal decision |
| Content and branding | Final organization wording, logo, Tamil translations, production content, and client assets | Client input and UAT |

## Staging and production gates

The following release work remains open:

- Provision an isolated staging environment with PostgreSQL, Redis, private object storage, TLS, secrets, and images produced by green CI.
- Execute the deployment migration job, synthetic-data smoke tests, critical end-to-end flows, and negative authorization tests in staging.
- Configure provider sandboxes and validate webhook and notification behavior.
- Complete security, accessibility, performance, and load acceptance appropriate to the release scope.
- Approve privacy and consent copy and complete client UAT.
- Validate backups through a restore rehearsal and approve RPO, RTO, and retention settings.
- Configure monitoring, error tracking, incident contacts, TLS/DNS, and the incident runbook.
- Complete administrator provisioning and a privilege review.
- Validate rollback artifacts and database compatibility.
- Deliver training, user guides, handover material, and assign the stabilization owner.

## Product decisions awaiting owners

The open-questions register still requires decisions or confirmed owners for:

- official organization spelling, logo, and program naming;
- expected program, cohort, center, applicant, and participant volumes;
- Tamil translation ownership and delivery timing;
- final application fields, eligibility rules, documents, declarations, and consent wording;
- scoring conflicts, reviewer policy, waitlist behavior, reopening rules, and authorized overrides;
- attendance thresholds and certificate signatories;
- Meta assets, WhatsApp ownership, and external notification providers;
- hosting, domains, object storage, video delivery, and production credentials;
- privacy, deletion, consent, and retention policies;
- RPO, RTO, backup retention, and incident contacts;
- impact-indicator definitions and reporting ownership;
- scheme and funding content ownership;
- native mentor-mobile scope;
- business-tool priorities; and
- UAT, security, and production-release approvers.

## Future scheduled scope

The following are future implementation slices and are not defects or unfinished acceptance criteria in already completed slices:

- L01 learning management
- L02 assessments
- L03 certificates
- M01 mentoring
- K01 knowledge resources
- S01 schemes and opportunities
- I01 impact reporting

## Recommended continuation rule

Before starting L01, commit and push the current changes and obtain remote CI results. Repository-wide CMS Ruff/MyPy debt is verified and remains tracked for remediation; it must not be attributed to later focused modules. Native macOS validation, live-provider work, staging, and production gates may remain explicitly deferred while local feature development continues.

Update this register whenever an item is completed, deferred by an approved decision, or superseded. Link the supporting commit, CI run, ADR, test evidence, or release record in the corresponding row.

## Update - 2026-09-26

- P01.3 and its flow documentation were committed and pushed to origin/main in commit ae7cff4.
- Repository-wide Ruff was verified and reports 166 pre-existing legacy CMS and early-migration findings; strict MyPy also contains documented CMS and selection debt. Focused P01.3 and L01.1 checks pass.
- Superseded P01.2 coordinator wording was reconciled.
- L01.1 course catalog and enrollment access is implemented and locally accepted. It remains uncommitted at the time of this update; remote CI therefore remains pending.
- Later L01 work includes lesson progress, prerequisites, trainer bindings and signed media delivery.
