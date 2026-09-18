# ADR 0002 — Person identity, scoped permissions and durable events

Status: proposed for the foundation implementation; bootstrap may prepare interfaces only.

Use a Person independent of login User to avoid duplicating leads/applicants/participants. Normalize verified account identifiers; candidate CRM matches need human or verified linkage. Model multi-program enrollments separately.

Roles are permission bundles, with scoped bindings and deny-by-default object access. Browser uses a same-origin Next.js BFF with opaque HttpOnly session cookie; tokens stay server-side. Mobile uses short-lived bearer access and rotated opaque refresh token in OS secure storage. PostgreSQL stores refresh hashes/family/revocation; reuse revokes family. BFF mutating routes enforce CSRF/Origin checks. Do not implement token persistence in browser localStorage.

Commit business data, audit and outbox atomically. Celery provides at-least-once execution; database dedupe and provider idempotency handle repeats. Redis loss must not lose business events. Cost is extra tables/dispatcher and explicit retry policy, preferable to lost notifications or implicit exactly-once claims.
