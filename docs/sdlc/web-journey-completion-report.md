# Process 2 / web journey completion report

Recorded: 2026-10-23. Status: local web/API acceptance complete. Scope follows the [process plan](web-journey-completion-plan.md). Baseline commit `c9877ab` and all continuation work remain local under the owner's instruction; no push or deployment is authorized.

## Implemented behavior

- Ordinary authenticated applicants can continue to applications without organization/staff grants. Valid organization/intake identifiers survive account registration, local verification and sign-in; malformed or repeated explicit destinations are rejected instead of silently opening another intake. External return destinations are ignored.
- Owner-only application history is independent of open-intake discovery, uses bounded stable pagination and omits answers, scores, private notes and decision reasons. Closed-cycle applications remain readable. Every non-draft state is read-only, and draft creation rejects every later state consistently. Reload preserves the currently selected intake and reconciles both detail and history after an uncertain write. Failed reads preserve context, history replacement cannot race an old page, and busy destinations are explicitly disabled. Dirty answers are protected on cycle/history/reload changes, global link clicks and document unload.
- Account and participant navigation use actual capabilities, preserve organization/locale, include learning and provide working skip targets. Tamil navigation labels were corrected.
- A localized public contact form is enabled only when both localized privacy links and approved consent text are configured. Anonymous BFF traffic uses CSRF/origin validation, a fixed server organization, a honeypot, fatal UTF-8 decoding and a 32 KiB body bound. The direct API applies the same body boundary plus persistent source/email throttles, current consent-version checks and deduplication. Public receipts exclude contact data.
- Enquiry staff can read a scoped paginated queue/detail and advance `new → reviewed → closed` using expected versions. Explicit refresh after an uncertain status response reconciles the detail and filtered queue. Received content is immutable, initial state/version and transition evidence are database guarded, and audits omit message/contact text. Staff notes are outside this slice.
- Staff content authoring exposes the existing create/update/publish/archive/restore permissions, supports explicit stale-version review while retaining local text, and prevents in-place edits to a published entry. An uncertain create freezes retries until a bounded exact-address check; adopting stored content is explicit and preserves the local draft. Publication changes require archive, restore to draft, edit and republish. Public content lists have ordered, scoped pagination including events with no date. A pre-existing non-empty public-list DTO validation failure was corrected without changing its response shape. CMS mutations reject malformed UTF-8.
- Media screens expose permission-scoped metadata only. Byte upload, scanning, verified storage and public delivery remain Process 3 work; metadata does not imply those capabilities exist.

## Verification ledger

| Check | Current evidence |
| --- | --- |
| API static checks | Final Ruff clean; 180 files formatted; mypy 104 sources clean |
| API/PostgreSQL | Full regression: 128 passed in 480.68 s, with two upstream deprecation warnings. After the additive staff slug filter, final editorial/CMS regression: 13 passed in 69.58 s, including the new exact-scope filter case |
| Migrations | Final enquiry trigger reapplied on guarded `edp_test`; head downgrade/re-upgrade and zero drift pass. Newly owned empty database passes head → base → head and zero drift, then is removed |
| Web static/unit/build | Final 308 tests across 57 files, clean ESLint, TypeScript and production build pass |
| Chrome | Existing foundation/B01/B02, K01, helpdesk and reporting/impact regressions pass. New applicant → enquiry → editorial/media runner passes all three scripts on the final build, including no-grant registration, closed-cycle receipt/status, staff lifecycle, two-tab content recovery, 27-entry public pagination, strict API negatives and no JavaScript errors |
| Responsive and keyboard | Applicant/enquiry: 360/390/768/1280 px; editorial/public/media: 360/768/1280 px. English/Tamil and main-target focus assertions pass. Applicant, public enquiry, staff enquiry, editorial studio, media and public content screenshots visually inspected without clipping |
| Secret scan | Verified Gitleaks 8.24.3 preliminary sealed source snapshot: 635 files, zero findings. Final selected-source scan evidence is retained under ignored `.local/process2-gitleaks-final-20261023` |
| Generated contracts | OpenAPI and TypeScript regenerated twice with identical SHA256 hashes. Paths 223 → 228, no removed paths; five new history/enquiry paths. Only existing schema change is additive `EnquiryView` version/timestamps; staff editorial list gains optional validated exact slug |

The browser runner uses owned loopback servers, temporary keys, synthetic policy settings and a guarded synthetic database. It executes applicant, enquiry and editorial acceptance sequentially and records diagnostics in ignored `.tool-cache/{web-journey-browser-test,enquiry-browser-test,editorial-browser-test}.log` files. CI includes the same runner; no remote execution is claimed. All owned test servers were stopped. The installed Next.js documentation confirms that streamed not-found pages can carry HTTP 200; invalid HTML-query tests require the actual not-found UI, noindex and no content cards, while API negative status assertions remain strict.

## Remaining release boundaries

Public enquiry collection remains disabled by default until approved bilingual consent and privacy links are supplied. Secure documents, verified media bytes, real delivery providers, native workflows, staging, operational recovery, UAT and production approval remain outside this local web slice. Nine high npm findings from unpatched transitive `braces` remain tracked under the baseline. Remote CI remains unverified under the owner's local-only instruction; its gate has not been waived or marked passed.

Process 2's in-scope local acceptance is complete. Notify the owner before continuing to Process 3 shared secure files. The release boundaries above remain open.

## Enquiry boundary follow-up

Preparing Process 3 exposed an error in the earlier direct-API boundary claim: commit `23a5a46` enforced 32 KiB in the public BFF, while the API middleware still used its general 256 KiB cap. The API now independently enforces 32 KiB for public enquiries. Ten enquiry API/database tests pass (33.44 s), including otherwise-valid Tamil JSON at exactly 32,768 bytes and rejection at 32,769 bytes with normal, misleading and absent/chunked Content-Length. Only the accepted record persists. Existing domain JSON limits remain unchanged. Ruff lint/format pass; this correction does not claim a new full-suite or browser run.
