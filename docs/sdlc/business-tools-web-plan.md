# Business tools web acceptance plan

Prepared 2026-10-24 under the development closure request. Implement the four authorized entrepreneur tools using the existing participant business profile and current server ownership rules.

1. Add a closed, CSRF-protected, byte-bounded BFF for owner card/catalogue/quotation/contact/follow-up commands. Forward only supported pagination/filter parameters. Treat printable HTML as an attachment with a restrictive sandbox policy.
2. Integrate English/Tamil forms for explicit card preview, save, publish/revoke and printable download; bounded catalogue editing and sharing; decimal-string quotations with catalogue references, server totals, immutable issue and download; private contact/task editing and history.
3. Keep command UUIDs and exact payloads during an uncertain response. Pause new writes, offer exact retry and authoritative reload, and preserve edited input. Require explicit reconciliation of stale versions before replacement. Guard unsaved navigation.
4. Add anonymous no-store share views that render only the deliberately public projection, with immediate revoked/unavailable states and safe links/text.
5. Verify route boundaries, CSRF/body limits, lost response recovery, explicit sharing, decimal values, immutable issue, UTC schedules, bilingual states and navigation. Run full web tests/lint/types/build and an authenticated synthetic browser workflow against the real API. Reconcile generated contracts, migrations and documentation with backend acceptance.

Real personal/contact data, provider delivery, remote CI, deployment, approved sharing/retention copy and client UAT remain separate release gates.
