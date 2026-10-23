import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import ReportsWorkspace from "./view";
import { Comparison, Evidence } from "./evidence";
import { words, type Definition } from "../../impact/content";
import { dashboard, definition, job, org, response, snapshot, summary } from "../../impact/test-fixtures";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
function api({ lostSnapshot = false, definitions = [] as Definition[], staleDefinition = false } = {}) {
  const reads: string[] = []; const writes: { url: string; body: Record<string, unknown> }[] = [];
  let editions = definitions; let snapshotWrites = 0; let definitionWrites = 0;
  const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const path = url.split("?")[0];
    if (url === "/api/session/csrf") return response({ csrf_token: "csrf" });
    if (!init?.method) {
      reads.push(url);
      if (path.endsWith("/dashboard")) return response(dashboard());
      if (path.endsWith("/options")) return response({ programs: [{ id: "66666666-6666-4666-8666-666666666666", name_en: "Example program", name_ta: "திட்டம்", program_id: null }], cohorts: [{ id: "77777777-7777-4777-8777-777777777777", name_en: "Example cohort", name_ta: "குழு", program_id: "66666666-6666-4666-8666-666666666666" }], program_next_cursor: null, cohort_next_cursor: null });
      if (path.endsWith("/snapshots")) return response({ items: [summary()], next_cursor: null });
      if (path.includes("/snapshots/")) return response(snapshot());
      if (path.endsWith("/exports")) return response({ items: [], next_cursor: null });
      if (path.endsWith("/definitions")) return response({ items: editions, next_cursor: null });
      if (path.includes("/download/")) return Promise.resolve(new Response("metric,value\r\nexample,3\r\n", { headers: { "Content-Type": "text/csv" } }));
      throw new Error(`Unexpected read ${url}`);
    }
    const body = JSON.parse(String(init.body)) as Record<string, unknown>; writes.push({ url, body });
    if (path.endsWith("/snapshots")) { snapshotWrites += 1; if (lostSnapshot && snapshotWrites === 1) return Promise.reject(new Error("response lost")); return response(snapshot({ request_id: body.request_id as string })); }
    if (path.endsWith("/exports")) return response(job({ request_id: body.request_id as string }));
    if (path.endsWith("/access")) return response({ token: "a".repeat(43), expires_at: "2099-01-01T00:00:00Z" });
    if (path.includes("/definitions")) {
      definitionWrites += 1;
      if (staleDefinition && definitionWrites === 1) { editions = [definition({ state: "draft", version: 5 })]; return response({}, 409); }
      const item = path.endsWith("/publish") ? definition({ state: "published", version: Number(body.expected_version) + 1 }) : definition({ ...body as Partial<Definition>, state: "draft", version: 1, published_at: null }); editions = [item]; return response(item, 201);
    }
    throw new Error(`Unexpected write ${url}`);
  }); vi.stubGlobal("fetch", fetcher); return { reads, writes };
}

