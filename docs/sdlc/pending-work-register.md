# Pending Work Register

**Recorded:** 2026-09-25  
**Updated:** 2026-10-24
**Purpose:** Preserve the outstanding work associated with completed implementation slices before the project proceeds to the next scheduled module.

## Current position

Earlier foundation/learning/mentoring slices, B01, K01 and Phase 9 B02/S01 are accepted for their documented local web/API scope. Phase 10 reporting and impact local web/API acceptance, including final Tamil responsive review, passed on 2026-10-23. These slices are not formally released, and the milestone Definition of Done remains open where remote CI, native-device validation, external providers, staging, production operations, or client approval are required.

[Process 2 web journeys](web-journey-completion-report.md) and [Process 3 secure files](secure-files-acceptance-report.md) are locally accepted. The 2026-10-24 checkpoint records 289 API tests passed, one POSIX-only skip, 406 web tests passed, ten final-build browser runners, zero migration drift and deterministic contracts. Current npm and complete Python runtime/development audits report zero findings. The historical nine-high braces result is superseded. All source remains local; exact-revision remote CI remains deferred and no push is authorized. This section and the latest checkpoint supersede historical descriptions below.

## Immediate closure work

Process 3 is locally accepted under the [secure-files plan](secure-files-plan.md). Application documents, CMS verified media, learning and helpdesk bindings passed combined local checks, browser acceptance and visual review. Explicit draft material removal/replacement retains history; incomplete active material blocks publication. Real collection and maintenance remain disabled, and no real document list or retention policy has been approved. The next authorized local process is [background-job recovery](background-job-recovery-plan.md), followed separately by essential communications; see the [six-step plan](remaining-development-plan.md).

These tasks should be completed before or alongside the next feature implementation:

| Priority | Task | Recorded status |
| --- | --- | --- |
| P0 | Commit and push the P01.3 implementation and flow documentation | Completed in `ae7cff4` as recorded on 2026-09-26; current-baseline review and source-control work are tracked separately below |
| P0 | Close Phase 10 final responsive acceptance | Completed 2026-10-23: fresh reporting/impact Chrome assertions, Tamil responsive controls and single-line numeric cells pass with no JavaScript errors; focused screenshots visually inspected. See the [Phase 10 report](milestone-10-report.md) |
| P0 | Review the current changes, prepare the intended revision and obtain green GitHub Actions for that revision | Baseline captured locally as `c9877ab`; remote CI remains unverified and is deferred under the owner's 2026-10-23 local-only instruction. No push is authorized |
| P0 | Resolve dependency security findings without weakening scans | Resolved in the 2026-10-24 local checkpoint: npm and complete Python runtime/development audits report zero findings after compatible transitive, pip and filelock fixes. Historical reports retain their dated results; no advisory or package is ignored. |
| P0 | Resolve repository-wide Ruff and strict MyPy checks | Resolved locally 2026-10-21: repository-wide Ruff, formatting and strict MyPy pass; see the [dependency repair report](dependency-repair-report.md). Remote CI remains unverified. |
| P1 | Reconcile superseded milestone-report wording | Completed 2026-09-26: the P01.2 checkpoint now explicitly points to the superseding P01.3 implementation |

## Deferred implementation and acceptance work

| Area | Pending work | Classification |
| --- | --- | --- |
| Secure files | Local implementation and acceptance complete 2026-10-24; live storage/scanner, Linux/device, operational holds and approved real collection rules remain open | External runtime and policy gates |
| Flutter | Applicant/student/alumni domain workflows, deep links, and Android/iOS secure-storage/session/device acceptance; secure refresh storage, rotation and session-revocation controls are implemented | Domain implementation remains open; native runtime verification is deferred under ADR 0004 |
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

## Remaining implementation and acceptance scope

The following distinguish deferred channel/integration implementation from acceptance still needed for the documented local slices:

