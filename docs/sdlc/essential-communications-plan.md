# Essential communications implementation plan

Prepared: 2026-10-24. Status: plan only, step 3 of the [six authorized local development steps](remaining-development-plan.md). Implementation starts after the background-job checkpoint and progress report. All work remains local; no real message, provider activation, collection policy, source publication or deployment is authorized.

## Current behavior and outcome

Identity verification/reset currently requires the encrypted local/test queue; `identity.service.delivery_available` rejects every staging/production request. This prevents real account entry/recovery even if an organization has no notification requirement. Identity delivery must remain global and independent of organization grants.

Enrollment atomically writes `enrollment.created` to `programs.models.DomainOutbox`, with organization, enrollment aggregate and an identifier-only JSON payload. Its current schema has a dispatched flag/timestamp but no consumer, attempt state or unsupported-event visibility. CRM notifications and helpdesk notices already have their own working in-app behavior; preserve those contracts and authorization.

The first accepted scope is working, configurable verification/reset email delivery plus a real enrollment-to-participant-inbox journey. This is the foundation for additional application/training events and channels, not evidence that email/SMS/WhatsApp/FCM all exist or that a local test sent an external message. Add further events only with explicit recipient and current-access rules; never broadcast arbitrary outbox payloads.

## Ordered implementation slices

### Global identity challenge delivery

- Keep verification/reset creation, hashed token, encrypted payload, audit and delivery intent in the same transaction. Reuse global user/challenge identity; do not require organization membership or CRM permissions.
- Preserve local CLI retrieval as an explicitly no-delivery development capability. Add an explicitly configured SMTP transport behind a capability-aware provider interface, disabled until approved configuration is supplied. SMTP is provider-neutral configuration, not an invented cloud API. Missing/disabled configuration fails unavailable outside local/test.
- API requests enqueue only. A bounded database dispatcher and worker deliver outside the request transaction. Store an immutable message identity, template edition, locale, attempts, safe provider reference/result, fences and timestamps; do not expose or log the destination, token, credentials, body or encrypted payload.
- Prepare versioned English/Tamil verification/reset templates. Make activation/copy approval explicit. Use configured canonical HTTPS action URLs in staging/production and reject unsafe origins/headers; never accept a browser-supplied redirect or sender. Local synthetic fixtures may use loopback URLs.
- Use a token-free canonical `/{locale}/account/verify` or `/reset` page plus the existing manually entered secret code for the first SMTP slice. Dedicated pages remain usable when another account is signed in; purpose comes from the fixed route. Consume only after an explicit POST. Never put the code in a URL, browser persistence, analytics or logs. Clear code/password after success. Preserve the existing account/intake navigation independently.
- Require explicit TLS configuration and certificate verification. Secrets remain server-side. Bound connection, read and total execution times, recipient count, message bytes and attempts. No cleartext credential fallback, arbitrary transport URL or catch-all success.
- Model accepted/sent only when the provider protocol proves acceptance; SMTP acceptance does not prove recipient delivery. Do not invent a delivery callback for a transport that has none.
- Preserve a proved final DATA acknowledgement even if later QUIT/connection cleanup fails. Never enable SMTP protocol debug output: it can expose message contents and credentials. Use the Python runtime's documented [SMTP/TLS behavior and exception categories](https://docs.python.org/3.13/library/smtplib.html), with controlled protocol peers verifying the adapter's actual classifications.
- Classify definite pre-acceptance transient/permanent failures separately from ambiguous delivery. A lost acknowledgement or worker loss after sending cannot trigger an automatic resend. Preserve a stable message identifier and an operator-review state; any reasoned recovery follows the documented capability and unchanged token expiry.
- Recheck current challenge consumption/expiry and current account state before sending. Suppress obsolete challenges, suspended accounts and ineligible purposes. An older verification/reset request cannot overwrite or expose a newer one. Fence late worker outcomes using a monotonic claim version/token.
- Configure approved message retention without a privacy default. Local/test fixtures use synthetic policies. Minimize retained challenge payloads according to the explicit lifecycle; retain only safe operational/audit metadata after disposal. Do not silently reinterpret a token's 30-minute validity as an approved business retention policy.

### Enrollment outbox and participant inbox

