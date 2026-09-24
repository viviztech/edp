# Security and RBAC architecture

Status: foundation authentication and organization-scoped authorization implemented; see [foundation report](../sdlc/foundation-auth-report.md) for verification and remaining production/device gates. Broader domain policies remain planned.

## Trust boundaries and controls

Untrusted browser/mobile/provider input crosses TLS edge into typed API/BFF. DB, Redis, workers and object buckets are private. Every request checks account active status, permission and resource scope; object IDs are not proof of access. Queries apply scope before pagination/aggregation. Deny missing bindings, expired assignments and incompatible center/program relationships. Role changes revoke sessions or force permission re-resolution immediately.

Argon2id through maintained library; calibrated cost, no custom crypto. Hash reset/verification/refresh tokens at rest; reset tokens single-use with expiry. ADR 0003 selects opaque access tokens: hash lookup validates token kind, expiry, account status and revocation instead of JWT claims; default candidate TTL 10 minutes and refresh 14 days configurable, pending review. Refresh rotation uses row lock and one-use constraint; replay revokes the family transactionally. Logout revokes current/all sessions. Password reset/suspension revoke all. Do not issue authenticated sessions for pending/unverified accounts. Rate-limit login/reset by normalized identifier and source with generic errors to reduce enumeration; privileged MFA architecture reserved.

Browser BFF: opaque HttpOnly SameSite cookie, Secure in TLS environments; no browser-readable refresh/access tokens. Server session references encrypted token material or server session service, not client localStorage. CSRF token and strict Origin validation for mutations, rotate on login. Mobile: in-memory access token, refresh in OS secure storage, single-flight refresh, clear on logout/revocation; never log headers or persist sensitive document cache.

## Initial permission bundles

Configurable seed roles, no role-name conditionals. `view`, `create`, `update`, `publish`, `assign`, `export`, `review`, `finalize`, `issue`, `manage` remain distinct permissions. No implicit wildcard role grants.

| Role | Initial permission family | Scope / exclusions |
|---|---|---|
| Super Admin | Explicit complete permission catalog, system.manage, audit.view | Organization; separately provisioned, MFA-ready; actions audited |
| Program Director | application.form.view/create/update/publish, report.view/export, program.view, participant.view, selection.finalize | Authorized organizations/programs; application publication and exports explicit |
| Program Manager | application.form.view/create/update, program/cohort/enrollment manage, participant update, mentor assign | Assigned organizations/programs; cannot publish application policy or grant global roles |
| CRM Executive | crm.lead.view/create/update, follow-up manage | Assigned leads; assign/export separate grants |
| Marketing Executive | campaign manage, attribution reports | Campaign scope; no applicant documents |
| Selection Committee | application.view/review, selection.score | Assigned reviews; no finalization by default |
| Trainer | lms.course.manage, attendance.manage, assessment.manage | Assigned courses/cohorts; certificate.issue separate |
| Mentor | mentor.session/note/goal manage | Assigned participants, note visibility; no identity documents |
| Training Center Coordinator | schedule manage, attendance.manage, participant.view | Assigned center and cohorts |
| Funding Coordinator | scheme/funding/opportunity manage, funding.case.update | Assigned cases; no automatic approval decisions |
| Content Manager | cms.page.view/create/update/publish, media manage | Organization content; no participant PII |
| Support Executive | ticket.view/assign/update | Assigned queue/tickets; internal comments protected |
| Participant | own profile/application/learning/bookmark/ticket actions | Self and active enrollment; no staff notes |

Implemented binding stores organization; program/center scopes are deferred and not granted implicitly. Future binding design supports optional program/center; self/assigned are permission policy modes, not user-chosen filters. Cross-program users require independent bindings. Authorization test matrix: anonymous, inactive, wrong permission, correct permission/wrong scope, correct scope, revoked role, alternate channel and export routes.

## Threats and evidence

| Threat | Required prevention / proof |
|---|---|
| IDOR / mass assignment | Scoped repository reads; input DTO allowlists; cross-user/program negative tests |
| Credential theft / replay | Hashing, token rotation/revocation, CSRF, throttles, session tests |
| XSS / injection | React escaping, sanitized CMS allowlist, CSP, bound SQL, malicious-input tests |
| Forged/replayed webhook | Raw-body signature verification, constant-time secret comparison via library, inbox uniqueness |
| Malicious upload / SSRF | Private quarantine, type/size/signature checks, scanning adapter, fetch allowlist and private-address denial |
| Export/log exfiltration | Permission+audit, formula-safe CSV, expiring links, PII allowlist/redaction, no payload logging |
| Duplicate/lost jobs | Transactional outbox, unique dedupe, backoff, failure visibility, restart tests |
| Privilege escalation | No self-role assignment; catalog validation, scoped grants, reauthentication for consequential administration |

AuditLog records actor/system identity, action, object reference, scope, UTC timestamp, request ID, reason and allowlisted changed field names. No password/token/document/body values. Application runtime may insert but cannot mutate audit rows in deployment roles; security operator retention jobs separate. Critical write failure to audit aborts transaction. Read/export auditing where sensitive is explicit and tested. Audit access itself restricted.

