# Meta integration contract plan

Disabled until business/app ownership, permissions and credentials are supplied. Use official Graph API and validate capabilities/version against Meta documentation during C03. No invented provider fields or delivery guarantees.

Verification endpoint compares configured verify token and returns challenge only on matching mode/token. POST verifies signature over raw bytes before parsing; persist inbox with provider event/lead ID uniqueness. Fetch permitted details in worker, map through versioned form mapping, record attribution and candidate duplicate contacts; no auto-merge from shared contact. Transaction includes lead mutation, audit and outbox. Bounded retries for safe transient failures; auth/permission failures visible to administrator. Store secret references only, redact payloads, configure approved raw-metadata retention before ingestion. Tests cover forgery, duplicate/concurrent delivery, unknown mapping, permission expiry and safe replay.
