# B01 business-plan builder plan

Status: B01 web/API implementation and local acceptance complete on 2026-10-21. See the [acceptance report](b01-acceptance-report.md). Formal Milestone 7, remote CI and release gates remain open.

## Scope and sequence

1. B01.1: one enrollment-owned plan, the master specification's structured sections, draft autosave, section completion, immutable revision history, and English/Tamil participant UI.
2. B01.2: assigned mentor comments on submitted plan versions, participant-visible feedback, and permissioned review transitions (changes requested or approved). Preserve submitted evidence when a participant starts a new draft.
3. B01.3: acceptance hardening, generated contracts, full integration journey, and documentation. PDF export remains a later server-side document-generation slice, as allowed by master Section 14.

## Acceptance criteria

- A participant can access only a plan attached to their own active enrollment. A staff or mentor role alone never grants access to another participant's draft.
- Each autosave checks the expected plan version, changes only one allowed section, and records an immutable revision. Section completion is derived from saved content.
- Submission freezes a numbered snapshot. A mentor must hold an active assignment for that enrollment to view or comment; private mentoring notes never appear in the plan.
- Reviews are audited and version checked. An approved snapshot cannot be silently overwritten. Revisions after requested changes retain earlier evidence.
- API validation bounds text size; audit payloads contain identifiers and field names, not plan prose or financial assumptions. UI and API expose no financial guarantee.
- Migration upgrade/downgrade and drift, authorization negatives, conflict and immutability checks, generated contracts, API and web checks, and an authenticated browser journey pass before B01 is called locally complete.

## Dependencies and deferred decisions

Uses enrollment ownership and M01 active mentor assignment. Native mobile follows ADR 0004. Final client wording, plan approval policy, and PDF presentation need owner approval before release.

## B01 autosave recovery continuation - 2026-10-21

The next development slice repairs stale-version recovery in the participant web editor without changing the schema or authorization model.

- Use generated API contracts for plan reads and section/submission mutations.
- Pause autosave on conflicts or ambiguous network failure, preserve every unsaved local section, and refresh only through the existing owner-scoped plan endpoint.
- Reconcile against the last acknowledged plan: retain local changes, adopt remote changes to untouched sections, and require an explicit choice before replacing a remotely changed section with different local text.
- Present English/Tamil conflict explanations, saved/local comparison and clear recovery actions. Loading the saved version requires confirmation before discarding edits.
- Refresh before retrying an ambiguous failure so an already committed write is acknowledged without an extra revision. Repeated conflicts must repeat reconciliation against the new version.
- If a failed write remains uncommitted after refresh, pause for manual recovery rather than repeatedly resending validation, rate-limit or service failures. Navigation protection also covers an unacknowledged write when local text has been reverted to the old baseline.
- A refresh that races an ambiguous pending commit cannot discard a local revert merely because it matches the previous baseline. Retain that explicit intent through a version-checked retry and any further conflict; an unchanged-text revision may be necessary to fence the earlier request.
- Preserve edits typed while a save or refresh is in flight. Submitted/approved plans remain locked; refresh failure or access revocation must not resume writes or erase text.
- Respect the API's boundary-whitespace normalization when acknowledging saves and comparing drafts, so normalized responses do not cause an autosave loop or duplicate revisions.
- Block submission while text is unsaved, recovery is pending, or the plan is no longer editable. Warn before tab close/reload and ordinary link navigation while unsaved edits remain; do not persist sensitive plan prose in browser storage.
- Verify independent concurrent edits, overlapping conflicts, latest-version retries, lost responses, in-flight typing, locked state/access failures and discard confirmation with behavior-level component tests.
- Add an authenticated browser journey using two tabs for a real conflict and verify saved history in PostgreSQL. Run the relevant existing API journey, web lint/types/tests/build, and browser acceptance before recording this slice locally verified.

Native mobile, PDF export, remote CI, the upstream dependency advisory and production release gates remain separately tracked.

Local verification for this focused recovery slice passed on 2026-10-21: the existing B01 PostgreSQL/API workflow, web lint/types, 77 tests including 31 recovery cases, production build, and authenticated two-tab Chrome acceptance with revision-history assertions and no JavaScript errors. See the [autosave recovery report](b01-autosave-recovery-report.md). Full submission/mentor-review browser acceptance was still pending at that checkpoint and is closed by the continuation below.

## B01 local acceptance closure - 2026-10-21

Complete the current B01 web/API phase before starting K01. Keep the existing autosave recovery and B02 regression coverage.

- Exercise all 20 sections through the participant interface, save and submit a complete plan, and verify locked submitted content after reload.
- Use a separately authenticated, actively assigned mentor to review the immutable submitted snapshot, request changes with section feedback, and verify that the participant sees that feedback without private mentoring notes.
- Revise and resubmit as the participant, then approve as the assigned mentor. Verify that both numbered submissions and the original feedback remain unchanged and the approved plan cannot be edited.
- Verify unrelated users and unassigned mentors cannot read another participant's draft or review their submission. Repeat optimistic-version, duplicate-review and immutable-evidence checks in the API/database tests.
- Harden the mentor interface around generated contracts, review failures, stale versions and preserved entered feedback. Avoid persistent browser storage for sensitive prose.
- Add meaningful mentor component tests and extend the authenticated Chrome journey with exact PostgreSQL submission/review/revision and audit assertions.
- Run backend lint/format/strict typing and the full PostgreSQL test suite; verify migration round trip/drift and generated contracts. Run web lint/types/tests/build, browser acceptance and diff whitespace checks. Preserve existing release security gates.
- Update participant/mentor guidance, the phase report and pending register. Mark B01 locally accepted only when these checks pass. Remote CI, native Flutter, later PDF export, final client policy and production/provider/infrastructure gates remain explicitly deferred and do not become locally verified by this closure.

Closure evidence: all 93 API/PostgreSQL tests, backend Ruff/format/strict MyPy, isolated B01/B02 migration downgrade/re-upgrade and zero drift, unchanged regenerated contracts, web lint/types, 104 tests and production build pass. The authenticated Chrome journey completes the entire separate-actor workflow through approval, preserved immutable snapshots/reviews, exact audit evidence and authorization negatives with no JavaScript errors. Guidance and pending records are updated. K01 knowledge resources is the next scheduled development phase.
