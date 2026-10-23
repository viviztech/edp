# B02 post-training business tracking plan

Status: B02 local web/API acceptance is complete in [Phase 9](milestone-09-report.md), including profiles, frozen follow-up schedules, outcomes, ownership and immutable evidence. Earlier focused editing acceptance is recorded in the [dependency repair report](dependency-repair-report.md); B01 acceptance is separate in the [B01 report](b01-acceptance-report.md). Public publishing, final policy decisions, native clients, remote CI and release gates remain open.

## Scope

An enrolled participant may create one private business profile per enrollment, update it with optimistic version checks, and opt in explicitly before any public visibility. The profile stores bounded business details and revenue/investment bands rather than exact revenue. Every profile change creates an immutable historical snapshot. The enrollment remains the ownership boundary.

Each organization has a versioned follow-up policy with day offsets; the safe default is 30, 90, 180, 365, and 730 days after profile creation. A profile freezes the active policy into scheduled follow-ups. A participant can record one immutable outcome snapshot for each follow-up, including business activity, jobs, funding band, challenges, support requested, mentor interventions, and outcomes. Staff can view a bounded due queue and counts within their organization; only the participant can submit their own outcome.

## Acceptance criteria

- Owner and organization scope are server-derived. Cross-owner, wrong-organization, withdrawn-enrollment, and unauthorized staff requests fail without disclosing profile content.
- Profile creation is unique per enrollment, updates require an exact version, and revision rows are append-only at the database layer.
- Follow-up policy changes require a manager permission, version and audit reason. Existing scheduled dates remain fixed; new profiles use the current policy.
- Follow-up submission checks the owner and due record, rejects duplicates, stores an immutable historical snapshot, and audits only identifiers and field names.
- No business profile is public without explicit opt-in; the initial B02 release exposes no public business-profile endpoint. Financial bands are self-reported and are not presented as verified facts.
- English/Tamil participant and staff web flows use fixed CSRF-protected BFF routes, bounded request bodies, and loading/error/empty states.
- PostgreSQL migration round trip and drift, authorization and immutability tests, generated contracts, web checks, and authenticated browser acceptance pass before B02 is marked locally complete.

## Deferred decisions

Client approval is needed for public-profile publishing, final bands, follow-up ownership and notification delivery. Native mobile remains deferred under ADR 0004. No provider message is sent in this slice.