- Extend the existing outbox through one Alembic migration with bounded attempt/next-run/error/terminal state as needed. Preserve event identity, organization, aggregate and original payload. Keep unsupported events visible with a fixed reason; never mark them dispatched merely to clear backlog.
- Handle only the typed `enrollment.created` contract initially. Validate its aggregate and minimal identifier payload against current relational enrollment/application/participant rows. Resolve the recipient from the participant's current global user and organization access; client IDs cannot select a different recipient.
- In one transaction, create a deduplicated participant notification and settle the supported event. Enforce uniqueness on source event/recipient/topic. Duplicate tasks and concurrent dispatchers yield one accepted in-app notice, not duplicate inbox entries. A failed transaction leaves the event recoverable.
- Store topic, template edition, source identifiers and lifecycle metadata, not application answers, ticket text, document names or contact data. The UI renders approved localized copy and a safe allowlisted destination that reauthorizes the underlying object.
- Participant inbox/list/read/preference endpoints require current authenticated recipient ownership and relevant enrollment/access. Do not reuse CRM's `crm.lead.view` requirement for participants, or add staff access to participant-private data. Bound pagination and validate versions for read/preference mutations.
- Use a separate typed participant-notice table because the existing CRM notification resource has a real lead foreign key. Fix the initial topic rule to the owning active/completed enrollment plus current `participant.self`; suspended/withdrawn enrollment and revoked grants hide it. Use a single allowlisted schedule action kind instead of arbitrary links. An in-app preference suppresses future events without deleting earlier authorized history or backfilling suppressed events when re-enabled.
- Suppress or hide notices after account/access revocation according to the documented topic rule. Distinguish notice visibility in the inbox from external delivery. Apply explicit retention/expiry and bounded disposal without changing the source enrollment or audit evidence.
- Add English/Tamil web navigation and complete inbox loading/error/empty/read/preference states. Extend only the necessary BFF paths/query allowlists, preserving HttpOnly session cookies, endpoint CSRF tokens and origin checks. No generic notification/resource proxy.

### Operations and additional channels

- Add safe scoped failure visibility and reasoned recovery where required; preserve existing CRM/helpdesk operations. Show unsupported-event, retry-exhausted, ambiguous, expired and disabled-provider outcomes without copying sensitive payloads.
- API, workers and exactly one Beat share database/configuration. Queue payloads carry IDs only. Test duplicate messages, expired leases, worker loss, broker outage and retry exhaustion; direct function tests remain distinct from a real Redis/worker/Beat pass.
- SMS, WhatsApp and FCM require selected/approved providers, account ownership, templates/consent rules and verified capabilities. Keep them explicitly unavailable until implemented and configured. A stub must never be selectable as a successful production sender. Native push/device token and deep-link lifecycle follows the Flutter step.

## Required acceptance

| Case | Required observation |
| --- | --- |
| Registration/reset in configured external environment | Durable encrypted intent is created without request-path provider I/O; a configured worker can accept it through a controlled SMTP peer |
| Missing/disabled provider | Real-environment entry fails unavailable; no fake success, token or destination leaks |
| Message rendering | English/Tamil edition and safe action URL are correct; no header/HTML injection; byte limits enforced |
| Protocol outcomes | Accepted, definitive transient/permanent rejection and ambiguous acknowledgement have different truthful states |
| Challenge changes | Consumed, superseded, expired or suspended-user work is suppressed; token remains single use |
| Worker and delivery recovery | Fences reject late results; uncertain post-send work does not resend automatically; bounded explicit recovery preserves expiry |
| Enrollment event | Real domain transaction plus consumer yields exactly one owner notice; rollback, duplicate and concurrent cases preserve invariants |
| Unsupported or invalid event | Visible safe error; no false dispatched state or arbitrary resource access |
| Participant privacy | Peer, other organization, revoked/suspended and staff-without-topic-access reads/mutations fail |
| Inbox behavior | Real English/Tamil UI lists, marks read and changes preferences with versions, CSRF and usable recovery states |
| Retention | Explicit synthetic policy gates disposal; absent policy is not replaced with an invented default |

Run meaningful protocol/unit, guarded PostgreSQL/SQL-negative, API and web component/BFF/browser acceptance. Include migrations/drift, strict backend checks, deterministic contracts, web checks/build and final selected-source scan. Report actual commands/results and prepare a local source checkpoint before Flutter implementation.

## External acceptance boundaries

Controlled SMTP peers and injected adapters are protocol evidence, not a live email provider or delivery-to-recipient pass. Real sender/domain configuration, approved bilingual copy, transactional-consent rules, retention, callback verification where supported and provider sandbox/live evidence remain explicit. Redis/worker/one-Beat runtime, exact-revision CI, native push/devices, staging, UAT and release approval stay open until executed or supplied. Continue independent authorized local implementation without reporting these gates passed.
