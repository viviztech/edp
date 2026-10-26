# Staging UAT execution packet

Prepared 2026-10-26 (Asia/Calcutta). Status: **PREPARED; NOT EXECUTED**.
This packet defines client acceptance of the implemented scope. It does not record
completed UAT, native acceptance, provider activation or deployment approval.
Prior local tests and a green CI run are supporting evidence, not client approval.

Use the [administrator](../user-guides/admin.md) and
[participant](../user-guides/participant.md) guides while executing these cases.
The [master specification](../../EDP_CODEX_MASTER_INPUT.md),
[test strategy](test-strategy.md) and
[release checklist](../sdlc/release-checklist.md) define the acceptance boundary.

## Execution record

Create a separate copy of this packet in the approved restricted evidence location
for each candidate. Do not overwrite an earlier execution record.

| Field | Required entry | Current value |
| --- | --- | --- |
| Execution reference and coordinator | Unique reference; named client coordinator | PENDING OWNER |
| Candidate | Full source revision, source-manifest digest, API/web/edge image digests, configuration digest, migration head | PENDING EVIDENCE |
| CI and contracts | Exact-revision run URL, required-job results, OpenAPI/client digests, dependency/container/native scan references | PENDING EVIDENCE |
| Environment | Approved isolated HTTPS origin, environment owner, database/storage separation and synthetic-data statement | PENDING OWNER |
| Mobile | Android/iOS artifact digest, app identifier, build mode, OS/device model or simulator, API endpoint reference | PENDING EVIDENCE |
| Service capabilities | Actual Redis/worker/single-Beat, object version/key/scanner, Meta and sender evidence; explicitly list unavailable services | PENDING EVIDENCE |
| Product rules | Approved form/document/rubric/attendance/certificate/content/consent/retention/sharing editions and approvers | PENDING OWNER |
| Schedule | UTC start/end and Asia/Calcutta presentation dates; participant availability | PENDING OWNER |
| Evidence custody | Restricted destination, custodian, redaction/access rules and approved disposal schedule | PENDING OWNER |

Before execution, verify the candidate identities against the filled release
manifest described in the [staging runbook](../deployment/staging.md). Never use
the example manifest's placeholder revision/digests as release evidence. Freeze
the candidate during a run; a new build/configuration/schema requires a new
execution reference and retesting of affected cases.

## Prerequisites and synthetic actors

All rows are **NOT EXECUTED** until observed by the named tester. Populate the
owner/evidence columns before acceptance; a checked plan is not an observation.

| ID | Prerequisite | Owner and evidence | Status |
| --- | --- | --- | --- |
| P01 | Isolated staging origin, TLS, secure cookies, trusted-proxy boundaries and private backing services verified | Operations owner: PENDING; evidence: PENDING | NOT EXECUTED |
| P02 | Candidate CI/scans, compatible migrations/grants and restoration evidence reviewed | Engineering/security owners: PENDING; evidence: PENDING | NOT EXECUTED |
| P03 | Approved synthetic fixture inventory and currently valid account/role assignments established | Program/UAT owners: PENDING; evidence: PENDING | NOT EXECUTED |
| P04 | Required policies/content/translation editions approved; real collection and senders remain disabled unless separately authorized | Client/privacy/content owners: PENDING; evidence: PENDING | NOT EXECUTED |
| P05 | Native artifacts and supported test devices available; unavailable platforms explicitly recorded | Mobile owner: PENDING; evidence: PENDING | NOT EXECUTED |
| P06 | Critical defect handling, evidence custody and client decision maker agreed | UAT/security owners: PENDING; evidence: PENDING | NOT EXECUTED |

Provision separate synthetic people in organization A and organization B. Within A,
use two applicants/participants, a CRM assignee and another CRM user, an assigned
reviewer and an unassigned reviewer, two interview panel members, a program manager,
a director, a cohort trainer, an assigned mentor, a support assignee and a content
manager. Add a coordinator restricted to one center/cohort. Give only the required
permissions; do not use a shared Super Admin session to prove ordinary workflows.
Keep an active participant, a completed alumnus and a withdrawn/revoked actor for
scope checks. Record fixture references and permissions without credentials.

Use two browsers or independent sessions for concurrent/stale-operation tests.
Fixture staff may prepare records that the tested role cannot author, but the
actual acceptance action must run through that role's authenticated channel.

