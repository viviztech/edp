# Essential communications checkpoint

Recorded: 2026-10-24 (Asia/Calcutta). Step 3 is locally accepted after the background-job checkpoint `679ebdc` and its owner progress report. Implementation and local integrated acceptance are complete; external runtime and release gates remain open. No real message, provider activation, collection-policy change, source publication or deployment was performed.

## Delivered behavior

- Global verification/reset creation keeps the challenge hash, encrypted delivery intent and audit atomic, without organization grants or request-path provider I/O. Local/test development mode remains an explicit no-delivery queue.
- Configured SMTP supports verified implicit TLS/STARTTLS, bounded DNS/connect/read/total time, an immutable message identity and versioned English/Tamil plain-text templates. The code is entered on a fixed token-free verification/reset page; GET consumes nothing. Tamil wire content is quoted-printable and the initial adapter supports ASCII envelope addresses.
- Preparing and sending claims are version/token/deadline fenced. Definite pre-acceptance failures can retry within the cumulative budget; interrupted sending or uncertain DATA acknowledgement remains ambiguous for explicit operator reconciliation. Accepted DATA survives failed QUIT. SQL prevents ambiguous work being disguised as a retryable failure.
- Bounded dispatch, recovery and approved payload disposal retain safe operational/audit evidence. Trusted global health/inspect/recover commands expose no destination, code, body, encrypted payload or credentials. Development messages are never silently promoted to SMTP delivery.
- Typed `enrollment.created` consumption validates exact relational identity/current access and atomically commits one deduplicated participant notice or suppression with source settlement. Unknown/invalid/expired/exhausted work remains visible. Deferred SQL pairing rejects orphan notice commits.
- The participant inbox is separate from CRM/helpdesk. It has current owner/enrollment checks, bounded keyset pagination, exact-version read/preference mutations, safe schedule actions and approved expiry disposal. Broad staff grants alone do not grant a participant inbox. Opt-out affects future events without erasing authorized history or backfilling suppressed events.
- English/Tamil web challenge and inbox pages include endpoint CSRF/origin protection, closed BFF paths/query sets, loading/error/empty states, preserved input and explicit reconciliation of uncertain writes. No secret appears in an action URL or ordinary browser storage.

## Database, configuration and rollout

Revisions `o0e6f2a8b345` and `p1f7a3b9c456` extend authentication delivery/outbox state and add participant notices/preferences. The full metadata contains 130 model tables. Existing legacy development auth messages remain development-only. Preserve the existing CRM/helpdesk contracts.

API, worker and exactly one Beat share the documented configuration. SMTP activation requires complete sender/origin/TLS credentials, explicit template approval and `AUTH_DELIVERY_RETENTION_DAYS`; defaults do not send mail. Participant notices require separate `PARTICIPANT_NOTIFICATION_RETENTION_DAYS` for dispatch. No real privacy policy is inferred from a token/access expiry or synthetic test setting. Stop/drain old writers, apply the release migration and start the matching revision; no mixed-version rolling compatibility or destructive production downgrade is claimed.

## Verification ledger

| Check | Evidence/result |
| --- | --- |
| SMTP protocol/templates/config | 20 controlled-peer/pure tests pass: implicit/STARTTLS, trusted/untrusted TLS, MAIL rejection before RCPT/DATA, accepted DATA with failed QUIT, lost/malformed acknowledgement, definite 451, total deadline, ASCII wire/Tamil content and token-free URLs; `.local/auth-mail-protocol-20261024.xml` |
| Focused PostgreSQL | Initial combined run: 72 passed and one staff-list boundary failure. The own-participant-profile boundary was corrected without removing the assertion; final affected rerun: 18 passed, `.tool-cache/communications-backend-20261024-54f232d6/` |
| Full API regression | 368 passed, one POSIX-only skip, four upstream deprecation warnings in 797.38 seconds; `.tool-cache/communications-backend-20261024-3fe52a12/`. The skip remains a Linux acceptance gate |
| API static/dependencies | Ruff/format pass for 243 files, strict MyPy passes for 140 sources, `pip check` passes |
| Final migration | Fresh base/head/base/head and unfiltered zero drift across 130 models after the SQL guard fixes; all five recorded model/migration hashes match final source; `.local/communications-migration-acceptance-9090545b.json`; newly owned database dropped |
| Web | All 464 tests pass, ESLint, TypeScript and production build pass; `.local/communications-web-latest.json`. All commands completed before a console-encoding failure while printing the build tail; final evidence was recovered from the successful exit codes without rerunning completed checks |
| Contracts | Current OpenAPI generation is deterministic and matches the saved contract after platform line-ending normalization; web uses regenerated component types and whitespace checks pass |
| Connected communications browser | `.local/communications-acceptance-52384aa0.json` passes against unchanged artifact `q-fzOtP4NriOzmoxzB42B`; fixed verify/reset while another account is signed in, old password rejection, real enrollment transaction, exactly one notice, read/opt-out/no backfill, CSRF/current-grant revocation and English/Tamil 390/1280 keyboard layouts. No JavaScript errors |
| Existing foundation regression | `.local/communications-foundation-acceptance-d398bfb5.json` passes identity/CMS/applications/selection/enrollment/learning/attendance/mentoring/business-plan/tracking on the same unchanged artifact. Its isolated database and owned servers are distinct from the API suite |
| Visual review | English desktop and Tamil mobile inbox screenshots inspected; controls and content remain contained. This scoped review is not native or full screen-reader acceptance |
| Dependency audits | Fresh unsuppressed runtime 61/development 101/npm 795 package audits: zero findings and no skips/ignores; `.local/communications-audit-summary-21512801.json`. Initial sandbox network failures remain historical; approved read-only audit retry passed |
| Source secrets | Final selected-source evidence: `.local/essential-communications-latest-source-scan.json`; local acceptance requires exit zero and zero findings after documentation/source stabilize |

The initial communications browser fixture used an email domain rejected by the real email validator; synthetic addresses were corrected to the reserved example.com domain. No validation was weakened. The fixed manual-code form removes its cleared inputs after success; browser assertions verify that behavior and the completion message.

## Remaining gates and continuation

Controlled SMTP peers establish the exercised wire protocol only. Direct task-function/browser acceptance establishes database/API/UI behavior only. Real sender/domain/content/consent/retention approval, recipient delivery evidence, Redis/worker/one-Beat outage/crash acceptance, Linux confinement, native devices, exact-revision remote CI, staging, UAT and production approval remain open. Docker/Redis/WSL are unavailable on this host. No SMS/WhatsApp/FCM adapter or push-device registration is implied by this slice.

After final regression/source checks and the local checkpoint report, continue [Flutter domain journeys](flutter-domain-plan.md) in the authorized order. SDK preflight runs Flutter 3.47.0/Dart 3.13.0 from the existing workspace cache; it is not mobile-domain or native-device acceptance.
