# Process 4 / communications and background jobs

Prepared: 2026-10-23. Status: next-process plan; implementation starts after the complete Process 3 local acceptance checkpoint and owner progress notification. All work remains local. No external message, provider activation, push or deployment is authorized by this plan.

## Existing behavior and concrete gaps

CRM already has two in-app notification topics, versioned preferences, current-recipient suppression, bounded dispatch, three delivery attempts, retention and audited replay. Here, delivered means visible in an authorized inbox. Helpdesk notices are committed synchronously with ticket events and are reauthorized against current ticket access; their separate retention policy remains open. Authentication messages are encrypted local/test artifacts for CLI retrieval; external-environment delivery deliberately fails unavailable. No email, SMS, WhatsApp or FCM sender currently exists.

Enrollment atomically writes `enrollment.created` to `domain_outbox`, but there is no consumer. CRM export jobs have a specific durability gap: the API commits queued work before broker publication, and the worker commits running before generation. A crash between these steps can strand a job indefinitely. The worker also needs current requester status/export permission checks. Existing CSV escaping tests do not establish crash or broker recovery.

## Ordered slices

1. **Recover existing CRM export jobs.** Add bounded rediscovery of retained queued jobs and expiring fenced execution leases. Duplicate, delayed and stale tasks cannot complete another lease. Recheck current requester status, organization and export permission before generation/completion and preserve current download authorization. Use IDs in task payloads and safe failure codes/audits. Keep existing CSV escaping and output limits. Honor existing access expiry; physical disposal requires an explicitly configured approved policy rather than an invented retention default. Add bounded attempts and explicit, reasoned recovery where needed.
2. **Complete the minimal event-to-notification lifecycle.** Review the existing enrollment outbox and define one explicit supported event/recipient/topic at a time. Preserve atomic business transaction + event creation, database deduplication, bounded claims, retry/replay, current recipient access, expiry and preferences. Unsupported events must remain visible for operations rather than being silently marked dispatched. Avoid copying application answers, ticket text, document names/content or contact details into event payloads.
3. **Prepare approved channel integration.** Establish versioned bilingual template identity, destination/consent scope, bounded attempts, provider references, signed/validated callbacks, idempotency and ambiguous-response reconciliation before adding an external adapter. Authentication's global identity scope must remain separate from organization domain grants. Select a sender/provider and approve copy, transactional-consent rules and retention before any real delivery. Missing configuration fails unavailable; test transports never masquerade as production success.
4. **Accept the runtime and operating workflow.** Exercise the real Redis broker, worker and exactly one Beat scheduler in isolated infrastructure: queue round trips, duplicated tasks, broker outage/recovery, worker termination after claim, lease expiry, retry exhaustion, authorized replay and monitoring. Preserve scoped operator permissions and redact destinations/tokens/provider payloads in logs. Native push/device lifecycle follows the mobile process.

## First-slice acceptance

Use isolated synthetic PostgreSQL and deterministic clocks/leases without weakening database guards. Cover commit-before-publish recovery, a failed broker publication, death after claim, concurrent workers, stale completion, revoked/suspended requesters, expired output and CSV correctness. A state/version/lease invariant must also survive direct SQL negative cases. Regenerate contracts only if the public shape changes; run affected API/static checks and current web checks if its behavior changes. Prepare a local source checkpoint and report the actual evidence before the next slice.

A direct task-function test is not a broker/worker/Beat runtime pass. Compose already declares those processes and its smoke script probes the queue, but this workstation has no accepted Redis/container runtime. Continue independent local implementation and record the unexecuted runtime gate clearly. Existing npm security findings, remote CI, real provider credentials, approved notification/helpdesk retention, staging, UAT and production release remain open.

## Subsequent sequence

After Process 4 local implementation/acceptance, continue Flutter applicant/student/alumni workflows, staging/operations and launch acceptance, then approved P1 business tools. Real provider, native-device, staging and release approvals remain explicit boundaries; local implementation evidence does not substitute for them.
