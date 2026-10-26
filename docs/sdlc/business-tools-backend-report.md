# Business tools backend acceptance

Date: 2026-10-24 (Asia/Calcutta). The authorized digital card, catalogue, quotation
and entrepreneur mini CRM API slices are implemented and locally verified. Their
integrated web/browser acceptance belongs to the overall development closure
report. This checkpoint does not approve real contact collection, publication,
provider delivery or production release.

## Implemented behavior

`apps/api/app/modules/business_tools` contains typed contracts, relational models,
owner authorization, idempotent/versioned commands and thin routes. All reads,
mutations, command retries and downloads recheck the current owning Person,
organization, `participant.self` permission and active/completed participant and
enrollment. Peer and staff roles do not grant another owner's private tools.

Cards and catalogues have independent explicit publish/revoke commands. Saving
content revokes current sharing and requires deliberate republication. Anonymous
projections contain only deliberately selected business details/available items
under stable random share IDs; no internal owner/profile/enrollment/account data
is exposed. Withdrawal, suspension and permission removal immediately deny new
anonymous reads. Responses use no-store caching.

Quotations contain bounded manual or current catalogue lines, exact decimal
quantities/prices, server-calculated ROUND_HALF_UP line totals, bounded discount
and immutable issued snapshots. Issue rechecks catalogue ownership, availability,
price, currency and version. Business name and customer/line details remain fixed
after issue. Private printable HTML artifacts escape entered text, preserve line
breaks, use constant attachment filenames/restrictive CSP and audit downloads.

Private contacts and UTC follow-ups stay separate from marketing CRM and providers.
Expected versions and immutable request UUID/digests handle concurrent/lost writes.
Completed/cancelled tasks remain terminal. Bounded filters/pagination and exact
item/contact/task detail reads support explicit reconciliation even when an edited
record disappears from the current list. Safe append-only history records field
names and versions without copying customer or quotation prose.

## Database and security

Migration `q2a8b4c0d567` adds nine `tool_*` tables with composite profile/organization
foreign keys, bounded enums/numeric values and version/identity checks. Database
triggers preserve issued quotation/line immutability and append-only command and
history evidence; deferred constraints verify line counts and calculated subtotals.

Follow-up migration `q3b9c5d1e678` closes the SQL CHECK UNKNOWN/null case by explicitly
requiring a catalogue reference version whenever its item ID is present. The API
already rejected incomplete reference pairs; the SQL-negative test now verifies
the same condition directly. No new dependencies, file-upload system, payment or
external messaging provider was introduced.

## Verification

| Check | Actual result |
| --- | --- |
| Complete integrated API suite on final q3 schema | **404 passed, 1 skipped**, 0 failures/errors, 1276.64 seconds; 405 collected cases include 26 business-tool and 8 mobile policy cases |
| Final q3 diagnostics | 5 passed: legacy CSV migration, initial helpdesk-file cases, strict SQL-negative checks and exact-detail recovery authorization |
| Backend lint | `ruff check app tests migrations` passed |
| Backend strict typing | `mypy app` passed across 147 source files |
| Fresh complete migration chain | base → q3 head → base → q3 head passed; both Alembic drift checks clean |
| Schema count | 140 public tables including Alembic metadata; 9 new tool tables |

The complete regression suite ran on the guarded loopback **edp_test** database,
required by the existing legacy CSV migration safety assertion. It used verbose
per-case progress and `faulthandler_timeout=90`. The earlier interrupted full run
on edp_auth_test is preserved as incomplete and is not counted as acceptance.
The previous helpdesk stop did not recur on diagnostic or final full execution.

The one skip is the existing POSIX directory-mode/symlink check on Windows; Linux
confinement still needs its real environment. Four existing FastAPI/Starlette and
Alembic configuration deprecation warnings remain visible and unsuppressed.

Evidence is retained under `.tool-cache/business-tools-final-all-b64f1d1e/`
(`pytest.log`, `tests.xml`, `acceptance.json`), with diagnostic evidence under
`.tool-cache/business-tools-final-diagnose-4b793993/`. The fresh complete q3
migration evidence is `.tool-cache/edp_tools_migration_3450e383d484/result.json`
and its per-step logs. The acceptance JSON pins the backend tool source hashes.

## Remaining external gates

Exact-revision remote CI, approved sharing/contact/retention policy, deployed
TLS/hosting/secrets, native/runtime/provider checks, client UAT and release retain
their separate real-environment acceptance requirements. Locally runnable APIs
and synthetic anonymous previews do not satisfy those gates.

See [API usage and recovery](../api/business-tools.md) and the
[implementation plan](business-tools-implementation-plan.md).