- L02 follow-up: secure assignment file evidence is locally accepted in Process 3; approved certificate signatories/PDF presentation and any attendance gate remain open; core eligibility/issuance/verification is complete locally
- M01 mentoring is complete locally; provider reminder delivery and native mobile remain deferred
- K01 native client and approved live resource ownership/content; web/API local acceptance is recorded below
- S01 native client, approved support/retention policy and external notification delivery remain open; broader private attachments are locally accepted in Process 3
- I01 policy/native/release gates and exact-revision CI; reporting/impact local web/API acceptance, including final responsive review, is complete as documented in the [Phase 10 report](milestone-10-report.md)

## B01.1 continuation — 2026-10-08

B01 implementation has started after M01. The participant draft and submission API, immutable revision/snapshot/review design, assigned mentor review API, bilingual participant and mentor web flows, CSRF BFF, generated contracts, and focused static/web checks are present. On 2026-10-08 the isolated PostgreSQL `edp_test` workflow test passed, along with migration downgrade/re-upgrade and zero drift. Across the full API run and a targeted retry using a project-local temp directory, 89 tests passed. Authenticated browser acceptance and remote CI remain open. Do not mark B01 complete until the Milestone 7 plan's acceptance gates pass.

## Recommended continuation rule

Remote CI results remain required for release. The owner's 2026-10-23 local-only instruction explicitly permits local continuation without publishing source; it does not count as a green CI or security result. Repository-wide CMS Ruff/MyPy debt was resolved locally on 2026-10-21; the unpatched transitive npm advisory remains explicitly tracked in the [dependency repair report](dependency-repair-report.md). Native macOS validation, live-provider work, staging, and production gates remain explicitly deferred while local feature development continues.

The approved remaining-development sequence is [baseline verification](baseline-verification-plan.md), [complete web journeys](web-journey-completion-plan.md), shared secure files, communications/jobs, Flutter domain workflows, staging/operations and launch acceptance, followed by approved P1 business tools. Report each process's local completion evidence before starting the next; failing or unverified release checks remain open and must not be described as passed.

Update this register whenever an item is completed, deferred by an approved decision, or superseded. Link the supporting commit, CI run, ADR, test evidence, or release record in the corresponding row.

## Update - 2026-09-26

- P01.3 and its flow documentation were committed and pushed to origin/main in commit ae7cff4.
- Repository-wide Ruff was verified and reports 166 pre-existing legacy CMS and early-migration findings; strict MyPy also contains documented CMS and selection debt. Focused P01.3 and L01.1 checks pass.
- Superseded P01.2 coordinator wording was reconciled.
- L01.1 course catalog and enrollment access was committed on `main` as `8b075ee`; remote CI remains pending until the pushed commit completes its workflow.
- L01.1-L01.3 now cover catalog/access, progress/prerequisites/completion, trainer scope and local/test signed material delivery.

## L01.2 completion record

L01.2 adds ordered prerequisites, draft-only completion rules, immutable lesson completion evidence, derived course progress, automatic enrollment completion, and count-only cohort summaries. L01.3 completes the remaining trainer and local/test private-media scope. L02.1 quiz assessment, L02.2 text assignments/manual grading, L02.3 certificate eligibility/issuance/verification, and L03 attendance/QR are complete locally. Secure assignment file evidence, an approved certificate attendance gate and signatories/PDF presentation, native Flutter after macOS migration, remote CI confirmation, and closure of legacy repository-wide Ruff/MyPy debt remain open.

## L01.3 completion record

L01.3 adds trainer-scoped published course delivery, cohort learner progress, short-lived private material capabilities, a confined local/test file adapter, BFF binary delivery and English/Tamil web states. Production private object/video hosting, storage retention and operational acceptance remain open release gates. Future work is M01 mentoring, secure assignment file evidence, approved certificate attendance/signatory/PDF policy, native Flutter after macOS migration, remote CI confirmation and closure of separately recorded legacy Ruff/MyPy debt.

## L02.1 completion record

