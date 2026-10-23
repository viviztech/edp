# Content studio and media metadata web journey

Recorded: 2026-10-23. Process 2 connects the existing editorial and asset-record APIs. This is local development work; production content approval and the secure file pipeline remain separate release requirements.

## Scope and permissions

`/{locale}/admin/content?organization={uuid}` requires the selected organization's `cms.editorial.view` permission. The studio provides news, events, FAQs and testimonials, with separate English and Tamil entries. Creating the same kind and slug in the other language creates its counterpart. The UI uses the actual `cms.editorial.create`, `.update`, `.publish` and `.archive` permissions; restore uses `.update`. It does not infer permissions from role names. An explicitly requested ungranted organization never falls back to another grant.

Staff module navigation and account destinations expose content and media only for their scoped view capabilities. Server pages, browser BFF requests and API authorization each retain their access checks.

## Publication and recovery

New entries begin as drafts. Saving and lifecycle commands use the current `expected_version`. Dirty drafts prevent switching entries or filters and prevent publication; controls freeze during a request and duplicate mutations are locked. Failed requests retain the local fields. A version conflict requires loading the latest server values, reviewing the comparison, and explicitly selecting that version while keeping local changes before a retry. Duplicate addresses can be corrected without discarding the draft.

When a create response is lost or a server error leaves its outcome uncertain, resubmission is disabled. The explicit address check uses the current organization plus exact kind, locale and validated slug with `limit=1`; it does not scan pages or resend a write. A stored entry is shown for comparison without claiming it came from the attempted request. Adopting its version while keeping local content requires a separate explicit action. A genuine duplicate can instead keep its original record untouched while the editor chooses another address. A confirmed empty lookup enables an explicit retry.

Editorial entries do not have the separate publication snapshots used by CMS pages. Consequently published editorial entries are read-only in both the studio and API (`409 published_entry_read_only`). Editing requires archive with a reason, restore to draft, save and republish. Archive immediately removes the public entry; restore does not republish it. This rule leaves the existing CMS page revision behavior unchanged. Local changes also survive archive/restore when a concurrent publication is discovered during stale-draft recovery.

Event dates are entered explicitly in UTC, validated before writing and displayed according to the selected public locale. Each language has its own state and version.

## Lists and media boundary

Staff lists use bounded cursor pagination. Public editorial lists preserve kind and locale across next/first links. Public cursors are validated against the selected organization, kind, locale and published state; invalid or unavailable cursors return `400 invalid_cursor`. Pagination compares the actual ordering tuple: `(sort_order, id)` for most content and `(starts_at NULLS LAST, sort_order, id)` for events. It uses one list query and one additional scoped cursor lookup on subsequent pages.

`/{locale}/admin/media?organization={uuid}` requires `cms.asset.view` and shows only recorded title, filename, media type, byte size, scan state and visibility. It does not expose byte URLs, file inputs, creation, publishing or scanner controls. Secure upload, storage verification, scanning, authorized delivery and retention belong to Process 3. A recorded clean/public flag is not presented as proof that a file can be delivered.

The CMS BFF forwards only named page/editorial operations and read-only asset listing. Query allowlists are specific to collection/history/detail/mutation routes and reject repeated, unknown or unbounded inputs. Mutations retain origin/CSRF checks, JSON and streamed byte limits. Responses are private, no-store, and do not propagate upstream cookies or credentials.

## Verification

Focused component and BFF tests cover draft/save/publish, permission filtering, duplicate writes, network and stale-version recovery, a concurrent-publication archive/restore sequence, Tamil authoring, date validation, read-only media, cursor retry and public links. Server-page tests cover locale, organization mismatch, specific view permissions and unauthenticated entry. PostgreSQL tests in `tests/test_editorial_workflows.py` cover publication isolation, audit events, ordering, null dates, cursor scope/publication negatives and bounded query count. The integrated local acceptance run records browser and full static/build results in the process report.
