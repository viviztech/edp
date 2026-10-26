# Training, handover and rollback packet

Prepared 2026-10-26 (Asia/Calcutta). Status: **PREPARED; TRAINING, HANDOVER AND
DEPLOYMENT NOT EXECUTED**. This packet supplies exercises and evidence forms for
completion items 5/6. It does not appoint a person, accept a service level, activate
collection/delivery, attest training attendance or approve a release.

The [staging UAT packet](../testing/staging-uat.md),
[administrator guide](../user-guides/admin.md),
[participant guide](../user-guides/participant.md),
[staging runbook](staging.md), [incident runbook](incident-response.md) and
[recovery runbook](backup-restore.md) remain the operating references.

## Ownership and custody record

The client must replace each pending entry with a named owner, deputy, approved
contact/escalation reference and acceptance date in the restricted handover record.
Do not put personal contact details, credentials or private-key material in Git.
One person may cover several roles only after responsibilities and privileges are
reviewed; ownership never implies a blanket Super Admin grant.

| Responsibility | Custody and required decision | Current owner / acceptance |
| --- | --- | --- |
| Client release authority and UAT coordinator | Scope, required cases, defects, final UAT and separate deployment decision | PENDING OWNER; NOT EXECUTED |
| Program/selection lead | Intake/eligibility/document rules, rubric/conflicts/overrides, cohort capacity, attendance and certificate issuer/signatories | PENDING OWNER; NOT EXECUTED |
| Content and Tamil review | Organization/program wording, source-backed resources, independent EN/TA publication and update responsibilities | PENDING OWNER; NOT EXECUTED |
| Privacy/security authority | Approved consent/retention/deletion/sharing, legal holds, evidence custody, compromise and access decisions | PENDING OWNER; NOT EXECUTED |
| Platform/registry custodian | Hosting/domain/cost approval, TLS/DNS, immutable artifact registry, configuration and deployment access | PENDING OWNER; NOT EXECUTED |
| Database/recovery custodian | Separate owner/API/worker roles, backup custody, restore/deletion ledger, approved RPO/RTO and retention | PENDING OWNER; NOT EXECUTED |
| Storage/key custodian | Private bucket, exact versions, encryption/key recovery, scanner, holds and authorized disposal | PENDING OWNER; NOT EXECUTED |
| Queue/provider custodian | Redis/worker/one-Beat, dispatch receipts, sender/provider accounts, callback verification and ambiguous-attempt reconciliation | PENDING OWNER; NOT EXECUTED |
| Mobile/signing custodian | Approved app IDs/domains, Android signing and Apple/APNs accounts where applicable; device/platform evidence and store ownership | PENDING OWNER; NOT EXECUTED |
| Support/incident commander | Incident escalation, alert receipt, support boundaries, user communications and stabilization coverage | PENDING OWNER; NOT EXECUTED |
| Engineering maintainer | Source/CI/contracts/migrations, defect remediation, compatible rollback assessment and technical handover | PENDING OWNER; NOT EXECUTED |

Working hours, escalation times, support service levels, backup targets and
stabilization end conditions are **PENDING OWNER DECISION**. No numbers or named
contacts in local fixtures/runbooks establish those commitments.

## Candidate and prior-artifact inventory

Complete this inventory before rehearsal. An example manifest, mutable image tag,
unsigned simulator app or debug APK cannot identify an approved production release.

| Inventory item | Required recorded reference | Current state |
| --- | --- | --- |
| Candidate source and CI | Full revision, source digest, exact-revision CI URL/results, reviewed contracts and lockfiles | PENDING EVIDENCE |
| Application artifacts | Immutable API/web/edge image digests, provenance/SBOM and accepted scans; native artifact digests/build modes/platform results | PENDING EVIDENCE |
| Configuration | Non-secret configuration digest, approved origins/proxy settings, secret-store references and separate environment identities | PENDING EVIDENCE |
| Database compatibility | Current/target migration heads, populated migration evidence, runtime grants, compatible-writer assessment | PENDING EVIDENCE |
| Previous accepted release | Exact previous source/images/config/schema contract, retained accessible artifacts, verified custody and expiry | PENDING EVIDENCE; no prior production release assumed |
| Recovery materials | Approved backup/recovery point, dump/object-version inventory/digests, independent key custody and protected deletion/dispatch ledgers | PENDING EVIDENCE |
| Operations | Actual readiness/queue/storage/scanner/alert/restore evidence and assigned responders | PENDING EVIDENCE |
| Product and client acceptance | Approved policy/content editions, UAT decision, attended training and accepted handover | PENDING OWNER |