L02.1 adds draft-only bilingual single-choice assessment authoring, publication validation, immutable attempt evidence, server-derived grading, pass marks and bounded retries. Learner contracts omit answer keys; trainer summaries reuse active cohort delivery scope. The full API suite, migration round trip, drift check, generated contracts, web lint/type/test/build and authenticated Chrome journey pass locally.

## L02.2 completion record

L02.2 adds draft-only bilingual text assignments, immutable sequential submissions, review-before-resubmission, bounded trainer grading, server-derived pass state and learner feedback. PostgreSQL repeats revision-limit and immutability controls. Focused API/database acceptance, migration round trip and drift, generated contracts, web lint/type/test/build and authenticated Chrome submission/grading pass locally. The eligibility/certificate continuation is recorded in L02.3 below; file evidence remains deferred until the shared secure-upload pipeline exists.

## L02.3 completion record

L02.3 adds derived lesson/quiz/assignment eligibility, versioned bilingual templates, manual permissioned issuance, immutable snapshots, reasoned revocation, random identifiers, SVG QR and privacy-minimized anonymous verification. PostgreSQL/API, migration, contract, web and authenticated/anonymous browser gates pass locally. Remaining certificate release work is approved signatory/PDF presentation and an approved L03 attendance gate; secure assignment file evidence remains deferred to the shared upload pipeline.

## L03 completion record

L03 adds versioned cohort policy, scoped manual attendance, digest-only time-limited QR windows, participant check-in, duplicate prevention, immutable corrections, derived percentages and low-attendance status, and English/Tamil staff/participant web flows. No location, biometric, or device-fingerprint data is collected. Final threshold approval, outbound alert delivery, any certificate attendance gate, native Flutter, remote CI, and production operational acceptance remain open.

## M01 completion record

M01 adds eligible mentor profiles, expertise and availability, one active enrollment-scoped assignment, conflict-checked sessions, author-only private notes, participant-shared notes, versioned goals/actions, durable follow-up reminders, immutable participant feedback and count/average monitoring. PostgreSQL repeats scope and immutability controls. English/Tamil staff and participant web flows use a closed BFF allowlist. Native mentor mobile access, production reminder dispatch, retention approval, remote CI and production operational acceptance remain open. The next scheduled module is K01 knowledge resources.

## Dependency repair and B02 editing - 2026-10-21

Python/Node/Flutter dependencies and locks are aligned; an isolated UTC PostgreSQL cluster supports local acceptance. B02 updates after reload now send only writable contract fields. All 92 backend tests, 46 web tests, eight Flutter tests, both web builds, migration checks and the authenticated Chrome journey pass locally. The full details, an unpatched upstream npm advisory, unavailable Docker/Redis runtime gates and deferred native/remote/release work are recorded in the [repair report](dependency-repair-report.md). This closes the focused editing defect without declaring the broader Milestone 7 scope released.

## B01 autosave recovery - 2026-10-21

The focused recovery slice is locally verified: independent-section merging, explicit conflicting-text choices, lost-response and late-commit handling, preserved in-flight edits, failure pauses and navigation warnings. The existing B01 API workflow, web lint/types, 77 tests, production build and authenticated two-tab browser acceptance pass. See the [recovery report](b01-autosave-recovery-report.md).

The full B01 journey was pending at this checkpoint and is closed by the continuation below. Remote CI, final approval policy, PDF/native work and previously recorded release gates remain open.

## B01 local acceptance closure - 2026-10-21

B01 web/API development and local acceptance are complete. Separate participant and assigned-mentor actors exercise submission, requested changes, preserved feedback, revision/resubmission, approval and locked immutable evidence. Mentor stale/interrupted-review recovery, bilingual decisions, valid proxy text sizes and normalized reason validation are verified. All 93 backend tests, 104 web tests, static checks, production build, migration round trip/drift, generated contracts and the full authenticated Chrome journey pass. See the [acceptance report](b01-acceptance-report.md).

The next scheduled development phase is K01 knowledge resources. Broader B02 acceptance/decisions, remote CI, native/PDF scope, the recorded upstream dependency advisory and operational release gates remain open; no formal milestone or production release is implied.