## Fourteen required connected journeys

For every case record tester, timestamp, actor/organization references, exact
artifact, English evidence, Tamil evidence, observed results, audit/persisted-state
reference, defect IDs and result. Evidence cells below deliberately remain pending.

| ID | Journey and concrete exercise | Expected result and required negative checks | Evidence / status |
| --- | --- | --- | --- |
| U01 | Public user to application: open the published program, register a synthetic account, verify through the configured test capability, sign in, select intake, save answers, supply only approved synthetic documents, accept pinned declarations and submit. Reload the receipt. | Pending/unverified sign-in is denied. Required fields/acknowledgements and usable document evidence gate submission. Duplicate submit preserves one receipt and immutable evidence. A second applicant and organization B cannot read or change it. Disabled collection, rejected/expired scans and closed intake show accurate states. | Tester: PENDING; EN/TA/audit: PENDING; **NOT EXECUTED** |
| U02 | Meta lead to applicant conversion: the authorized marketing owner submits a test lead through the actual approved Meta test asset; observe attributed CRM creation, assignment, notes/follow-up and supported lead-to-applicant linkage. Repeat the same webhook delivery and inspect its operational state. | One durable lead/event outcome; source identifiers survive conversion. Invalid signatures, unknown asset mappings and organization B are denied. Revoke the assignee and verify current access. Controlled signed fixtures cover local behavior only; absent Meta asset/provider evidence leaves this case open. | Tester: PENDING; EN/TA/provider/audit: PENDING; **NOT EXECUTED** |
| U03 | Reviewer to selection: publish the approved rubric, activate the closed intake's selection cycle, assign reviewers, clear conflict state, save/submit scores, shortlist, schedule an interview, collect each panel score, complete the interview, record a terminal decision and finalize. | Weights/totals are server derived; submitted scores and decisions retain history. An unassigned/conflicted reviewer or non-panel user cannot score. Incomplete panels block completion; stale versions and unauthorized terminal overrides fail. Applicants never receive staff notes or scores. | Tester: PENDING; EN/TA/audit: PENDING; **NOT EXECUTED** |
| U04 | Selected applicant to mobile participant: enroll a finalized selected candidate into a cohort with capacity, observe the participant link and enrollment update, then sign into Android and iOS and open schedule. | One enrollment reuses person identity and records audit/outbox evidence. Capacity, duplicate and non-selected enrollment are rejected. Another participant cannot see the schedule; a withdrawn/revoked session is denied on refresh. In-app enrollment evidence does not establish external message delivery. | Tester: PENDING; EN/TA/Android/iOS/audit: PENDING; **NOT EXECUTED** |
| U05 | Learning to progress: start the assigned published course, attempt a blocked lesson, complete prerequisites, access a synthetic private material, fail/pass a quiz within allowance, submit text/file assignment, have the scoped trainer grade it, and refresh progress. Verify eligible certificate issuance by the authorized staff role and anonymous verification. | Server rules determine availability, scores, submissions and eligibility. No answer key reaches the learner. Peer/unassigned trainer access, exhausted attempts, invalid files and revoked enrollment fail. Lost responses require authoritative readback before another command. Certificate verification exposes minimal fields; trainer cannot issue or alter a certificate. | Tester: PENDING; EN/TA/grade/certificate/audit: PENDING; **NOT EXECUTED** |
| U06 | Trainer attendance to check-in: approve the cohort policy, open a session window, scan its synthetic QR on each native platform, inspect the populated field, explicitly check in, then perform a reasoned staff correction. | Scanning alone sends nothing. Manual entry remains usable when scanning is unavailable. Invalid, foreign, expired, replayed and out-of-window payloads fail without arbitrary navigation. A peer cohort/unassigned trainer is denied. Lost response is reconciled; original mark/correction history persists. Redact raw QR tokens from evidence. | Tester: PENDING; EN/TA/Android/iOS/audit: PENDING; **NOT EXECUTED** |
| U07 | Mentor assignment to follow-up: assign an eligible mentor, schedule a session, record shared and private notes, advance a goal/action, complete the session, schedule follow-up and submit owner feedback. | Participant sees shared material only. Another mentor/participant and organization B are denied; duplicate feedback is rejected. End the assignment and recheck read/mutation access according to the current service. Provider reminders remain unaccepted without real delivery evidence. | Tester: PENDING; EN/TA/audit: PENDING; **NOT EXECUTED** |
| U08 | Business plan to review: the active participant saves sections, refreshes, submits a snapshot; assigned mentor requests changes with feedback; participant revises/resubmits; mentor approves the latest submission. | Earlier snapshots/reviews remain immutable. Simultaneous stale save and interrupted save/review preserve entered content and require explicit readback. Unassigned mentor/peer cannot review; completed-alumni access does not bypass the active-enrollment authoring rule. No unsupported PDF or calculated-profit claim. | Tester: PENDING; EN/TA/snapshots/audit: PENDING; **NOT EXECUTED** |
| U09 | Resource discovery to funding tracker: publish separately reviewed EN/TA source-backed entries, search/filter, follow a safe official link, save/express interest and advance an owned funding case through the permitted states. | Source/verification/availability and edition remain visible. Approval precedes disbursement; skipped transitions, stale reasons and peer writes fail. Unavailable saved content reveals no stale private details. Completed alumni receive only currently permitted public/participant access. | Tester: PENDING; EN/TA/audit: PENDING; **NOT EXECUTED** |
| U10 | Alumni business follow-up: create/update an owned private profile, inspect revision history and frozen due dates, submit one pending follow-up outcome and separately submit an approved impact baseline/outcome observation. | Server dates/definitions and immutable outcomes are preserved; reports do not conflate B02 follow-ups with impact observations. Future dates, inconsistent started/active answers, changed idempotency payloads and peer/organization access fail. Public-profile interest does not publish a directory or contact details. | Tester: PENDING; EN/TA/history/audit: PENDING; **NOT EXECUTED** |
| U11 | Support ticket lifecycle: owner creates a ticket, scoped staff claim/assign, exchange shared replies, add a private note, wait/resolve/close and perform the permitted reasoned reopen. Exercise one approved synthetic attachment, recipient notice and preference. | Owner never sees private notes/internal files or staff assignment controls. Reassignment/revocation is enforced on the next detail/download. Stale/lost replies preserve text without duplicate posting; unclean/unbound files stay unavailable. A peer cannot read the ticket or inbox. External delivery is not implied by an in-app notice. | Tester: PENDING; EN/TA/attachment/audit: PENDING; **NOT EXECUTED** |
| U12 | CMS publication to public view: content manager saves EN/TA page/editorial drafts, reviews preview and metadata, publishes each locale, then archives/restores with a reason; exercise one verified synthetic media binding. | Draft content is private; a saved edit does not silently replace publication. Only published usable media is public; revocation removes new access. Missing publish permission, cross-organization edits, unsafe input and unverified media are denied. Locale publication and archive are independently observed on public web/mobile. | Tester: PENDING; EN/TA/public/audit: PENDING; **NOT EXECUTED** |
| U13 | Unauthorized actor matrix: repeat protected read/write/download/export operations using signed-out, peer, organization B, wrong cohort/center, unassigned/conflicted reviewer, ended mentor, reassigned staff, suspended account and revoked session contexts. | Backend denies each unauthorized action without record content. Browser POST without valid CSRF/origin fails. Retained URLs, anonymous shares, deep links, old file capabilities and broad staff grants do not create participant ownership. Record actual denial/result without requiring an existence-leaking response. | Tester: PENDING; EN/TA/API/audit: PENDING; **NOT EXECUTED** |
| U14 | Sensitive export: authorized requester prepares an organization-filtered CRM export and a core aggregate report export, observes history/status, downloads before access expiry and reconciles row counts/metric definitions. | Current permission/requester scope is rechecked at execution/download; peer/revoked access fails. Interrupted creation is inspected through history before any new request. Bounded overflow fails explicitly; no partial-success claim. Formula-like CSV values are escaped. Aggregate exports exclude participant prose/identities and preserve period/cohort/source caveats. Audit records each export/download. | Tester: PENDING; EN/TA/CSV/reconciliation/audit: PENDING; **NOT EXECUTED** |

