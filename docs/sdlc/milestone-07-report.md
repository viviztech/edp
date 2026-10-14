# Milestone 7 report

Status: M01 locally accepted; B01 local API/web/browser acceptance passed on 14 October 2026. Milestone 7 remains open for the B01 CI dependency gate, B02 and deferred native-client/operational gates.

M01 now covers eligible mentor profiles, bilingual expertise labels, recurring availability, one active mentor per enrollment, session conflict checks, author-only private notes, shared participant notes, goals, action items, durable follow-up reminders, immutable feedback, aggregate monitoring and explicit assignment/session/outcome transitions. The API and PostgreSQL schema enforce organization scope, optimistic versions, uniqueness and immutable evidence. The web provides English/Tamil staff and participant routes through the hardened BFF.

Local acceptance on 2026-10-05 passed: 88 API/PostgreSQL tests, focused strict MyPy for all five mentoring source files, Ruff for the changed backend and browser files, Alembic downgrade/upgrade plus zero-drift check, 16 web test files with 38 tests, ESLint, TypeScript, the Next.js production build, and the authenticated Chrome journey with no JavaScript errors. The browser evidence includes a responsive mentoring screenshot and asserts that the participant cannot see the private note.

Production reminder adapters, calendar integration, retention approval, native mentor access, remote CI and production operational acceptance remain open.

## B01 business-plan continuation

B01 core implementation is present; overall acceptance remains open for the CI gate below. Enrollment-owned business plans now have 20 structured sections, version-checked autosave, immutable section revisions, derived completion counts, recent history, and English/Tamil participant web editing. Submission freezes a numbered immutable snapshot only when all sections are complete. An active assigned mentor can review the latest submission, record section comments and choose changes requested or approved. A participant can revise after changes are requested without overwriting earlier submissions or reviews. The API owner check derives identity from the authenticated Person and active Enrollment; mentor access derives an active M01 assignment. The web BFF uses a fixed route allowlist and CSRF protection. Audit entries contain section codes and transition names, not plan prose or review comments.

### Initial verification — 8 October 2026 (superseded by the continuation below)

The OpenAPI and TypeScript contracts are regenerated. Focused Ruff and strict MyPy pass; web ESLint, TypeScript, 40 Vitest tests, and the Next.js production build pass. On 2026-10-08, the project-owned PostgreSQL 17 `edp_test` database was migrated from M01 to B01. The B01 workflow test passed with drafts, conflicts, submission, mentor review and immutable evidence. Alembic downgrade/re-upgrade and zero-drift check passed. The full API suite recorded 86 passes and three `tmp_path` setup errors caused by the execution environment denying access to the Windows user temp directory; rerunning those three with a fresh project-local pytest temp directory passed, giving 89 passing tests across the two runs. Authenticated browser acceptance and remote CI remain unverified, so B01 is not locally accepted yet. PDF export is later scope under master Section 14.

## B01.3 acceptance hardening — 14 October 2026

The authenticated browser script now covers B01 with separate participant and Mentor-only sessions, all 20 editors, autosave/reload, incomplete and stale request rejection, draft privacy, submission/review/revision/resubmission/approval, historical snapshots and English/Tamil mobile layouts. The runner explicitly enables registration only inside its isolated localhost test environment, uses the Windows-compatible API launcher and copies standalone public assets. Public CMS checks use semantic content locators after the redesign and verify script text remains escaped. Visual QA found inline labels wrapping beside their textareas; scoped participant/mentor form styles now stack labels above full-width controls, and the browser checks actual label/field geometry in both participant languages and the mentor review form.

Executed local checks:

- Full PostgreSQL/API suite: 90 passed in one run, using a fresh workspace-local pytest temp directory.
- Ruff lint and format: passed across the backend (151 files); strict MyPy: 87 source files passed. CMS typing/import placement and selection Decimal annotations were corrected; other backend changes are formatting. These changes do not alter executable workflow logic or database types.
- Disposable `edp_test` migration downgrade to base, upgrade to head and Alembic drift check: passed. This CI-style round trip uses empty synthetic tables; an initial attempt after populated API fixtures correctly failed when newer application-history states could not fit an older check constraint.
- OpenAPI and TypeScript contracts regenerated without changes. Web ESLint, TypeScript, all 56 Vitest tests in 23 files and the Next.js production build passed. Vitest used `--maxWorkers=1` after the workstation exhausted memory with its default worker count.
- Backend `pip-audit -r requirements.lock`: no known vulnerabilities found.
- Full authenticated Chrome journey: passed with no JavaScript errors, including the B01 draft/review/revision/approval workflow and persisted snapshot/audit assertions. All 20 participant fields in both languages and 22 mentor-review controls passed mobile label-position, width and containment checks. The four business-plan screenshots under `.tool-cache/evidence/` were visually reviewed for the scoped form correction.

Next.js and eslint-config-next are pinned to 16.3.8, and compatible lockfile updates include patched sharp, MCP SDK and source-map-js releases. The remaining npm audit result is nine high findings along the same transitive `braces` dependency chain. [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) lists no patched version, and the registry's latest release is 3.0.3. The audit gate is retained; no breaking downgrade or advisory suppression was applied. Full B01 Definition of Done remains open until remote CI passes, including resolution of this dependency gate. Acceptance changes are isolated on `feature/b01-acceptance`.

B02, native/device acceptance, final client wording/review policy, PDF export and production operational acceptance remain separate open work. No database schema change is introduced by this continuation.
