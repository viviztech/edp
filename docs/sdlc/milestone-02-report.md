# Milestone 2 - C01.1 localized publishing report

Status: implementation delivered on feature/cms-pages; validation underway. C01.2-C01.6 remain planned. Native runtime checks are deferred under ADR 0004; no production release claim.

Implemented: organization-scoped page drafts, independently published English/Tamil revisions, immutable publication history, versioned edit/publish/archive/restore, transactional audit metadata, scoped permission seeds, public ETags and bounded APIs. Next.js staff editor supports drafts, locale creation, preview, history and transitions. Public SSR pages and Flutter guest list/detail render escaped plain text. No media upload, HTML editor, enquiry collection or domain workflows in this slice.

Database: 2b3fcc875606 follows 1de5e104c2f7; adds pages/translations/revisions, scope-preserving cyclic publication FK, immutable revision trigger and nullable audit version/reason/field-name columns. Existing audit mutation trigger remains. The migration lifecycle is defined and the CMS tests cover upgrade-dependent behavior. Local Windows migration execution is currently blocked by the installed psycopg/SQLAlchemy driver returning SHOW server_version as bytes; no shared or production database was touched. Linux CI must provide migration upgrade/downgrade/re-upgrade and drift evidence before this slice is marked complete.

Security: exact organization permissions, fixed browser proxy allowlist, Origin and session-bound CSRF, 256 KiB CMS body cap, 50,000-character plain-text cap, SQL row locks and optimistic versions, no public drafts or staff fields. History pointers cannot cross locale/organization. No new external messaging or secrets. Public metadata uses only published values. Admin is noindex/no-store. Next.js streamed not-found pages may carry HTTP 200; content API absence is HTTP 404 and unavailable pages are noindex.

Validation: Ruff, Ruff format, MyPy, web lint/typecheck/Vitest, Flutter analyze/tests, OpenAPI export and contract generation, Next production build, and Flutter web build passed. The Flutter build retains the known secure-storage Wasm dry-run warning. CMS PostgreSQL tests were not executed locally because the Windows driver issue prevented migration setup; the Linux CI migration, backend test and drift gates passed in [run 35377007966](https://github.com/viviztech/edp-digital/actions/runs/35377007966). First browser run identified a streamed-page HTTP status assertion; acceptance now checks the API contract separately from rendered availability.


## C01.2 navigation update

C01.2 implementation is ready on the CMS feature branch. The web shell now derives navigation from the published CMS list and an explicit informational slug allowlist, preserving Home, Pages, Account and language controls even when CMS is unavailable. The public home has a responsive discovery grid and a localized Applications link; content titles remain CMS-owned. No unpublished page becomes navigable. Web validation passed lint, strict typecheck, six Vitest tests and the Next production build. Flutter public page routing from C01.1 remains available for guest/mobile navigation.


## C01.3 ? Editorial content

Implemented localized News, Events, FAQ, and Testimonials with bounded public listing/detail APIs, explicit draft/publish/archive/restore transitions, event dates and deterministic ordering, organization-scoped editorial permissions, audit records, and public Next.js and Flutter views. Validation: web lint/typecheck, Flutter analyze, Python compileall, and `git diff --check` passed. Native runtime tests remain deferred to macOS migration per ADR 0004.


## C01.4 ? Asset quarantine foundation

Added organization-scoped asset metadata with allowlisted MIME types, a 10 MiB size limit, quarantine scan states, explicit public approval, bounded staff/public listing APIs, audit events, and a PostgreSQL migration. The current slice intentionally keeps uploads quarantined until the object-storage and malware-scanning adapters are connected; no asset can become public while its scan status is pending.


C01.4 follow-up adds an authenticated scanner callback, scanner-key configuration, rejection of non-clean assets at publication, and an object-storage protocol boundary for S3-compatible adapters. The repository still requires deployment-specific object-storage and malware-scanner implementations before production media uploads are enabled.


## C01.5 ? Privacy-safe enquiries

Added a minimal organization-scoped enquiry table and API. Submission requires the configured privacy notice version, validates bounded contact fields, stores a dedupe hash, returns a generic 202 receipt for new and duplicate submissions, and records only allowlisted audit metadata. Staff reads require the separately granted `enquiry.view` permission; enquiry data is excluded from public CMS DTOs and logs. Rate limiting and retention execution remain deployment gates.


## C01.6 ? SEO foundation

Added localized sitemap and robots routes, canonical metadata, English/Tamil language alternates, and public editorial metadata. Web lint, strict typecheck, and production build passed.


## C02 foundation ? CRM leads

Started the CRM vertical with organization-scoped leads, normalized duplicate protection, attributed source/campaign fields, explicit lifecycle states, assignment/version checks, audited create/update operations, CRM Executive permissions, and a PostgreSQL migration. Follow-up activities, CSV export, merge review, Meta ingestion, and application conversion remain separate slices.


## C02 follow-up activities

Added append-oriented lead follow-up activities for calls, email, meetings, tasks, and notes with organization checks, separate CRM activity permissions, due dates, actor attribution, and audit metadata.