## K01 local knowledge and funding acceptance - 2026-10-21

K01 web/API development and local acceptance are complete. Schemes, funding programs and opportunities have versioned publication, safe official sources, verification/availability information, bilingual discovery and scoped participant resources. Saved items, opportunity interest and owner funding cases preserve original evidence; only approval can precede disbursement. Staff funding access is read-only and organization-scoped.

All 97 backend tests, final four K01 database tests, 132 web tests, static checks, migration round trip/drift, compatible generated contracts, production build, dedicated K01 Chrome acceptance and the existing foundation/B01/B02 browser regression pass. See the [Milestone 8 report](milestone-08-report.md).

The next scheduled development phase is S01 helpdesk. K01 native screens/device acceptance, live content/translation ownership and policy approval, remote CI, broader B02 decisions and the previously recorded dependency/infrastructure/production release gates remain open. Local acceptance does not waive the formal Definition of Done or declare production readiness.

## Phase 9 local post-training and helpdesk acceptance - 2026-10-21

Phase 9 B02/S01 web/API development and local acceptance are complete. Private business profiles, fixed periodic follow-ups and immutable self-reported outcomes now have full separate-actor/policy-freeze/withdrawal coverage and safe save recovery. Helpdesk adds scoped claim/assignment queues, shared replies and private notes, bounded private text files, controlled lifecycle/reopen, immutable history and recipient-only in-app notices/preferences. Current assignment and eligible owner status are rechecked for content and downloads.

All 103 API/PostgreSQL tests, 159 web tests, backend/web lint and typing, compatible generated contracts, migration round trip/drift and the final production build pass. Dedicated Phase 9 Chrome acceptance and the existing foundation/B01/B02 regression pass without JavaScript errors. Tamil responsive evidence was inspected; temporary servers were stopped. See the [Phase 9 report](milestone-09-report.md).

The next scheduled domain phase is I01 reporting and impact. Native domain screens/device acceptance, public business publishing, final support/outcome/retention/translation policy, broader private-file ingestion, external communications, remote CI and previously recorded dependency/infrastructure/production gates remain open. Earlier entries describe their historical checkpoints and are superseded by this acceptance record for B02/S01 local scope.

## Process 1 baseline reconciliation - 2026-10-23

Phase 10 reporting/impact local web/API acceptance is complete on 2026-10-23. Fresh Chrome assertions and the final Tamil responsive review passed; focused filter, metric and participant-control screenshots were visually inspected without clipping. Fresh API/PostgreSQL regression (112 tests), web regression (180 tests across 37 files), static checks, production build, disposable migration round trips/drift and compatible contracts also passed. The [Phase 10 report](milestone-10-report.md) preserves the 2026-10-21 checkpoint and adds the fresh closure evidence. README, backlog, this register and mobile status distinguish implemented local scope from remaining domain/native/provider/operations work.

The [baseline plan](baseline-verification-plan.md) and current [report](baseline-verification-report.md) govern verification, dependency remediation, CI corrections and the reviewed revision. Process 1 remains open because nine high findings from unpatched `braces` and missing exact-revision CI leave required gates unsatisfied. Native-device validation, provider activation, staging, UAT and production release remain open; local acceptance does not close them. Phase 11/P1 tools follow the outstanding P0 journey and release work in the approved continuation sequence.

## Process 2 web journey acceptance - 2026-10-23

Applicant entry/context and owner-only closed-intake history, permission-aware participant navigation, gated bilingual public enquiries with a versioned staff inbox, and editorial/media metadata web workflows are locally accepted. The [completion report](web-journey-completion-report.md) records 128 full API tests plus 13 final editorial/CMS tests, 308 web tests, static checks, builds, migrations/drift, compatible generated contracts and all seven browser scripts across the five runners. English/Tamil screenshots and keyboard targets were reviewed. Public collection remains disabled until approved policy is configured. Secure bytes/scanning, native/provider/operations and baseline security/CI release gates remain open. Notify the owner and continue with shared secure files; no push or deployment is authorized.
