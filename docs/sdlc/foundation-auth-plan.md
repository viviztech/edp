# Foundation authentication slice ? F02/F03

Authorized continuation of Milestone 1; no business modules. Follow master Sections 5,25,35,38. Acceptance gates below precede implementation.

- Person/account separate; normalized unique email, account pending/active/suspended/archived. Registration never accepts staff role or scope. Passwords Argon2id, 12?128 characters.
- Verification/reset are single-use, expiring and purpose-bound; request responses do not reveal existence. Development delivery encrypted at rest; no public token retrieval; production delivery disabled until adapter configured.
- Mobile short-lived opaque access plus refresh rotation. Reusing a consumed refresh token revokes the entire session family, including its current access token. Logout current/all; account suspension and role revocation effective immediately.
- Browser BFF exposes no access/refresh credentials to JavaScript. Backend-backed opaque HttpOnly cookie; Origin + CSRF checks, bounded body and fixed route allowlist. Browser-to-backend internal endpoints require server-only BFF key.
- Configurable role/permission tables. First implemented scope is organization. Program/center scopes stay denied until their domain models arrive; no unvalidated generic scope IDs. Seed all master role names; permissions only for implemented actions. No self-escalation.
- Staff entry and audit list require explicit organization permission. Audit log append-only through PostgreSQL trigger; successful identity changes and session revocations audited in transaction. Audit payload contains no credentials or private content.
- PostgreSQL-backed atomic throttles survive process restarts. No in-memory-only login limiter. Failed authentication stays generic; account and source limits.
- English/Tamil web/mobile registration, verification, reset, sign-in, account/session/logout states; admin shell authorized server-side. UI includes loading, empty and error states.
- Tests: real PostgreSQL migration cycle; duplicate registration; pending account denied; verification expiry/reuse; reset invalidates sessions; refresh race/replay; inactive account; missing/wrong-org permission; audit append-only; CSRF/origin/token leakage; Flutter secure storage and session handling.
- Lint/type/tests/builds, contract regeneration and documentation. Live CI, Docker and native-device gates remain unpassed until executed. Do not claim full Milestone 1 complete from unit tests.
