import type { components } from "../../../lib/api-contracts";

export const org = "11111111-1111-4111-8111-111111111111";
export const resourceId = "22222222-2222-4222-8222-222222222222";
export const timestamp = "2026-10-21T08:00:00Z";
export const root = `/api/knowledge/organizations/${org}`;
export function resource(overrides: Partial<components["schemas"]["KnowledgeView"]> = {}): components["schemas"]["KnowledgeView"] {
  return { id: resourceId, kind: "funding", locale: "en", slug: "synthetic-funding", title: "Synthetic funding",
    provider: "Example provider", type: "Grant", description: "Synthetic official program description",
    eligibility: "Read the official eligibility rules", benefits: "Training support", sector: "Services", geography: "Tamil Nadu",
    tags: ["enterprise"], application_process: "Apply with the official provider", documents: ["Application"],
    official_url: "https://example.gov.in/funding", opens_on: "2026-01-01", closes_on: "2026-12-31",
    last_verified_at: "2026-10-21", visibility: "public", contact: "Official reference", funding_amount_min: "1000.00",
    funding_amount_max: "2000.00", currency: "INR", state: "published", version: 2, published_at: timestamp,
    updated_at: timestamp, availability: "open", ...overrides };
}
export function fundingCase(overrides: Partial<components["schemas"]["FundingCaseView"]> = {}): components["schemas"]["FundingCaseView"] {
  return { id: "33333333-3333-4333-8333-333333333333", item_id: resourceId, item_title: "Synthetic funding", locale: "en",
    participant_id: "44444444-4444-4444-8444-444444444444", status: "interested", version: 1,
    created_at: timestamp, source: resource(), history: [{ id: "event-1", status: "interested", reason: "Tracker started", created_at: timestamp }], ...overrides };
}
export function emptyMine(): components["schemas"]["KnowledgeMine"] {
  return { saved_items: [], interests: [], funding_cases: [], next_saved_cursor: null, next_interest_cursor: null, next_case_cursor: null };
}
export function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}
