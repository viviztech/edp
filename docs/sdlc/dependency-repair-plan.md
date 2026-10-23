# Dependency repair and B02 continuation

Recorded: 2026-10-21. Status: core dependency repairs and focused B02 implementation locally verified; remaining gates and exact results are in [the repair report](dependency-repair-report.md).

## Sequence

1. Restore the approved toolchain: Python 3.13 with an isolated virtual environment, Node 24/npm with the committed lockfile, and the CI-pinned Flutter SDK where available. Keep tools and caches project-local; preserve the system Python installation.
2. Install the existing locked dependencies before considering version changes. Check dependency consistency, backend lint/types/tests, web contracts/lint/types/tests/build, and available mobile checks. Record unavailable service/device gates explicitly.
3. Repair dependency or tooling incompatibilities without changing the FastAPI/Next.js/Flutter architecture or weakening quality gates.
4. Once the web/backend dependencies are usable, repair B02 profile updates after reload and add behavior-level regression coverage.

## Acceptance

- The backend environment reports Python 3.13 and installs the committed development lock without dependency conflicts.
- Web dependencies install reproducibly with `npm ci`; Node 24 is declared consistently with CI.
- Flutter's configured SDK matches CI, or the exact installation/runtime blocker is recorded.
- Checks report actual passes/failures; missing PostgreSQL, Redis, Docker, device SDKs, or remote CI are not counted as passes.
- B02 requests contain only writable profile fields and the expected version, using generated contracts.
- Regression coverage exercises create, reload, edit, save and reload, and verifies version-conflict behavior without silently discarding edits.
- Backend authorization remains authoritative; no production data, provider messages, schema changes or deployment are part of this task.

The existing B02 milestone acceptance criteria remain binding. This focused repair does not by itself complete all B02 release gates.
