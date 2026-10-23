# Privacy data inventory

Owner approvals pending. No real data in development. Default is minimize collection and disable unapproved ingestion; absence of a retention decision is a launch blocker, not permission for indefinite retention.

| Data | Purpose / access | Storage / disposal decision |
|---|---|---|
| Person name, contact, locale | Identity/contact; self and scoped staff | PostgreSQL; approved retention and anonymization schedule pending |
| Password hash, sessions, reset hashes | Authentication; service only | PostgreSQL; expire/revoke; never logs/exports |
| Eligibility, education, business idea | Application review; applicant and assigned reviewers | Relational versioned records; rejected applicant retention pending |
| Identity/supporting documents | Required evidence only; assigned reviewers | Private S3; quarantine, signed access; deletion policy pending |
| Lead attribution/provider metadata | CRM and troubleshooting; assigned staff | Minimal provider inbox fields require an approved period; expired inbox rows are hidden and purged by a scheduled worker. CRM attribution, audit and backups have separate pending policies |
| Scores, private notes, decisions | Accountable selection/mentoring | PostgreSQL; staff visibility separate from participant DTOs |
| Learning/attendance/grades/certificates | Program delivery | PostgreSQL; no precise location/biometrics; retention pending |
| Business outcome/revenue bands | Impact; self and scoped reporting staff | Minimize exact financial data; dated snapshots, aggregate output |
| Consent/preferences/device push tokens | Communication | Versioned consent, revocable preferences; remove stale device tokens |
| CRM assignment and follow-up notification intents | Staff in-app notices; recipient and scoped CRM staff | PostgreSQL stores organization, recipient, lead/activity IDs, topic, state and timestamps without lead contact details, activity notes or message body. CRM activity retains a last-reminded recipient marker under its own lifecycle. Preferences are versioned. Approval of the retention period remains pending; configurable hiding and bounded audited disposal are implemented, with no code default; synthetic data only |
| Audit and operational logs | Accountability/incident response | Allowlisted metadata; separate access and approved retention |
| Backups | Recovery | Encrypted separate storage; deletion propagates through documented expiry |

Product owner approves field purpose, consent copy, privacy notice, processors, retention periods, data requests and deletion exceptions. Operations owns backups/deletion execution. Engineering owns enforcement and tests. Export/download creates an auditable access event. Public business profile requires explicit opt-in. AI receives no participant data in initial release.

## A01.4 submitted application evidence

Submitted answers are stored in immutable relational revisions. Declaration and consent evidence stores the immutable policy-definition ID and acceptance timestamp; the policy text remains on the pinned form version. The generated application number contains UTC year and a sequence only. Applicant-visible history excludes staff notes. Audit stores identifiers and changed-field names without answer or acknowledgement content. Submitted-answer retention, deletion exceptions and data-subject handling still require owner approval before real applicant data is collected; A01.3 document ingestion remains disabled.

## Selection review evidence

Criterion scores, weighted totals and internal reviewer comments are confidential staff selection records linked to an application, reviewer and published rubric. Applicant responses do not expose them. Submitted evidence is database-immutable; reasoned moderation is a separate audited record. Retention and subject-access/export treatment require the same approved selection-record policy before real-data production use.

## Interview and selection decisions

Panel scores/comments, interview averages, decision reasons and evidence snapshots are confidential selection records. Applicant receipts expose status only. Submitted panel evidence, completed interviews and decision history are immutable; authorized overrides add history instead of rewriting it. Retention, subject-access and bulk-communication policy remain deployment prerequisites before real applicant data is used.

P01.2 Participant stores only organization, Person reference, lifecycle status and version; it does not copy name, email or contact data. Enrollment stores lifecycle identifiers and timestamps. ProgramSession contains bilingual schedule content and location/joining details, so staff must not place secrets in that field. The participant timeline excludes reviewer comments, scores, decision reasons and audit records. The enrollment outbox payload contains UUID references only.

## L02.1 quiz evidence

