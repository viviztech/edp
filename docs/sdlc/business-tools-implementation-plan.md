# Business tools implementation and acceptance

Prepared 2026-10-24. Implements the four authorized P1 slices after the existing
business profile: bilingual digital card, catalogue, quotation and private mini CRM.
The owner boundary is the current `participant.self` permission and an active or
completed enrollment/participant belonging to the authenticated Person. A staff
permission does not grant private access. Every request rechecks that boundary.

## Contracts and data

Authenticated routes live under `/api/v1/business-tools/organizations/{org}/profiles/{profile}`.
Card and catalogue publishing are separate expected-version decisions. Their stable
anonymous share references return only selected public business text and prices;
no account, enrollment, owner UUID, financial history or customer data is projected.
All responses use `no-store`. Revocation and withdrawal immediately remove public access.

Relational tables store card, catalogue settings/items, quotation/lines, contacts
and follow-ups. Compound scope foreign keys prevent cross-profile references.
Every write carries an immutable request UUID. The server serializes a profile's
commands, compares a canonical request digest and rejects reuse with changed input.
Updates also require the expected version. The transactional command ledger and safe
history contain identifiers and changed field names, not customer content. No
automated provider, email or organization CRM side effect exists.

Quotations contain at most 50 lines, explicit customer text and INR/USD/EUR/GBP
currency. Prices and discounts have two decimal places; quantities have three.
Each line rounds quantity times price to two places using decimal ROUND_HALF_UP;
subtotal is the sum of rounded lines and total is subtotal minus bounded discount.
Catalogue references must match current owner, availability, currency and version;
their displayed name and current price are snapshotted on save. Issued quotations
and their lines become immutable. Export is an escaped HTML printable document
with a safe constant filename and an audited authorized download. It makes no
tax/invoice or accounting compliance claims.

## Acceptance

1. Card: bilingual save/retry/stale save, explicit publish/revoke, safe anonymous
   projection, escaped printable artifact, current-owner/withdrawal negatives.
2. Catalogue: bounded lists, exact decimals, versioned edits, explicit share/revoke,
   current price/version references and consistent immutable quotation history.
3. Quotation: server totals/rounding/bounds, scoped catalogue references, lost issue
   retry, immutable issued snapshot and safe authorized artifact.
4. Mini CRM: private scoped contact lifecycle, UTC due times, terminal follow-up
   transitions, versioned updates, safe history, bounded filters, retry negatives.
5. Verify PostgreSQL migration round trip/drift, direct constraint negatives,
   backend lint/types/tests, deterministic OpenAPI/web integration and build.

Native/external runtime, exact-revision CI, real sharing/contact policy, retention,
UAT and release remain external gates. Synthetic local testing does not approve
real collection or publication.
