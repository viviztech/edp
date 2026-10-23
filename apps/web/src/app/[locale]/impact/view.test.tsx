import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import ImpactWorkspace from "./view";
import { words, type Mine, type RecordView } from "./content";
import { definition, enrollment, mine, org, record, response } from "./test-fixtures";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
function setup(initial = mine(), mode: "ok" | "lost" | "conflict" = "ok") {
  let data = initial; const writes: Record<string, unknown>[] = []; const reads: string[] = [];
  const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); if (url === "/api/session/csrf") return response({ csrf_token: "csrf" });
    if (!init?.method) { reads.push(url); return response(data); }
    const body = JSON.parse(String(init.body)) as Record<string, unknown>; writes.push(body);
    if (mode === "conflict" && writes.length === 1) { data = mine({ records: [record({ revision: 4, jobs_created: 9 })] }); return response({}, 409); }
    const result = record({ ...body as Partial<RecordView>, revision: Number(body.expected_revision) + 1 });
    data = { ...data, records: [result, ...data.records.filter((item) => item.id !== result.id)] };
    if (mode === "lost" && writes.length === 1) return Promise.reject(new Error("connection lost"));
    return response(result, 201);
  }); vi.stubGlobal("fetch", fetcher); return { writes, reads, setMine: (next: Mine) => { data = next; } };
}
async function fill() {
  const form = await screen.findByRole("form", { name: words.en.title });
  fireEvent.change(within(form).getByLabelText("Enrollment"), { target: { value: enrollment } });
  fireEvent.change(within(form).getByLabelText("Measurement definition"), { target: { value: definition().id } });
  fireEvent.change(within(form).getByLabelText("Observed on"), { target: { value: "2026-10-01" } });
  fireEvent.change(within(form).getByLabelText("Reason for this observation or correction"), { target: { value: "Initial evidence collected" } });
  return form;
}
describe("participant impact evidence", () => {
  it("records independent baseline evidence with an exact revision and request identity", async () => {
    const api = setup(); render(<ImpactWorkspace org={org} locale="en" />); const form = await fill();
    fireEvent.submit(form); await screen.findByText("Saved.");
    expect(api.writes).toHaveLength(1); expect(api.writes[0]).toMatchObject({ enrollment_id: enrollment, stage: "baseline", business_started: false, business_active: false, jobs_created: 0, expected_revision: 0 });
    expect(api.writes[0].request_id).toMatch(/^[a-f0-9-]{36}$/); expect(Object.keys(api.writes[0]).sort()).toEqual(["enrollment_id", "definition_id", "stage", "observed_on", "business_started", "business_active", "jobs_created", "reason", "expected_revision", "request_id"].sort());
    expect(api.reads.every((url) => url.includes("/impact/") && !url.includes("business"))).toBe(true);
  });
  it("pins archived editions on correction and appends the expected revision", async () => {
    const api = setup(mine({ definitions: [definition({ state: "archived" })], records: [record({ revision: 3 })] })); render(<ImpactWorkspace org={org} locale="en" />);
    fireEvent.click(await screen.findByRole("button", { name: "Correct this observation" })); const form = screen.getByRole("form", { name: words.en.title });
    expect((within(form).getByLabelText("Measurement definition") as HTMLSelectElement).disabled).toBe(true);
    expect((within(form).getByLabelText("Observed on") as HTMLInputElement).disabled).toBe(true);
    fireEvent.change(within(form).getByLabelText("Jobs created"), { target: { value: "2" } }); fireEvent.change(within(form).getByLabelText("Reason for this observation or correction"), { target: { value: "Corrected count from original notes" } });
    fireEvent.submit(form); await screen.findByText("Saved."); expect(api.writes[0]).toMatchObject({ expected_revision: 3, definition_id: definition().id, jobs_created: 2 });
  });
  it("recovers a lost response by explicitly repeating the same immutable request", async () => {
    const api = setup(mine(), "lost"); render(<ImpactWorkspace org={org} locale="en" />); const form = await fill(); fireEvent.submit(form);
    await screen.findByText(words.en.uncertain); expect((within(form).getByLabelText(words.en.reason) as HTMLTextAreaElement).value).toBe("Initial evidence collected");
    expect((within(form).getByLabelText("Jobs created") as HTMLInputElement).closest("fieldset")?.disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Recover request" })); await screen.findByText(words.en.recovered);
    expect(api.writes).toHaveLength(2); expect(api.writes[1]).toEqual(api.writes[0]);
  });
  it("refreshes a stale correction while preserving typed values and requires another explicit submit", async () => {
    const api = setup(mine({ records: [record()] }), "conflict"); render(<ImpactWorkspace org={org} locale="en" />);
    fireEvent.click(await screen.findByRole("button", { name: "Correct this observation" })); const form = screen.getByRole("form", { name: words.en.title });
    fireEvent.change(within(form).getByLabelText("Jobs created"), { target: { value: "5" } }); fireEvent.change(within(form).getByLabelText(words.en.reason), { target: { value: "My careful correction" } });
    fireEvent.submit(form); fireEvent.click(await screen.findByRole("button", { name: words.en.refresh })); await screen.findByText(words.en.refreshed);
    expect((within(form).getByLabelText("Jobs created") as HTMLInputElement).value).toBe("5"); expect((within(form).getByLabelText(words.en.reason) as HTMLTextAreaElement).value).toBe("My careful correction");
    expect(api.writes).toHaveLength(1); expect(api.reads.at(-1)).toContain(`enrollment_id=${enrollment}&stage=baseline&observed_on=2026-10-01`);
    fireEvent.submit(form); await screen.findByText("Saved."); expect(api.writes[1].expected_revision).toBe(4); expect(api.writes[1].jobs_created).toBe(5);
  });
  it("rejects active-without-started data and preserves local fields while paging evidence", async () => {
    const api = setup(mine({ record_next_cursor: record().id })); render(<ImpactWorkspace org={org} locale="en" />); const form = await fill();
    fireEvent.click(within(form).getByLabelText("Business is active")); fireEvent.submit(form); await screen.findByText(words.en.invalid); expect(api.writes).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Load more · Observation history" })); await waitFor(() => expect(api.reads.length).toBe(2));
    expect((within(form).getByLabelText(words.en.reason) as HTMLTextAreaElement).value).toBe("Initial evidence collected");
  });
  it("renders truthful empty states and Tamil controls without inventing definitions", async () => {
    setup(mine({ enrollments: [], definitions: [] })); render(<ImpactWorkspace org={org} locale="ta" />); await screen.findByText(words.ta.noEnrollments); expect(screen.getByText(words.ta.noneDefinitions)).toBeTruthy();
    expect((screen.getByRole("button", { name: words.ta.submit }) as HTMLButtonElement).disabled).toBe(true);
  });
});
