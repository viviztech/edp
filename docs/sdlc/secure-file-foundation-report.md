# Process 3 / secure-file foundation checkpoint

Recorded: 2026-10-23. Scope: the first slice of the [secure-files plan](secure-files-plan.md). Process 3 remains in progress. The owner selected configurable rules; there are no approved real document/retention defaults, and collection and maintenance remain disabled. This checkpoint does not provide a generic upload/download API. All commits remain local; no push, provider activation or deployment occurred.

## Implemented

- Organization/purpose-specific policy editions with explicit bilingual notice, MIME, count, size, retention and frozen-disposal rules. Publication retires the previous edition; published contents remain immutable. Scoped view/manage permissions are seeded only for Super Admin and Program Director. Mutation reasons and edition changes are audited.
- Shared file metadata, immutable typed domain context, normalized request replay, expected/verified byte identity, upload and scan leases, bounded scan retries, holds, frozen evidence, expiry and metadata-preserving disposal. PostgreSQL constraints and triggers enforce the stored lifecycle evidence.
- Confined local storage and checksummed/version-pinned private S3 adapters; exact bytes are verified before use. ClamD protocol adapter fails closed. Interrupted-write recovery verifies recorded opaque keys without arbitrary key deletion or bucket listing.
- Lazy runtime factories, bounded raw-body buffering, safe private attachment snapshots and individually bounded background jobs. Policy metadata is capped at 64 KiB in the API/BFF; existing enquiry and other JSON limits remain unchanged.
- English/Tamil policy administration with blank rule inputs, exact lost-create replay, stale-version preservation, immutable edition copying, explicit recovery and view-only access. Publication does not toggle collection.

## Local evidence

The full API run recorded **228 passed, one POSIX-only skip and one new worker-test fixture error**, with two upstream deprecation warnings. That test was corrected to register its imported authorization fixture and use expired synthetic retention against the database's own clock. The subsequent foundation/configuration rerun passed 27 cases; the corrected real worker lifecycle test then passed independently, including duplicate scan, hold denial and expiry disposal. No production clock or guard was weakened. Foundation database coverage includes scoped policy immutability, concurrent replay/claims, real byte/hash/type checks, lease fencing, scan failure, legal holds, frozen disposal and crash/late-completion recovery.

Migration `h3d9e5f1a678` passed upgrade → downgrade to `g2c8d4e0f567` → upgrade and Alembic drift checks on guarded PostgreSQL. The repository-wide API Ruff check/format passed for 199 files and strict MyPy passed for 115 source files. Adapter tests exercise real Windows confinement, botocore Stubber and a loopback fake ClamD protocol peer; no provider is contacted. The platform-specific skip is the POSIX temporary-directory permission/symlink test and remains a Linux acceptance requirement.

The full web suite passed **337 tests in 62 files**, followed by clean ESLint and TypeScript. That worktree also contains separately excluded A01 preparation tests; they are not a claim that application uploads are integrated. The policy production build and isolated Chrome runner passed, including lost responses, stale tabs, scoped reader/organization/CSRF negatives, pagination, English/Tamil keyboard focus and no horizontal overflow at 360/390/768/1280 widths. Root visually inspected Tamil mobile and English desktop evidence. Browser log: `.tool-cache/file-policy-browser-test.log`; runner: `scripts/run-file-policy-browser-test.py`. No JavaScript errors were recorded.

Contract comparison found 228 → 232 paths, no removed or modified existing paths and no changed existing schemas. Python dependency audits reported zero findings across 61 runtime and 101 development packages; `pip check` passed. The separate pre-existing web `braces` advisory and remote CI gates remain open. Source-secret scan evidence is recorded with the local checkpoint.

## Remaining Process 3 work

Next is A01.3: pinned document requirements, owner uploads/replacement, current-assignment reviewer access and immutable submitted evidence. Then complete CMS verified public bytes/revocation, assignment/LMS bindings, helpdesk attachments and cross-domain lifecycle acceptance. The foundation alone is not Process 3 completion.

Live S3 compatibility/IAM/encryption, ClamD/signature limits, Redis/Celery process behavior, Linux confinement, backup/object restoration, volume/performance controls and approved real collection rules remain external/runtime gates. See [runtime preparation](../deployment/secure-files.md). No live-provider or production acceptance is claimed.