Quiz attempts retain enrollment, quiz, submitted choices, awarded points, calculated percentage, pass state and submission time. Learners see their own summary and immediate grading result. Trainers see only attempt count, best percentage, pass state and last submission time for learners in assigned cohorts; answer selections and answer keys are excluded. Audit does not copy question, choice or grade values. Assessment retention and subject-access policy remain required before real participant use.

## L02.2 assignment evidence

Assignment submissions retain the learner's course-enrollment reference, assignment, immutable revision text and submission time. Grades retain grader identity, points, derived pass state, feedback and grading time. The owning learner and currently authorized cohort delivery staff can view this evidence; other learners and out-of-scope trainers cannot. Audit records identifiers and changed fields without response text, feedback or score values. File evidence is not accepted. Assessment retention, export, correction and subject-access policy remain required before real participant use.

## L02.3 certificate evidence

Private Certificate rows snapshot recipient name, bilingual certificate/course text, issuer, template version, verification identifier, issuer actor and issue/revocation evidence. The snapshot preserves the issued record when profile or template text later changes. Learners see their own record; authorized learning staff see scoped eligibility and certificate state. Anonymous verification excludes recipient name, statement, organization/enrollment IDs, scores and feedback. Retention, subject access, signatory policy and revocation operations require program/privacy approval before production use.

## K01 resource preferences and funding evidence

Editorial resources contain source, eligibility, process and verification information intended for their selected public/participant audience. Saved resources and opportunity interests associate that information with an authenticated participant and are private preferences/evidence, never public lead lists. Funding cases retain participant/item identifiers, the original resource snapshot and participant-reported status/reasons. Owners and authorized organization funding staff can read case evidence; only the owner can progress it. No bank details, identity documents, precise financial transactions or external application submissions are collected in this phase.

Immutable source and status evidence preserves accountability when a resource changes or expires. Logs/audit omit resource prose, participant reasons and financial values. Retention, subject-access/deletion exceptions, staff responsibilities and final content verification ownership require approval before real participant use. No provider, recommendation engine or AI receives this data.

## Phase 9 support and post-training evidence

Helpdesk stores ticket category/subject/priority, derived participant/user ownership, staff assignments, shared replies and staff-only notes, immutable lifecycle evidence, and optional private UTF-8 text attachments. Owners and currently authorized assigned/admin staff can read shared content; only authorized staff can read internal content. No attachment is publicly addressable. In-app notices retain recipient/ticket IDs and event/version only, and preferences record per-organization opt-out. Do not include identity documents, banking credentials or unnecessary personal data in tickets or text files. Acceptance uses synthetic data.

B02 profiles, fixed scheduled follow-ups and immutable self-reported business outcomes continue under private owner scope, including eligible completed alumni. Financial bands are self-reported, not verified accounts. Public opt-in does not publish a profile in this phase. Support/outcome retention, deletion exceptions, subject access, approved Tamil copy and the private-document pipeline require policy approval before real collection or deployment. No external provider or AI receives ticket or outcome content.

## Phase 10 measurement and report evidence

Minimal impact observations collect enrollment/measurement edition, baseline or outcome stage, observed date, started/active booleans, bounded jobs-created count and a correction reason. They are self-reported evidence independent of the optional business profile. Owners can read their eligible private evidence; reporting staff receive aggregated values and coverage rather than observation rows or reasons. Mixed editions remain distinct, matched comparisons use the same edition and missing data is explicit. No precise revenue, funding transaction, bank details or new documents are collected.

Snapshots preserve aggregate values, measurement/dictionary definitions, source/period/population metadata and generation time. CSV jobs retain aggregate content, requester and reason; capability storage contains hashes only. Download expiry is not physical deletion. Final indicator wording, lawful purpose/consent, retention/deletion exceptions, approved translations and reporting ownership still require approval before real participant collection or release. Small internal cohorts remain confidential: reports and exports are authorized staff tools, not public impact claims or verified causal results.
