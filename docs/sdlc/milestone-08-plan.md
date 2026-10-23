# Milestone 8 / K01 knowledge and funding plan

Recorded: 2026-10-21. Status: K01 web/API implementation and local acceptance complete; see the [phase report](milestone-08-report.md). Requirement R10, backlog K01 and master Sections 15, 26 and 37 govern this phase. Formal remote/native/security/operational release gates remain open.

## Complete vertical slice

1. K01.1: staff publish schemes, funding programs and opportunities with source and verification evidence; visitors and active participants browse scoped, filtered resources.
2. K01.2: participants save resources, express opportunity interest and maintain their own funding cases through controlled transitions with immutable history.
3. K01.3: English/Tamil web integration, generated contracts, permission/privacy negatives, PostgreSQL migration and workflow checks, authenticated/anonymous browser acceptance and documentation.

## Resource contract

Use one repository with a typed kind (`scheme`, `funding`, `opportunity`) and relational tags. Each resource has a language (`en` or `ta`), organization, slug, title, provider/department, type, description, eligibility, benefits, sector, geography, process, required-document labels, official source URL, contact/reference information, optional officially supplied funding amount/range/currency, opening/closing dates and last verification date. English and Tamil entries are independently authored and versioned; the selected language filters the catalog. Do not fabricate translations, funding amounts or live schemes. Acceptance uses synthetic data only.

Resources have `draft`, `published` and `archived` states plus optimistic versions. Edit only drafts. Explicit reasoned transitions publish, return to draft or archive; each change records immutable evidence and an audit event without content prose. A published entry requires a safe HTTP(S) official URL and non-future verification evidence. Dates must be consistent; availability is derived as upcoming/open/closed. Default discovery includes open/upcoming published entries; an explicit filter can include closed entries. Closed/upcoming resources must be clearly labeled, and closed resources cannot receive new interest/cases.

Public reads expose published public entries only. Active enrolled participants may also see published participant-only entries for their organization. An unrelated role or organization does not grant access. A saved resource that becomes unavailable must be represented without revealing draft/private text. Existing funding cases preserve the submitted source snapshot and history when a resource changes or expires.

Agreed routes: authenticated `/api/v1/knowledge/organizations/{org}` with staff `/items`, `/items/{id}`, `/items/{id}/{publish|draft|archive}` and `/items/{id}/history`; participant `/catalog`, `/catalog/{id}`, `/mine`, `/saved/{item_id}`, `/interests/{item_id}`, `/funding-cases` and `/funding-cases/{id}/status`. Anonymous read routes are `/api/v1/public/organizations/{org}/knowledge` and its item detail. Lists use bounded pagination and validated search/kind/language/sector/geography/tag/availability filters. The fixed web BFF forwards only allowed methods, paths and bounded query/body values with CSRF on mutations.

## Participant funding rules

An owner must hold `participant.self` and an active enrollment in the organization. Derive participant identity from the authenticated Person; never trust an owner ID from the request. Keep one funding case per participant/resource, unique saved items and unique opportunity interests; safe repeats cannot create duplicate evidence. A funding case retains the source evidence shown when it was created. Progress is participant-reported external activity, not an organizational funding decision or guarantee.

Allowed progression is `interested → eligibility_check → document_preparation → applied → under_review → approved|rejected`, then `approved → disbursed`. Rejected and disbursed are terminal in this phase. No skips, arbitrary status mutation or resubmission after rejection. Every transition requires an exact version and a meaningful bounded reason, adds immutable history and audits identifiers/field names only. Only the owner can change a case; `funding.manage` grants a bounded organization-scoped staff read queue without impersonating the participant.

Permissions: `knowledge.manage` for Super Admin, Program Director, Program Manager, Funding Coordinator and Content Manager; `funding.manage` for Super Admin, Program Director, Program Manager and Funding Coordinator. Existing participant permission remains unchanged. Public routes must never expose bookmarks, interests, cases, internal history or draft text.

## Acceptance gates

- Alembic schema/FK/unique/check/index/append-only evidence constraints, upgrade/downgrade/re-upgrade and zero drift on a guarded isolated database.
- Separate-actor API tests cover all resource kinds and languages, publication/source/date validation, filters/pagination, saved/interest idempotency, funding approval/disbursement and rejection branches, immutable snapshots/history, stale writes, wrong owner/org, non-enrolled/withdrawn participants and unauthorized staff.
- Web provides anonymous resource discovery, active participant saves/interest/funding history and staff resource authoring/transitions/scoped case queue. Use generated contracts, English/Tamil labels, accessible fields, empty/loading/error/conflict states and visible official source/verification/availability. Preserve entered data on failed writes and prevent duplicate consequential actions.
- Meaningful component/BFF tests, backend Ruff/format/strict typing, full PostgreSQL regression suite, regenerated OpenAPI/TypeScript contracts, web lint/types/tests/production build and diff whitespace checks pass.
- Real Chrome journey exercises staff author/publish, anonymous/private/draft negatives and filtering, participant saves/interest/full funding progression, unrelated actor/CSRF/invalid-path negatives, database evidence and responsive layouts without JavaScript errors. Existing foundation/B01/B02 acceptance remains green.
- Update ERD/security/privacy/API/user guidance, backlog/pending register, README and the phase report with actual results. Report local acceptance separately from remote CI and production release.

Native Flutter domain screens and native-device acceptance remain deferred under ADR 0004's current development sequencing. No provider lookup, external application submission, automatic recommendation, notification delivery, document upload or financial guarantee is introduced. Final resource ownership/content, retention and client policy approval remain release work.

## Local acceptance result

All 97 API/PostgreSQL tests, final K01 database checks, backend Ruff/format/strict typing, migration round trip/drift, regenerated compatible contracts, web lint/types, 132 tests and production build pass. The dedicated K01 Chrome journey and existing foundation/B01/B02 regression pass without JavaScript errors. Responsive evidence was reviewed, including visible form controls and Tamil public discovery. K01 is locally accepted for the scoped web/API channels; S01 helpdesk is the next scheduled development phase.
