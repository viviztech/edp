# Milestone 8 / K01 local web/API acceptance

Recorded: 2026-10-21. Status: K01 web/API implementation and local acceptance complete. Requirement R10/backlog K01 and the [Milestone 8 plan](milestone-08-plan.md) define this phase. Formal remote CI, native and production release gates remain separate.

## Implementation

The knowledge repository covers schemes, funding programs and opportunities with independently authored English/Tamil entries, official sources, verification dates, eligibility/process/documents, geography/sector/tags, dates and optional official funding ranges. Versioned draft/publish/archive transitions preserve immutable resource evidence. Public discovery excludes participant-only and unpublished entries; active participants can save resources, express opportunity interest and open private funding cases. Closed entries remain discoverable through explicit filters but cannot start new interest/cases.

Funding cases retain the original source snapshot and follow the fixed owner-only progression through eligibility/document preparation/application/review, approval or rejection, and disbursement only after approval. Terminal states cannot be reopened or skipped. The staff funding queue is organization-scoped and read-only. Progress is participant-reported external activity, not a platform funding decision.

The phase adds a PostgreSQL migration with organization-aware keys, unique preferences/cases, publication/source guards and append-only revisions, interests and funding history. API and web input validation, CSRF and fixed BFF routes remain enforced. Private participant reasons and resource prose are excluded from audit payloads. No provider calls, new dependencies, live scheme imports, document uploads or outbound applications are introduced.

## Verification

- All 97 API/PostgreSQL regression tests passed in 284.74 seconds. The final four K01 database tests passed again after the audit-field, chronological-history and batched-tag-query refinements; the catalog query regression verifies two SQL reads. Two upstream TestClient/AnyIO deprecation warnings remain.
- Backend Ruff and formatting pass for 158 files; strict MyPy passes for 92 source files.
- The K01 migration upgraded a fresh temporary database to head, downgraded to the previous B02 head, re-upgraded and passed zero drift. The temporary database was removed. Project development and browser databases were upgraded with zero drift.
- OpenAPI and TypeScript contracts were regenerated. A semantic comparison against the earlier contract confirms 15 new paths and 15 new schemas, with no changed existing path/schema definitions.
- Web ESLint, TypeScript, all 132 tests across 28 files and the Next.js 16.4.2 production build pass. Coverage includes 26 new K01 behavior/proxy tests plus scoped navigation checks, in-flight and lost-response protection, independent pagination, failed writes and bilingual visibility.
- Dedicated K01 Chrome acceptance passes: eight staff-authored resources spanning all three kinds, both languages and public/participant/draft/closed/upcoming visibility; anonymous discovery/filter/source checks; saved-item removal/idempotency, opportunity interest, owner approval/disbursement and peer rejection; resource withdrawal/edit/expiry without changing original case evidence; role/owner/organization/enrollment, CSRF and unsupported-path negatives; database immutability and responsive layouts. No JavaScript errors were observed.
- Existing foundation/B01/B02 authenticated Chrome regression also passes with no JavaScript errors. Responsive public Tamil and funding-tracker screenshots were visually reviewed. K01 form styles are scoped to these new workspaces and preserve visible controls, focus and disabled states; history actions are localized.
- Browser script syntax/Ruff and diff whitespace checks pass. The authenticated browser CI job now includes the standalone K01 journey alongside existing foundation acceptance; remote CI itself has not run against these changes.

Browser evidence is stored locally at `.tool-cache/evidence/knowledge-staff-en.png`, `knowledge-public-ta-mobile.png`, `knowledge-funding-mobile.png` and `knowledge-staff-ta.png`. Both browser runners stopped their owned temporary servers. All records are synthetic; no live provider or production data was used. Deployment instructions, ERD, security/privacy/API guidance, participant/staff guides and the pending register are updated.

## Remaining gates

Native Flutter domain screens/device acceptance, approved resource ownership/content and translations, privacy/retention policy, remote CI, staging/UAT and production operations remain open. Official funding amount fields are optional and INR-only in this phase; other provider information remains available in text/source links pending owner decisions. Existing dependency and infrastructure release findings remain in the [dependency repair report](dependency-repair-report.md); no security gate has been waived. The next scheduled module is S01 helpdesk.