Execute the current approved entrepreneur scope as supplemental case U15: edit a
card/catalogue, preview, explicitly share, view anonymously, save/revoke and verify
the next anonymous request loses access; save/issue/download a decimal quotation;
complete a private contact follow-up. Verify issued snapshots, exact totals,
owner-only access, stale/lost-command recovery and no transfer to marketing CRM.
Quotations are private printable HTML, not statutory invoices. U15 tester/evidence:
PENDING; status: **NOT EXECUTED**.

## Cross-cutting execution matrix

These rows are required observations across the relevant journeys, not substitutes
for the connected domain evidence above.

| ID | Observation and pass condition | Evidence / status |
| --- | --- | --- |
| X01 | English and Tamil: approved labels/content/notices, validation, loading/error/empty/retry, preserved input and date/number presentation; record each language separately | Owner: PENDING; evidence: PENDING; NOT EXECUTED |
| X02 | Responsive web: critical public/owner/staff screens at 320/390 widths and desktop; keyboard-only flow, visible focus, labels, error association, dialog recovery, zoom and absence of obstructed controls | Owner: PENDING; evidence: PENDING; NOT EXECUTED |
| X03 | Assistive technology: supported desktop screen reader and Android TalkBack/iOS VoiceOver; reading/focus order, large text, live notices, manual attendance fallback and accessible upload/recovery actions | Owner: PENDING; platform evidence: PENDING; NOT EXECUTED |
| X04 | Native lifecycle: secure storage, rotation, second-session revocation, process death, offline logout, file picker/provider bounds, temporary-file cleanup, scanner cancellation/background and authorized deep links on both platforms | Owner: PENDING; platform evidence: PENDING; NOT EXECUTED |
| X05 | Service faults: actual Redis outage/restart, worker termination after claim, one-Beat verification, scanner unavailable/stale, exact object-version/key failure and ambiguous sender response; no duplicate effect, unsafe retry or fail-open bytes | Owner: PENDING; service evidence: PENDING; NOT EXECUTED |
| X06 | Security/operations: actual TLS/origin/proxy/upload boundaries, redacted logs, runtime DB privileges, restore/deletion/dispatch reconciliation and alert receipt by the agreed responder | Owner: PENDING; evidence: PENDING; NOT EXECUTED |
| X07 | Performance: owner-approved data volumes, user/endpoint mix and latency/error/resource budgets; measured public/API/worker/report behavior with scope-safe fixtures and no unsupported capacity claim | Owner: PENDING; approved budget/result: PENDING; NOT EXECUTED |

