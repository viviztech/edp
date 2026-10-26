# Ordered development progress

Updated: 2026-10-24 (Asia/Calcutta). The owner requested completion of all six authorized local processes in their recommended order. The [execution plan](remaining-development-plan.md) defines scope and the separate external release gates. Report each local checkpoint before continuing; local-only source control remains in effect.

| Process | Local position | Evidence |
| --- | --- | --- |
| 1. Secure files | Accepted | `74fb149`; [acceptance](secure-files-acceptance-report.md) |
| 2. Background-job recovery | Accepted and reported | `679ebdc`; [report](background-job-recovery-report.md), final CRM browser pass and zero-finding selected-source scan |
| 3. Essential communications | Accepted and reported | Configured global identity SMTP transport, fixed manual-code web routes, typed enrollment outbox and participant inbox. Controlled protocol tests, full web checks, final migrations and connected browser pass; 368 API tests passed with one POSIX-only skip |
| 4. Flutter domain journeys | M00–M02 verified; M03/M04/M05 source and initial live API journeys implemented; final checks in progress | [plan](flutter-domain-plan.md), [closure status](development-closure-report.md); source and unavailable native runtime checks remain distinct |
| 5. Staging operations and launch acceptance preparation | Local artifacts, regression tests and actual PostgreSQL role/restore drills pass on final q3 schema | [report](staging-operations-report.md); Docker/TLS/queue/storage/device/remote acceptance and deployment remain unexecuted |
| 6. Business tools | All four local vertical slices implemented; final API/web tests, static checks, q3 migration round trip/drift and connected browser acceptance pass | [report](business-tools-report.md), [API](../api/business-tools.md); real collection/sharing policy and release gates remain external |

## Acceptance boundary

No real messages, provider activation, personal-data collection, source publication, infrastructure provisioning, store submission or deployment is authorized by this sequence. Live storage/scanner, Redis/worker/one-Beat, Linux confinement, native devices/signing, approved content/policy/retention, exact-revision remote CI, staging, UAT and release remain explicit until actually executed or supplied. Docker, Redis and WSL are unavailable on this Windows host; the absence is not a passing runtime check. Independent authorized local implementation continues after the preceding implementable checkpoint is verified and reported.
