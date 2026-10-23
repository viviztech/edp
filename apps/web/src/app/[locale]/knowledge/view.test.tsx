import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { components } from "../../../lib/api-contracts";
import KnowledgeWorkspace from "./view";
import { words } from "./content";
import { emptyMine, fundingCase, org, resource, root, response, timestamp } from "./test-fixtures";

type Mine = components["schemas"]["KnowledgeMine"];
function mockApi(options: { initial?: Mine; resources?: ReturnType<typeof resource>[]; conflict?: boolean; status?: number; lostResponse?: boolean } = {}) {
  let mine = options.initial ?? emptyMine(); let conflict = options.conflict ?? false;
  const writes: { path: string; body: Record<string, unknown>; method: string }[] = [];
  const reads: string[] = [];
  const resources = options.resources ?? [resource()];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const [path] = url.split("?");
    if (url === "/api/session/csrf") return response({ csrf_token: "csrf" });
    if (!init?.method) {
      reads.push(url);
      if (path === `${root}/catalog`) return response({ items: resources, next_cursor: null });
      if (path === `${root}/mine`) return response(mine);
    }
    if (init?.method) {
      expect(new Headers(init.headers).get("x-csrf-token")).toBe("csrf");
      const body = init.body ? JSON.parse(String(init.body)) as Record<string, unknown> : {};
      writes.push({ path, body, method: init.method });
      if (options.status) return response({ error: { code: "rejected" } }, options.status);
      if (path.endsWith("/status")) {
        if (conflict) { conflict = false; mine = { ...mine, funding_cases: mine.funding_cases.map((item) => ({ ...item, version: 2 })) }; return response({}, 409); }
        const item = mine.funding_cases[0]; expect(body.expected_version).toBe(item.version);
        const status = body.status as typeof item.status;
        mine = { ...mine, funding_cases: [{ ...item, version: item.version + 1, status,
          history: [...item.history, { id: `event-${item.version + 1}`, status, reason: String(body.reason), created_at: timestamp }] }] };
        if (options.lostResponse && writes.length === 1) return Promise.reject(new Error("Response lost after commit"));
        return response(mine.funding_cases[0]);
      }
      const item = resources.find((item) => path.endsWith(item.id)) ?? resources[0];
      if (path.includes("/saved/")) {
        mine = { ...mine, saved_items: init.method === "DELETE" ? [] : [{ item_id: item.id, item, created_at: timestamp }] };
        return response(init.method === "DELETE" ? {} : mine.saved_items[0], init.method === "DELETE" ? 204 : 200);
      }
      if (path.includes("/interests/")) { mine = { ...mine, interests: [{ id: "interest", item_id: item.id, item_title: item.title, locale: item.locale, created_at: timestamp }] }; return response(mine.interests[0], 201); }
      if (path.endsWith("/funding-cases")) { mine = { ...mine, funding_cases: [fundingCase()] }; return response(mine.funding_cases[0], 201); }
    }
    throw new Error(`Unexpected request ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock); return { writes, reads, fetchMock };
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("participant knowledge resources", () => {
  it("applies bounded filters and keeps official source, verification and closed status visible", async () => {
    const api = mockApi({ resources: [resource({ availability: "closed" })] });
    render(<KnowledgeWorkspace org={org} locale="en" />);
    const article = await screen.findByRole("article", { name: "Synthetic funding" });
    expect(within(article).getByRole("link", { name: "Official source" }).getAttribute("href")).toBe("https://example.gov.in/funding");
    expect(within(article).getByText("Closed")).toBeTruthy();
    expect((within(article).getByRole("button", { name: "Start funding tracker" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Search resources"), { target: { value: "equipment" } });
    fireEvent.change(screen.getByLabelText("Resource kind"), { target: { value: "funding" } });
    fireEvent.change(screen.getByLabelText("Availability"), { target: { value: "closed" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => expect(api.reads.some((url) => url.includes("q=equipment") && url.includes("kind=funding") && url.includes("availability=closed"))).toBe(true));
  });

  it("saves, removes, records opportunity interest once and starts a funding case with owner derived by API", async () => {
    const opportunity = resource({ id: "55555555-5555-4555-8555-555555555555", title: "Synthetic exhibition", kind: "opportunity", funding_amount_min: null, funding_amount_max: null });
    const api = mockApi({ resources: [resource(), opportunity] }); render(<KnowledgeWorkspace org={org} locale="en" />);
    const catalog = await screen.findByRole("region", { name: words.en.title });
    const funding = within(catalog).getByRole("article", { name: "Synthetic funding" });
    fireEvent.click(within(funding).getByRole("button", { name: "Save resource" }));
    await screen.findByText("Saved.");
    fireEvent.click(within(funding).getByRole("button", { name: "Remove saved resource" }));
    await waitFor(() => expect(api.writes.length).toBe(2));
    await waitFor(() => expect((within(funding).getByRole("button", { name: "Save resource" }) as HTMLButtonElement).disabled).toBe(false));
    const exhibition = within(catalog).getByRole("article", { name: "Synthetic exhibition" });
    fireEvent.click(within(exhibition).getByRole("button", { name: "Express interest" }));
    expect((await within(exhibition).findByRole("button", { name: "Interest recorded" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(within(funding).getByRole("button", { name: "Start funding tracker" }));
    await screen.findByRole("region", { name: "My funding tracker" });
    await waitFor(() => expect(api.writes.at(-1)?.body).toEqual({ item_id: resource().id }));
    expect(api.writes[1].method).toBe("DELETE");
  });

  it("records every legal funding transition and preserves immutable displayed source and history", async () => {
    const api = mockApi({ initial: { ...emptyMine(), funding_cases: [fundingCase()] } });
    render(<KnowledgeWorkspace org={org} locale="en" />);
    const tracker = await screen.findByRole("region", { name: "My funding tracker" });
    const statuses = ["eligibility_check", "document_preparation", "applied", "under_review", "approved", "disbursed"];
    for (const [index, status] of statuses.entries()) {
      fireEvent.change(within(tracker).getByLabelText("Next status"), { target: { value: status } });
      fireEvent.change(within(tracker).getByLabelText("Reason for change"), { target: { value: `Reported step ${index + 1}` } });
      fireEvent.click(within(tracker).getByRole("button", { name: "Record progress" }));
      await waitFor(() => expect(api.writes.length).toBe(index + 1));
      await waitFor(() => expect(within(tracker).queryByDisplayValue(`Reported step ${index + 1}`)).toBeNull());
    }
    expect(within(tracker).queryByRole("button", { name: "Record progress" })).toBeNull();
    expect(within(tracker).getByText("This case has reached its final status.")).toBeTruthy();
    expect(within(tracker).getByText("Reported step 1")).toBeTruthy();
    expect(within(tracker).getByText("Reported step 6")).toBeTruthy();
    expect(api.writes.map((write) => write.body.expected_version)).toEqual([1, 2, 3, 4, 5, 6]);
    expect(api.writes.map((write) => write.body.status)).toEqual(statuses);
  });

  it("refreshes a stale case version without losing an entered reason and retries only on explicit save", async () => {
    const api = mockApi({ initial: { ...emptyMine(), funding_cases: [fundingCase()] }, conflict: true });
    render(<KnowledgeWorkspace org={org} locale="en" />);
    const reason = await screen.findByLabelText("Reason for change");
    fireEvent.change(reason, { target: { value: "Eligibility checked with the provider" } });
    fireEvent.click(screen.getByRole("button", { name: "Record progress" }));
    fireEvent.click(await screen.findByRole("button", { name: "Refresh funding tracker" }));
    await screen.findByText(words.en.refreshed);
    expect((screen.getByLabelText("Reason for change") as HTMLTextAreaElement).value).toBe("Eligibility checked with the provider");
    expect(api.writes.length).toBe(1);
    fireEvent.click(screen.getByRole("button", { name: "Record progress" }));
    await waitFor(() => expect(api.writes.at(-1)?.body.expected_version).toBe(2));
  });

  it.each([403, 422, 503])("preserves reason and avoids retries after a rejected %s write", async (status) => {
    const api = mockApi({ initial: { ...emptyMine(), funding_cases: [fundingCase()] }, status });
    render(<KnowledgeWorkspace org={org} locale="en" />);
    fireEvent.change(await screen.findByLabelText("Reason for change"), { target: { value: "Unsaved progress evidence" } });
    fireEvent.click(screen.getByRole("button", { name: "Record progress" }));
    await screen.findByText(status === 403 ? words.en.access : words.en.error);
    expect((screen.getByLabelText("Reason for change") as HTMLTextAreaElement).value).toBe("Unsaved progress evidence");
    expect(api.writes.length).toBe(1);
    expect((screen.getByRole("button", { name: "Record progress" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Refresh funding tracker" })).toBeTruthy();
  });

  it("recovers a committed status after a lost response without resubmitting or losing the entered reason", async () => {
    const api = mockApi({ initial: { ...emptyMine(), funding_cases: [fundingCase()] }, lostResponse: true });
    render(<KnowledgeWorkspace org={org} locale="en" />);
    fireEvent.change(await screen.findByLabelText("Reason for change"), { target: { value: "Provider eligibility verified" } });
    fireEvent.click(screen.getByRole("button", { name: "Record progress" }));
    const refresh = await screen.findByRole("button", { name: "Refresh funding tracker" });
    expect((screen.getByRole("button", { name: "Record progress" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(refresh); await screen.findByText(words.en.refreshed);
    expect((screen.getByLabelText("Reason for change") as HTMLTextAreaElement).value).toBe("Provider eligibility verified");
    expect((screen.getByLabelText("Next status") as HTMLSelectElement).value).toBe("document_preparation");
    expect(api.writes.length).toBe(1);
    const history = screen.getByText("Progress history").closest("details")!;
    expect(within(history).getByText("Provider eligibility verified")).toBeTruthy();
  });

  it("shows unavailable saved entries without content and keeps them removable", async () => {
    mockApi({ initial: { ...emptyMine(), saved_items: [{ item_id: resource().id, item: null, created_at: timestamp }] }, resources: [] });
    render(<KnowledgeWorkspace org={org} locale="en" />);
    await screen.findByText(words.en.unavailable);
    expect(screen.queryByText("Synthetic official program description")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Remove saved resource" }));
    await screen.findByText(words.en.noSaved);
  });

  it("keeps a second-page case draft through bookmark writes and catalog filters without reloading own lists", async () => {
    const first = fundingCase(); const second = fundingCase({ id: "55555555-5555-4555-8555-555555555555", item_title: "Second funding" });
    const reads: string[] = [];
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/session/csrf") return response({ csrf_token: "csrf" });
      if (init?.method === "POST" && url.includes("/saved/")) return response({ item_id: resource().id, item: resource(), created_at: timestamp });
      if (url.includes("/catalog")) return response({ items: [resource()], next_cursor: null });
      if (url.includes("/mine")) {
        reads.push(url);
        return response({ ...emptyMine(), funding_cases: url.includes("case_cursor=") ? [second] : [first], next_case_cursor: url.includes("case_cursor=") ? null : first.id });
      }
      throw new Error(`Unexpected request ${url}`);
    }));
    render(<KnowledgeWorkspace org={org} locale="en" />);
    const tracker = await screen.findByRole("region", { name: "My funding tracker" });
    fireEvent.click(within(tracker).getByRole("button", { name: "Load more" }));
    const caseCard = (await within(tracker).findAllByRole("article", { name: "Second funding" }))[0];
    fireEvent.change(within(caseCard).getByLabelText("Reason for change"), { target: { value: "Second page unsaved reason" } });
    const catalog = screen.getByRole("region", { name: words.en.title });
    fireEvent.click(within(catalog).getByRole("button", { name: "Save resource" }));
    await screen.findByText("Saved.");
    fireEvent.change(screen.getByLabelText("Search resources"), { target: { value: "program" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => expect((screen.getByRole("button", { name: "Apply filters" }) as HTMLButtonElement).disabled).toBe(false));
    expect((within(caseCard).getByLabelText("Reason for change") as HTMLTextAreaElement).value).toBe("Second page unsaved reason");
    expect(reads.length).toBe(2);
  });

  it("renders Tamil participant controls and terminal rejection without an actionable next state", async () => {
    mockApi({ initial: { ...emptyMine(), funding_cases: [fundingCase({ status: "rejected" })] } });
    render(<KnowledgeWorkspace org={org} locale="ta" />);
    await screen.findByText(words.ta.terminal); expect(screen.getByRole("heading", { name: words.ta.title })).toBeTruthy();
    expect(screen.queryByLabelText(words.ta.next)).toBeNull();
  });
});
