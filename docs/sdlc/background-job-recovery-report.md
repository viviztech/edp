# Background-job recovery local checkpoint

Recorded: 2026-10-24 (Asia/Calcutta). Step 2 of the authorized six-process sequence is locally accepted. Step 1 secure files remains accepted at `74fb149`. Real Redis/Celery/one-Beat process acceptance, remote CI, providers, devices and deployment remain open. No external message, provider request or deployment was performed.

## Implementation

CRM export creation commits a durable request and audit without broker I/O. Periodic bounded rediscovery repairs lost publication and expired execution claims. Random-token digests, monotonic versions and cumulative attempts fence both success and failure. Current requester status and export permission are checked at claim, completion, status/history and download. CSV generation preserves formula-prefix escaping and fails explicitly above row/byte limits. Owner history recovers references after reload or a committed lost response without repeating the POST.

Migration `n9d5e1f7a234` backfills stranded jobs, enforces state/lease/version/identity invariants, and preserves exact oversized legacy completed output without allowing new exemptions. Access expiry remains distinct from separately configured approved disposal; absent retention disables deletion and blocks real-environment export creation/execution. Health diagnostics expose bounded aggregates only. Meta recovery terminalizes expired final attempts and fences late worker or publication-failure outcomes.

This migration requires paused/drained old CRM writers followed by the matching new revision; it does not support mixed old/new writers. See [architecture](../architecture/background-job-recovery.md).

## Verification

| Evidence | Result and scope |
| --- | --- |
| Fresh API static checks | Ruff check and format pass, 227 files formatted; strict MyPy passes for 131 sources; `pip check` passes |
| Recorded integrated API baseline | 309 passed, one POSIX-only skip; `.tool-cache/job-recovery-backend-20261024-c346b286/result.json`. Later affected changes are covered separately below |
| Final focused CRM/CSV regression | 17 passed, including legacy oversized-output preservation and late-claim fencing; `.tool-cache/crm-export-recovery-23f4fbf6/api.xml` |
| Final focused Meta regression | 15 passed, including lost publication acknowledgement and terminal-state fencing; `.local/meta-ack-recovery-20261024.xml` |
| Final migration | Fresh base to head, downgrade to base and re-upgrade; zero global drift across 128 model tables; current model/migration hashes match `.local/job-migration-acceptance-809ad8fe.json`; newly owned database dropped |
| Recorded final web checks | 436 tests across 73 files, lint, typecheck and build pass; `.tool-cache/job-recovery-web-final-20261024/`. The serial full-suite run preserves all assertions/timeouts |
| Fresh focused web smoke | 32 CRM security/export tests pass |
| Contracts | OpenAPI matches current app with platform line endings normalized; TypeScript regeneration and `git diff --check` pass |
| Fresh connected Chrome acceptance | `.local/crm-export-acceptance-e4f23151.json` passes against unchanged build `rcpdxNPGkbrOfNbiSPPQc`; failure/retry/completion, escaped CSV, duplicate task, history/reload, committed lost response, peer/organization/CSRF/current-permission negatives; zero JavaScript errors |
| Visual/keyboard review | English/Tamil at 390/1280 widths; skip-link and download focus verified. English desktop failed state and Tamil mobile completed-history screenshots inspected; controls/references remain contained |
| Source secrets | Final source-only scan recorded in `.local/background-jobs-latest-source-scan.json`; no environment credentials, uploaded bytes or build artifacts included |

The earlier browser run failed a skip-link timing check. The subsequent runner exposed an incorrect Playwright callback default argument (the supplied Request replaced the intended list); the callback was corrected without weakening the committed-response-loss assertions. Both failed runs remain historical and are superseded by the successful fresh run.

## Remaining runtime and release gates

Browser acceptance deliberately has Redis unavailable and executes task functions directly. It proves database/API/BFF/UI behavior, not broker delivery, worker termination/restart or scheduler operation. Real isolated Redis, real workers and one Beat must still pass round trip, duplicate publication, outage/recovery, death after claim and final-attempt exhaustion. Linux confinement remains the recorded POSIX skip. Approved retention, live storage/scanner, native devices, exact-revision remote CI, staging, client UAT and release approval remain separate gates.

The next authorized local process is [essential communications](essential-communications-plan.md): configurable global verification/reset delivery first, then the enrollment outbox and participant inbox. Report this checkpoint to the owner before starting that implementation.
