# Public subpages and navigation — 2026-10-10

## Scope

Create the public destinations named in the project plan: About, Eligibility, Benefits, Training Structure, Mentors, Success Stories, Resources, Schemes, Funding Opportunities, Events, News, FAQ, Contact, and Apply. The home page remains the fifteenth public destination. Existing editorial routes continue to serve Events, News, FAQ, and Stories.

The eleven program pages use bilingual starter content under the current CMS page route. A published CMS page with the same slug takes precedence. Starter content describes planned capabilities and avoids inventing eligibility rules, schedules, contacts, funding guarantees, named mentors, or testimonials.

## Acceptance criteria

- Every destination is reachable from a grouped, keyboard-operable navbar in English and Tamil.
- A public page index lists all program pages even when the CMS API is unavailable, plus any additional published CMS pages.
- Published CMS copy replaces starter content at the same slug without duplicate navigation entries.
- Every starter page has a distinct purpose, relevant next step, localized metadata, and a truthful availability note where final details are pending.
- Unknown slugs render the framework's not-found state with noindex metadata; English and Tamil routes render without the API.
- Web typecheck and a representative route check pass.