Use the [release manifest schema](../../infra/deployment/release-manifest.schema.json)
and [deployment input reference](../../infra/deployment/staging.env.example).
Preserve secret references and rotation/recovery instructions, not secret values.
Verify an independent authorized custodian can retrieve the needed materials in a
rehearsal; an inventory entry alone does not prove recovery access.

## Role-based training exercises

Schedule supervised exercises against the accepted isolated candidate with
synthetic actors and approved EN/TA content. Give each learner a distinct scoped
account. Record language, device/browser, candidate, trainer, learner, UTC times,
redacted evidence, observed result and follow-up action. Use the least-privileged
role that can perform the exercise; separate staff preparation from learner work.

| ID / learner role | Exercise | Demonstrated acceptance | Evidence / status |
| --- | --- | --- | --- |
| T01 Account/privileged operator | Provision the approved account/organization grant through the documented operator process; learner signs in, identifies current devices, revokes a second synthetic session and performs reset/logout. Review an audit entry without sharing credentials. | Learner distinguishes account status, organization grants and object ownership; revoked sessions fail and passwords/codes stay out of evidence. Privileged credentials are held separately. | Trainer/learner: PENDING; evidence: PENDING; NOT EXECUTED |
| T02 Content/Tamil editor | In Publishing workspace/Content studio, save separate language drafts, preview, publish one locale, inspect the public result, then archive with a reason and restore to draft. Show a stale-edit recovery. | Learner explains saved versus published content, language independence, permission limits and retention of history; no unreviewed copy or unverified media is published. | Trainer/learner: PENDING; EN/TA evidence: PENDING; NOT EXECUTED |
| T03 CRM/marketing assignee | Inspect a synthetic attributed lead, assign permitted work, create a due follow-up, read an in-app notice, prepare an export and recover its reference through history after an interrupted response. | Learner respects organization/assignee scope, explains queue/provider capability, avoids duplicate export commands and cannot download another requester's export. | Trainer/learner: PENDING; evidence: PENDING; NOT EXECUTED |
| T04 Reviewer/panel/director | Use separate assigned reviewer and panel accounts to score once, submit, shortlist/interview, make an authorized reasoned decision and finalize; demonstrate one denied conflicting/unassigned action. | Learner preserves submitted scores, reasons and decision history; only authorized decision roles override and applicants do not receive private scores/notes. | Trainer/learners: PENDING; evidence: PENDING; NOT EXECUTED |
| T05 Program manager/coordinator | Enroll a finalized selected applicant, inspect capacity and participant timeline, create a bilingual session and demonstrate a coordinator's single-center/cohort boundary and revocation. | Learner avoids duplicate person/enrollment creation, recognizes event/inbox boundaries and cannot operate another center/cohort. | Trainer/learners: PENDING; evidence: PENDING; NOT EXECUTED |
| T06 Trainer/attendance staff | Review published learning rules, grade an owned assignment, inspect progress, open/close a QR window and make a reasoned correction; show certificate eligibility and route issuance to the permitted role. | Learner cannot rewrite published/graded evidence, bypass eligibility or act outside assigned cohorts; correction retains its prior value. QR secrets are not retained in evidence. | Trainer/learners: PENDING; evidence: PENDING; NOT EXECUTED |
| T07 Mentor | Read assigned participant material, distinguish shared/private notes, complete an action/session and review the latest submitted business-plan snapshot; request changes and observe a revised submission. | Learner does not expose private notes, review an unassigned participant or copy stale feedback onto another snapshot. | Trainer/learner: PENDING; evidence: PENDING; NOT EXECUTED |
| T08 Resource/funding owner | Review an official source/verification date and independently publish EN/TA entries; owner participant saves a resource and advances a funding case using valid transitions. | Learners distinguish a source listing from an award promise; disbursement follows approval and staff read access does not imply owner write access. | Trainer/learners: PENDING; EN/TA evidence: PENDING; NOT EXECUTED |
| T09 Support assignee | Claim/assign a synthetic ticket, post a shared reply and a separate private note/file, wait/resolve and perform permitted reopen; reassign and inspect loss of access. | Learner respects visibility, current assignment and clean/bound attachment rules; uncertain replies require reading saved state before retrying. | Trainer/learners: PENDING; evidence: PENDING; NOT EXECUTED |
| T10 Applicant/student/alumnus | On web and Android/iOS, save/submit application evidence, recover interrupted learning/attendance work, use support and notifications, record private business/follow-up and independent impact observations. | Learner recognizes authoritative saved states, immutable evidence, unavailable services and lifecycle access; offline logout makes no server-revocation claim. Record actual platform exercises separately. | Trainer/learners: PENDING; EN/TA/platform evidence: PENDING; NOT EXECUTED |
| T11 Entrepreneur | Preview/share/revoke a synthetic card/catalogue, issue a decimal quotation and complete a private contact task. Inspect the next anonymous request after revocation and an owner-only artifact download. | Learner understands explicit sharing, revocation limits for already exported copies, immutable issued snapshots and separation from marketing CRM; no statutory-invoice claim. | Trainer/learner: PENDING; evidence: PENDING; NOT EXECUTED |
| T12 Reporting/management | Apply scoped dates/cohort filters, inspect metric definitions/coverage/caveats, reconcile source totals and export an aggregate report. Compare compatible baseline/outcome editions. | Learner distinguishes unavailable from zero, self-report from verified/causal impact and aggregate reporting from disclosure of private records. | Trainer/learner: PENDING; evidence: PENDING; NOT EXECUTED |
| T13 Operations/security responder | Rehearse the incident, rollback and restored-dispatch exercises below, identify own permissions and evidence custody, and route a decision to the designated owner. | Responder finds the exact artifact/runbook and explains the stop/reconcile/restart decision without clearing queues, weakening guards or exposing secrets. | Trainer/responders: PENDING; evidence: PENDING; NOT EXECUTED |