Use environment/secret store references; no credentials in repo, client bundles or fixtures. CI secret/dependency/container scanning, restricted DB roles, approved deletion/anonymization, TLS, signed URLs, backup encryption, tested restore and incident runbook required before launch. Legal policy and retention require owner review; no jurisdictional compliance certification implied.

Implementation reference: [ADR 0003](../architecture/adr/0003-foundation-session-implementation.md). PostgreSQL trigger rejects audit UPDATE/DELETE. Production database ownership/GRANT separation remains a deployment gate; privileged table owners can bypass database protections. No public role-management endpoint; trusted operator CLI grants/revokes roles with audit.

## Meta provider boundary

Meta configuration requires explicit meta.integration.view/manage permissions in organization scope. Marketing Executive receives that bounded family; CRM permissions and applicant data remain separate. Provider access tokens and application secrets are encrypted with a dedicated Fernet key, verification tokens are hashed, and no secret appears in response schemas, browser code, Celery arguments, audit fields, or logs. Webhook POST bodies are capped before JSON parsing, authenticated with the exact raw-body SHA-256 HMAC and constant-time comparison, then deduplicated in PostgreSQL before dispatch. The worker accepts only an inbox UUID, sends credentials in the Authorization header to the fixed https://graph.facebook.com host, maps only configured fields, classifies permanent provider rejection separately from retryable rate-limit/server/network failures, and never automatically merges an existing identity.

Application definition administration separates view, create, update and publish permissions. Program Managers prepare drafts; Program Directors and Super Admins may publish. Published and retired titles/fields are protected by PostgreSQL triggers, and existing applicant drafts remain pinned to their original definition version.

## P01.1 program administration

Implemented permissions are program.view, program.manage, cohort.manage and application.cycle.manage at organization scope. Program Directors and Program Managers receive all four; Training Center Coordinators receive view only until center-scoped bindings exist. Composite database keys block cross-organization and cross-program links. Versioned state commands require audit reasons, and audit rows exclude bilingual names and application policy content.

## A01.4 submission controls

Applicants may list only currently open cycles in their organization and may read, save or submit only the application owned by their Person. UUID-shaped BFF route allowlists, session authentication, origin/CSRF enforcement, body limits and no-store responses constrain browser access. Submission locks the row, checks optimistic version and cycle/form scope, and commits acknowledgement references, non-PII application number, timestamp, history and allowlisted audit atomically. PostgreSQL triggers protect submitted evidence even outside the service. Audit excludes answer and policy text. Supporting documents and real-data use remain disabled until scanning and retention controls are approved.

## A02.1 selection controls

Implemented permissions are selection.cycle.view/manage, selection.rubric.manage/publish, selection.assignment.manage and selection.review at organization scope. Program Managers prepare cycles, rubrics and assignments without publication authority. Program Directors and Super Admins may publish. Selection Committee members can see only their own assignments and declare only their own conflict status. Assignment validates an active reviewer binding and never exposes applicant answers through the workspace DTO. Published policy is database-immutable; assignments pin a rubric version. The only enabled application transition is submitted to under_review on first assignment, with append-only history and an audit row that contains identifiers but no answers, criterion text or conflict note.
## A02.2 scoring and moderation controls

`selection.review` permits an assigned reviewer to edit only their own unsubmitted review after conflict clearance. `selection.review.moderate` is granted to Program Director and Super Admin, not Program Manager or Selection Committee. Reviewers receive neither other reviewers' assignments nor application aggregates. The API derives weighted totals from the immutable published rubric, rejects client-selected criteria and out-of-range scores, and uses optimistic versions on every command. Internal comments stay in the staff selection workspace and never enter applicant-facing application responses. Moderation requires a reason, preserves evidence and is audited separately from submission.

## A02.3 interview and finalization controls

`selection.interview.manage` and `selection.decision.manage` are granted to Program Managers, Directors and Super Admins. `selection.interview.score` is granted to Selection Committee, Directors and Super Admins and still requires exact panel membership. `selection.finalize` and `selection.decision.override` remain Director/Super Admin permissions. Every mutation checks organization scope and optimistic versions; terminal changes require an explicit override flag and reason. Reviewer/panel workspaces show only their own assignments and interviews and no decision history. Panel comments, review comments and scores remain staff-only. Audit rows record action, actor, resource, version and decision reason without copying comments or score payloads.

## P01.2 authorization

`enrollment.manage`, `participant.view`, `participant.update` and `schedule.manage` are organization-scoped staff permissions granted to Program Directors, Program Managers and Super Admins. `participant.self` is granted only to the Participant role and every query also matches `Participant.person_id` to the authenticated User. Conversion derives Person, program and cohort from the immutable selected application and finalized cycle. Training Center Coordinators do not receive mutation permissions until center/cohort bindings prevent organization-wide access. Participant responses exclude scores, comments, decision reasons and staff audit evidence.
