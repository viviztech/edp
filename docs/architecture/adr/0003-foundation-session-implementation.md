# ADR 0003 ? Opaque sessions and incremental scope enforcement

Status: accepted implementation detail for F02/F03 continuation, consistent with master Section 5 token flows. Refines proposed ADR 0002.

Use cryptographically random opaque access/refresh/session tokens and SHA-256 hashes in PostgreSQL. Unlike JWTs, these need no signing key, issuer or audience claim verification; server-side lookup validates token kind, expiration, account status and revocation on every request. Access 10 minutes, refresh family maximum 14 days, configurable. Row locks serialize rotation; consumed refresh remains as replay evidence. No custom cryptographic algorithm.

Browser sessions live in the backend session service. Next.js holds a server-only BFF key and forwards an opaque HttpOnly cookie; it never returns mobile access/refresh tokens to browser code. State-changing BFF calls validate configured Origin and double-submit CSRF; authenticated backend calls additionally verify the session-bound CSRF hash. Cookie security uses explicit deployment setting, not NODE_ENV, so local production builds can be tested over loopback HTTP. Deployed environments must enforce Secure and HTTPS.

Only organization-scoped role bindings are implemented now. Program/center/assigned/self policies are reserved for relevant domain slices; no implicit broadening or arbitrary scope UUID. All initial role names seeded, with only implemented permission codes. Participant self account access uses authenticated identity, never a staff grant. Add domain-specific permissions with migrations/tests.

Authentication email requests persist an encrypted token payload in a durable restricted delivery table alongside token hash and audit. Fernet key is environment supplied; public responses contain no delivery token. Local CLI can inspect the queue only in local mode; production requests are disabled until an approved provider adapter is implemented. This is a testable delivery seam, not a claim of email integration. Do not send real mail during foundation work.

References: https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html ; https://argon2-cffi.readthedocs.io/en/stable/howto.html ; https://nextjs.org/docs/app/api-reference/functions/cookies .
