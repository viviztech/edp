# Flutter M05 alumni, impact and enrollment updates

Updated: 2026-10-24 (Asia/Calcutta). Local working-tree implementation/API checkpoint. No production collection, providers, source publication, provisioning or release was performed by this slice.

## Implementation

Owned active/completed enrollment entries support bounded private business profile creation/update, immutable revisions, server-frozen follow-up dates and one immutable outcome per follow-up. Mobile keeps public sharing off; public-card/catalogue publication is a separate explicit business-tools workflow. Lost creation/outcome results retain input and reconcile through the exact owner's authoritative record before another decision. Existing-profile responses never authorize silent overwrite.

Self-reported impact remains separate from follow-up outcomes. Eligible enrollments, published definition IDs/editions, baseline/outcome stages, calendar dates, revision expectations, reasons and unchanged request UUID/body are pinned. Enrollment/definition/record cursors remain independent. Past observations and superseding revisions are shown as self-reported evidence, without fabricating financial metrics or impact denominators.

Enrollment updates paginate, use versioned read/preference commands and reauthorize both the current notice and its owned enrollment timeline before routing to schedule. Revoked sessions cannot restore private business, impact or inbox state. Business/follow-up internal links pin both parent enrollment and follow-up and re-read ownership.

English/Tamil messages/field/state labels are generated from ARB sources. Business, impact and updates layouts were checked at 320 logical pixels with enlarged text, with golden artifacts in `apps/mobile/test/goldens/`. Shared internal links reject foreign origins, unknown/repeated parameters, control characters and inconsistent parent IDs.

The shared app-policy client parses bounded semantic versions, validates platform and configured HTTPS destinations, and shows a localized update prompt. Disabled/missing/offline/malformed metadata fails open; it does not invent a store URL or discard the current workspace. `APP_VERSION` defaults to the current `pubspec.yaml` version (`0.1.0`) and must match the release build name.

## Evidence

- `python scripts/run-mobile-alumni-tests.py`: **6 real Flutter/API cases passed** on the current contract, including lost profile/outcome responses, immutable revision/outcome evidence, active/completed owner versus peer/organization denial, independent impact pagination/definition pinning/revision/idempotency, inbox authorization and revoked sessions.
- Guarded record `.local/mobile-api-alumni-63579ec3.json`; logs `.tool-cache/mobile-api-alumni-63579ec3`. Owned API/Flutter processes stopped and the temporary credential fixture was removed.
- Exported schema SHA-256: `6ea0802b512a5cc1b47f66e19cc718896a70c8e944c0f021d20570e143e9d2d3`.
- Profile/impact lost-result recovery, malformed-success uncertainty, independent cursors, notice target authorization and English/Tamil widgets pass. Three M05 Tamil goldens cover business, impact and updates. Integrated domain layout/recovery checks: **18 passed**. Scanner/link/policy tests are included in the integrated mobile suite.

No new database schema is needed for these mobile clients. The synthetic inbox fixture now consumes the bounded worker batches until its expected notices exist; one batch is no longer incorrectly assumed to contain all 29 enrollment events. This is direct local task-function evidence, not broker/worker/Beat or push-provider delivery evidence.

## Remaining validation

Native compilation/device matrices, encrypted/protected-file lifecycle, real secure storage, TalkBack/VoiceOver, approved platform IDs/signing, OS domain association, provider configuration, real retention/content approvals, exact-revision remote CI, staging/UAT and release remain separate requirements. Private persistent caching, offline writes, mentor mobile authoring and unapproved provider features are not enabled by the local checkpoint.
