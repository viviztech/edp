# Entrepreneur business tools API

The four locally implemented tools use the existing private business profile.
They are separate from staff marketing CRM and do not send messages or collect
payments. See the generated OpenAPI contract for exact field lengths and types.

Base path: `/api/v1/business-tools/organizations/{organization}/profiles/{profile}`.
All private requests require the current authenticated owner, `participant.self`,
and an active or completed enrollment and participant. Staff access does not grant
access to an entrepreneur's customer records or quotations. Every response and
anonymous share response uses `Cache-Control: no-store`.

| Tool | Read | Commands |
| --- | --- | --- |
| Card | `GET /card`, `GET /card/artifact` | `POST /card`, `POST /card/sharing` |
| Catalogue | `GET /catalogue`, `GET /catalogue/items/{id}` | `POST /catalogue/items`, `POST /catalogue/items/{id}/update`, `POST /catalogue/sharing` |
| Quotation | `GET /quotes`, `GET /quotes/{id}`, `GET /quotes/{id}/artifact` | `POST /quotes`, `POST /quotes/{id}/update`, `POST /quotes/{id}/issue` |
| Private CRM | `GET /contacts`, `GET /contacts/{id}`, `GET /tasks`, `GET /tasks/{id}` | `POST /contacts`, `POST /contacts/{id}/update`, `POST /tasks`, `POST /tasks/{id}/update` |
| Safe history | `GET /history` | Append only as part of the corresponding command |

Lists accept `limit` (1–100, default 25) and `offset` (0–10000). Contact lists
support `status` and bounded literal name `search`; tasks support `contact_id`
and `status`; history supports `kind` and `resource_id`. Results include `items`,
`limit` and `offset`; catalogue also includes sharing `settings`.

## Write and recovery rules

Every command has a client-generated UUID `request_id`. Keep that UUID and the
exact submitted input until the response is certain. A retry of that command
does not create another record or repeat its state transition. The response
returns current authoritative resource state; it can reflect a later edit or
revocation. Reusing a UUID for another operation or changed input fails with
`request_conflict` (409). The server rechecks ownership before resolving a retry.

Updates and sharing/issue decisions also require `expected_version`. Card creation
uses zero; a new catalogue sharing configuration may use zero. All other updates
start at one. A stale version fails with `version_conflict` (409). Preserve local
input, fetch current state and reconcile before submitting a new UUID and version.
After an uncertain network failure, retry the exact UUID/input or inspect current
state; do not silently turn the uncertain write into a new command.

Item, contact and task detail routes return current state independently of list
filters and pagination. Use the exact resource detail to reconcile an editor;
a concurrently completed task may disappear from a pending-only list while its
detail remains accessible to the current owner.

## Sharing

Saving a card leaves it unpublished. Editing a published card immediately revokes
its current public projection. Catalogue item creation or updates likewise revoke
catalogue sharing and increment the catalogue settings version. Sharing is a
separate explicit command `{request_id, expected_version, published}`. Existing
business profile `public_opt_in` never implicitly publishes either tool.

Anonymous reads use `/api/v1/public/business-tools/cards/{share_id}` or
`/api/v1/public/business-tools/catalogues/{share_id}`. Card fields are only the
business details explicitly entered in the card. Public catalogue items expose
only bilingual product/service text, availability, explicit price/currency and
the catalogue share reference. They omit internal item/profile/owner/organization
identifiers. Only available items appear. Revocation, withdrawal, account
suspension or loss of owner permission removes anonymous access.

## Quotations and artifacts

Price/discount values have two decimal places and quantities have at most three.
Clients should send decimal strings. Server line totals use decimal
`ROUND_HALF_UP(quantity × unit_price, 2)`. Subtotal is the sum of rounded line
totals; final total subtracts a nonnegative discount no greater than the subtotal.
Values and aggregate totals cannot exceed `999999999999.99`. At most 50 lines
are accepted. Supported currencies are INR, USD, EUR and GBP.

Each line is explicitly manual, or references a current catalogue item with both
`catalogue_item_id` and `catalogue_version`. References must belong to the same
profile, be available and match current price/currency/version. The server
snapshots the bilingual item name; changing catalogue values later never changes
an issued quotation. Issuing also rechecks references, so changed catalogue items
require deliberate draft reconciliation. `catalogue_conflict` is a 409.

A draft may be updated with its expected version. Issue is an idempotent command
and permanently freezes quotation fields, business/customer details, line values,
totals and dates. PostgreSQL triggers enforce immutability and deferred checks
verify the line count and subtotal. Artifacts are escaped, printable HTML
attachments with constant filenames and restrictive content security policy.
Downloads require current ownership and append an audit record. Quotations are
labelled as quotations and carry no tax invoice/accounting compliance claim.

## Private follow-ups

Contacts use `lead`, `customer` or `archived`; an archived contact stays archived
and cannot receive new tasks. Task creation accepts an explicit contact, title,
notes and an offset-aware due time, which the server normalizes to UTC. A pending
task may be edited, completed or cancelled. Completed/cancelled tasks remain
terminal; completion stores the server UTC timestamp. No provider/reminder is
triggered. History contains safe identifiers, versions, actions and field names,
without customer text or quotation contents.

Production use still requires approved collection/sharing/retention content and
the separately documented operational release gates. Synthetic local sharing
acceptance is not publication of real entrepreneur details.