A demonstration by engineering is not proof that the receiving learner can
operate the system. Record the learner's independent repeat and questions. A
tabletop discussion can validate understanding but cannot replace actual native,
service, restore, alert or deployment evidence. Do not mark absent learners as
trained. Required attendees, pass criteria and any retraining are owner decisions.

## Compatible rollback rehearsal

Rehearse only in an explicitly approved isolated environment. The sequence below
is a decision/checklist packet, not authority to mutate a live system. Execute
the environment-specific commands from reviewed operator runbooks only after the
target, privileges, change window and rollback decision have been approved.

| ID | Required observation and decision | Owner / evidence / status |
| --- | --- | --- |
| R01 | Identify the incident/failed acceptance trigger; record candidate and prior accepted image/config/source identities and the decision maker. If no accepted compatible prior artifact exists, stop and choose a reviewed roll-forward or isolated recovery plan. | Owner: PENDING; evidence: PENDING; NOT EXECUTED |
| R02 | Prove the prior API/web/worker can read/write the actual target schema and honor current immutable state/guards. Review migration compatibility and newly required worker grants. The CRM recovery migration already requires matching writers; disposable downgrade evidence does not authorize mixed-version deployment. | Engineering/database owners: PENDING; evidence: PENDING; NOT EXECUTED |
| R03 | Route traffic to the approved maintenance boundary; stop the one Beat, drain/stop relevant workers under the reviewed grace policy, pause affected collection/senders and preserve leases/outbox/provider evidence. Handle callback ingress through the approved provider runbook; never acknowledge work as accepted without durable acceptance. | Operations/provider owners: PENDING; evidence: PENDING; NOT EXECUTED |
| R04 | Select the reviewed compatible immutable application/configuration. Preserve the live database and evidence. Do not routinely downgrade schema, drop/truncate tables, remove trigger guards, clear Redis queues or overwrite an existing database as a rehearsal. | Release/database owners: PENDING; evidence: PENDING; NOT EXECUTED |
| R05 | With outward effects still disabled, verify readiness, representative actor scopes, file/object access, audit continuity and exact source/config/schema identity; reconcile pending/ambiguous dispatch using the matrix below. | Engineering/security owners: PENDING; evidence: PENDING; NOT EXECUTED |
| R06 | Obtain the named owner's approval for controlled traffic restoration, then restart only the approved workers and one Beat. Observe actual round trip, due-age/error trends and alert receipt; retain elapsed times and unresolved losses without inventing an SLA. | Incident/release owners: PENDING; evidence: PENDING; NOT EXECUTED |

Record start/end/recovery UTC timestamps, original and recovered artifact/config
identities, actions, authorized actors, observed smoke/negative results, outstanding
losses and client decision. A successful application rollback does not establish
database/object recovery or retrospectively approve the failed candidate.

## Restore, deletion and dispatch reconciliation exercise

Keep outbound effects, access and disposal paused during a restore rehearsal.
Follow the [backup/restore runbook](backup-restore.md) in a fresh isolated target;
local guarded drill tooling is restricted to its documented synthetic loopback
databases and is not a general production restore command.

