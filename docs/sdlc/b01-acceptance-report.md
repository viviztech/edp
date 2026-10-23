# B01 local web/API acceptance

Recorded: 2026-10-21. Status: B01 local web/API implementation and acceptance complete. Formal milestone and release gates remain separate.

## Delivered behavior

Participants build and save 20 sections, submit immutable numbered evidence, receive an assigned mentor's section feedback, revise and resubmit, and retain both earlier snapshots and recorded reviews. Approval locks editing and further submission. The [autosave recovery](b01-autosave-recovery-report.md) behavior remains covered.

The mentor screen uses generated contracts, identifies the enrollment and submission, limits review forms to the latest submission, and freezes inputs while recording a decision. Failed or stale reviews pause until an authoritative refresh. An interrupted response can be acknowledged from the recorded review without replaying the write. Feedback entered after that attempt is preserved; unavailable and historical drafts remain read-only and are never retargeted to another submission. Successful reviews remain visible if the list refresh fails. English/Tamil feedback decisions use localized labels.

The web proxy now measures UTF-8 request bytes and permits the API's maximum valid text after JSON escaping: 64 KiB for section saves, 256 KiB for reviews, and 1 KiB for create/submit. Oversized requests, invalid JSON, unsupported paths and CSRF failures remain rejected. The API rejects review reasons shorter than three characters after boundary-whitespace normalization. No schema, permission, dependency or provider change was needed.

## Acceptance evidence

| Gate | Result |
| --- | --- |
| Requirement and acceptance criteria | Updated [B01 plan](milestone-07-b01-plan.md) before implementation |
| API/PostgreSQL workflow | Focused two-test suite and all 93 backend tests pass; full suite completed in 232.17 seconds with two upstream TestClient/AnyIO deprecation warnings |
| Ownership and review authorization | Separate participant, assigned mentor, unrelated participant, unassigned mentor and privileged staff tested; wrong organization, withdrawn enrollment and ended assignment denied |
| State transitions and immutable evidence | Full submit/request changes/revise/resubmit/approve journey; stale, duplicate, historical and locked writes denied; database UPDATE and DELETE rejected for revisions, submissions and reviews |
| Audit privacy | Exact actor, organization, version, request ID and changed fields checked for successful transitions; plan prose and review reasons/comments excluded |
| Schema migration/drift | Fresh temporary PostgreSQL database upgraded to head, downgraded to M01, re-upgraded and checked with zero drift; temporary database removed afterward |
| Generated contracts | OpenAPI and TypeScript regenerated with no content drift |
| Backend static checks | Ruff and formatting pass for all 151 files; strict MyPy passes for 87 source files |
| Web component/proxy checks and production build | ESLint, TypeScript, all 104 tests across 23 files and the Next.js production build pass; includes 35 participant tests, 17 mentor tests and six proxy regressions |
| Authenticated Chrome journey | Passed: participant saves all 20 sections, submits, separately authenticated assigned mentor requests changes, participant reads feedback and revises/resubmits, mentor approves, both actors reload retained evidence and approved editing stays locked; role/ownership negatives and existing autosave/foundation/B02 checks pass with no JavaScript errors |
| Documentation and independent review | Participant and mentor guidance updated; independent review of authorization, privacy and recovery completed |
| Native client | Deferred under ADR 0004; unchanged in this phase |
| Remote CI, security and release | Pending; existing upstream dependency and infrastructure gates remain recorded in the [dependency repair report](dependency-repair-report.md) |

The earlier B01 API test stopped after the first requested-changes review. The new separate-actor test adds revision, resubmission and approval evidence rather than relying on that earlier coverage claim.

Browser database evidence verifies the approved plan at version 32, all 27 immutable section revisions including the earlier conflict-recovery history, two numbered submission snapshots, two reviews by the separate assigned mentor and 32 audit events containing only identifiers/field names. Responsive screenshots are available locally at `.tool-cache/evidence/business-plan-mobile.png` and `.tool-cache/evidence/business-plan-review-mobile.png`. Browser harness syntax/Ruff and final diff whitespace checks pass. Temporary API/web processes were stopped by the runner; only isolated synthetic data was used.

## Deferred scope and next phase

PDF export remains later scope explicitly permitted by master Section 14. Native device acceptance, final client approval policy, remote CI, staging, provider activation and production operations remain unverified. The upstream npm advisory remains open; the security gate has not been disabled or waived.

The next scheduled module is K01 knowledge resources. Broader B02 decisions and operational release work remain in the pending register. This report does not declare all Milestone 7 or production acceptance complete.
