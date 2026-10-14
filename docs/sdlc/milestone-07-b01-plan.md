# B01 business-plan builder plan

Status: local API/web/browser acceptance passed on 14 October 2026. B01 remains open for the CI dependency gate; M01 mentoring is locally accepted and Milestone 7 remains open for B02 and deferred release gates. See `milestone-07-report.md`.

## Scope and sequence

1. B01.1: one enrollment-owned plan, the master specification's structured sections, draft autosave, section completion, immutable revision history, and English/Tamil participant UI.
2. B01.2: assigned mentor comments on submitted plan versions, participant-visible feedback, and permissioned review transitions (changes requested or approved). Preserve submitted evidence when a participant starts a new draft.
3. B01.3: acceptance hardening, generated contracts, full integration journey, and documentation. PDF export remains a later server-side document-generation slice, as allowed by master Section 14.

## Acceptance criteria

### B01.3 acceptance continuation — 14 October 2026

Extend the existing isolated, authenticated browser journey to cover participant draft persistence, all 20 section completions, immutable submission, assigned-mentor feedback, requested revisions, resubmission and approval. Exercise English/Tamil and a narrow viewport, and retain synthetic screenshots under the ignored browser evidence directory. Run against the dedicated project-owned test database and temporary API/web processes only. Recheck the B01 PostgreSQL workflow, generated contracts and relevant lint/type/test/build gates; record remote CI evidence separately. Keep B02, native verification and real-service launch acceptance open.

The current remote CI run also exposes an outdated registration assumption in the browser runner, backend lint/type debt and dependency audit failures. Enable self-service explicitly only inside the isolated browser runner, repair backend formatting/typing without weakening checks, and apply compatible published dependency fixes. Record any upstream advisory without a published fix as unresolved rather than suppressing the audit gate.

- A participant can access only a plan attached to their own active enrollment. A staff or mentor role alone never grants access to another participant's draft.
- Each autosave checks the expected plan version, changes only one allowed section, and records an immutable revision. Section completion is derived from saved content.
- Submission freezes a numbered snapshot. A mentor must hold an active assignment for that enrollment to view or comment; private mentoring notes never appear in the plan.
- Reviews are audited and version checked. An approved snapshot cannot be silently overwritten. Revisions after requested changes retain earlier evidence.
- API validation bounds text size; audit payloads contain identifiers and field names, not plan prose or financial assumptions. UI and API expose no financial guarantee.
- Migration upgrade/downgrade and drift, authorization negatives, conflict and immutability checks, generated contracts, API and web checks, and an authenticated browser journey pass before B01 is called locally complete.

## Dependencies and deferred decisions

Uses enrollment ownership and M01 active mentor assignment. Native mobile follows ADR 0004. Final client wording, plan approval policy, and PDF presentation need owner approval before release.