describe("reporting workspace", () => {
  it("compares matched impact evidence per edition and keeps absent editions unavailable", () => {
    const aggregate = { definition: definition(), eligible_enrollments: 2, baseline_reported: 2, outcome_reported: 1, matched_sample: 1, baseline_jobs: 3, outcome_jobs: 5, matched_baseline_jobs: 2, matched_outcome_jobs: 5, matched_jobs_change: 3, outcome_started: 1, outcome_active: 1, caveat_en: "Self-reported matched sample", caveat_ta: "சுய அறிக்கை மாதிரி" };
    const older = { ...aggregate, matched_outcome_jobs: 4, matched_jobs_change: 2 };
    const absent = { ...aggregate, definition: definition({ id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", edition: 2 }) };
    render(<Comparison current={dashboard({ impact: [aggregate, absent] })} previous={dashboard({ impact: [older] })} locale="en" />);
    const first = screen.getByRole("heading", { name: "Edition 1: Enterprise evidence" }).closest("article")!;
    const matchedRow = within(first).getByRole("row", { name: "Matched outcome jobs 5 4 1" }); expect(matchedRow).toBeTruthy();
    const second = screen.getByRole("heading", { name: "Edition 2: Enterprise evidence" }).closest("article")!;
    expect(within(second).getByRole("row", { name: "Matched outcome jobs 5 Unavailable Unavailable" })).toBeTruthy();
    expect(screen.getByText(words.en.comparisonCaveat)).toBeTruthy();
  });
  it("renders all seven groups with unavailable values, source definitions and explicit missing coverage", () => {
    render(<Evidence dashboard={dashboard({ eligible_impact_enrollments: 0, impact_coverage: null })} locale="en" />);
    for (const label of ["Marketing", "Program", "Learning", "Entrepreneurship", "Funding", "Support", "Impact"]) expect(screen.getByRole("heading", { name: label })).toBeTruthy();
    const funding = screen.getByRole("region", { name: "Funding" }); expect(within(funding).getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(within(funding).getByText("Exact funding amounts are not recorded.")).toBeTruthy(); expect(screen.getAllByText("Recorded source").length).toBe(7);
    expect(screen.getByText(words.en.noImpact)).toBeTruthy();
  });
  it("normalizes optional filters, resets a cohort when the program changes and rejects invalid windows", async () => {
    const service = api(); render(<ReportsWorkspace org={org} locale="en" canView canExport={false} canManage={false} />);
    await screen.findByRole("heading", { name: "Marketing" }); const form = screen.getByRole("form", { name: "Report filters" });
    fireEvent.change(within(form).getByLabelText("Cohort"), { target: { value: "77777777-7777-4777-8777-777777777777" } });
    expect((within(form).getByLabelText("Program") as HTMLSelectElement).value).toBe("66666666-6666-4666-8666-666666666666");
    fireEvent.change(within(form).getByLabelText("Program"), { target: { value: "" } }); expect((within(form).getByLabelText("Cohort") as HTMLSelectElement).value).toBe("");
    fireEvent.change(within(form).getByLabelText("From date"), { target: { value: "2026-10-20" } }); fireEvent.change(within(form).getByLabelText("Through date"), { target: { value: "2026-10-01" } });
    const before = service.reads.length; fireEvent.submit(form); await screen.findByText(words.en.invalid); expect(service.reads).toHaveLength(before);
    fireEvent.change(within(form).getByLabelText("From date"), { target: { value: "2026-10-01" } }); fireEvent.change(within(form).getByLabelText("Through date"), { target: { value: "2026-10-20" } }); fireEvent.submit(form);
    await waitFor(() => expect(service.reads.length).toBe(before + 1)); expect(service.reads.at(-1)).toContain("?from_date=2026-10-01&through_date=2026-10-20"); expect(service.reads.at(-1)).not.toContain("program_id=");
    expect(service.reads.some((url) => url.includes("/exports"))).toBe(false); expect(screen.getByText(words.en.exportUnavailable)).toBeTruthy();
  });
  it("freezes applied filters, recovers an uncertain snapshot with the same UUID and compares saved evidence", async () => {
    const service = api({ lostSnapshot: true }); render(<ReportsWorkspace org={org} locale="en" canView canExport canManage={false} />);
    await screen.findByRole("heading", { name: "Marketing" }); const filters = screen.getByRole("form", { name: "Report filters" });
    fireEvent.change(within(filters).getByLabelText("From date"), { target: { value: "2026-09-01" } });
    fireEvent.click(screen.getByRole("button", { name: words.en.freeze })); await screen.findByText(words.en.uncertain);
    expect(service.writes[0].body).toMatchObject({ from_date: "2026-10-01", through_date: "2026-10-20" });
    fireEvent.click(screen.getByRole("button", { name: words.en.recover })); await screen.findByText(words.en.recovered); expect(service.writes[1]).toEqual(service.writes[0]);
    expect((screen.getByLabelText(words.en.view) as HTMLSelectElement).value).toBe(snapshot().id);
    fireEvent.change(screen.getByLabelText(words.en.compare), { target: { value: snapshot().id } }); await screen.findByRole("heading", { name: words.en.comparison }); expect(screen.getByText(/Comparison evidence: 2026-10-01/)).toBeTruthy();
  });
  it("creates an aggregate export only from a snapshot and downloads through an undisplayed capability", async () => {
    const service = api(); const create = vi.fn().mockReturnValue("blob:report"); const revoke = vi.fn(); Object.defineProperty(URL, "createObjectURL", { configurable: true, value: create }); Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revoke });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<ReportsWorkspace org={org} locale="en" canView canExport canManage={false} />); await screen.findByRole("heading", { name: "Marketing" });
    expect((screen.getByRole("button", { name: words.en.exportCreate }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText(words.en.view), { target: { value: snapshot().id } }); await waitFor(() => expect((screen.getByLabelText(words.en.view) as HTMLSelectElement).value).toBe(snapshot().id));
    fireEvent.change(screen.getByLabelText(words.en.exportReason), { target: { value: "Program reporting review" } }); fireEvent.submit(screen.getByRole("form", { name: words.en.exports })); await screen.findByText(words.en.exportDone);
    expect(service.writes[0].body).toMatchObject({ snapshot_id: snapshot().id, reason: "Program reporting review" }); expect(service.writes[0].body.request_id).toMatch(/^[a-f0-9-]{36}$/);
    fireEvent.click(screen.getByRole("button", { name: words.en.download })); await screen.findByText(words.en.downloaded);
    expect(create).toHaveBeenCalledOnce(); expect(click).toHaveBeenCalledOnce(); expect(service.reads.at(-1)).toContain(`/download/${"a".repeat(43)}`); expect(document.body.textContent).not.toContain("a".repeat(43)); expect(document.querySelector(`a[href*="${"a".repeat(43)}"]`)).toBeNull();
  });
  it("allows definition management without fetching reports and explicitly publishes a bilingual edition", async () => {
    const service = api(); render(<ReportsWorkspace org={org} locale="en" canView={false} canExport={false} canManage />);
    await screen.findByText(words.en.noDefinitions); const form = screen.getByRole("form", { name: words.en.createDefinition });
    const fields = { "English title": "Enterprise evidence", "Tamil title": "தொழில் சான்று", "English definition": "Self-reported business activity and jobs", "Tamil definition": "சுய அறிக்கை தொழில் வேலைகள்", "Reason for definition change": "Approved local measurement policy" };
    for (const [label, value] of Object.entries(fields)) fireEvent.change(within(form).getByLabelText(label), { target: { value } }); fireEvent.submit(form); await screen.findByText("Saved.");
    const editionForm = screen.getByRole("form", { name: "Measurement definition 1" }); expect((within(editionForm).getByRole("button", { name: words.en.publish }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(within(editionForm).getByLabelText(words.en.definitionReason), { target: { value: "Policy reviewed for publication" } }); fireEvent.submit(editionForm);
    await waitFor(() => expect(service.writes.length).toBe(2)); expect(service.writes[1].body).toEqual({ expected_version: 1, reason: "Policy reviewed for publication" }); expect(service.reads.every((url) => url.includes("/impact/"))).toBe(true);
  });
  it("preserves a rejected publication reason through refresh without replaying the command", async () => {
    const service = api({ definitions: [definition({ state: "draft", version: 1 })], staleDefinition: true }); render(<ReportsWorkspace org={org} locale="en" canView={false} canExport={false} canManage />);
    const form = await screen.findByRole("form", { name: "Measurement definition 1" }); fireEvent.change(within(form).getByLabelText(words.en.definitionReason), { target: { value: "Retained publication reason" } }); fireEvent.submit(form);
    fireEvent.click(await screen.findByRole("button", { name: words.en.refreshDefinitions })); await waitFor(() => expect((within(form).getByRole("button", { name: words.en.publish }) as HTMLButtonElement).disabled).toBe(false));
    expect((within(form).getByLabelText(words.en.definitionReason) as HTMLTextAreaElement).value).toBe("Retained publication reason"); expect(service.writes).toHaveLength(1); fireEvent.submit(form);
    await waitFor(() => expect(service.writes.length).toBe(2)); expect(service.writes[1].body.expected_version).toBe(5);
  });
});
