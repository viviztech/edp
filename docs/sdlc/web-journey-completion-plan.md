# Process 2 / complete the web journeys

Recorded: 2026-10-23. Status: local web/API acceptance complete; see the [completion report](web-journey-completion-report.md). The owner authorized the remaining-development sequence and subsequently instructed that baseline commit `c9877ab` remain local. All development and commits in this process remain local. Baseline functional checks passed; remote CI, the unpatched tooling advisory, native/provider acceptance and production release gates remain open.

## Ordered local slices

1. **Applicant entry and history.** Preserve a validated organization/intake destination through account registration, verification and login. Offer ordinary authenticated applicants an application entry without requiring a staff/organization role. List their own applications independently of open intake, including closed cycles and current selection/enrollment status. Keep new-intake discovery separate from saved/submitted history.
2. **Participant navigation.** Add permission-aware account destinations and consistent participant links including learning. Preserve organization and locale, replace broken Tamil labels and ensure skip-link targets resolve on the affected pages.
3. **Public enquiries and staff inbox.** Connect the existing enquiry API to a bilingual public contact form and permission-scoped staff queue/lifecycle. Add current-version consent, direct-API anti-abuse/body limits and versioned forward transitions through the existing new/reviewed/closed states. Keep contact data private and audit only metadata. Enable public collection only with configured localized consent text and privacy links; synthetic acceptance explicitly supplies test policy values. Staff notes are outside this enquiry slice. No invented contact details or real-data policy approval.
4. **Staff content operations.** Connect existing editorial APIs to bilingual staff authoring/publication controls and complete public list pagination. Expose only currently supported media metadata/status; secure byte upload/storage/scanning belongs to Process 3 and must remain explicitly unavailable until implemented.

## Acceptance

- A fresh synthetic applicant with no organization grants can follow public Apply, register, verify using the local development delivery workflow, sign in, choose an open intake and submit without an out-of-band organization URL.
- The chosen organization/cycle survives account modes and login. Destination input accepts only validated IDs and known local paths; external URLs, traversal and cross-locale redirects are rejected.
- Authenticated application history is bounded and owner-only, across relevant organization/cycle scopes. Closed intake does not hide prior drafts or submitted status. Responses omit staff notes, scores, decision reasons and other owners' data. Stale or unavailable selected entries never silently load another application or overwrite a draft.
- Application history/detail APIs, closed BFF paths and generated contracts agree. Pagination/query inputs are bounded and unsupported paths/verbs/queries rejected. Existing submission immutability and anti-CSRF behavior remain intact.
- Account links route participants to their portal and staff to authorized workspaces. Participant links include schedule, learning, attendance, mentoring and currently supported support/resource/outcome flows, with explicit organization and English/Tamil labels.
- Public enquiries honor the existing backend privacy version and validation. Staff controls respect current permissions, scope and expected versions. Enquiry text/contact information never appears in public responses or logs.
- Content publication remains versioned and permissioned. Public views expose published editions only, with usable pagination; no unimplemented secure-upload capability is implied.
- Meaningful API/database, component/BFF and Chrome journey tests cover the new behavior, no-grant applicants, closed intake, peer/organization/role negatives, recovery, responsive English/Tamil and keyboard/skip-link navigation. Run relevant migrations/drift if schema changes, backend/static checks, generated contracts and web lint/types/tests/build before local acceptance.

## Boundaries and reporting

Use synthetic data and existing local adapters only. Production email, secure supporting documents, provider activation, native workflows, real consent/content decisions, staging and release acceptance remain later requirements. Keep existing dependency/CI gates enabled. Report completed local slices with test evidence, and report Process 2 complete only when all its in-scope local acceptance criteria pass. Notify the owner before continuing to Process 3.
