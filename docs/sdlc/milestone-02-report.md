# Milestone 2 - C01.1 localized publishing report

Status: implementation delivered on feature/cms-pages; validation underway. C01.2-C01.6 remain planned. Native runtime checks are deferred under ADR 0004; no production release claim.

Implemented: organization-scoped page drafts, independently published English/Tamil revisions, immutable publication history, versioned edit/publish/archive/restore, transactional audit metadata, scoped permission seeds, public ETags and bounded APIs. Next.js staff editor supports drafts, locale creation, preview, history and transitions. Public SSR pages and Flutter guest list/detail render escaped plain text. No media upload, HTML editor, enquiry collection or domain workflows in this slice.

Database: 2b3fcc875606 follows 1de5e104c2f7; adds pages/translations/revisions, scope-preserving cyclic publication FK, immutable revision trigger and nullable audit version/reason/field-name columns. Existing audit mutation trigger remains. The migration lifecycle is defined and the CMS tests cover upgrade-dependent behavior. Local Windows migration execution is currently blocked by the installed psycopg/SQLAlchemy driver returning SHOW server_version as bytes; no shared or production database was touched. Linux CI must provide migration upgrade/downgrade/re-upgrade and drift evidence before this slice is marked complete.

Security: exact organization permissions, fixed browser proxy allowlist, Origin and session-bound CSRF, 256 KiB CMS body cap, 50,000-character plain-text cap, SQL row locks and optimistic versions, no public drafts or staff fields. History pointers cannot cross locale/organization. No new external messaging or secrets. Public metadata uses only published values. Admin is noindex/no-store. Next.js streamed not-found pages may carry HTTP 200; content API absence is HTTP 404 and unavailable pages are noindex.

Validation: Ruff, Ruff format, MyPy, web lint/typecheck/Vitest, Flutter analyze/tests, OpenAPI export and contract generation, Next production build, and Flutter web build passed. The Flutter build retains the known secure-storage Wasm dry-run warning. CMS PostgreSQL tests were not executed locally because the Windows driver issue prevented migration setup; the Linux CI migration, backend test and drift gates passed in [run 35377007966](https://github.com/viviztech/edp-digital/actions/runs/35377007966). First browser run identified a streamed-page HTTP status assertion; acceptance now checks the API contract separately from rendered availability.


## C01.2 navigation update

C01.2 implementation is ready on the CMS feature branch. The web shell now derives navigation from the published CMS list and an explicit informational slug allowlist, preserving Home, Pages, Account and language controls even when CMS is unavailable. The public home has a responsive discovery grid and a localized Applications link; content titles remain CMS-owned. No unpublished page becomes navigable. Web validation passed lint, strict typecheck, six Vitest tests and the Next production build. Flutter public page routing from C01.1 remains available for guest/mobile navigation.
