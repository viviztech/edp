# Essential communications boundaries

Implementation follows the [accepted plan](../sdlc/essential-communications-plan.md). Identity challenge delivery is global and has no organization or domain grant dependency. Enrollment notices have a separate typed participant model; the existing CRM and helpdesk notification contracts remain intact.

## Global identity delivery

Verification/reset requests persist the hashed challenge, encrypted delivery payload and audit in one transaction. The API never contacts a sender. Development is explicitly a no-delivery capability and is rejected outside local/test. SMTP requires explicit activation, complete verified TLS/sender/origin configuration, approved templates and configured retention. English/Tamil messages contain a code plus a fixed token-free account route. GET never consumes a challenge.

A worker first claims preparing work with a version/token/deadline, then commits a sending marker before the external effect. Definitive pre-acceptance failures can retry with bounded attempts. An ambiguous acknowledgement or worker loss after the sending marker requires operator review and cannot trigger an automatic resend. A proven final SMTP DATA acceptance survives a later connection-cleanup failure; it does not prove recipient delivery. Tokens, destinations, payloads and credentials are excluded from logs and task results.

Protocol behavior is grounded in the official Python 3.13 [smtplib](https://docs.python.org/3.13/library/smtplib.html) and [TLS context](https://docs.python.org/3.13/library/ssl.html#ssl.create_default_context) interfaces. Local controlled peers and injected doubles establish only the exercised protocol behavior. They do not authorize an external sender or real message.

## Enrollment outbox and inbox

The supported event is `enrollment.created`. Its exact enrollment/application/participant identifiers are validated against current relational state. A locked transaction atomically creates one unique recipient notice or records suppression and settles the event; duplicate workers cannot commit duplicate notices. Unknown events remain visible with fixed safe reasons. Database failures roll back the transaction and preserve recoverability.

The owning active user needs current `participant.self` and an active/completed participant and enrollment. Inbox access repeats these checks. An allowlisted `schedule` action links only to the current organization schedule; the destination reauthorizes. Preference changes affect future delivery, do not erase authorized history, and do not backfill previously suppressed events. Notice reads/preferences require expected versions. Retention has an explicit setting and no invented privacy default.

## Local acceptance

Use guarded synthetic PostgreSQL databases, controlled SMTP peers, component/BFF tests, and a real browser journey on one final web artifact. Test duplicate events, rollback, unsupported payloads, expiry, revocation, preference suppression, version conflicts, lost responses and English/Tamil keyboard layouts. Queue payloads carry identifiers only. Real Redis/worker/one-Beat, approved senders/content/retention, devices, staging/UAT and release are distinct acceptance gates.
