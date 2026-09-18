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
| Program Director | report.view/export, program.view, participant.view, selection.finalize | Authorized programs; exports explicit |
| Program Manager | program/cohort/enrollment manage, participant update, mentor assign | Assigned programs; cannot grant global roles |
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
