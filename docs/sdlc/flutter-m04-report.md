# Flutter M04 participant support journeys

Updated: 2026-10-24 (Asia/Calcutta). Local implementation/API checkpoint; native/provider and release gates remain separate.

## Implementation

Separate typed repositories and screen-owned controllers implement owned mentoring assignments/sessions/shared notes/work/feedback, the twenty-section versioned business plan, public/participant knowledge catalogs and saved items, opportunity interest, the fixed funding transition graph, and owner helpdesk/messages/history/notices/preferences. Internal staff projections and assignment controls are excluded. Current server permission/enrollment checks govern every action, including completed alumni's restricted active-enrollment features.

Business-plan saves are serialized, retain dirty text on conflicts/unknown results and show immutable submitted snapshots/review comments. Review cannot be acknowledged until an authoritative read succeeds; the audit fixed a bypass that could otherwise discard the current version. Acknowledged saves survive later read failures.

Helpdesk creation retains one exact request UUID/body for recovery. Definitive validation rejection returns the entered text to an editable state. Replies, status and notice/preference commands require exact-object readback after uncertain results. Ticket switches cannot move unsent prose or staged file selections to another conversation. Legacy bounded UTF-8 TXT remains available. Secure files register/stage/upload/scan separately; a staged file does not appear as posted until its exact binding is included in a shared reply. Private staff notes/files never enter owner models.

Knowledge cursors for saved items, interests and funding cases are independent. Unsupported shortcuts are rejected before sending; optimistic-version conflicts retain the entered reason. Unavailable saved content stays redacted. Official links are validated HTTP(S), opened without bearer headers after current detail readback, and never imply an award or funding approval.

UI messages, supported statuses/categories/fields and business-plan sections use generated English/Tamil ARB localization. Timestamps use localized local-time presentation and calendar dates remain dates. Narrow-screen tests caught and fixed overflowing dropdowns while preserving server enum values in requests. Owner ticket links reauthorize their exact target; public resource links reload their published projection.

## Evidence

- `python scripts/run-mobile-api-tests.py --slice support`: **4 real Flutter/API journey cases passed** covering complete versioned plan submission/stale rejection, mentoring private-note exclusion/one owned feedback, public and participant funding discovery/all allowed transitions, and owner helpdesk replay/reply/close/reopen/notices/preferences.
- Secure helpdesk evidence includes registration/PUT/controlled clean scan/private download, peer denial, staging excluded from messages, explicit reply binding and frozen posted evidence. The legacy TXT download was also read back.
- Guarded record `.local/mobile-api-support-e602e92b.json`; logs `.tool-cache/mobile-api-support-e602e92b`. One controlled synthetic scan completed; owned processes and credential fixtures were cleaned up.
- Exported schema SHA-256: `6ea0802b512a5cc1b47f66e19cc718896a70c8e944c0f021d20570e143e9d2d3`.
- Seven recovery/privacy controller tests and four Tamil 320-pixel/large-text support/mentoring/plan/resource widgets pass. The four M04 goldens live in `apps/mobile/test/goldens/` and were visually reviewed. Integrated domain layout/recovery checks: **18 passed**.

No schema change is introduced by the mobile slice. Its synthetic policy/scanner harness uses only a guarded mobile database and explicit per-run collection; it does not approve real evidence collection or establish storage/scanner/broker/worker runtime acceptance.

## Remaining validation

Native picker/provider behavior, file encryption/protection and cleanup on supported devices, secure-storage/session lifecycle, large-text native accessibility and final Android/iOS compilation require actual platform evidence. Android app-private cache paths alone do not establish encrypted-at-rest storage: the [file matrix](../testing/native-file-acceptance.md) now explicitly requires credential encryption and locked/reboot-before-unlock checks. Real delivery/retention approvals, OS links, signing, remote CI, staging/UAT and release remain unpassed until executed.
