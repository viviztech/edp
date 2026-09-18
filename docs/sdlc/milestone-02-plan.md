# Milestone 2 - Public website and CMS

Status: planned; implementation not started. Authority: master Sections 2, 6, 24, 30, 35 and 38; backlog C01 (P0). The [native deferral](../architecture/adr/0004-native-verification-deferral.md) permits this transition without falsely closing Milestone 1. Final branding, copy and translation ownership remain open; use clearly marked synthetic draft content during development.

## Product requirements and acceptance

| ID | Story and acceptance | Size / dependency |
|---|---|---|
| C01.1 | As a Content Manager, create/edit/preview an English or Tamil page in my organization, then explicitly publish it. Anonymous web and Flutter users see only the published revision. Draft edits never change live content; missing locales return unavailable rather than silent fallback. Unauthorized or wrong-org access is denied. Publish/archive and edits are audited transactionally. | L / foundation |
| C01.2 | As a visitor, navigate localized Home, About, Eligibility, Benefits, Training Structure, Mentors, Success Stories and Apply information. Organization-scoped menus, items and banners reference only eligible published content. Apply links to existing registration and clearly indicates application submission is not yet available. | L / C01.1 |
| C01.3 | As an editor, publish news, events, FAQ and testimonials with localized content and appropriate dates/order. Public lists are bounded; archived/draft entries are hidden. Event date/time display is explicit; no fabricated event booking. | L / C01.1 |
| C01.4 | As an editor, upload and reuse approved images/resources in object storage. Quarantine, validation, scan status, size/type limits and authorization prevent unsafe publication. Resources show title/type/size; public files are explicitly approved for public access. | L / C01.1; object-storage and scanning adapters |
| C01.5 | As a visitor, submit a contact enquiry with minimal contact fields and an approved privacy notice. Generic acknowledgement, rate limits and duplicate protection apply. Only separately permitted staff can read the submission; no contact data enters public CMS DTOs or logs. | M / approved notice before real collection |
| C01.6 | As a visitor/search engine, receive published localized metadata, canonical URLs, sitemap and language alternates; drafts/previews are noindex and uncached. Web/mobile support loading/error/empty states, accessible forms and English/Tamil UI. | M / C01.1-5 |

Master pages Resources, Events, News, FAQ and Contact are covered above. Schemes and Funding Opportunities get informational CMS pages only in this milestone; structured repositories/tracking remain Phase 8. Mentors page is editorial content, not the mentoring workflow. Application forms remain Phase 4. CRM integration of enquiries is Phase 3 and must not silently create leads now.

Scheduled publication is optional (master: if feasible); it is not in the initial acceptance commitment. Rich-text editing, public assets and navigation are later slices within this milestone, not implied by the first page slice. No website builder, arbitrary HTML, real notifications or domain workflows are introduced in C01.1.

## Execution order and reviewable changes

1. C01.1 data/API: implement the reviewed page design, migration, explicit permission seed, service transitions, negative authorization tests and exported contracts. Do not declare the feature complete at this intermediate point.
2. C01.1 channels: web CMS list/editor/preview/publish/archive and public page; Flutter public page/list; localization and accessibility states. Run the connected editor-to-public workflow. Admin authoring is web-only.
3. C01.2 navigation and informational pages; C01.3 content types, each with its own schema/API/UI/test slice.
4. C01.4 media/resources after validating storage/scanning boundaries; do not bypass quarantine to supply placeholder images.
5. C01.5 enquiry privacy/abuse boundaries; C01.6 full SEO and accessibility review.

Deliver each slice through a feature branch and reviewed CI-green merge. Use two-week sprints where practical; no calendar promise without capacity and content inputs. Keep the current authentication flows working throughout.

## First slice Definition of Done evidence

Requirements: C01.1 and [page design](../architecture/cms-page-design.md). Database: upgrade/downgrade/re-upgrade and drift on disposable PostgreSQL; constraint and concurrent-publish tests. Security: anonymous/inactive/participant/revoked-role/wrong-org tests, stored-markup payload tests, BFF Origin/CSRF and body limits, audit rollback and no draft leaks. Backend: lint/type/tests; frontend: lint/type/tests/build; Flutter: analyze/tests/build. Regenerate OpenAPI/TypeScript and keep Dart DTO parity explicit. CI must pass.

Manual/browser smoke: staff creates English/Tamil drafts, previews, publishes English, confirms Tamil remains hidden, publishes Tamil, edits without changing live output, checks stale-write conflict, archives and confirms public removal. Include mobile-width and accessible labels. Flutter public flow gets automated/widget evidence; actual native runtime checks remain deferred under ADR 0004. Record every gate as passed/failed/deferred/N/A, never infer a pass from a scaffold.

## Ownership and open inputs

Engineering owns implementation, authorization and test evidence. Client/content owner must supply approved branding, copy/translations, testimonial consent and public resource rights before launch. Operations must choose production domain/object storage/scanning and deployment policy before their live slices. Privacy owner must approve contact notice/retention before real enquiries. Existing launch gates remain unchanged. No new input is required to begin C01.1 using synthetic content.

Next authorized implementation: C01.1 localized publishing vertical slice. This planning change adds no runtime routes or migrations.