| ID | Exercise and acceptance evidence | Owner / evidence / status |
| --- | --- | --- |
| D01 | Verify backup/dump digest, UTC recovery point, compatible schema/config, exact object versions/lengths/hashes/encryption and independent key custody. Missing versions/keys stay unavailable; a newer object is not substituted for immutable evidence. | Database/storage custodians: PENDING; evidence: PENDING; NOT EXECUTED |
| D02 | Recover the independently protected post-backup deletion/withdrawal/revocation/disposal ledger. Apply approved later decisions before access, preserving holds/frozen evidence and minimal audit references. No disposed bytes or revoked grants are resurrected. | Privacy/recovery custodians: PENDING; evidence: PENDING; NOT EXECUTED |
| D03 | Reconcile restored jobs against the durable database event/idempotency state and available provider receipts; classify unknown effects as ambiguous. Verify old lease/version claims cannot overwrite a later settlement. | Queue/provider custodians: PENDING; evidence: PENDING; NOT EXECUTED |
| D04 | Reapply reviewed separate owner/API/worker grants and validate denied privileges. Verify current recipients/consent/ownership, audit continuity and authorization negatives before enabling access, sends or a single scheduler. | Database/security custodians: PENDING; evidence: PENDING; NOT EXECUTED |
| D05 | Measure restore plus validation duration, backup age/recovery point and unresolved losses; compare only with explicitly approved RPO/RTO. Record target cleanup/custody and acceptance decision. | Recovery/client owners: PENDING; evidence: PENDING; NOT EXECUTED |

Use the supported workflow for each recovered job type:

| Work type | Operator decision rule |
| --- | --- |
| Authentication SMTP | Use trusted global health/inspect diagnostics without exposing destinations/codes. Ambiguous attempts can be reasoned accepted/failed at the exact current version; they cannot be retried as fresh work. Definite failed delivery can retry only while the challenge/account/configuration and cumulative budget remain eligible. SMTP acceptance is not recipient delivery. |
| CRM export | Let fenced durable recovery handle eligible queued/expired claims. Current requester permission, access expiry and byte/row bounds still apply. Failed terminal work is investigated before an explicit new export; do not reset terminal rows or guess a lost creation reference. |
| Meta lead intake | Match the existing provider event and mapping. Review safe failure/current version before authorized replay; exhausted expired leases settle without another provider call. Duplicate callbacks must not create duplicate leads. |
| Enrollment/CRM/helpdesk inbox | Retain source uniqueness and supported visibility/preferences. In-app availability is not a provider receipt. Do not backfill previously suppressed events or use a staff operations grant to inspect another participant's inbox. |
| Private files | Reconcile the exact upload/scan/disposal lease and policy version. Missing or unverified bytes fail closed. A timeout does not approve another byte write, a clean scan or disposal of held/frozen evidence. |
| Any unsupported external channel | Record unavailable capability and assigned follow-up. Never mark a fake/no-delivery adapter as sent/delivered or infer SMS/WhatsApp/FCM acceptance from an in-app record. |

Do not insert/update database rows by hand to manufacture a delivery receipt or
policy approval. Preserve ambiguous/unmatched evidence under restricted custody
and obtain the designated operator/provider decision. Encryption-key rotation must
cover retained records and backups; replacing an environment value alone is not
a recovery or rotation plan.

## Handover and release decision

| ID | Required handover item | Receiver / evidence / status |
| --- | --- | --- |
| H01 | Receiver can locate the exact source/CI/contracts/artifacts, current guides and their maintenance owner | PENDING OWNER; evidence: PENDING; NOT EXECUTED |
| H02 | Role provisioning/privilege review completed with separate privileged access and credential custody | PENDING OWNER; evidence: PENDING; NOT EXECUTED |
| H03 | Required learners completed independent EN/TA/platform exercises and unresolved training issues are assigned | PENDING OWNER; attendance/observations: PENDING; NOT EXECUTED |
| H04 | Hosting/domain/recurring costs, provider accounts, app IDs/signing and renewal/rotation/recovery custodians accepted | PENDING OWNER; references: PENDING; NOT EXECUTED |
| H05 | Actual backup/restore, object/key, deletion/dispatch reconciliation and compatible rollback rehearsal accepted | PENDING OWNER; measurements/decision: PENDING; NOT EXECUTED |
| H06 | Alert destinations tested with actual receipt, named incident responders and agreed escalation/coverage | PENDING OWNER; evidence: PENDING; NOT EXECUTED |
| H07 | Client UAT/security/privacy/content decisions recorded against this candidate and unresolved defects explicitly treated | PENDING OWNER; decisions: PENDING; NOT EXECUTED |
| H08 | Stabilization owner, support route, defect intake, observation period and exit criteria agreed | PENDING OWNER; agreement: PENDING; NOT EXECUTED |
| H09 | Separate deployment target/window, candidate identities, accountable approver and go/no-go decision recorded | PENDING RELEASE AUTHORITY; decision: PENDING; NOT EXECUTED |

For each accepted handover item record giver, receiver, UTC time, scope, artifact
identity, redacted evidence reference, outstanding action and its owner. Approval
must come from the actual designated person; a prepared checklist or engineering
statement does not supply it. Keep UAT, operational custody and deployment approval
as distinct decisions. All unchecked requirements in the
[release checklist](../sdlc/release-checklist.md) remain open until evidenced.