Follow the separate [native session](native-session-acceptance.md),
[native files](native-file-acceptance.md),
[native attendance](native-attendance-acceptance.md) and
[native compile CI](native-build-ci.md) packets. Android Play services supplies the
scanner UI; iOS camera permission is an application responsibility. A compile,
widget test, mock scanner or manual-code success does not close device rows.
FCM/SMS/WhatsApp or other unavailable provider capabilities stay unavailable until
their implementation, configuration and actual platform/provider evidence exist.

## Evidence, defects and decision

Use these fields for each observation:

```text
case_id / execution_reference:
status: NOT EXECUTED
tester / client witness: PENDING
source / image / config / schema / mobile identities: PENDING
language / platform / viewport / accessibility tool: PENDING
UTC start/end / synthetic actor and organization references: PENDING
steps / expected result / actual result: PENDING
redacted screenshot or log reference / digest: PENDING
persisted-state or minimal audit reference: PENDING
defect reference / severity decision owner / retest reference: PENDING
approver / decision / UTC decision time: PENDING
```

Use PASS only after observed success; use FAIL for an observed mismatch, BLOCKED
for a named missing prerequisite and NOT EXECUTED for work not attempted. Preserve
failed observations when retesting. No assumed approval, blank evidence, fixture
substitution or waived security assertion counts as a pass. Client/security owners
set defect severity, acceptance thresholds and waiver policy before approval;
engineering must not invent them to close a case.

Record only synthetic identifiers and minimal audit evidence. Exclude passwords,
tokens, raw QR payloads, provider credentials, capability URLs, document bytes and
unnecessary contact/prose from screenshots/logs. Keep any restricted evidence under
the approved custodian; issue reports carry references rather than private content.

Final UAT decision: **PENDING CLIENT APPROVER; NOT EXECUTED**. Required fields are
named approver, accepted scope, all required results/evidence, unresolved defects
and explicit treatment, artifact/environment identities and UTC decision time.
This decision does not grant production deployment permission. Continue with the
[training and handover packet](../deployment/training-handover.md) and obtain the
separate release decision required by the release checklist.
