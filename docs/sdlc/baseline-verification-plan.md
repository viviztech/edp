# Process 1 / verified development baseline

Recorded: 2026-10-23. Status: in progress. This is the first process in the remaining-development sequence approved by the project owner. Existing local implementation and historical acceptance evidence are preserved; completion is assessed against the current revision.

## Scope and acceptance

1. Close Phase 10's remaining English/Tamil responsive reporting and participant-impact acceptance. Record the actual environment, screenshots, browser assertions and any corrections; do not infer a pass from a successful build.
2. Reconcile README, backlog, pending register, mobile README and Phase 10 plan/report. Distinguish implemented local scope, verified checks, deferred native/provider/operations work and release blockers. Prioritize outstanding P0 journeys before conditional Phase 11/P1 tools.
3. Verify backend lint/format/types, PostgreSQL tests, disposable migration round trips and drift, generated API/client contracts, web lint/types/tests/build and available Flutter checks. Use only isolated synthetic databases. Preserve development records and never run test truncation against a shared database.
4. Inspect CI and fix reproducible configuration defects without weakening authorization, database guards, dependency scans or other quality gates. Run the authenticated browser suites using their guarded databases and owned temporary servers.
5. Review dependency findings against current authoritative advisories and the actual dependency graph. Apply supported compatible remediation where available; explicitly retain unresolved findings and failed gates. A failed network request is not a clean security scan.
6. Prepare a coherent reviewed revision and obtain CI evidence for that exact revision when repository access is available. Keep secrets, local credentials, uploads, tool caches and generated build outputs out of version control.

## Completion boundary

Process 1 is complete only when its required checks and reviewed-revision CI are green. Unavailable infrastructure, failed security gates or missing CI evidence remain open blockers, rather than passes. Report the completed work and any remaining blocker before starting the next process. Native-device and live-provider acceptance remain separate later requirements; their absence must remain visible.

## Next process

Process 2 completes the web journeys: ordinary applicant entry with preserved intake context, application history after intake closes, participant/learning navigation, public enquiries and staff CMS operations, with English/Tamil and accessibility acceptance. Its own plan and acceptance criteria are required before implementation.
